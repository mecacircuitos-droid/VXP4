import math
import matplotlib.pyplot as plt
from typing import Dict
from .types import Measurement

BLADES = ["BLU", "GRN", "YEL", "RED"]
REGIMES = ["GROUND", "HOVER", "HORIZONTAL"]
REGIME_LABEL = {"GROUND":"100% Ground","HOVER":"Hover Flight","HORIZONTAL":"Horizontal Flight"}

def plot_track_marker(meas: Measurement) -> plt.Figure:
    # Smaller footprint to better match the original VXP XGA layouts.
    fig = plt.figure(figsize=(3.6, 1.25), dpi=110)
    fig.patch.set_facecolor("#c0c0c0")
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")
    ax.set_ylim(-32.5, 32.5)
    ax.set_xlim(0.5, len(BLADES)+0.5)
    ax.set_yticks([-32.5, 0.0, 32.5])
    ax.set_ylabel("mm", fontsize=9)
    ax.set_xticks(range(1, len(BLADES)+1))
    ax.set_xticklabels(BLADES, fontsize=9, fontweight="bold")
    for i in range(1, len(BLADES)+1):
        ax.axvline(i, color="black", linewidth=0.6, linestyle=":")
    xs = list(range(1, len(BLADES)+1))
    ys = [meas.track_mm[b] for b in BLADES]
    ax.scatter(xs, ys, marker="s", s=28)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_title(f"Track Height (mm) — {REGIME_LABEL[meas.regime]}", fontsize=9, fontweight="bold")
    for sp in ax.spines.values():
        sp.set_color("black"); sp.set_linewidth(1.0)
    fig.tight_layout(pad=0.8)
    return fig

def plot_track_graph(meas_by_regime: Dict[str, Measurement]) -> plt.Figure:
    xs = [REGIME_LABEL[r] for r in REGIMES if r in meas_by_regime]
    fig = plt.figure(figsize=(3.6, 1.35), dpi=110)
    fig.patch.set_facecolor("#c0c0c0")
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")
    for b in BLADES:
        ys = [meas_by_regime[r].track_mm[b] for r in REGIMES if r in meas_by_regime]
        ax.plot(xs, ys, marker="s", linewidth=1.2, markersize=4, label=b)
    ax.set_ylim(-32.5, 32.5)
    ax.set_ylabel("mm", fontsize=9)
    ax.set_title("Track Height (relative to YEL)", fontsize=9, fontweight="bold")
    ax.axhline(0.0, linewidth=0.8)
    ax.grid(True, linestyle=":", linewidth=0.6)
    for sp in ax.spines.values():
        sp.set_color("black"); sp.set_linewidth(1.0)
    ax.tick_params(axis="x", labelsize=7)
    ax.legend(loc="upper right", ncol=4, fontsize=7, frameon=False)
    fig.tight_layout(pad=0.9)
    return fig

def plot_polar(meas: Measurement) -> plt.Figure:
    fig = plt.figure(figsize=(3.6, 2.6), dpi=110)
    fig.patch.set_facecolor("#c0c0c0")
    ax = fig.add_subplot(111, projection="polar")
    ax.set_facecolor("white")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ticks = [math.radians(t) for t in range(0, 360, 30)]
    labels = ["12","1","2","3","4","5","6","7","8","9","10","11"]
    ax.set_xticks(ticks); ax.set_xticklabels(labels, fontsize=9, fontweight="bold")
    ax.set_rmax(max(0.35, meas.balance.amp_ips*1.4))
    ax.grid(True, linestyle=":", linewidth=0.6)
    theta = math.radians(meas.balance.phase_deg)
    ax.plot([theta],[meas.balance.amp_ips], marker="o", markersize=7)
    ax.text(theta, meas.balance.amp_ips+0.01, f"{meas.balance.amp_ips:.2f}", fontsize=9, ha="center")
    ax.set_title("1/rev Balance (IPS vs Phase)", fontsize=9, fontweight="bold", pad=10)
    fig.tight_layout(pad=0.8)
    return fig


def plot_polar_compare(meas_by_regime: Dict[str, Measurement]) -> plt.Figure:
    """Polar plot with up to 3 points (GROUND/HOVER/HORIZONTAL) for quick comparison."""
    fig = plt.figure(figsize=(3.6, 2.6), dpi=110)
    fig.patch.set_facecolor("#c0c0c0")
    ax = fig.add_subplot(111, projection="polar")
    ax.set_facecolor("white")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    ticks = [math.radians(t) for t in range(0, 360, 30)]
    labels = ["12","1","2","3","4","5","6","7","8","9","10","11"]
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=9, fontweight="bold")

    amps = [meas_by_regime[r].balance.amp_ips for r in REGIMES if r in meas_by_regime]
    rmax = max([0.35] + [a * 1.4 for a in amps])
    ax.set_rmax(rmax)
    ax.grid(True, linestyle=":", linewidth=0.6)

    for r in REGIMES:
        if r not in meas_by_regime:
            continue
        meas = meas_by_regime[r]
        theta = math.radians(meas.balance.phase_deg)
        ax.plot([theta], [meas.balance.amp_ips], marker="o", markersize=6)
        # annotate with a short regime tag + amplitude (keeps the plot compact)
        tag = "GND" if r == "GROUND" else ("HOV" if r == "HOVER" else "HOR")
        ax.text(theta, meas.balance.amp_ips + 0.012, f"{tag} {meas.balance.amp_ips:.2f}", fontsize=8, ha="center")

    ax.set_title("1/rev Balance (compare regimes)", fontsize=9, fontweight="bold", pad=8)
    fig.tight_layout(pad=0.6)
    return fig
