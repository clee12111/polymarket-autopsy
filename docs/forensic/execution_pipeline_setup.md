> **Note:** This forensic document was extracted from the private working repo
> polymarket-vault for inclusion in the public autopsy. VPS IPs, personal wallet
> addresses, and internal paths have been redacted. The original document was
> written as an in-project working note, not for publication, and may reference
> internal context.
>
> Last updated in private repo: 2026-05-10

# Polymarket CLOB v2 Execution Setup

## Summary

- **Date debugged:** May 7, 2026
- **Total time:** 8+ hours across two sessions
- **Outcome:** Working order placement at 425ms total latency (316ms network + 109ms signing)
- **VPS:** Amsterdam (<AMSTERDAM_VPS_IP>) — 316ms RTT to CLOB
- **Package:** py-clob-client-v2==1.0.1rc1
- **Working combo:** POLY_1271 (sig_type=3) + Gnosis Safe funder + EOA-derived API key

---

## The Five Errors We Hit and What They Mean

### 1. "Could not create api key" (400 on POST /auth/api-key)

**What it means:** You tried to POST to `/auth/api-key` with `POLY_ADDRESS` set to a contract address (the deposit wallet/funder). The CLOB uses ECDSA ecrecover to validate L1 headers — it recovers the signing address from the signature and checks it matches `POLY_ADDRESS`. A contract address cannot sign with ECDSA, so ecrecover returns a different address and the header is invalid.

**What we tried:** Manually constructing L1 headers with `POLY_ADDRESS=funder`, hoping EIP-1271 would validate it.

**Actual cause:** CLOB L1 auth is pure ECDSA. EIP-1271 is only used for order signature verification, not API key creation.

**Fix:** Never set `POLY_ADDRESS` to a contract address. Always derive API keys with `POLY_ADDRESS=EOA`.

---

### 2. "the order signer address has to be the address of the API KEY"

**What it means:** The `signer` field in the submitted order does not match the address that the API key is registered to. For POLY_1271, the SDK sets `order.signer = funder` (via `_v2_order_signer()`). The CLOB looks up which address the API key belongs to and compares it to `order.signer`.

**What we tried:**
- Using deposit wallet (`0x5dE32BBF...`) as funder with derived EOA API key → funder ≠ EOA, mismatch
- FunderSigner patch (making `POLY_ADDRESS` header = funder) → didn't fix it; CLOB checks `order.signer` vs DB-registered key address, not the header
- Using Builder Code API key (`019e045b...`) with POLY_1271 → builder key was created for a different (old/leaked) wallet

**Actual cause:** The funder address being used (`0x5dE32BBF...`) was the undeployed deposit wallet, not the established Gnosis Safe. The Gnosis Safe (`<GNOSIS_SAFE_FUNDER_REDACTED>...`) IS registered in the CLOB system and the derived EOA key IS accepted for it.

**Fix:** Use the correct Gnosis Safe address as funder. Derive API key normally.

---

### 3. "maker address not allowed, please use the deposit wallet flow"

**What it means:** The `maker` field in the order is an address the CLOB does not allow for this account's sig_type combination. Seen with: EOA as maker (sig_type=0), Gnosis Safe as maker with sig_type=1 or 2.

**What we tried:**
- EOA mode (sig_type=0): EOA as maker → blocked
- POLY_PROXY (sig_type=1) with deposit wallet funder → blocked (deposit wallet address triggers "use deposit wallet flow" for non-3 sig_types)
- POLY_GNOSIS_SAFE (sig_type=2) with Gnosis Safe funder → blocked
- POLY_PROXY (sig_type=1) with Gnosis Safe funder → blocked

**Actual cause:** The account requires POLY_1271 (sig_type=3). Sig_types 0/1/2 are all rejected for this account's maker address combinations. Only POLY_1271 + correct Gnosis Safe funder passes.

**Fix:** Use POLY_1271 exclusively for this account type.

---

### 4. Builder Code API keys causing auth failures

**What it means:** Polymarket Settings shows multiple API key types. Builder Code keys (`019e045b...`) are for order attribution and volume tracking — they are NOT CLOB L2 trading credentials. Using them as `ApiCreds` causes either silent auth failures or "unauthorized" responses.

**What we tried:** Setting `CLOB_API_KEY` env var to the builder key, using it as `ApiCreds` with POLY_PROXY and POLY_1271 clients.

**Actual cause:** Builder key was created for a different wallet entirely (confirmed: `derived_key=47f5d8c4 ≠ builder_key=019e045b`). Even if the builder key were for this wallet, it routes to different CLOB endpoints.

**Fix:** Always call `client.derive_api_key()` from the current private key. Never use manually-copied keys from Settings for order placement.

---

### 5. Signature type sweep — all four types (0/1/2/3) failing simultaneously

**What it means:** When sweeping all sig_types with the wrong funder (deposit wallet `0x5dE32BBF...`):
- Sig_types 0/1/2: "maker address not allowed, please use the deposit wallet flow" (deposit wallet address requires POLY_1271)
- Sig_type 3 (POLY_1271): "order signer address has to be the address of the API KEY" (API key registered to EOA, `order.signer`=deposit wallet, mismatch)

**What we tried:** Full automated sweep of all four sig_types with deposit wallet as funder.

**Actual cause:** All failures stemmed from using the wrong funder address. The deposit wallet `0x5dE32BBF...` is undeployed and not registered in the CLOB. The Gnosis Safe `<GNOSIS_SAFE_FUNDER_REDACTED>...` is the actual trading address.

**Fix:** Identify the correct funder (Polymarket profile URL: `polymarket.com/@0x...`) before sweeping.

---

## The Key Insights

### 1. Polymarket has multiple wallet types that look similar but are NOT interchangeable

| Sig Type | Name | order.maker | order.signer | When to use |
|----------|------|-------------|--------------|-------------|
| 0 | EOA | EOA | EOA | Pure MetaMask, no proxy |
| 1 | POLY_PROXY | funder | EOA | Old Magic Link proxy (largely deprecated) |
| 2 | POLY_GNOSIS_SAFE | funder | EOA | Gnosis Safe multisig |
| 3 | POLY_1271 | funder | funder | Magic Link / email accounts post-2024 |

For POLY_1271 specifically: `_v2_order_signer()` in the SDK returns `self.funder`, making both maker and signer = funder. The EOA signs the EIP-712 message, but the Gnosis Safe contract verifies it via EIP-1271 (`isValidSignature`).

### 2. The Settings page shows multiple addresses that mean different things

For Magic Link / email login accounts, there are THREE addresses:

| Address | Where to find it | Role |
|---------|-----------------|------|
| EOA | `reveal.magic.link/polymarket` → export private key | Signs orders. Your private key controls this. |
| Gnosis Safe proxy | `polymarket.com/@0x...` profile URL | **Actual trading address. Use as `funder`.** |
| Deposit wallet | Settings → Deposit | New system, may be undeployed. NOT for trading yet. |

**The deposit wallet shown in Settings is a red herring for pre-existing accounts.** Your real trading address is the Gnosis Safe visible in your profile URL.

### 3. Builder Code API keys are NOT CLOB trading API keys

Polymarket Settings shows three different API key sections:

| Key type | Purpose | Use for orders? |
|----------|---------|-----------------|
| Builder Code | Order attribution, volume tracking | No |
| Relayer API key | Gas-free on-chain transactions | No |
| CLOB API key | Order placement | Yes — derive via SDK, don't copy |

CLOB API keys are never shown in Settings. Always derive them: `client.derive_api_key()` from your private key.

### 4. Library version matters critically

```bash
# WRONG — stable release, missing deposit wallet flow support
pip install py-clob-client-v2

# CORRECT
pip install 'py-clob-client-v2==1.0.1rc1' --break-system-packages
pip show py-clob-client-v2 | grep Version
# Must show: Version: 1.0.1rc1
```

### 5. Geographic restrictions

The Polymarket CLOB blocks US IPs and rejects the Frankfurt VPS (<FRANKFURT_VPS_IP>). Amsterdam VPS (<AMSTERDAM_VPS_IP>) is the confirmed working execution node. Do not run live execution from US-based IPs or Frankfurt. See Geographic Optimization Tests section for full details.

---

## Working Configuration

```python
import os, time
from py_clob_client_v2 import ClobClient, MarketOrderArgs, OrderType, PartialCreateOrderOptions
from py_clob_client_v2.order_builder.builder import SignatureTypeV2
from py_clob_client_v2.order_builder.constants import BUY

CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID  = 137
EOA_KEY   = os.environ["POLY_PRIVATE_KEY"]                # from reveal.magic.link/polymarket
FUNDER    = "<GNOSIS_SAFE_FUNDER_REDACTED>"  # Gnosis Safe — polymarket.com/@0x...

# Step 1: Derive CLOB API creds — once per session (~50ms)
bare  = ClobClient(host=CLOB_HOST, chain_id=CHAIN_ID, key=EOA_KEY)
creds = bare.derive_api_key()

# Step 2: Build trading client — REUSE this object for all orders
client = ClobClient(
    host=CLOB_HOST,
    chain_id=CHAIN_ID,
    key=EOA_KEY,
    creds=creds,
    signature_type=SignatureTypeV2.POLY_1271,  # sig_type=3
    funder=FUNDER,
)

# Step 3: Place FAK market order with latency breakdown
TOKEN_ID  = "..."    # from Gamma API discovery
TICK_SIZE = "0.01"  # must match market tick size exactly

t_build = time.perf_counter()
signed  = client.create_market_order(
    order_args=MarketOrderArgs(
        token_id=TOKEN_ID,
        side=BUY,
        amount=1.0,  # USDC to spend (BUY side uses amount in USDC)
        order_type=OrderType.FAK,
    ),
    options=PartialCreateOrderOptions(tick_size=TICK_SIZE, neg_risk=False),
)
build_ms = (time.perf_counter() - t_build) * 1000

t_post  = time.perf_counter()
resp    = client.post_order(signed, order_type=OrderType.FAK)
net_ms  = (time.perf_counter() - t_post) * 1000

print(f"build={build_ms:.0f}ms  net={net_ms:.0f}ms")
# Successful response shape:
# {"errorMsg":"","orderID":"0x...","status":"matched","success":true,"transactionsHashes":["0x..."]}
```

### BTC 5-min market discovery

```python
import urllib.request, json
from datetime import datetime

GAMMA_API = "https://gamma-api.polymarket.com/markets"

def find_btc_market():
    now_s = int(time.time())
    for offset in [0, 1, -1, 2]:
        w_ts = (now_s // 300 + offset) * 300
        if w_ts < now_s - 60:
            continue
        slug = f"btc-updown-5m-{w_ts}"
        try:
            req = urllib.request.Request(
                f"{GAMMA_API}?slug={slug}",
                headers={"User-Agent": "bot/1.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
        except Exception:
            continue
        if not data:
            continue
        m         = data[0]
        end_ts    = datetime.fromisoformat(m["endDate"].replace("Z", "+00:00")).timestamp()
        secs_left = end_ts - time.time()
        if secs_left < 10:
            continue
        token_ids = json.loads(m.get("clobTokenIds") or "[]")
        prices    = [float(p) for p in json.loads(m.get("outcomePrices") or "[]")]
        tick_val  = float(m.get("orderPriceMinTickSize") or 0.01)
        return [str(t) for t in token_ids], prices, tick_val, secs_left
    return None, None, None, None

token_ids, prices, tick_val, secs_left = find_btc_market()
# Pick cheaper side
side_name, token_id = ("Up", token_ids[0]) if prices[0] <= prices[1] else ("Down", token_ids[1])
tick_str = (
    "0.0001" if tick_val <= 0.0001 else
    "0.001"  if tick_val <= 0.001  else
    "0.01"   if tick_val <= 0.01   else
    "0.1"
)
```

---

## Latency Baseline (Amsterdam → CLOB, May 7 2026)

| Run | Sign/build [A] | Network POST [B] | Total order | Script wall |
|-----|---------------|-----------------|-------------|-------------|
| Cold (first run) | 4,075ms | 899ms | 4,974ms | 6,042ms |
| Warm (reused client) | 109ms | 316ms | 425ms | 1,211ms |

**316ms is the Amsterdam→CLOB network baseline.** The cold-start 4s signing cost is EIP-712 domain initialization — fully amortized when the client object is reused across orders.

The 1,211ms script wall time on warm run includes:
- ~47ms derive_api_key (network call, once)
- ~80ms Gamma API market discovery
- ~109ms sign/build
- ~316ms network POST
- ~659ms Python startup overhead

---

## WebSocket Price Feed Audit (May 7 2026)

### Investigation result: feed was already WebSocket-based

`clob_depth_logger_v2.py` connects to `wss://ws-subscriptions-clob.polymarket.com/ws/market` with one persistent WebSocket per active market — it has never been a REST poller. The pre-fix p50=2,534ms staleness was entirely from a write-buffer bug (FLUSH_EVERY_S=5.0), not polling. That bug was fixed on Day 21.

### Bugs found and fixed (May 7 2026)

**Bug 1 — WS_READ_TIMEOUT=15s caused reconnect storm.**
`asyncio.wait_for(ws.recv(), timeout=15)` fires on quiet markets with no price changes for 15s, even though `ping_interval=20` keeps the TCP connection alive. Result: 51 reconnects in 27 minutes, constant 3s data gaps, 19k noisy health-log lines.
- Fix: `WS_READ_TIMEOUT = 120` — health monitor's TICK_STALE_WARN=60s now handles genuine staleness.
- Before/after: 51 reconnects/27min → 0 in 5+ minutes post-fix.

**Bug 2 — Subscription message format non-standard.**
Was sending `{"type": "subscribe", "assets_ids": tokens}`. Correct initial format: `{"type": "market", "initial_dump": true, "level": 2, "custom_feature_enabled": true}`.
- Fix: Updated subscription payload. `custom_feature_enabled: true` enables `best_bid_ask` push events.

**Bug 3 — price_change events had empty bids/asks; market_prices not updated.**
`price_change` events carry no orderbook data. The stored prices in `market_prices` were not updated until the next full `book` snapshot arrived — meaning every non-book tick reflected stale prices. `best_bid_ask` events (now enabled) carry the current best bid/ask and update `market_prices` inline immediately when a price changes.
- Fix: Handle `best_bid_ask` event type in ws_handler; update `market_prices` directly on receipt.

**Bug 4 (pre-existing, surfaced by Bug 3) — yes_mid/no_mid wrong for non-book ticks.**
`yes_mid = best_mid(bids, asks)` returned 0.5 whenever bids/asks were empty (all price_change and best_bid_ask events). At a price like bid=0.64/ask=0.65, bots were reading yes_mid=0.5 instead of 0.645 — a 14-cent mid error propagating to edge calculations. Affected ~75% of records before fix.
- Fix: Compute `yes_mid`/`no_mid` from `market_prices` (always current), not from bids/asks.
- After fix: 0 bad yes_mid records in 300-record sample.

### Post-fix data latency pipeline

```
Polymarket price change
  → WS best_bid_ask push received         ~40ms  (Frankfurt ↔ CLOB)
  → market_prices updated inline           ~0ms
  → flush to clob_depth_log.jsonl         ≤20ms  (FLUSH_EVERY_S=0.02)
  → bot reads file (LOOP_INTERVAL=0.10)  0–100ms
─────────────────────────────────────────────────
Total price-change-to-bot: ~40–160ms
```

Staleness measurement (120 samples, 100ms cadence, post-fix): p50=191ms, p90=623ms, p95=924ms. High p95 reflects genuine market quiet periods (no price changes for several seconds), not system delay.

---

## Geographic Optimization Tests

Tested May 7, 2026 to determine whether VPS location meaningfully reduces POST latency.

### Results

| VPS | Location | RAM | Warm POST latency | Notes |
|-----|----------|-----|-------------------|-------|
| Amsterdam (<AMSTERDAM_VPS_IP>) | AMS | 1 GB | **386ms** | Working baseline |
| Toronto test node | YYZ | 512 MB | 504ms | Slower — RAM constraint, not geography |
| Frankfurt (<FRANKFURT_VPS_IP>) | FRA | 8 GB | N/A | Geo-blocked (Polymarket CLOB rejects) |
| US-East | IAD/EWR | — | N/A | Geo-blocked |

### Key Finding

**Polymarket sits behind Cloudflare. Network POST latency is dominated by the Cloudflare-edge → CLOB-backend hop (~280–330ms), not the VPS-to-edge hop (~5ms).** Geographic location of VPS does NOT meaningfully reduce POST latency. All external traders route through the same Cloudflare → backend path regardless of where their VPS sits.

The Toronto result (504ms vs 386ms Amsterdam) is explained by RAM: 512 MB forces paging during EIP-712 signing/building, adding ~118ms. Not a geographic effect.

### Conclusion

**Amsterdam is the final execution VPS.** The 386ms warm latency (or ~354ms with pre-signing) is the realistic floor for an external trader. There is no geographic shortcut.

### What Works vs What Doesn't

| Optimization | Effect | Notes |
|---|---|---|
| Persistent client object | Eliminates 4s cold start | Do this — mandatory |
| Pre-cache derived API creds | Saves ~50ms | Do this — cheap |
| Pre-sign orders during prior tick | Eliminates ~32ms from hot path | Do this — removes build latency |
| Adequate VPS RAM (1 GB+) | Avoids sign/build paging | Do this — Toronto proved 512 MB too slow |
| VPS geographic relocation | No meaningful effect | All routes hit same Cloudflare → backend |
| Smaller/cheaper VPS | Slower if RAM-constrained | 512 MB demonstrated ~118ms penalty |

### Final Production Stack

- **Amsterdam VPS (<AMSTERDAM_VPS_IP>):** live execution (1 GB+ RAM required)
- **Frankfurt VPS (<FRANKFURT_VPS_IP>):** paper fleet, Binance logger, CLOB depth logger
- **Data flow:** live bot on Amsterdam reads market data from Frankfurt via SSH/SCP/rsync, OR runs its own local Binance + CLOB loggers

---

## Optimizations for Live Bot

1. **Reuse client object** — create once on startup, reuse for all orders. The 4s cold-start cost is one-time.
2. **Cache derived API creds** — call `derive_api_key()` once on startup, store result. Costs ~50ms each time if re-called.
3. **Pre-discover market token_ids** — run discovery loop in background; keep current window's token_ids cached so you don't pay the Gamma API RTT at fire time.
4. **Pre-sign orders during prior tick** — build/sign during the tick before fire condition triggers; POST immediately on signal. Eliminates ~32ms from hot path. (Geographic relocation does NOT reduce latency — see Geographic Optimization Tests above.)
5. **HTTP/2 connection reuse** — httpx with `http2=True` (SDK default) keeps connection warm; don't recreate `httpx.Client` per order.
6. **Adequate VPS RAM** — use 1 GB+ minimum. 512 MB causes sign/build paging; demonstrated +118ms penalty on Toronto test.

---

## Debugging Workflow for Future Errors

```
1. Check py-clob-client-v2 version:
   pip show py-clob-client-v2 | grep Version   # must be 1.0.1rc1

2. Derive fresh creds and print:
   bare = ClobClient(host=CLOB_HOST, key=key, chain_id=137)
   print(f"EOA: {bare.get_address()}")
   creds = bare.derive_api_key()
   print(f"API key: {creds.api_key[:8]}...")

3. For any order failure, print maker/signer/api_key:
   print(f"order.maker   = {client.builder.funder}")
   # POLY_1271 → order.signer = funder; types 0/1/2 → order.signer = EOA
   print(f"api_key addr  = {bare.get_address()}")

4. Error → cause mapping:
   "maker address not allowed"           → wrong funder address or wrong sig_type
   "signer must match API key"           → wrong funder (usually deposit wallet vs Gnosis Safe)
   "Invalid L1 Request headers" (401)    → trying POLY_ADDRESS=contract in L1 headers; don't do this
   "Unauthorized" / "Invalid api key"    → using Builder Code key instead of derived CLOB key

5. If all sig_types fail:
   - The funder address is wrong. Go to polymarket.com → your profile → copy the 0x... in the URL.
   - That is the Gnosis Safe. Use it as funder with POLY_1271.

6. Sweep confirmation pattern (use only for diagnosis):
   for sig_type in [3, 2, 1, 0]:
       try client with that sig_type, print maker/signer/error
```

---

## What NOT to Do

| Don't | Why |
|-------|-----|
| Use deposit wallet address from Settings as funder | Undeployed for pre-existing accounts; causes all sig types to fail |
| Use Builder Code API keys for order placement | Different system; key registered to different wallet |
| Use Relayer API keys for CLOB order placement | Different system; for gas-free on-chain ops only |
| Copy API keys from Settings | CLOB keys aren't shown in Settings; derive them via SDK |
| Install py-clob-client-v2 without pinning version | Default stable (1.0.0) lacks deposit wallet flow |
| Set POLY_ADDRESS=funder in L1 headers | CLOB uses ecrecover, not EIP-1271, for L1 auth; always 401 |
| Recreate the client object on every order | Causes 4s cold-start signing penalty each time |
| Run from US IPs | Geographic block; use Amsterdam VPS only |
| Assume Frankfurt reduces latency | Frankfurt is geo-blocked for live execution; geographic location of VPS has no effect on POST latency anyway |
| Use 512 MB VPS for execution | RAM-constrained signing adds ~118ms; use 1 GB+ |

---

## Wallet Security Notes

- Private keys leaked in chat must be rotated immediately via Magic Link (Settings → Export Private Key → Rotate)
- Always use environment variables: `export POLY_PRIVATE_KEY="0x..."` — never hardcode in scripts
- Use `read -s POLY_PRIVATE_KEY && export POLY_PRIVATE_KEY` to suppress echo; terminal appears to hang — paste key and press Enter
- Never log or print the full private key; print only the last 6 chars for identification: `key[-6:]`
- Funder/proxy address is public info — safe to log and hardcode
- Don't paste keys in analysis sessions, Slack, or shared terminals
- SSH sessions started by Claude do NOT inherit environment variables set in your interactive shell; always set keys in the same session where scripts run
