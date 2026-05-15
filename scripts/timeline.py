"""
Timeline figure: 45-day project window with key events marked
Helps reader orient at the top of the document
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

fig, ax = plt.subplots(figsize=(14, 4.5), dpi=200)

# Project window: Day 1 to Day 45
# Day 1 = April 21, Day 45 = June 4
ax.set_xlim(0, 46)
ax.set_ylim(-2.5, 3.5)

# Main timeline bar
ax.axhline(0, xmin=0.02, xmax=0.98, color='#444444', linewidth=2, zorder=2)

# Mark each day with small ticks
for day in range(1, 46):
    if day % 5 == 0:
        ax.plot([day, day], [-0.15, 0.15], color='#444444', linewidth=1, zorder=2)
        ax.text(day, -0.55, f"Day {day}", ha='center', va='top', fontsize=8, color='#666666')

# Key events
events = [
    {"day": 1, "label": "Start", "color": "#2E8B57", "y": 1.5, "marker": "o"},
    {"day": 16, "label": "Proxy PnL bug\ndiscovered", "color": "#C73E1D", "y": 1.5, "marker": "X"},
    {"day": 17, "label": "Backtest invalidated\n+ OBI cascade", "color": "#C73E1D", "y": 2.5, "marker": "X"},
    {"day": 25, "label": "JOIN bug\ndiscovered", "color": "#C73E1D", "y": 1.5, "marker": "X"},
    {"day": 27, "label": "Phantom Vectors\n1, 2, 3 patched", "color": "#C73E1D", "y": 2.5, "marker": "X"},
    {"day": 26, "label": "Live deployment\nbegins", "color": "#1F5582", "y": -1.3, "marker": "s"},
    {"day": 29, "label": "Project end\n(Day 29 active)", "color": "#444444", "y": -2.0, "marker": "o"},
]

# Phase shaded regions
ax.axvspan(0, 15, alpha=0.08, color='#2E8B57', zorder=1)
ax.axvspan(15, 25, alpha=0.08, color='#DAA520', zorder=1)
ax.axvspan(25, 29, alpha=0.08, color='#C73E1D', zorder=1)
ax.axvspan(29, 45, alpha=0.04, color='#888888', zorder=1)

# Phase labels at top
ax.text(7.5, 3.2, "Act 1: Searching for Signal", ha='center', fontsize=10, fontweight='bold', color='#2E8B57', alpha=0.85)
ax.text(20, 3.2, "Act 2: Building, Breaking, Fixing", ha='center', fontsize=10, fontweight='bold', color='#DAA520', alpha=0.85)
ax.text(27, 3.2, "Act 3:\nPhantom\nCascade", ha='center', fontsize=9, fontweight='bold', color='#C73E1D', alpha=0.85)
ax.text(37, 3.2, "Project window (timeline ended Day 29)", ha='center', fontsize=10, style='italic', color='#888888', alpha=0.85)

# Plot events
for event in events:
    # Marker
    ax.scatter(event["day"], 0, s=120, c=event["color"], marker=event["marker"],
               edgecolors='black', linewidth=1.2, zorder=4)
    
    # Vertical line from marker to label
    ax.plot([event["day"], event["day"]], [0, event["y"]], 
            color=event["color"], linewidth=1, linestyle='-', alpha=0.6, zorder=3)
    
    # Label
    va = 'bottom' if event["y"] > 0 else 'top'
    ax.text(event["day"], event["y"] + (0.1 if event["y"] > 0 else -0.1), 
            event["label"],
            ha='center', va=va, fontsize=8.5, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', edgecolor=event["color"], linewidth=0.8))

# Legend
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#2E8B57', markeredgecolor='black', markersize=10, label='Project milestone'),
    Line2D([0], [0], marker='X', color='w', markerfacecolor='#C73E1D', markeredgecolor='black', markersize=10, label='Bug discovered / fixed'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='#1F5582', markeredgecolor='black', markersize=10, label='Live deployment'),
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=9, framealpha=0.95)

# Clean axes
ax.set_yticks([])
ax.set_xticks([])
for spine in ['top', 'right', 'left', 'bottom']:
    ax.spines[spine].set_visible(False)

ax.set_title("Project Timeline: 45-Day Window (April 21 – June 4, 2026)",
             fontsize=12, fontweight='bold', pad=10)

plt.tight_layout()
output_path = '/home/claude/autopsy/figures/fig0_timeline.png'
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print(f"Saved: {output_path}")
