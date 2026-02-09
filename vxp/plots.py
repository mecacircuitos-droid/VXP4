import math
from typing import Dict, List

import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

from .types import Measurement

BLADES = ["BLU", "GRN", "YEL", "RED"]

# Keep in sync with vxp.sim.REGIMES
REGIMES = ["GROUND", "HOVER", "KIAS120", "BANK45"]

# Labels used across the UI (legacy-like)
REGIME_LABEL = {
    "GROUND": "100% Ground",
    "HOVER": "Hover Flight",
    "KIAS120": "120 KIAS Level",
    "BANK45": "45 Bank (120 K)",
}

# Short labels for the x-axis
REGIME_LABEL_SHORT = {
    "GROUND": "100% Ground",
    "HOVER": "Hover Flight",
    "KIAS120": "120 KIAS Level",
    "BANK45": "45 Bank (120 K)",
}

# Colors to mimic the legacy VXP appearance (blue/green/yellow/red)
BLADE_COLOR = {
    "BLU": "#0047AB",
    "GRN": "#0A8F08",
    "YEL": "#B58900",
    "RED": "#B00020",
}
REGIME_TAG = {"GROUND": "GND", "HOVER": "HOV", "KIAS120": "120", "BANK45": "45B"}
REGIME_COLOR = {"GROUND": "#000000", "HOVER": "#0047AB", "KIAS120": "#0A8F08", "BANK45": "#B00020"}


def _track_rel(meas: Measurement, blade_ref: str) -> List[float]:
    """Return track values relative to blade_ref (defaults to YEL)."""
    ref = float(meas.track_mm.get(blade_ref, 0.0))
    return [float(meas.track_mm[b]) - ref for b in BLADES]


def plot_measurements_panel(meas_by_regime: Dict[str, Measurement], selected_regime: str, blade_ref: str = "YEL") -> plt.Figure:
    """Single, VXP-like figure: Track marker + track trend + polar compare.

    This is meant for the MEASUREMENTS GRAPH window (XGA 1024×768), where separate
    figures waste margins and look "zoomed".
    """
    # Right pane is about half of XGA; ~520 px wide at 120 dpi.
    fig = plt.figure(figsize=(4.35, 5.25), dpi=120)
    fig.patch.set_facecolor("#c0c0c0")

    gs = fig.add_gridspec(nrows=3, ncols=1, height_ratios=[1.05, 1.25, 3.10], hspace=0.38)

    # ----------------------
    # Track marker (selected regime)
    # ----------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor("white")
    ax1.set_ylim(-32.5, 32.5)
    ax1.set_xlim(0.5, len(BLADES) + 0.5)
    ax1.set_yticks([-32.5, 0.0, 32.5])
    ax1.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax1.tick_params(axis="y", labelsize=8)
    ax1.set_ylabel("mm", fontsize=8, fontweight="bold")

    ax1.set_xticks(range(1, len(BLADES) + 1))
    ax1.set_xticklabels(BLADES, fontsize=9, fontweight="bold")

    for i in range(1, len(BLADES) + 1):
        ax1.axvline(i, color="black", linewidth=0.6, linestyle=":")

    m = meas_by_regime[selected_regime]
    xs = list(range(1, len(BLADES) + 1))
    ys = _track_rel(m, blade_ref)
    ax1.scatter(
        xs,
        ys,
        marker="s",
        s=30,
        c=[BLADE_COLOR[b] for b in BLADES],
        edgecolors="black",
        linewidths=0.4,
    )
    ax1.axhline(0.0, color="black", linewidth=0.8)

    # Legacy VXP screen shows no explicit title on this panel.

    for sp in ax1.spines.values():
        sp.set_color("black")
        sp.set_linewidth(1.0)

    # ----------------------
    # Track trend across regimes (relative to blade_ref)
    # ----------------------
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.set_facecolor("white")

    regimes_present = [r for r in REGIMES if r in meas_by_regime]
    x_labels = [REGIME_LABEL_SHORT[r] for r in regimes_present]
    x = list(range(len(regimes_present)))

    ax2.set_ylim(-32.5, 32.5)
    ax2.set_yticks([-32.5, 0.0, 32.5])
    ax2.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax2.tick_params(axis="y", labelsize=8)
    ax2.set_ylabel("mm", fontsize=8, fontweight="bold")

    ax2.set_xticks(x)
    ax2.set_xticklabels(x_labels, fontsize=8)

    for b in BLADES:
        yb = []
        for r in regimes_present:
            rr = _track_rel(meas_by_regime[r], blade_ref)
            yb.append(rr[BLADES.index(b)])
        ax2.plot(
            x,
            yb,
            marker="o",
            markersize=3.5,
            linewidth=1.2,
            color=BLADE_COLOR[b],
        )

        # Label each blade near its last point (like legacy displays, but without a legend box)
        if len(x) > 0:
            ax2.text(
                x[-1] + 0.08,
                yb[-1],
                b,
                fontsize=8,
                fontweight="bold",
                color=BLADE_COLOR[b],
                va="center",
            )

    ax2.axhline(0.0, color="black", linewidth=0.8)
    ax2.grid(True, linestyle=":", linewidth=0.6)
    # Legacy VXP screen shows no explicit title on this panel.

    # Make room on the right for the inline labels
    ax2.set_xlim(-0.15, (len(x) - 1) + 0.55 if len(x) else 1.0)

    for sp in ax2.spines.values():
        sp.set_color("black")
        sp.set_linewidth(1.0)

    # ----------------------
    # Polar compare (up to 3 regimes)
    # ----------------------
    ax3 = fig.add_subplot(gs[2, 0], projection="polar")
    ax3.set_facecolor("white")
    ax3.set_theta_zero_location("N")
    ax3.set_theta_direction(-1)

    ticks = [math.radians(t) for t in range(0, 360, 30)]
    labels = ["12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    ax3.set_xticks(ticks)
    ax3.set_xticklabels(labels, fontsize=9, fontweight="bold")

    amps = [meas_by_regime[r].balance.amp_ips for r in regimes_present]
    rmax = max([0.35] + [a * 1.8 for a in amps])
    # Round up to a nice ring (0.05 increments)
    rmax = math.ceil(rmax * 20.0) / 20.0
    ax3.set_rmax(rmax)

    # Radial ticks every 0.1 like the legacy screen
    rticks = [round(0.1 * i, 2) for i in range(1, int(rmax / 0.1) + 1)]
    if rticks and rticks[-1] < rmax:
        rticks.append(rmax)
    if not rticks:
        rticks = [0.1, 0.2, 0.3]

    ax3.set_rticks(rticks)
    ax3.set_yticklabels([f"{t:.2f}" if t < 1 else f"{t:.1f}" for t in rticks], fontsize=8)
    ax3.grid(True, linestyle=":", linewidth=0.6)

    for r in regimes_present:
        meas = meas_by_regime[r]
        theta = math.radians(meas.balance.phase_deg)
        amp = meas.balance.amp_ips
        ax3.plot(
            [theta],
            [amp],
            marker="o",
            markersize=7,
            color=REGIME_COLOR.get(r, "black"),
        )
        tag = REGIME_TAG.get(r, r[:3].upper())
        txt_r = min(amp + 0.03, rmax * 0.98)
        ax3.text(theta, txt_r, f"{tag} {amp:.2f}", fontsize=8, ha="center")

    fig.subplots_adjust(left=0.08, right=0.98, top=0.97, bottom=0.06)
    return fig


# ------------------------------------------------------------------
# Legacy smaller plots (still used in other screens)
# ------------------------------------------------------------------

def plot_track_marker(meas: Measurement) -> plt.Figure:
    fig = plt.figure(figsize=(3.6, 1.12), dpi=120)
    fig.patch.set_facecolor("#c0c0c0")
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")
    ax.set_ylim(-32.5, 32.5)
    ax.set_xlim(0.5, len(BLADES) + 0.5)
    ax.set_yticks([-32.5, 0.0, 32.5])
    ax.set_xticks(range(1, len(BLADES) + 1))
    ax.set_xticklabels(BLADES, fontsize=9, fontweight="bold")
    for i in range(1, len(BLADES) + 1):
        ax.axvline(i, color="black", linewidth=0.6, linestyle=":")
    xs = list(range(1, len(BLADES) + 1))
    ys = [meas.track_mm[b] for b in BLADES]
    ax.scatter(xs, ys, marker="s", s=28)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_title(f"Track Height — {REGIME_LABEL_SHORT[meas.regime]}", fontsize=9, fontweight="bold")
    for sp in ax.spines.values():
        sp.set_color("black")
        sp.set_linewidth(1.0)
    fig.tight_layout(pad=0.55)
    return fig


def plot_track_graph(meas_by_regime: Dict[str, Measurement]) -> plt.Figure:
    xs = [REGIME_LABEL_SHORT[r] for r in REGIMES if r in meas_by_regime]
    fig = plt.figure(figsize=(3.6, 1.18), dpi=120)
    fig.patch.set_facecolor("#c0c0c0")
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")
    for b in BLADES:
        ys = [meas_by_regime[r].track_mm[b] for r in REGIMES if r in meas_by_regime]
        ax.plot(xs, ys, marker="s", linewidth=1.2, markersize=4, label=b)
    ax.set_ylim(-32.5, 32.5)
    ax.set_title("Track Height (rel. YEL)", fontsize=9, fontweight="bold")
    ax.axhline(0.0, linewidth=0.8)
    ax.grid(True, linestyle=":", linewidth=0.6)
    for sp in ax.spines.values():
        sp.set_color("black")
        sp.set_linewidth(1.0)
    ax.tick_params(axis="x", labelsize=7)
    fig.tight_layout(pad=0.55)
    return fig


def plot_polar(meas: Measurement) -> plt.Figure:
    fig = plt.figure(figsize=(3.6, 2.35), dpi=120)
    fig.patch.set_facecolor("#c0c0c0")
    ax = fig.add_subplot(111, projection="polar")
    ax.set_facecolor("white")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ticks = [math.radians(t) for t in range(0, 360, 30)]
    labels = ["12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=9, fontweight="bold")
    ax.set_rmax(max(0.35, meas.balance.amp_ips * 1.4))
    ax.grid(True, linestyle=":", linewidth=0.6)
    theta = math.radians(meas.balance.phase_deg)
    ax.plot([theta], [meas.balance.amp_ips], marker="o", markersize=7)
    ax.text(theta, meas.balance.amp_ips + 0.01, f"{meas.balance.amp_ips:.2f}", fontsize=8, ha="center")
    fig.tight_layout(pad=0.55)
    return fig


def plot_polar_compare(meas_by_regime: Dict[str, Measurement]) -> plt.Figure:
    fig = plt.figure(figsize=(3.6, 2.35), dpi=120)
    fig.patch.set_facecolor("#c0c0c0")
    ax = fig.add_subplot(111, projection="polar")
    ax.set_facecolor("white")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    ticks = [math.radians(t) for t in range(0, 360, 30)]
    labels = ["12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=8, fontweight="bold")

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
        tag = "GND" if r == "GROUND" else ("HOV" if r == "HOVER" else "HOR")
        ax.text(theta, meas.balance.amp_ips + 0.012, tag, fontsize=8, ha="center")
    fig.tight_layout(pad=0.5)
    return fig
