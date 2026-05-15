"""
Dual-Claude workflow diagram: Planner / Critic / Executor
Shows the three-role architecture and information flow
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(11, 6.5), dpi=200)
ax.set_xlim(0, 11)
ax.set_ylim(0, 6.5)
ax.axis('off')

# Three role boxes
def draw_role_box(ax, x, y, w, h, title, role, items, color, title_color):
    """Draw a rounded rectangle role box with content."""
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                          linewidth=2, edgecolor=color, facecolor=color, alpha=0.12)
    ax.add_patch(box)
    
    # Title
    ax.text(x + w/2, y + h - 0.30, title,
            ha='center', va='top', fontsize=13, fontweight='bold', color=title_color)
    # Role label
    ax.text(x + w/2, y + h - 0.75, role,
            ha='center', va='top', fontsize=9.5, style='italic', color='#444444')
    
    # Bullet items
    item_y = y + h - 1.25
    for item in items:
        ax.text(x + 0.20, item_y, "•", fontsize=10, color=color, fontweight='bold')
        ax.text(x + 0.40, item_y, item, fontsize=9, color='#222222', va='top')
        item_y -= 0.40

# Planner (center, top)
draw_role_box(ax, 4.0, 3.7, 3.0, 2.2, "Human (Planner)", "Decision + judgment layer",
              ["Sets priorities", "Makes architectural calls", "Resolves disagreements"],
              "#1F5582", "#1F5582")

# Critic (left, bottom)
draw_role_box(ax, 0.3, 0.8, 3.0, 2.4, "Claude.ai (Critic)", "Analysis + planning",
              ["Reviews proposed code", "Flags inconsistencies", "Pushes back on weak logic", "Builds prompts for Executor"],
              "#C73E1D", "#C73E1D")

# Executor (right, bottom)
draw_role_box(ax, 7.7, 0.8, 3.0, 2.4, "Claude Code (Executor)", "Execution + debugging",
              ["Runs code on VPS", "Edits files", "Debugs failures", "Reports results back"],
              "#2E8B57", "#2E8B57")

# Arrows between roles
arrow_kwargs = dict(arrowstyle='->', color='#555555', linewidth=1.5,
                    mutation_scale=18, connectionstyle="arc3,rad=0.0")

# Planner -> Critic
ax.annotate('', xy=(1.8, 3.2), xytext=(4.5, 4.0),
            arrowprops=arrow_kwargs)
ax.text(2.7, 3.7, "decisions\n+ context", fontsize=8, color='#555555',
        ha='center', style='italic')

# Critic -> Planner
ax.annotate('', xy=(4.5, 3.9), xytext=(2.5, 3.2),
            arrowprops=dict(arrowstyle='->', color='#C73E1D', linewidth=1.5,
                          mutation_scale=18, connectionstyle="arc3,rad=0.0"))
ax.text(3.7, 3.4, "pushback\n+ analysis", fontsize=8, color='#C73E1D',
        ha='center', style='italic', fontweight='bold')

# Planner -> Executor
ax.annotate('', xy=(9.2, 3.2), xytext=(6.5, 4.0),
            arrowprops=arrow_kwargs)
ax.text(8.3, 3.7, "prompts\n(via Claude.ai)", fontsize=8, color='#555555',
        ha='center', style='italic')

# Executor -> Planner
ax.annotate('', xy=(6.5, 3.9), xytext=(8.5, 3.2),
            arrowprops=dict(arrowstyle='->', color='#2E8B57', linewidth=1.5,
                          mutation_scale=18, connectionstyle="arc3,rad=0.0"))
ax.text(7.3, 3.4, "outputs\n+ failures", fontsize=8, color='#2E8B57',
        ha='center', style='italic', fontweight='bold')

# Critic <-> Executor (the seam where discoveries happened)
ax.annotate('', xy=(7.5, 1.6), xytext=(3.5, 1.6),
            arrowprops=dict(arrowstyle='<->', color='#AA8800', linewidth=2,
                          mutation_scale=15, connectionstyle="arc3,rad=-0.3"))
ax.text(5.5, 0.45, "The seam: results flagged inconsistent by Critic\nprompted Executor investigations → bugs surfaced",
        fontsize=9, color='#AA8800', ha='center', style='italic', fontweight='bold',
        bbox=dict(boxstyle="round,pad=0.4", facecolor='#FFFAE5', edgecolor='#AA8800', linewidth=1.2))

# State files annotation (top right)
state_text = "Shared state:\ncontext.md (Day 1-45 timeline)\nscope.md (current day priorities)\nCLAUDE.md (executor context)"
ax.text(9.5, 5.95, state_text, fontsize=8.5, color='#444444', ha='center', va='top',
        bbox=dict(boxstyle="round,pad=0.3", facecolor='#F0F0F0', edgecolor='#888888', linewidth=0.8))

# Title
ax.text(5.5, 6.2, "Three-Role Workflow Architecture",
        ha='center', fontsize=13, fontweight='bold', color='#222222')

plt.tight_layout()
output_path = '/home/claude/autopsy/figures/fig_workflow.png'
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
plt.close()
print(f"Saved: {output_path}")
