import math
from typing import Dict, Tuple
from .types import Measurement

BLADES = ["BLU", "GRN", "YEL", "RED"]
REGIMES = ["GROUND", "HOVER", "HORIZONTAL"]
BLADE_CLOCK_DEG = {"YEL": 0.0, "RED": 90.0, "BLU": 180.0, "GRN": 270.0}

PITCHLINK_MM_PER_TURN = 10.0
TRIMTAB_MMTRACK_PER_MM = 15.0
BOLT_IPS_PER_GRAM = 0.0020

def track_limit(regime: str) -> float:
    return 5.0 if regime in ("HOVER", "HORIZONTAL") else 10.0

def balance_limit(regime: str) -> float:
    return 0.40 if regime == "GROUND" else 0.05

def track_spread(m: Measurement) -> float:
    vals = [m.track_mm[b] for b in BLADES]
    return float(max(vals) - min(vals))

def all_ok(meas_by_regime: Dict[str, Measurement]) -> bool:
    for r in REGIMES:
        if r not in meas_by_regime:
            return False
        if track_spread(meas_by_regime[r]) > track_limit(r):
            return False
        if meas_by_regime[r].balance.amp_ips > balance_limit(r):
            return False
    return True

def _round_quarter(x: float) -> float:
    return round(x * 4.0) / 4.0

def suggest_pitchlink(meas: Dict[str, Measurement]) -> Dict[str, float]:
    used = [r for r in ("GROUND", "HOVER") if r in meas]
    if not used:
        return {b: 0.0 for b in BLADES}
    out = {}
    for b in BLADES:
        avg = sum(meas[r].track_mm[b] for r in used) / len(used)
        out[b] = _round_quarter((-avg) / PITCHLINK_MM_PER_TURN)
    return out

def suggest_trimtabs(meas: Dict[str, Measurement]) -> Dict[str, float]:
    if "HORIZONTAL" not in meas:
        return {b: 0.0 for b in BLADES}
    out = {}
    for b in BLADES:
        dev = meas["HORIZONTAL"].track_mm[b]
        out[b] = max(-5.0, min(5.0, _round_quarter((-dev) / TRIMTAB_MMTRACK_PER_MM)))
    return out

def suggest_weight(meas: Dict[str, Measurement]) -> Tuple[str, float]:
    if not meas:
        return ("YEL", 0.0)
    worst_r = max(meas.keys(), key=lambda r: meas[r].balance.amp_ips)
    m = meas[worst_r]
    amp = m.balance.amp_ips
    phase = m.balance.phase_deg
    target = (phase + 180.0) % 360.0

    def dist(a, b):
        d = abs(a - b) % 360.0
        return min(d, 360.0 - d)

    blade = min(BLADES, key=lambda bb: dist(target, BLADE_CLOCK_DEG[bb]))
    grams = max(5.0, min(120.0, round(amp / BOLT_IPS_PER_GRAM / 5.0) * 5.0))
    return blade, grams
