> **Note:** This forensic document was extracted from the private working repo
> polymarket-vault for inclusion in the public autopsy. VPS IPs, personal wallet
> addresses, and internal paths have been redacted. The original document was
> written as an in-project working note, not for publication, and may reference
> internal context.
>
> Last updated in private repo: 2026-05-10

# gross_pnl_proxy Bug — Root Cause, Blast Radius, Day 17 Plan
**Date:** 2026-05-04 (Day 16)  
**Status:** CONFIRMED BUG. All prior fleet metrics invalid. No code changes tonight.  
**Author:** Day 16 investigation session

---

## 1. Bug Summary

### The formula (identical across all bots, all versions V3–V8)

```python
# Bots/crypto_paper_*/paper_trader_*.py  (line ~199 in each)
def _gross_pnl_proxy(tracker, proxy: str) -> float:
    """Estimate PnL at resolution. Assumes avg fill ~0.50. Not for accounting."""
    if tracker.total_exposure == 0:
        return 0.0
    if proxy == "YES":
        return float(tracker.net_yes_usdc) - float(tracker.net_no_usdc)
    else:
        return float(tracker.net_no_usdc) - float(tracker.net_yes_usdc)
```

Found in every active bot's paper_trader file:
- `Bots/crypto_paper_v6_5/paper_trader_v6_5.py:199`
- `Bots/crypto_paper_v6_5_latency/paper_trader_v6_5_latency.py:199`
- `Bots/crypto_paper_v6b/paper_trader_v6b.py:199`
- `Bots/crypto_paper_v6b5/paper_trader_v6b5.py:199`
- `Bots/crypto_paper_v6b5_nohedge/paper_trader_v6b5_nohedge.py:199`
- `Bots/crypto_paper_v6_v5_lat_82/paper_trader_v6_v5_lat_82.py:183`
- `Bots/crypto_paper_v6_v5_lat_87/paper_trader_v6_v5_lat_87.py:183`
- `Bots/crypto_paper_v6_5_lat_size/paper_trader_v6_5_lat_size.py:192`
- Also present in archived bots: v3, v4, v5c, v5c_latency, v6, v6_latency, v6_4, v6_4_latency, v6b_slip

### What `net_yes_usdc` and `net_no_usdc` track

```python
# Bots/crypto_paper_v6_5/state_v6_5.py:391
def record_trade(self, side: str, usdc: float, ...) -> None:
    if side == "YES":
        self.net_yes_usdc += usdc   # cumulative USDC cost of YES entries
    else:
        self.net_no_usdc  += usdc   # cumulative USDC cost of NO entries
    self.total_exposure += usdc
```

For MOM_ADD: `usdc = main_shares × fill_price` (token cost basis)  
For HEDGE: `usdc = _hedge_size_to_target(HEDGE_TARGET_NET)` (USDC amount to reduce net_position to target)  
For TAIL_SWEEP: `usdc = tail_shares × sweep_price` (token cost basis)

### What the proxy computes vs what it should compute

**Proxy computes:**  
`proxy = (USDC spent on winning side) − (USDC spent on losing side)`

This is the **net cost differential** between the two sides.

**True economic P&L:**  
`true_pnl = (winning_shares × $1.00) − total_usdc_cost_both_sides`  
`         = winning_side_shares − net_yes_usdc − net_no_usdc`

**The gap:**  
`proxy − true = (net_winning_usdc − net_losing_usdc) − (winning_shares − net_winning_usdc − net_losing_usdc)`  
`             = 2 × net_winning_usdc − winning_shares`  
`             = winning_shares × (2×price − 1)`

At price=0.50: proxy = true (coincidence). Above 0.50: proxy inflates wins. Below 0.50: proxy deflates wins.

**In words:** The proxy treats USDC cost as a proxy for profit. When you buy a winning token at 80c, you spent 80% of eventual payout. Proxy counts the entire cost as "profit from the winning side." True profit is only 20% of payout. The proxy overstates the win by 4×.

---

## 2. Verified Test Cases

### Test Case 1 — The original verified window (V6_5, 03:45-03:50 UTC, YES resolves)

```
Fire: FILL_MOMENTUM_ADD  NO   25sh @0.66   cost=$16.50   Lost  pnl=-$16.52
Fire: FILL_HEDGE         YES  29sh @0.465  cost=$13.49   Won   pnl=+$15.49
Fire: TAKE_TAIL_SWEEP    NO    5sh @0.89   cost=$4.45    Lost  pnl=-$4.49

net_yes_usdc = $25.08    net_no_usdc = $0.00
PROXY (net_yes - net_no):    +$25.08
CORRECTED (fire-level):       -$5.51
DISCREPANCY:                 +$30.59  (proxy over-reports by $30.59)
```

*Proxy note: net_yes_usdc=25.08 reflects the large HEDGE firing BEFORE the smaller MOMENTUM_ADD — the tracker accumulates net_yes from the hedge sizing calculation, not shares×price.*

### Test Case 2a — V6b5_nohedge (11:30-11:35 UTC, NO resolves)

```
Fire: TAKE_TAIL_SWEEP    NO    5sh @0.89   cost=$4.45    Won   pnl=+$0.52
Fire: TAKE_MOMENTUM_ADD  NO   24sh @0.82   cost=$19.68   Won   pnl=+$4.07
Fire: TAKE_TAIL_SWEEP    NO    5sh @0.85   cost=$4.25    Won   pnl=+$0.70

net_no_usdc = $38.22    net_yes_usdc = $0.00
PROXY (net_no - net_yes):    +$38.22
CORRECTED (fire-level):       +$5.28
DISCREPANCY:                 +$32.94  (all wins, but proxy counts cost as profit)
```

### Test Case 2b — V6b5_nohedge (11:45-11:50 UTC, YES resolves)

```
Fire: TAKE_MOMENTUM_ADD  YES  24sh @0.79   cost=$18.96   Won   pnl=+$4.75
Fire: TAKE_MOMENTUM_ADD  YES  24sh @0.76   cost=$18.24   Won   pnl=+$5.45

net_yes_usdc = $20.52    net_no_usdc = $0.00
PROXY (net_yes - net_no):    +$20.52
CORRECTED (fire-level):      +$10.20
DISCREPANCY:                 +$10.32  (proxy 2× correct value)
```

### Test Case 3 — V6b BIAS-active window (03:25-03:30 UTC, NO resolves)

```
Fire: TAKE_BIAS_PIVOT    YES  35sh @0.54   cost=$18.90   Lost  pnl=-$19.53
Fire: TAKE_MOMENTUM_ADD  NO   24sh @0.71   cost=$17.04   Won   pnl=+$6.60

net_no_usdc = $13.35    net_yes_usdc = $0.00
PROXY (net_no - net_yes):    +$13.35
CORRECTED (fire-level):      -$12.92
DISCREPANCY:                 +$26.27  (proxy shows win, reality is large loss)
```

**Test Case 3 is the most damaging finding:** A window where we LOST $12.92 economically (YES bet lost, NO won partially) is reported as a +$13.35 win by the proxy. The proxy doesn't just overstate magnitude — it **flips the sign** on windows with mixed-side positions where the losing side was larger.

---

## 3. Corrected Formula Spec

```python
# Fee function (analysis-only for now — do not change live bots tonight)
def calculate_fee(shares: float, price: float, is_taker: bool) -> float:
    if is_taker:
        return shares * 0.072 * price * (1.0 - price)
    else:
        return shares * 0.0008   # flat maker approx; true rebate TBD

# Action → (zone_label, is_taker) mapping
ACTION_MAP = {
    "TAKE_BIAS_PIVOT":   ("BIAS",    True),
    "TAKE_MOMENTUM_ADD": ("MOM_ADD", True),
    "FILL_MOMENTUM_ADD": ("MOM_ADD", False),
    "TAKE_TAIL_SWEEP":   ("TAIL",    True),
    "FILL_HEDGE":        ("HEDGE",   False),
}

# Per-fire P&L
def fire_pnl(shares, price, is_taker, side, window_resolution):
    fee = calculate_fee(shares, price, is_taker)
    won = (side == window_resolution)
    if won:
        return shares - shares * price - fee   # recover $1/share, net of cost and fee
    else:
        return -shares * price - fee           # lose cost + fee

# Window economic P&L
def window_pnl_economic(fires, window_resolution):
    return sum(fire_pnl(f.shares, f.price, f.is_taker, f.side, window_resolution)
               for f in fires)
```

**Validated against all 4 test cases above. Spec locked.**

**Key assumption:** `fill_price` in logs is the TOKEN price paid (YES price for YES entries, NO token price for NO entries). NOT the YES market price for all entries. Evidence: FILL_MOMENTUM_ADD NO@0.66 with sh=25 → cost=16.50 means 25 NO tokens at 0.66 each.

**Maker fee caveat:** `shares × 0.0008` is an approximation. Actual maker rebate on Polymarket may differ. Fee contributions are small (~2% of total discrepancy). Not the primary issue.

---

## 4. Refactor Scope

### Files where `_gross_pnl_proxy` is computed (bot code — do NOT touch tonight)

```
Bots/crypto_paper_v6_5/paper_trader_v6_5.py:199          → active
Bots/crypto_paper_v6_5_latency/paper_trader_v6_5_latency.py:199  → active
Bots/crypto_paper_v6b/paper_trader_v6b.py:199             → active
Bots/crypto_paper_v6b5/paper_trader_v6b5.py:199           → active
Bots/crypto_paper_v6b5_nohedge/paper_trader_v6b5_nohedge.py:199  → active
Bots/crypto_paper_v6_v5_lat_82/paper_trader_v6_v5_lat_82.py:183  → active
Bots/crypto_paper_v6_v5_lat_87/paper_trader_v6_v5_lat_87.py:183  → active
Bots/crypto_paper_v6_5_lat_size/paper_trader_v6_5_lat_size.py:192 → active
Bots/crypto_paper_v8/paper_trader_v8.py:201               → inactive (exists, not deployed)
[+5 archived bots: v3, v4, v5c, v5c_latency, v6, v6_latency, v6_4, v6_4_latency, v6b_slip]
```

All share identical `_gross_pnl_proxy` function body. Single fix propagates to all via copy.

### Files that READ gross_pnl_proxy from CSV logs

```
~/polymarket-vault/vault_metrics.py         — fleet metrics script (session tool)
~/polymarket-vault/lat_size_analysis.py     — lat_size analysis (session tool)
~/polymarket-vault/zone_decomp.py           — zone decomp (already uses corrected formula)
Bots/crypto_paper_v6_5/logger_v6_5.py:52 — logs it, doesn't compute
[+ all other logger_*.py files]
Tools/v5c_fill_rate_monitor.py            — NO dependency (confirmed)
```

### Recommendation: Option (b) — Add parallel column

**Add `window_pnl_economic` alongside `gross_pnl_proxy`. Do NOT replace.**

Reasoning:
- `gross_pnl_proxy` is already in all historical CSV data — replacing it breaks backwards reading of archives
- Adding a parallel column preserves the proxy for any downstream use, adds correct value
- Simpler rollout: add one field to `log_window_close()`, add one computation at window close time
- The proxy may still be useful as a live-session signal proxy (correlates directionally even if magnitude wrong) — keep it
- The economic column becomes the authoritative metric for all analysis going forward

**Column name:** `window_pnl_economic`  
**Location to add:** `log_window_close()` call in each `paper_trader_*.py`, computed using the corrected formula applied to the window's accumulated fire list

**Implementation requires:**
1. Bot must accumulate per-fire records during the window (list of dicts: shares, price, is_taker, side)
2. At WINDOW_CLOSE, iterate fires, compute corrected P&L, write to CSV
3. Clear fire list for next window

---

## 5. Affected Metrics

All of the following are proxy-derived and should be treated as INVALID until recalculated:

### Fleet metrics (all bots, all prior sessions)
- Window WR (per bot) — proxy sign errors mean some "wins" are actual losses
- Total PnL (per bot) — all are inflated; true values are negative (see zone decomp)
- EV/win, EV/window — all proxy-based
- The "V6_5 +$1,391" and "V6_5_lat +$1,258" numbers from prior sessions
- All Day 13–16 fleet metrics tables in CLAUDE.md and handoff docs

### Decisions that depended on proxy metrics
- **V6 deployed over V5c**: based on higher proxy EV. Valid directionally (V6 does appear better), but magnitude comparison wrong
- **V6b5_nohedge vs V6b5 comparison**: showed nohedge worse. Corrected: still worse, but gap different
- **TAIL_SWEEP contribution**: proxy couldn't reveal it was destroying value — now confirmed by corrected analysis
- **HEDGE value confirmation**: proxy was accidentally showing HEDGE as positive in some bots — corrected analysis confirms positive (at 0.465-0.480 only), so this conclusion survives
- **Live capital gate "N=100 at 68% WR"**: the 68% WR target is proxy-window-level. Corrected metric should be `window_pnl_economic > 0` for a resolved window. The gate criteria needs restatement

### Backtest results
- All backtests using `gross_pnl_proxy` as the PnL signal are suspect
- Specifically: v5c_bimodal_results.md, v4_no_prequeue_backtest.md, v3_july_oct_research_backtest.md, CROSSING_LOOKBACK sweep

### Analysis scripts (session-time tools)
- `~/polymarket-vault/vault_metrics.py` — reports proxy metrics as if real
- `~/polymarket-vault/lat_size_analysis.py` — same
- Any script using `gross_pnl_proxy` field from WINDOW_CLOSE rows as a PnL signal

---

## 6. Files Needing Update

| File | Change Needed | Priority |
|---|---|---|
| `Bots/crypto_paper_v6_5/paper_trader_v6_5.py` | Add fire accumulator + `window_pnl_economic` to log_window_close | P0 Day 17 |
| [same for all 7 other active bots] | Same change | P0 Day 17 |
| `Bots/crypto_paper_v6_5/state_v6_5.py` | Add `fire_log = []` and `fire_log.append(fire)` in record_trade | P0 Day 17 |
| [same for all other state files] | Same | P0 Day 17 |
| `~/polymarket-vault/vault_metrics.py` | Replace `gross_pnl_proxy` reads with `window_pnl_economic` | P1 Day 17 |
| `Strategy/zone_decomposition_day16.md` | Already uses corrected formula — no update needed | Done |
| `CLAUDE.md` | Flag all prior EV/PnL numbers as proxy-based | P1 Day 17 |
| Handoff docs | Add INVALIDATED METRICS note | P1 Day 17 |
| Backtest harness (if exists as script) | Audit for proxy dependency | P2 Day 18 |

---

## 7. Day 17 Plan

### Stage 1 — Fix one bot, validate (60 min)

1. Pick V6b5_nohedge (simplest: no BIAS, no HEDGE fires, cleanest fire attribution)
2. In `state_v6b5_nohedge.py`: add `self.fire_log = []` to `__init__`, add `self.fire_log.append({...})` in `record_trade`
3. In `paper_trader_v6b5_nohedge.py`: at WINDOW_CLOSE, compute `window_pnl_economic` from `fire_log`, clear list
4. In `logger_v6b5_nohedge.py`: add `window_pnl_economic` column
5. Kill and restart V6b5_nohedge only
6. Wait 3 windows (15 min), verify: `window_pnl_economic` column present, values match manual calculation for 2 windows
7. Compare `window_pnl_economic` vs `gross_pnl_proxy` in same rows — confirm discrepancy matches expected pattern

### Stage 2 — Roll out to remaining 7 bots (90 min)

8. Once Stage 1 passes, apply identical change to all 7 remaining bots
9. Kill/restart each one-at-a-time with 5-min gaps to avoid simultaneous restarts
10. Verify each bot writes valid `window_pnl_economic` before moving to next
11. Update `~/polymarket-vault/vault_metrics.py` to use `window_pnl_economic` for all metrics

### Stage 3 — Recompute fleet metrics with corrected column (30 min)

12. Run corrected fleet metrics: real WR (window won if window_pnl_economic > 0), real EV
13. Compare to proxy metrics — document magnitude of discrepancy per bot
14. Update CLAUDE.md with corrected numbers
15. Decision gate: if any bot shows corrected window_pnl_economic > 0 sustained, it survives. If all negative → strategy review.

### What to watch for
- Bot crash on restart (log ownership must be `polymarket:polymarket`)
- `fire_log` not being cleared between windows → stale fires contaminating next window
- `window_pnl_economic` being NULL/0 for no-trade windows (expected — guard with `total_exposure == 0` check)
- The proxy and economic columns should diverge significantly for TAIL-heavy windows (TAIL fires at 90c will show proxy≈cost, economic≈−large_loss)

---

## 8. Caveats

- **Maker fee (`shares × 0.0008`) is an approximation.** True Polymarket maker rebate structure not confirmed. This affects only FILL_HEDGE and FILL_MOMENTUM_ADD fires. Fee contribution is small — the primary discrepancy driver is the structural proxy formula error, not fees.
- **HEDGE size ≠ shares × price.** The HEDGE `usdc` passed to `record_trade` is `_hedge_size_to_target(HEDGE_TARGET_NET)`, not `shares × hedge_price`. This creates an additional source of proxy error beyond the formula error: the proxy's `net_yes_usdc` for HEDGE fires does not equal actual USDC cost of the hedge entry. The corrected formula uses shares and fill_price from the log row (not the tracker's internal usdc value), so it is immune to this issue.
- **Historical CSV data cannot be retroactively fixed.** Old logs still have only `gross_pnl_proxy`. The zone_decomp.py script already handles this correctly (re-derives economic P&L from fire-level rows, ignoring the proxy column).
- **Window WR comparison across bots (proxy-based) may still be directionally useful.** The proxy tends to overstate wins proportionally to entry price — bots trading at cheaper prices (lower MOM_ADD entries) will be less wrong. Relative ranking may hold even if absolute values don't.
