from __future__ import annotations

from typing import Dict, List, Tuple

from .types import Measurement
from .solver import suggest_pitchlink, suggest_trimtabs, suggest_weight

BLADES = ["BLU", "GRN", "YEL", "RED"]

# Blade colors (approximate legacy VXP palette)
BLADE_COLOR = {
    "BLU": "#0000cc",
    "GRN": "#008800",
    "YEL": "#b09000",
    "RED": "#cc0000",
}

# Subtle coloring for regime names (legacy screens used colored regime text)
REGIME_COLOR = {
    "GROUND": "#000000",
    "HOVER": "#0000cc",
    "HORIZ": "#008800",
}


def _c(txt: str, color: str) -> str:
    """Wrap text in a color span. Safe for use inside vxp-mono (white-space:pre)."""

    return f"<span style='color:{color};'>{txt}</span>"


# Display order (BO105 procedure): ONLY these three.
DISPLAY_POINTS: List[Tuple[str, str]] = [
    ("100% Ground", "GROUND"),
    ("Hover Flight", "HOVER"),
    ("Horizontal Flight", "HORIZ"),
]


def clock_label(theta_deg: float) -> str:
    """Convert phase degrees to a 12-hour clock label (legacy VXP style)."""

    hour = int(round(theta_deg / 30.0)) % 12
    hour = 12 if hour == 0 else hour
    minute = 0 if abs((theta_deg / 30.0) - round(theta_deg / 30.0)) < 0.25 else 30
    return f"{hour:02d}:{minute:02d}"


def legacy_results_text(run: int, meas_by_regime: Dict[str, Measurement]) -> str:
    """Legacy-like mono report used on MEASUREMENTS GRAPH / LIST.

    - BO105 only (Ground / Hover / Horizontal)
    - Adds blade & regime color cues
    - Aligns Adjustments so values appear directly under each blade
    """

    lines: List[str] = []
    lines.append("BO105   MAIN ROTOR   TRACK & BALANCE")
    lines.append("OPTION: B   STROBEX MODE: B")
    lines.append(f"RUN: {run}   ID: TRAINING")
    lines.append("")

    # -------------------------
    # Balance measurements
    # -------------------------
    lines.append("----- Balance Measurements -----")
    for name, src in DISPLAY_POINTS:
        if src not in meas_by_regime:
            continue
        m = meas_by_regime[src]
        amp = float(m.balance.amp_ips)
        ph = float(m.balance.phase_deg)
        reg = _c(f"{name:<18}", REGIME_COLOR.get(src, "#000"))
        lines.append(f"{reg}  1P {amp:0.2f} IPS  {clock_label(ph):>5}  RPM:{m.balance.rpm:0.0f}")

    lines.append("")

    # -------------------------
    # Track height
    # -------------------------
    lines.append("----- Track Height (mm rel. YEL) -----")
    for name, src in DISPLAY_POINTS:
        if src not in meas_by_regime:
            continue
        m = meas_by_regime[src]
        reg = _c(f"{name:<18}", REGIME_COLOR.get(src, "#000"))
        parts = [_c(f"{b}:{m.track_mm[b]:+5.1f}", BLADE_COLOR[b]) for b in BLADES]
        lines.append(f"{reg}  " + "  ".join(parts))

    # -------------------------
    # Solution / Prediction
    # -------------------------
    lines.append("")
    lines.append("----- Solution Options -----")

    used_regimes = [name for name, src in DISPLAY_POINTS if src in meas_by_regime]
    if not used_regimes:
        lines.append("(No regimes collected yet)")
        lines.append("")
        return "\n".join(lines)

    lines.append("SOLUTION TYPE: BALANCE")
    lines.append(f"REGIMES USED: {', '.join(used_regimes)}")
    lines.append("USED: Pitch link, Trim tab, Weight")

    pl = suggest_pitchlink(meas_by_regime)
    tt = suggest_trimtabs(meas_by_regime)
    wb, wg = suggest_weight(meas_by_regime)

    lines.append("")
    lines.append("Adjustments")

    # Header aligned like the original (values appear directly under each blade).
    # We use fixed-width columns so the result is stable even with inline <span> coloring.
    COL_W = 8

    def _hblade(b: str) -> str:
        return _c(f"{b:>{COL_W}}", BLADE_COLOR[b])

    def _vblade(b: str, s: str) -> str:
        return _c(f"{s:>{COL_W}}", BLADE_COLOR[b])

    def _hdr(label: str) -> str:
        return f"{label:<12}" + _hblade("BLU") + _hblade("GRN") + _hblade("YEL") + _hblade("RED")

    def _row(label: str, vals: Dict[str, float], fmt: str) -> str:
        return (
            f"{label:<12}"
            + _vblade("BLU", format(vals["BLU"], fmt))
            + _vblade("GRN", format(vals["GRN"], fmt))
            + _vblade("YEL", format(vals["YEL"], fmt))
            + _vblade("RED", format(vals["RED"], fmt))
        )

    # P/L
    lines.append(_hdr("P/L(flats)"))
    lines.append(_row("", pl, "6.2f"))

    # Keep the same names as the legacy screen (TabS5/TabS6)
    lines.append(_hdr("TabS5(deg)"))
    lines.append(_row("", {b: tt[b] * 0.8 for b in BLADES}, "6.1f"))
    lines.append(_hdr("TabS6(deg)"))
    lines.append(_row("", {b: tt[b] * 0.8 for b in BLADES}, "6.1f"))

    # Weight (only one blade gets the suggested grams)
    wrow = {b: 0.0 for b in BLADES}
    wrow[wb] = float(wg)
    lines.append(_hdr("Wt(plqts)"))
    lines.append(_row("", wrow, "6.0f"))

    lines.append("")
    lines.append("----- Prediction -----")
    for name, src in DISPLAY_POINTS:
        if src not in meas_by_regime:
            continue
        m = meas_by_regime[src]
        reg = _c(f"{name:<18}", REGIME_COLOR.get(src, "#000"))
        lines.append(f"{reg}  M/R L   {m.balance.amp_ips:0.2f}")

    lines.append("Track Split")
    for name, src in DISPLAY_POINTS:
        if src not in meas_by_regime:
            continue
        m = meas_by_regime[src]
        vals = [m.track_mm[b] for b in BLADES]
        split = max(vals) - min(vals)
        reg = _c(f"{name:<18}", REGIME_COLOR.get(src, "#000"))
        lines.append(f"{reg}  {split:0.2f}")

    lines.append("")
    return "\n".join(lines)
