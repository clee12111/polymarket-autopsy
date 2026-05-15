> **Note:** This forensic document was extracted from the private working repo
> polymarket-vault for inclusion in the public autopsy. VPS IPs, personal wallet
> addresses, and internal paths have been redacted. The original document was
> written as an in-project working note, not for publication, and may reference
> internal context.
>
> Last updated in private repo: 2026-05-10

# Day 17 Session Summary — May 4, 2026

## Headline finding

The proxy PnL formula used by all bots since inception was structurally wrong — it overstated wins and undercounted losses. The corrected formula (`fire_pnl = (sh - sh*p - fee) if won else (-sh*p - fee)`) has been validated against two independent bots to $0.0001 precision and is now the locked standard. All prior EV metrics are invalidated; live paper trading with the corrected metric is now the parameter-selection mechanism.

---

## Major events in chronological order

1. **Proxy formula bug confirmed (Day 16 carry-over)** — `gross_pnl_proxy = net_yes_usdc - net_no_usdc` overstates wins by factor `p/(1-p)` at entries above 50c. Full spec at `Strategy/proxy_pnl_bug_day16.md`. All prior EV numbers invalid.

2. **Stage 1 corrected metric validation — PASS** — v6b5_nohedge manual recompute matched corrected column to $0.0000. Formula locked.

3. **Fleet-wide corrected metrics computed** — All 8 retained bots recomputed with corrected formula. Summary: most bots cluster near zero EV with wide CI at all-time horizon. V6b is the only structural loser (-$493 all-time). V6b5 also negative (-$168).

4. **HEDGE zone price split discovered** — HEDGE fires pooled across all bots: below 0.475 = 69.5% WR, +$6.66/fire (N=82). Above 0.475 = 42.3% WR, -$0.96/fire (N=78). Clean structural split. A price ceiling of 0.475 on HEDGE entries would keep all the edge and eliminate the drag. Not yet implemented.

5. **Maker-vs-taker audit (V6_v5_82/87)** — TAKER_INTENTIONAL has negative EV/$ (-0.079 / -0.100). MAKER_FILLED is the strongest path (+0.254 / +0.108 EV/$). TAKER_PIVOT is positive but window-selection-biased (90% / 83% WR comes from pivoting in already-good windows). Latency implementation confirmed correct: 60ms + 310ms = 370ms matching `PIVOT_MAKER_TO_TAKER_MS` by coincidence. Dead config constants (`PIVOT_MAKER_TO_TAKER_MS`, `MAKER_CANCEL_LATENCY_MS`) never imported in trader — no bug, just dead code.

6. **OBI cascade failure diagnosed** — OBI logger (`obi_logger_v3`) had no restart wrapper and died at 21:47. All paper traders call `check_loggers(fatal=True)` at startup → `sys.exit(1)` on stale OBI log → crash-loop silently for ~2 hours. Fixed: OBI logger restarted with `while true; do python3 ...; sleep 5; done` wrapper. Pre-existing latency bots (V6_5_lat, V6_v5_82, V6_v5_87, V6_5_lat_size, V6b5_nohedge, V6_5, V6b, V6b5) retain `fatal=True` — they will crash-loop again if OBI dies.

7. **Droplet resize: 2 GB / 1 vCPU → 8 GB / 4 vCPU** — DigitalOcean credits cover cost. Required to run 22 concurrent screen sessions without OOM.

8. **CLOB-Gamma race condition discovered and fixed** — V5c-family bots use both CLOB and Gamma as condition_id sources. On first window, Gamma has not yet seen a market but CLOB has — mismatch caused new bots to never establish first window and log nothing. Fixed in v5c_clean via Option A: when Gamma condition_id doesn't match CLOB, adopt CLOB's view as fallback.

9. **v5c_clean baseline deployed and validated** — Stage 2E PASS. Manual recompute against corrected column matched to $0.0001. Clean V5c reference baseline now accumulating.

10. **Stage 2 sweep deployed — Group 1 (threshold) and Group 2 (lookback)** — 10 variants deployed across two parameter axes:
    - Threshold sweep: th_70, th_75, th_85, th_90, th_95 (baseline is th_82 / V5c default 0.82)
    - Lookback sweep: lb_30, lb_45, lb_75, lb_90 (baseline is lb_60 / V5c default 60s)
    - osc_off variant (OSCILLATION_KILL disabled) also deployed
    - All 10 screens confirmed detached and writing as of 00:21 UTC May 5

---

## Bugs identified and fixed today

- **gross_pnl_proxy structural error**: corrected formula locked; v6b5_nohedge and v5c_clean validated. Stage 1 column rollout pending for the 6 retained legacy bots (they don't have the corrected column yet — analysis scripts recompute on the fly).
- **OBI logger no restart wrapper**: died silently, cascaded to fleet crash-loop. Fixed with while-true wrapper. Lesson: all singleton infrastructure loggers need restart wrappers.
- **CLOB-Gamma race condition**: patched in v5c_clean with CLOB fallback on condition_id mismatch. Pre-existing bots not patched.

---

## Bugs identified but NOT yet fixed

- **Legacy bots `fatal=True` OBI check**: V6_5_lat, V6_v5_82, V6_v5_87, V6_5_lat_size, V6b5_nohedge, V6_5, V6b, V6b5 all crash-loop if OBI dies. Only v5c_clean and sweep variants have `fatal=False`. Fleet asymmetry — one OBI death kills legacy fleet.
- **ENTRY_EXPOSURE_CAP overshoot**: at least one v6b5_nohedge window deployed $37.97 vs cap of $35 (8.5% overshoot). Root cause unclear — may be race between HEDGE and MOMENTUM_ADD entries in same window_second.
- **v5c_clean corrected column**: manually verified but corrected column not yet written into v5c_clean CSV — analysis requires on-the-fly recompute script until column rollout.
- **Maker pricing logic ambiguity**: top-of-book vs inside-spread price used for maker order simulation not definitively characterized. Affects realism of maker fill rate and EV estimates.

---

## Methodology decisions made today

1. **Backtest demoted**: no longer used for parameter selection. Too many confounds (contaminated data, formula bugs). Use live paper trading with corrected metric as the selection mechanism. Backtest is sanity-check only.

2. **Three-stage framework formalized**:
   - Stage 2 (now): Maximum information collection. Single-axis sweeps including known-bad variants for survivorship coverage. 10+ variants, accumulate N≥100 each.
   - Stage 3 (post-sweep): Multi-axis hybrid construction. 2-3 deployment candidates assembled from sweep winners.
   - Live: Single best hybrid, minimum-shares, experimental fleet shuts down.

3. **Sweep variant philosophy**: prioritize unknowns over strong priors. Test parameter regions with minimum information, not where intuition is already strong.

4. **Verification discipline**: when an analytical claim feels alarming (e.g., "fleet is null"), require formal verification before action. Internal consistency cross-checks between narrative framing and computation are mandatory before reporting conclusions.

---

## Fleet state at end of session

**Infrastructure (Frankfurt VPS, <FRANKFURT_VPS_IP>, 8 GB / 4 vCPU):**
- `obi_logger` — screen 14756, restarted 22:38 UTC with while-true wrapper
- `clob_depth_logger` — screen 5265, running
- `clob_depth_rest` — screen 5268, running

**Retained legacy bots (6):**
- `crypto_paper_v6_5` — screen 2768, `fatal=True` OBI, accumulating
- `crypto_paper_v6_5_latency` — screen 2774, `fatal=True` OBI
- `crypto_paper_v6b` — screen 2782, `fatal=True` OBI (structural loser, keep for baseline)
- `crypto_paper_v6b5` — screen 2790, `fatal=True` OBI (negative all-time, keep for baseline)
- `crypto_paper_v6b5_nohedge` — screen 2800, `fatal=True` OBI, small N (restarted tonight)
- `crypto_paper_v6_5_lat_size` — screen 2836, `fatal=True` OBI, 4-sizing A/B (MEDIUM_MANY added Day 16)
- `crypto_paper_v6_v5_lat_82` — screen 2810, `fatal=True` OBI
- `crypto_paper_v6_v5_lat_87` — screen 2822, `fatal=True` OBI

**v5c baseline:**
- `crypto_paper_v5c_clean` — screen 34816, `fatal=False`, validated Phase 2E PASS

**Stage 2 sweep variants (10, all deployed 00:21 UTC May 5):**
- Threshold: `v5c_th_70`, `v5c_th_75`, `v5c_th_85`, `v5c_th_90`, `v5c_th_95`
- Lookback: `v5c_lb_30`, `v5c_lb_45`, `v5c_lb_75`, `v5c_lb_90`
- Ablation: `v5c_osc_off`
- All have `fatal=False` OBI check. All writing stub CSVs (376 bytes = header only at deploy time).

**Total screens: 22**

---

## Pending for tomorrow

1. **Verify sweep variants are accumulating** — check CSVs are growing past header. All were 376 bytes at 00:21 UTC; they need to have fired windows by morning.
2. **Update CLAUDE.md** — fleet state, new methodology decisions, corrected metric status, sweep deployment.
3. **Update `polymarketcontext.md`** — add 10 sweep variant rows, update infrastructure section.
4. **Implement HEDGE price ceiling at 0.475** — clear structural finding, zero ambiguity. Apply to v5c_clean and all sweep variants. Do not touch legacy bots.
5. **Investigate ENTRY_EXPOSURE_CAP overshoot** — trace which zone combination triggers the breach.
6. **Investigate maker pricing logic** — grep for where fill price is set on maker orders; confirm top-of-book vs mid-spread.
7. **After N≥50 per sweep variant**: first comparative analysis — threshold and lookback effect on WR and zone-level EV.

---

## Cutoff thresholds for sweep evaluation

- N=100 per variant before drawing significant conclusions
- 95% CI on per-window EV must clearly exclude zero before declaring "wins"
- Bonferroni correction for 11-variant comparison (v5c_clean + 10 sweep): per-comparison alpha = 0.05/11 ≈ 0.0045
- Zone-level effects converge faster than total-PnL — compare MOMENTUM_ADD and HEDGE EV by variant, not bot totals

---

## Critical reminders for tomorrow-self

- **Legacy bots have `fatal=True` OBI check** — if OBI logger dies again, legacy fleet crash-loops silently. Check OBI log freshness before assuming bots are healthy.
- **Corrected formula is locked**: `fee_taker = sh * 0.072 * p * (1-p)`, `fee_maker = sh * 0.0008`, `fire_pnl = (sh - sh*p - fee) if won else (-sh*p - fee)`. All scripts use this. Do not revert to proxy column.
- **Sweep variants differ from v5c_clean on ONE parameter each** — interpret effects in isolation. Do not combine across axes until Stage 3.
- **Stderr cleanliness ≠ health** — verify CSV rows are being written, not just that the process started.
- **HEDGE below 0.475 is the only clean price-zone finding with directional clarity** — everything else needs more N.
- **The L30 hot streaks on V6_v5_82/87 (93% WR) are not representative** — L60 drops to 80%/75%. Do not over-interpret short windows.
- **Do not update CLAUDE.md, polymarketcontext.md tonight** — those updates happen tomorrow morning sourced from this file.
