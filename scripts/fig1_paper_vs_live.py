"""
Figure 1: Paper EV vs Live EV scatter, 6 architectures
Shows the anti-prediction finding (Spearman ρ = -0.43)
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.stats import spearmanr
import numpy as np

# Data from autopsy paper-to-live comparison table
architectures = [
    {"name": "Barbell",    "paper_ev": +0.48,  "live_ev": -2.86, "direction": "reversed"},
    {"name": "Surgical",   "paper_ev": -0.18,  "live_ev": -0.61, "direction": "matched"},
    {"name": "Sniper",     "paper_ev": +0.00,  "live_ev": +0.08, "direction": "ambiguous"},
    {"name": "Reversion",  "paper_ev": +0.20,  "live_ev": +0.25, "direction": "matched"},
    {"name": "Ohanism",    "paper_ev": +0.09,  "live_ev": -0.51, "direction": "reversed"},
    {"name": "Conviction", "paper_ev": +1.16,  "live_ev": -0.90, "direction": "reversed"},
]

paper_evs = [a["paper_ev"] for a in architectures]
live_evs = [a["live_ev"] for a in architectures]

# Confirm Spearman correlation
rho, pval = spearmanr(paper_evs, live_evs)
print(f"Spearman ρ = {rho:.3f}, p = {pval:.3f}")

# Color by direction
color_map = {"reversed": "#C73E1D", "matched": "#2E8B57", "ambiguous": "#888888"}

fig, ax = plt.subplots(figsize=(8, 8), dpi=150)

# Zero reference lines
ax.axhline(0, color='#CCCCCC', linewidth=0.8, zorder=1)
ax.axvline(0, color='#CCCCCC', linewidth=0.8, zorder=1)

# Identity line (y=x): if paper were predictive of live
xlim = (-0.5, 1.4)
ylim = (-3.5, 0.7)
ax.plot([xlim[0], xlim[1]], [xlim[0], xlim[1]], 
        linestyle='--', color='#AAAAAA', linewidth=1, zorder=1, label='y = x (perfect agreement)')

# Plot points
for a in architectures:
    ax.scatter(a["paper_ev"], a["live_ev"],
               s=180,
               c=color_map[a["direction"]],
               edgecolors='black',
               linewidth=1.0,
               zorder=3)

# Label points - position labels to avoid overlap
label_offsets = {
    "Barbell":    (+0.08, +0.05),
    "Surgical":   (+0.08, -0.05),
    "Sniper":     (+0.08, +0.05),
    "Reversion":  (+0.08, -0.15),
    "Ohanism":    (-0.20, +0.18),
    "Conviction": (-0.30, -0.18),
}

for a in architectures:
    dx, dy = label_offsets[a["name"]]
    ax.annotate(
        a["name"],
        xy=(a["paper_ev"], a["live_ev"]),
        xytext=(a["paper_ev"] + dx, a["live_ev"] + dy),
        fontsize=10,
        fontweight='bold',
        zorder=4,
    )

# Annotation: ρ = -0.43 (top-right corner, but we have data in top-right; put in bottom-right area instead)
ax.text(1.30, -3.30, "Spearman ρ = −0.43",
        fontsize=14, fontweight='bold',
        ha='right', va='bottom',
        bbox=dict(boxstyle="round,pad=0.5", facecolor='white', edgecolor='black', linewidth=1))

# Quadrant note
ax.text(1.30, -3.10, "Paper EV not predictive of live EV.\nWhere agreement existed, it was near zero.",
        fontsize=9, style='italic', ha='right', va='bottom', color='#444444')

# Legend for colors
red_patch = mpatches.Patch(color='#C73E1D', label='Direction reversed (paper +, live −)')
green_patch = mpatches.Patch(color='#2E8B57', label='Direction matched')
gray_patch = mpatches.Patch(color='#888888', label='Ambiguous (paper ≈ 0)')
identity_line = plt.Line2D([0], [0], linestyle='--', color='#AAAAAA', label='y = x (perfect agreement)')

ax.legend(handles=[red_patch, green_patch, gray_patch, identity_line],
          loc='lower left', fontsize=9, framealpha=0.95)

# Axes
ax.set_xlim(xlim)
ax.set_ylim(ylim)
ax.set_xlabel("Paper EV per fire (USDC)", fontsize=12, fontweight='bold')
ax.set_ylabel("Live EV per fill (USDC)", fontsize=12, fontweight='bold')
ax.set_title("Paper EV vs Live EV across 6 deployed architectures\nThe bots paper said were best performed worst live.",
             fontsize=13, fontweight='bold', pad=15)

# Grid
ax.grid(True, alpha=0.3, linestyle=':', zorder=0)
ax.set_axisbelow(True)

# Clean spines
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)

plt.tight_layout()
output_path = '/mnt/user-data/outputs/fig1_paper_vs_live.png'
import os
os.makedirs('/mnt/user-data/outputs', exist_ok=True)
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

print(f"Saved: {output_path}")
