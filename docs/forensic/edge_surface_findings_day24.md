> **Note:** This forensic document was extracted from the private working repo `polymarket-vault` for inclusion in the public autopsy. VPS IPs, personal wallet addresses, and internal paths have been redacted. The original document was written as an in-project working note, not for publication, and may reference internal context.
>
> **Important context:** This analysis was produced on Day 24, three days before the Phantom Vector 3 discovery on Day 27 revealed that paper trading data was systematically contaminated (~135× PnL inflation, 99% phantom rate in late-window fires). The findings below were derived from data that was partially or substantially contaminated. They are preserved here as an artifact showing the analytical state of the project before the phantom discovery — not as validated results. See the main autopsy for the full contamination story.
>
> *Last updated in private repo: 2026-05-10*

# Edge Surface Re-Derivation — Day 24 Findings

**Date:** May 8, 2026
**Status:** LOCKED — two compounding bugs found, corrected surface derived

## Two Compounding Bugs: 20.5pp Overestimate

### Bug A: 10x Time Axis Mismatch

**Original calibration** (`Agents/v4_edge_surface.py`):
- Source: `0x7347_master_viz_1s.csv` — 1-second resolution data
- `TIME_EDGES = [5, 15, 25, 35, 50, 70, 100]` — labeled `"T7[100+s)"`, function named `time_bin(held_sec)`
- `direction_held_sec` computed via `cumcount() + 1` on 1s rows

**Bot implementation** (`Bots/crypto_paper_v5c_continuous_bilateral/state_v5c_cb.py`):
- `EDGE_SURFACE_TIME_EDGES = [5, 15, 25, 35, 50, 70, 100]` — same numbers
- `LOOP_INTERVAL = 0.10` (100ms) -> `direction_held_ticks` increments every 100ms
- `_time_bin(held_ticks)` applies second-based edges to tick-based values

**Result**: Bin 6 (`EDGE_SURFACE[0][6] = 0.9106`) triggers at 100 ticks = **10 seconds**, but was calibrated on **100+ seconds** of directional persistence. 10x error.

**Evidence**: Under original bins, 96% of conviction_only fires hit bin 6. Under corrected bins (ticks*10 -> seconds), fires distribute across all 7 bins:

| Corrected bin | Persistence | N | % of fires |
|---------------|-------------|---|------------|
| <5s | 0-50 ticks | 100 | 16.9% |
| 5-15s | 50-150 ticks | 43 | 9.1% |
| 15-25s | 150-250 ticks | 38 | 8.0% |
| 25-35s | 250-350 ticks | 69 | 14.6% |
| 35-50s | 350-500 ticks | 58 | 12.2% |
| 50-70s | 500-700 ticks | 66 | 13.9% |
| 70-100s | 700-1000 ticks | 100 | 21.1% |

### Bug B: ~9pp Scenario Filtering Inflation

Original calibration excluded scenarios S4 (oscillation, 3+ crossings) and S5 (fast crash). Fresh re-derivation on ALL 0x7347 data (no scenario filtering) shows **every cell 5-11pp lower** than the EDGE_SURFACE values:

| Cell | EDGE_SURFACE | Fresh (all data) | Inflation |
|------|-------------|------------------|-----------|
| D0,T6 | 0.9106 | 0.801 | +10.9pp |
| D0,T0 | 0.7979 | 0.706 | +9.1pp |
| D1,T6 | 0.9535 | 0.876 | +7.7pp |
| D2,T6 | 0.9661 | 0.918 | +4.8pp |
| D3,T6 | 0.9771 | 0.956 | +2.1pp |

Scenario filtering removed worst-performing windows, inflating WR by ~9pp at low distance bands.

### Combined Impact

```
Surface claim:           0.9106 (D0,T6 -- what bot reads)
Minus scenario inflation: 0.801  (correct value for 100+s at D0)
But bot fires at 10s:     0.706  (correct value for 5-15s at D0)
Total overestimate:       20.5pp
```

---

## Our Actual Conviction WR (Post-WS-Fix, De-duplicated)

82 unique windows (conviction fires from conviction_only bots, one per window):

**Overall: 58.5% WR vs 72.8% avg market prob = -14.3pp mispricing (NEGATIVE EV)**

Note: raw query returned 13,032 fires but these are 82 windows x ~71 bots = massive duplication.

| Persistence | N | WR | Market Prob | Mispricing |
|-------------|---|-----|------------|------------|
| <5s | 29 | 0.690 | 0.709 | -1.9pp |
| 5-15s | 14 | 0.500 | 0.704 | -20.4pp |
| 15-25s | 6 | 0.833 | 0.685 | +14.8pp |
| 25-35s | 6 | 0.500 | 0.722 | -22.2pp |
| 35-50s | 9 | 0.556 | 0.747 | -19.1pp |
| 50-70s | 11 | 0.545 | 0.785 | -24.0pp |
| 70-100s | 7 | 0.286 | 0.780 | -49.4pp |

**CRITICAL: WR DECREASES with persistence -- opposite of 0x7347 where WR increases.**

Explanation: `crossing_detected()` requires edge to have been below threshold recently. At high persistence, this fires on **exhaustion signals** (direction held a long time, edge just crossed up = late entry after the move). At low persistence, fires are **fresh directional signals** (direction just established).

---

## 0x7347 Corrected Surface (1.2M Samples, No Scenario Filtering)

```
                    5-15s   15-25s  25-35s  35-50s  50-70s  70-100s  100+s
D0[.03-.05)         0.706   0.714   0.715   0.727   0.756   0.760   0.801
D1[.05-.07)         0.737   0.763   0.784   0.791   0.796   0.821   0.876
D2[.07-.10)         0.765   0.785   0.796   0.822   0.835   0.864   0.918*
D3[.10-.15)         0.806   0.818   0.850   0.859   0.883*  0.909*  0.956*
D4[.15+)            0.886*  0.888*  0.879   0.900*  0.925*  0.938*  0.983*
* = meets CONVICTION_THRESHOLD (0.88)
```

Only **10 cells** pass 0.88 threshold. None are D0 or D1. Currently 93% of fires are D0.

---

## Corrected Config Values

```python
EDGE_SURFACE = {
    0: [0.7060, 0.7140, 0.7150, 0.7270, 0.7560, 0.7600, 0.8010],
    1: [0.7370, 0.7630, 0.7840, 0.7910, 0.7960, 0.8210, 0.8760],
    2: [0.7650, 0.7850, 0.7960, 0.8220, 0.8350, 0.8640, 0.9180],
    3: [0.8060, 0.8180, 0.8500, 0.8590, 0.8830, 0.9090, 0.9560],
    4: [0.8860, 0.8880, 0.8790, 0.9000, 0.9250, 0.9380, 0.9830],
}
EDGE_SURFACE_DIST_EDGES = [0.03, 0.05, 0.07, 0.10, 0.15]
EDGE_SURFACE_TIME_EDGES = [50, 150, 250, 350, 500, 700, 1000]  # TICKS at 100ms
```

---

## Confirmed Mispriced Cells (WR >= 0.88, N > 10000 from 0x7347)

| Cell | Distance | Persistence | WR | N |
|------|----------|-------------|-----|---|
| D2T6 | 0.07-0.10% | 100+s | 0.918 | 112,095 |
| D3T4 | 0.10-0.15% | 50-70s | 0.883 | 19,175 |
| D3T5 | 0.10-0.15% | 70-100s | 0.909 | 29,296 |
| D3T6 | 0.10-0.15% | 100+s | 0.956 | 118,528 |
| D4T0 | 0.15+% | 5-15s | 0.886 | 905 |
| D4T1 | 0.15+% | 15-25s | 0.888 | 1,732 |
| D4T3 | 0.15+% | 35-50s | 0.900 | 5,790 |
| D4T4 | 0.15+% | 50-70s | 0.925 | 10,660 |
| D4T5 | 0.15+% | 70-100s | 0.938 | 20,672 |
| D4T6 | 0.15+% | 100+s | 0.983 | 131,636 |

These require BTC moves >= 0.07% (D2) to >= 0.15% (D4). Current D0 fires (93% of total) at 0.03-0.05% would all be suppressed.

---

## Crossing Detection Problem

`crossing_detected()` in `state_v5c_cb.py:171-189` requires edge to have been **below** threshold within lookback window. This creates an anti-pattern at high persistence:

- **High persistence + crossing**: Direction held 50-100s, edge recently below threshold = direction weakening = **exhaustion signal**
- **Low persistence + crossing**: Direction just established, edge jumped above threshold = **fresh signal**

This explains the inverted WR vs persistence profile. The crossing gate selects for exhaustion at high persistence.

---

## Scenario Inflation Detail

0x7347 windows with crossing count analysis:
- 0-1 crossings: WR=0.861 (N=1,099,754) -- "clean" windows
- 3+ crossings: WR=0.559 (N=15,203) -- oscillation windows
- Difference: 30.1pp

Original excluded oscillation (S4) and crash (S5) scenarios. This is equivalent to only trading clean windows, inflating apparent WR. The bot cannot exclude these in real-time.

---

## Recommendations

1. **Fix TIME_EDGES**: `[50, 150, 250, 350, 500, 700, 1000]` (ticks)
2. **Fix EDGE_SURFACE values**: Use corrected 0x7347 surface
3. **Threshold sweep needed**: 0.88 kills D0/D1; consider 0.80 or target D2+ only
4. **Investigate crossing_detected()**: May need removal, inversion, or persistence-gating
5. **N=82 insufficient**: Need 500+ unique windows for our own cell validation
6. **Cell-array architecture validated**: Approach correct, inputs were wrong

---

## Scripts

- `Agents/v4_edge_surface.py` — original derivation (time in seconds)
- `Agents/edge_surface_rederivation.py` — corrected re-derivation (this analysis)
