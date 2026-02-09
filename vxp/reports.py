from typing import Dict, List, Tuple

from .types import Measurement
from .solver import suggest_pitchlink, suggest_trimtabs, suggest_weight

BLADES = ["BLU", "GRN", "YEL", "RED"]

# Display order (BO105 procedure). We intentionally exclude:
#  - Hover IGE (est)
#  - 40/80 KIAS (est)
DISPLAY_POINTS: List[Tuple[str, str]] = [
    ("100% Ground", "GROUND"),
    ("Hover Flight", "HOVER"),
    ("120 KIAS Level", "KIAS120"),
    ("45 Bank (120 K)", "BANK45"),
]

def clock_label(theta_deg: float) -> str:
    hour = int(round(theta_deg / 30.0)) % 12
    hour = 12 if hour == 0 else hour
    minute = 0 if abs((theta_deg / 30.0) - round(theta_deg / 30.0)) < 0.25 else 30
    return f"{hour:02d}:{minute:02d}"

def legacy_results_text(run: int, meas_by_regime: Dict[str, Measurement]) -> str:
    lines: List[str] = []
    lines.append("BO105   MAIN ROTOR  TRACK & BALANCE")
    lines.append("OPTION: B   STROBEX MODE: B")
    lines.append(f"RUN: {run}   ID: TRAINING")
    lines.append("")
    lines.append("----- Balance Measurements -----")
    for name, src in DISPLAY_POINTS:
        if src not in meas_by_regime:
            continue
        m = meas_by_regime[src]
        amp = m.balance.amp_ips
        ph = m.balance.phase_deg
        lines.append(f"{name:<18}  1P {amp:0.2f} IPS  {clock_label(ph):>5}  RPM:{m.balance.rpm:0.0f}")

    lines.append("")
    lines.append("----- Track Height (mm rel. YEL) -----")
    for name, src in DISPLAY_POINTS:
        if src not in meas_by_regime:
            continue
        m = meas_by_regime[src]
        row = "  ".join([f"{b}:{m.track_mm[b]:+5.1f}" for b in BLADES])
        lines.append(f"{name:<18}  {row}")

    # ------------------------------------------------------------------
    # Legacy-like solution + prediction summary (appears on the original
    # MEASUREMENTS GRAPH screen).
    # ------------------------------------------------------------------
    lines.append("")
    lines.append("----- Solution Options -----")

    used_regimes = [name for name, src in DISPLAY_POINTS if src in meas_by_regime]
    if used_regimes:
        lines.append("SOLUTION TYPE: BALANCE")
        lines.append(f"REGIMES USED: {', '.join(used_regimes)}")
        lines.append("USED: Pitch link, Trim tab, Weight")

        pl = suggest_pitchlink(meas_by_regime)
        tt = suggest_trimtabs(meas_by_regime)
        wb, wg = suggest_weight(meas_by_regime)

        lines.append("")
        lines.append("Adjustments")
        lines.append("P/L(flats)     BLU     GRN     YEL     RED")
        lines.append(
            "             "
            + "  ".join([f"{pl[b]:>6.2f}" for b in BLADES])
        )
        lines.append("TabS5(deg)     BLU     GRN     YEL     RED")
        lines.append(
            "             "
            + "  ".join([f"{(tt[b]*0.8):>6.1f}" for b in BLADES])
        )
        lines.append("TabS6(deg)     BLU     GRN     YEL     RED")
        lines.append(
            "             "
            + "  ".join([f"{(tt[b]*0.8):>6.1f}" for b in BLADES])
        )
        lines.append("Wt(plqts)      BLU     GRN     YEL     RED")
        wrow = {b: 0.0 for b in BLADES}
        wrow[wb] = wg
        lines.append(
            "             "
            + "  ".join([f"{wrow[b]:>6.0f}" for b in BLADES])
        )

        # Simple prediction: show current amps (we keep it deterministic and
        # transparent rather than claiming full physics fidelity).
        lines.append("")
        lines.append("----- Prediction -----")
        for name, src in DISPLAY_POINTS:
            if src not in meas_by_regime:
                continue
            m = meas_by_regime[src]
            lines.append(f"{name:<18}  M/R L   {m.balance.amp_ips:0.2f}")
        lines.append("Track Split")
        for name, src in DISPLAY_POINTS:
            if src not in meas_by_regime:
                continue
            m = meas_by_regime[src]
            vals = [m.track_mm[b] for b in BLADES]
            split = max(vals) - min(vals)
            lines.append(f"{name:<18}  {split:0.2f}")
    else:
        lines.append("(No regimes collected yet)")

    lines.append("")
    return "\n".join(lines)
