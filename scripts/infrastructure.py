"""
VPS infrastructure diagram for Act 2a
Shows the multi-VPS architecture with geo-blocking constraints and data sources
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

fig, ax = plt.subplots(figsize=(12, 6.5), dpi=200)
ax.set_xlim(0, 12)
ax.set_ylim(0, 7)
ax.axis('off')

# Title
ax.text(6, 6.5, "Multi-VPS Architecture: Geo-Blocking Forced the Topology",
        ha='center', fontsize=13, fontweight='bold', color='#222222')

# Helper to draw a VPS box
def draw_vps(ax, x, y, w, h, name, location, specs, role, color):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                          linewidth=2, edgecolor=color, facecolor=color, alpha=0.12)
    ax.add_patch(box)
    ax.text(x + w/2, y + h - 0.30, name, ha='center', va='top', fontsize=11, fontweight='bold', color=color)
    ax.text(x + w/2, y + h - 0.65, location, ha='center', va='top', fontsize=9, style='italic', color='#444444')
    ax.text(x + w/2, y + h - 0.95, specs, ha='center', va='top', fontsize=8, color='#666666', family='monospace')
    ax.text(x + w/2, y + 0.30, role, ha='center', va='top', fontsize=8.5, color='#222222')

# Helper to draw a data source box
def draw_source(ax, x, y, w, h, name, sub, color):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                          linewidth=1.5, edgecolor=color, facecolor='white')
    ax.add_patch(box)
    ax.text(x + w/2, y + h - 0.20, name, ha='center', va='top', fontsize=9.5, fontweight='bold', color=color)
    ax.text(x + w/2, y + h - 0.50, sub, ha='center', va='top', fontsize=7.5, color='#666666', style='italic')

# Data sources (top row)
draw_source(ax, 0.2, 5.0, 2.0, 0.9, "Binance Global", "Asia\n(geo-blocked from US)", "#C73E1D")
draw_source(ax, 2.6, 5.0, 2.0, 0.9, "Polymarket CLOB", "Europe\n(geo-blocked from US)", "#C73E1D")
draw_source(ax, 5.0, 5.0, 2.0, 0.9, "NOAA", "US-only API\nno daily limit", "#2E8B57")
draw_source(ax, 7.4, 5.0, 2.0, 0.9, "Open-Meteo", "international\nstrict daily limit", "#2E8B57")

# VPSes (middle row)
draw_vps(ax, 0.2, 2.4, 3.2, 2.0, "Frankfurt VPS", "Germany — 8 GB / 4 vCPU",
         "$24/mo", "Paper trading fleet\n+ CLOB/Binance loggers\n+ fleet.db\n(180 bots)", "#1F5582")

draw_vps(ax, 4.4, 2.4, 3.2, 2.0, "Amsterdam VPS", "Netherlands — 1 GB / 1 vCPU",
         "$6/mo", "Live execution only\n+ WS shadow feed\n(6 live bots,\nphysical isolation)", "#AA8800")

draw_vps(ax, 8.6, 2.4, 3.2, 2.0, "NY VPS", "United States — small instance",
         "$6/mo", "Weather data only\n(NOAA + Open-Meteo)\nNever used for crypto", "#888888")

# Arrows from data sources to VPSes
arrow_kwargs = dict(arrowstyle='->', color='#555555', linewidth=1.2, mutation_scale=12)
ax.annotate('', xy=(1.5, 4.35), xytext=(1.2, 5.0), arrowprops=arrow_kwargs)
ax.annotate('', xy=(2.5, 4.35), xytext=(3.6, 5.0), arrowprops=arrow_kwargs)
ax.annotate('', xy=(10, 4.35), xytext=(6.0, 5.0), arrowprops=arrow_kwargs)
ax.annotate('', xy=(10.5, 4.35), xytext=(8.4, 5.0), arrowprops=arrow_kwargs)

# Arrow from Frankfurt to Amsterdam (data sync)
ax.annotate('', xy=(4.4, 3.4), xytext=(3.4, 3.4),
            arrowprops=dict(arrowstyle='->', color='#1F5582', linewidth=2, mutation_scale=15))
ax.text(3.9, 3.6, "SCP\nsync", ha='center', fontsize=8, color='#1F5582', fontweight='bold')

# Local mirror (bottom)
draw_source(ax, 4.4, 0.5, 3.2, 1.0, "Local Desktop Mirror", 
            "C:/Users/.../polymarket-vault/\nbackup + offline analysis", "#444444")

# Arrows from Frankfurt to local
ax.annotate('', xy=(5.5, 1.5), xytext=(2.0, 2.4),
            arrowprops=dict(arrowstyle='->', color='#888888', linewidth=1.2, mutation_scale=12, linestyle='dashed'))
ax.text(3.0, 2.0, "periodic\npull", ha='center', fontsize=8, color='#888888', style='italic')

# Geo-blocking annotation
ax.text(6, 0.15, "Geo-blocking required this topology: US IPs blocked from Binance Global and Polymarket CLOB.\nFrankfurt sat closest to both data centers; Amsterdam was the only non-blocked region for live execution.",
        ha='center', fontsize=8.5, color='#444444', style='italic',
        bbox=dict(boxstyle="round,pad=0.4", facecolor='#FFFAE5', edgecolor='#AA8800', linewidth=0.8))

plt.tight_layout()
output_path = '/home/claude/autopsy/figures/fig_infrastructure.png'
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print(f"Saved: {output_path}")
