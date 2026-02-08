from typing import Dict, List, Tuple
from .types import Measurement

BLADES = ["BLU", "GRN", "YEL", "RED"]

DISPLAY_POINTS: List[Tuple[str, str]] = [
    ("100% Ground", "GROUND"),
    ("Hover Flight", "HOVER"),
    ("Hover IGE (est)", "HOVER"),
    ("40 KIAS (est)", "HORIZONTAL"),
    ("80 KIAS (est)", "HORIZONTAL"),
    ("Horizontal Flight", "HORIZONTAL"),
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
        amp = m.balance.amp_ips * (1.05 if "(est)" in name else 1.0)
        ph = (m.balance.phase_deg + (5 if "(est)" in name else 0)) % 360
        lines.append(f"{name:<18}  1P {amp:0.2f} IPS  {clock_label(ph):>5}  RPM:{m.balance.rpm:0.0f}")

    lines.append("")
    lines.append("----- Track Height (mm rel. YEL) -----")
    for name, src in DISPLAY_POINTS:
        if src not in meas_by_regime:
            continue
        m = meas_by_regime[src]

        def nud(x): return x + (0.6 if "(est)" in name else 0.0)

        row = "  ".join([f"{b}:{nud(m.track_mm[b]):+5.1f}" for b in BLADES])
        lines.append(f"{name:<18}  {row}")

    lines.append("")
    return "\n".join(lines)
