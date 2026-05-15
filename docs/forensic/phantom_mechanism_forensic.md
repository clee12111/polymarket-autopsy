> **Note:** This forensic document was extracted from the private working repo
> polymarket-vault for inclusion in the public autopsy. VPS IPs, personal wallet
> addresses, and internal paths have been redacted. The original document was
> written as an in-project working note, not for publication, and may reference
> internal context.
>
> Last updated in private repo: 2026-05-11

# Phantom-Price Bug: Full Forensic Analysis

## Discovery (Day 26, 2026-05-10)

Fleet-wide audit revealed 59% of paper PnL was phantom inflation.
- 95,652 total fires → 18,325 valid (19.2%)
- Paper PnL +$63,074 → Real PnL +$26,068 (41% of paper)
- 13 bots flipped paper-positive → real-negative
- 19 bots flipped paper-negative → real-positive

## Root Cause — Vector 1: CLOB-Gamma Race Fix (line ~514)

**Mechanism:** `get_clob_state(condition_id)` reads only last 32KB of `clob_depth_log.jsonl` (~5 seconds, ~90 lines). During late window (ws>=200), the next window's market floods the log with ws=0 entries, pushing the current market's sparse entries out of the tail.

When `get_clob_state` returns `None`, the CLOB-Gamma race fix at line ~514 calls `_get_any_clob_condition()` to adopt a fallback condition_id. At late window, this returns the **next window's** condition_id. The bot then reads that market's opening prices (typically ~$0.50), producing phantom fires at artificial 50/50 prices.

**Impact:** Cross-market condition_id hijacking → phantom $0.50 fires → inflated paper PnL.

**Fix (Patch 1):** Gate `_get_any_clob_condition()` fallback with `ws < 60` predicate. At ws>=60, skip fallback entirely and log `race-fix-skipped`. Rationale: CLOB-Gamma race (Gamma API sees market N while CLOB log has market N-1) only legitimately occurs at window transitions (ws < ~30). At ws>=60, absent CLOB data means the market genuinely has no orderbook, not a race condition.

```python
# Patch 1 (line ~519)
if clob is None:
    _ws_now = int(now - _window_open_ts(now))
    if _ws_now < 60:
        fallback_cid = _get_any_clob_condition()
        ...
    else:
        print(f"{TAG} race-fix-skipped: ws={_ws_now}, ...")
```

## Root Cause — Vector 2: Gamma API Poll Fallback (line ~494)

**Discovered:** Day 27 (2026-05-11), during canary validation of Patch 1.

**Discovery method:** Canary bot deployed with Patch 1 only, wide gates (fire in all ws buckets). T+30 analysis showed 3 phantom-suspect fires persisting at ws=214/267/269 with prices 0.49-0.51. Condition_id analysis revealed MULTI-CID pattern: every window had 2 distinct condition_ids, with the second appearing only at late ws.

**Mechanism:** `fetch_active_condition()` (Gamma API poll) runs every `GAMMA_POLL_SEC` (60s). When it returns `None` (API timeout, no candidates, stale response), the code falls back to `_get_any_clob_condition()` — the same function as Vector 1. This fallback had NO ws guard, so it adopted cross-market condition_ids at any point in the window.

This vector operates independently of Vector 1. Even with Patch 1 blocking the CLOB-Gamma race fix path, the Gamma poll path continued adopting wrong condition_ids every 60 seconds throughout the window.

**Evidence (preserved in `Logs/canary_patch1only_207fires_3phantoms.csv`):**
- 207 total fires, 3 phantom-suspect (ws=267/price=0.51, ws=269/price=0.49, ws=214/price=0.50)
- All 3 phantoms on cross-market condition_ids (0x4725f6..., 0x69dea6...)
- Every window showed MULTI-CID pattern in condition_id column

**Fix (Patch 2):** Same `ws < 60` gate applied to Gamma poll fallback. Distinguishable log line: `gamma-fallback-skipped`.

```python
# Patch 2 (line ~498)
if not new_cid:
    _gamma_ws = int(now - _window_open_ts(now))
    if _gamma_ws < 60:
        new_cid = _get_any_clob_condition()
    else:
        print(f"{TAG} gamma-fallback-skipped: ws={_gamma_ws}, ...")
```

## Call Site Audit

`_get_any_clob_condition()` is called from exactly 2 sites:
1. **Line ~494** (Gamma API poll fallback) — Patch 2 applied
2. **Line ~519** (CLOB-Gamma race fix) — Patch 1 applied

Both sites now gated with `ws < 60`. No other callers exist.

**Future-proofing lesson:** Any new caller of `_get_any_clob_condition()` MUST include the ws < 60 gate, or the phantom bug will recur. The function itself is not unsafe — it correctly returns the most recent condition_id from the CLOB log. The danger is in *when* the caller uses it.

## Deployment Timeline (Day 27, 2026-05-11)

| Time (UTC) | Action |
|---|---|
| 10:19 | Patch 1 applied to high_scaled |
| 10:25 | Patch 1 applied to conviction_only |
| 10:32 | Canary launched (cloned from patched high_scaled, wide gates) |
| 10:44 | Patch 1 applied to remaining 19 bots |
| 10:57 | Fleet restart #1 (21 bots, Patch 1 only) |
| 10:58 | Canary T+26 analysis: 3 phantom fires found, Vector 2 discovered |
| 11:03 | Patch 2 applied to all 22 bots |
| 11:05 | Patch 2 log line added (gamma-fallback-skipped) |
| 11:06 | Fleet restart #2 (22 bots, Patch 1 + Patch 2 + log lines) |
| 11:06 | Canary CSV reset for clean T+30 validation |
| 11:36 | T+30 validation pending |

## Validation Status

As of 2026-05-11 11:06 UTC: **Pending.** T+30 canary checkpoint at ~11:36 UTC will confirm whether both vectors are fully blocked.
