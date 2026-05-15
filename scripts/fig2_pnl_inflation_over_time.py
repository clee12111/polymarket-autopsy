"""
Figure 2: Apparent fleet PnL over time, with bug-correction annotations
Shows how the apparent PnL grew through measurement errors and collapsed after each fix
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

# Daily cumulative apparent PnL from autopsy
# This is what the fleet's PnL appeared to be at each date (phantom + real combined)
dates = [
    datetime(2026, 5, 5),
    datetime(2026, 5, 6),
    datetime(2026, 5, 7),
    datetime(2026, 5, 8),
    datetime(2026, 5, 9),
    datetime(2026, 5, 10),
    datetime(2026, 5, 11),
    datetime(2026, 5, 12),
    datetime(2026, 5, 13),
]

apparent_pnl = [
    499,
    64844,
    78273,
    80448,
    73425,
    117717,
    157795,   # peak — V3 fix deployed late this day
    160491,   # post-fix, dramatically fewer fires
    158277,   # final
]

# Fire counts per day (for size context, not plotted)
fire_counts = [1746, 48613, 56748, 108600, 63193, 80187, 40796, 15470, 1330]

# Final clean PnL after all corrections
clean_final = 1162

fig, ax = plt.subplots(figsize=(14, 7), dpi=150)

# Main line
ax.plot(dates, apparent_pnl,
        marker='o', markersize=8,
        linewidth=2.5,
        color='#C73E1D',
        markeredgecolor='black',
        markeredgewidth=0.8,
        zorder=3,
        label='Apparent cumulative PnL (uncorrected, what the metric SAID)')

# Fill area under curve to emphasize the inflation
ax.fill_between(dates, 0, apparent_pnl, alpha=0.15, color='#C73E1D', zorder=2)

# Horizontal line for the actual clean PnL
ax.axhline(clean_final, linestyle='--', color='#2E8B57', linewidth=2, zorder=2,
           label=f'Final clean PnL (post-V3-fix): +${clean_final:,}')

# Zero line
ax.axhline(0, color='black', linewidth=0.5, zorder=1)

# Annotation events
events = [
    {
        "date": datetime(2026, 5, 6),
        "label": "Day 16 — Proxy PnL bug discovered.\nWin values overstated 1.4×–9×.",
        "y_text": 95000,
        "x_offset_days": 0.2,
    },
    {
        "date": datetime(2026, 5, 7),
        "label": "Day 17 — Backtest invalidated.\nMethodology pivot.",
        "y_text": 50000,
        "x_offset_days": 0.2,
    },
    {
        "date": datetime(2026, 5, 10),
        "label": "Day 25 — Window-fire JOIN bug.\nWrong-day matches.",
        "y_text": 135000,
        "x_offset_days": -1.0,
    },
    {
        "date": datetime(2026, 5, 11),
        "label": "Day 27 — Phantom Vectors 1, 2, 3 patched.\nApparent PnL was phantom.",
        "y_text": 165000,
        "x_offset_days": -1.2,
    },
]

for event in events:
    # Vertical dashed line
    ax.axvline(event["date"], linestyle=':', color='#666666', linewidth=1.2, zorder=1, alpha=0.6)

    # Find the data point at this date
    idx = dates.index(event["date"])
    pnl_at_date = apparent_pnl[idx]

    # Arrow from text to the data point
    text_x = event["date"] + (mdates.num2timedelta(event["x_offset_days"]) if hasattr(mdates, 'num2timedelta')
                              else __import__('datetime').timedelta(days=event["x_offset_days"]))

    ax.annotate(
        event["label"],
        xy=(event["date"], pnl_at_date),
        xytext=(text_x, event["y_text"]),
        fontsize=9,
        fontweight='bold',
        ha='left' if event["x_offset_days"] > 0 else 'right',
        va='center',
        bbox=dict(boxstyle="round,pad=0.4", facecolor='white', edgecolor='#888888', linewidth=0.8),
        arrowprops=dict(arrowstyle='->', color='#666666', lw=1.0, connectionstyle="arc3,rad=0.1"),
        zorder=5,
    )

# Big callout: contamination ratio
ax.annotate(
    "",
    xy=(datetime(2026, 5, 13), clean_final),
    xytext=(datetime(2026, 5, 13), 158277),
    arrowprops=dict(arrowstyle='<->', color='#444444', lw=2),
)
ax.text(
    datetime(2026, 5, 13, 12), 78000,
    "~135× inflation\n($157K → $1.2K)",
    fontsize=12, fontweight='bold',
    ha='center', va='center',
    color='#444444',
    bbox=dict(boxstyle="round,pad=0.5", facecolor='#FFFAE5', edgecolor='#AA8800', linewidth=1.5),
)

# Format axes
ax.set_xlabel("Date (2026)", fontsize=12, fontweight='bold')
ax.set_ylabel("Cumulative apparent PnL (USDC)", fontsize=12, fontweight='bold')
ax.set_title("Apparent fleet PnL over time, with bug-correction events\nEvery spike was a measurement bug. The corrections revealed there was no real edge.",
             fontsize=13, fontweight='bold', pad=15)

# Date formatting
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')

# Y-axis formatting (thousands)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x/1000:.0f}K' if abs(x) >= 1000 else f'${x:.0f}'))

# Y-axis limits
ax.set_ylim(-5000, 200000)

# Grid
ax.grid(True, alpha=0.3, linestyle=':', zorder=0)
ax.set_axisbelow(True)

# Legend
ax.legend(loc='upper left', fontsize=10, framealpha=0.95)

# Clean spines
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)

plt.tight_layout()

output_path = '/mnt/user-data/outputs/fig2_pnl_inflation_over_time.png'
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

print(f"Saved: {output_path}")
