"""VXP UI (Streamlit).

Objetivo:
- Mantener la apariencia del APP.zip (XGA 1024×768, look XP, toolbar con iconos)
- Reincorporar pantallas que existían en el prototipo inicial (vxp_vxp_sim_bo105V0.zip)
  y que se habían ido perdiendo en el menú del procedimiento.

Notas:
- La UI se renderiza como UNA ventana activa dentro del "desktop" para evitar
  problemas de superposición (MDI) con Streamlit.
- La navegación del toolbar se hace con query params (?nav=...), consumiéndolos
  en cada carga para que no queden “pegados”.
"""

from __future__ import annotations

import json
import random
import time
from typing import Callable, Dict, Iterable, List, Optional

import streamlit as st

from .plots import plot_polar, plot_polar_compare, plot_track_graph, plot_track_marker
from .reports import clock_label, legacy_results_text
from .sim import (
    BLADES,
    REGIMES,
    REGIME_LABEL,
    BO105_DISPLAY_RPM,
    default_adjustments,
    simulate_measurement,
)
from .solver import (
    all_ok,
    balance_limit,
    suggest_pitchlink,
    suggest_trimtabs,
    suggest_weight,
    track_limit,
    track_spread,
)


# ---------------------------
# Navigation / state
# ---------------------------

def go(screen: str, **kwargs) -> None:
    """Set current screen and optional session_state values."""
    st.session_state.vxp_screen = screen
    for k, v in kwargs.items():
        st.session_state[k] = v


def init_state() -> None:
    st.session_state.setdefault("vxp_screen", "home")

    # Runs
    st.session_state.setdefault("vxp_run", 1)
    st.session_state.setdefault("vxp_runs", {1: {}})
    st.session_state.setdefault("vxp_completed_by_run", {1: set()})
    st.session_state.setdefault("vxp_view_run", 1)

    # Adjustable parameters (training)
    st.session_state.setdefault("vxp_adjustments", default_adjustments())

    # Acquisition flow
    st.session_state.setdefault("vxp_pending_regime", None)
    st.session_state.setdefault("vxp_acq_in_progress", False)

    # Aircraft info + note codes (recuperado del prototipo inicial)
    st.session_state.setdefault(
        "vxp_aircraft",
        {"weight": 0.0, "cg": 0.0, "hours": 0.0, "initials": ""},
    )
    st.session_state.setdefault("vxp_note_codes", set())

    # Simple event log (para VIEW LOG)
    st.session_state.setdefault("vxp_event_log", [])


def _log(msg: str) -> None:
    log: List[str] = st.session_state.vxp_event_log
    ts = time.strftime("%H:%M:%S")
    log.append(f"[{ts}] {msg}")
    # evita crecimiento infinito
    if len(log) > 250:
        del log[:-200]


def ensure_run(run: int) -> None:
    runs: Dict[int, dict] = st.session_state.vxp_runs
    runs.setdefault(run, {})
    st.session_state.vxp_completed_by_run.setdefault(run, set())


def current_run_data(run: int):
    ensure_run(run)
    return st.session_state.vxp_runs[run]


def completed_set(run: int):
    ensure_run(run)
    return st.session_state.vxp_completed_by_run[run]


def run_selector_inline(key: str = "run_selector") -> int:
    runs = sorted(st.session_state.vxp_runs.keys())
    cur = int(st.session_state.vxp_view_run)
    if cur not in runs:
        cur = runs[0]
        st.session_state.vxp_view_run = cur
    idx = runs.index(cur)
    r = st.selectbox("Run", runs, index=idx, key=key)
    st.session_state.vxp_view_run = int(r)
    return int(r)


# ---------------------------
# Toolbar routing (query params)
# ---------------------------

_NAV_TO_SCREEN = {
    "disconnect": "home",
    "upload": "upload",
    "download": "download",
    "viewlog": "viewlog",
    "print_au": "print_au",
    "print_pc": "print_pc",
    "help": "help",
    "exit": "exit",
}


def _get_query_param(name: str) -> Optional[str]:
    """Robust getter compatible with multiple Streamlit versions."""
    try:
        # Streamlit >= 1.30
        val = st.query_params.get(name)
        if isinstance(val, list):
            return val[0] if val else None
        return str(val) if val is not None else None
    except Exception:
        qp = st.experimental_get_query_params()
        val2 = qp.get(name)
        if not val2:
            return None
        return str(val2[0])


def _clear_query_params() -> None:
    try:
        # Streamlit >= 1.30
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()


def handle_nav_from_query_params() -> None:
    """Consume ?nav=... and route to internal screens.

    Call this once per render (after init_state).
    """
    nav = _get_query_param("nav")
    if not nav:
        return

    nav = nav.strip().lower()
    target = _NAV_TO_SCREEN.get(nav)
    _clear_query_params()

    if not target:
        _log(f"NAV desconocido: {nav}")
        return

    _log(f"Toolbar: {nav}")

    # Simple actions
    if nav == "disconnect":
        go("home")
    elif nav == "exit":
        go("exit")
    else:
        go(target)

    st.rerun()


# ---------------------------
# Window chrome helpers
# ---------------------------

def win_caption(title: str, active: bool) -> None:
    cls = "active" if active else "inactive"
    st.markdown(
        f"<div class='vxp-win-caption {cls}'>"
        f"<div>{title}</div>"
        "<div class='vxp-closebox'>✕</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def right_close_button(
    label: str,
    *,
    target: str | None = None,
    on_click: Callable[[], None] | None = None,
    key: str | None = None,
) -> None:
    """Classic right-aligned button (usually Close)."""
    screen = str(st.session_state.get("vxp_screen", ""))
    if key is None:
        safe = "".join(ch if ch.isalnum() else "_" for ch in label.lower())
        key = f"btn_{screen}_{safe}_right"

    cols = st.columns([0.75, 0.25])
    with cols[1]:
        if st.button(label, use_container_width=True, key=key):
            if target is not None:
                go(target)
            if on_click is not None:
                on_click()
            st.rerun()


# ---------------------------
# Desktop (single-window)
# ---------------------------

def render_desktop() -> None:
    """Render a single main window (no overlapping popups)."""

    try:
        desk = st.container(border=True)
    except TypeError:
        desk = st.container()

    with desk:
        st.markdown("<div class='vxp-desktop-marker'></div>", unsafe_allow_html=True)

        if st.session_state.vxp_screen == "home":
            render_select_procedure_window(active=True)
        else:
            render_active_window()


# ---------------------------
# Home screen
# ---------------------------

def render_select_procedure_window(active: bool) -> None:
    win_caption("Select Procedure:", active=active)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    left, _ = st.columns([0.72, 0.28], gap="small")
    with left:
        if st.button("Aircraft Info", use_container_width=True, key="home_aircraft_info"):
            go("aircraft_info")
            st.rerun()

        # Main Rotor runs (1..3)
        for run in (1, 2, 3):
            label = f"Main Rotor Balance Run {run}"
            if st.button(label, use_container_width=True, key=f"home_mr_run_{run}"):
                st.session_state.vxp_run = run
                ensure_run(run)
                go("mr_menu")
                st.rerun()

        if st.button("Tail Rotor Balance Run 1", use_container_width=True, key="home_tr_run1"):
            go("tr_menu")
            st.rerun()

        if st.button("T/R Driveshaft Balance Run 1", use_container_width=True, key="home_drv_run1"):
            go("drv_menu")
            st.rerun()

        if st.button("Vibration Signatures", use_container_width=True, key="home_vib_sig"):
            go("vib_signatures")
            st.rerun()

        if st.button("Measurements Only", use_container_width=True, key="home_meas_only"):
            go("meas_only")
            st.rerun()

        if st.button("Setup / Utilities", use_container_width=True, key="home_setup_utils"):
            go("setup_utils")
            st.rerun()


# ---------------------------
# Active window routing
# ---------------------------

def render_active_window() -> None:
    screen = st.session_state.vxp_screen

    # Main rotor procedure
    if screen == "mr_menu":
        screen_mr_menu_window()
    elif screen == "collect":
        screen_collect_window()
    elif screen == "acquire":
        screen_acquire_window()
    elif screen == "meas_list":
        screen_meas_list_window()
    elif screen == "meas_graph":
        screen_meas_graph_window()
    elif screen == "settings":
        screen_settings_window()
    elif screen == "solution":
        screen_solution_window()
    elif screen == "solution_text":
        screen_solution_text_window()
    elif screen == "solution_graph":
        screen_solution_graph_window()
    elif screen == "next_run_prompt":
        screen_next_run_window()

    # Aircraft info
    elif screen == "aircraft_info":
        screen_aircraft_info_window()
    elif screen == "note_codes":
        screen_note_codes_window()

    # Recuperados del menú antiguo
    elif screen == "test_sensors":
        screen_test_sensors_window()
    elif screen == "fastrak_options":
        screen_fastrak_options_window()

    # Otras aplicaciones (placeholders por ahora)
    elif screen == "tr_menu":
        screen_tail_rotor_menu_window()
    elif screen == "drv_menu":
        screen_driveshaft_menu_window()
    elif screen == "vib_signatures":
        screen_vibration_signatures_window()
    elif screen == "meas_only":
        screen_measurements_only_window()
    elif screen == "setup_utils":
        screen_setup_utils_window()

    # Toolbar windows
    elif screen == "viewlog":
        screen_viewlog_window()
    elif screen == "upload":
        screen_upload_window()
    elif screen == "download":
        screen_download_window()
    elif screen == "print_au":
        screen_print_au_window()
    elif screen == "print_pc":
        screen_print_pc_window()
    elif screen == "help":
        screen_help_window()
    elif screen == "exit":
        screen_exit_window()

    else:
        screen_not_impl_window()


# ---------------------------
# Helpers
# ---------------------------

def _centered_buttons(labels_and_targets: Iterable[tuple[str, str]]):
    left, mid, right = st.columns([0.10, 0.80, 0.10])
    with mid:
        for label, target in labels_and_targets:
            screen = str(st.session_state.get("vxp_screen", ""))
            safe_t = "".join(ch if ch.isalnum() else "_" for ch in str(target))
            k = f"btn_{screen}_{safe_t}"
            if st.button(label, use_container_width=True, key=k):
                go(target)
                st.rerun()


def _ensure_has_run_data(view_run: int) -> Dict[str, object]:
    data = current_run_data(view_run)
    return data


def _solution_text(view_run: int, data: Dict[str, object]) -> str:
    """Training-only solution text to resemble legacy VXP output."""
    # data: Dict[str, Measurement]
    lines: List[str] = []
    lines.append("BO105   MAIN ROTOR  TRACK & BALANCE")
    lines.append("OPTION: B   STROBEX MODE: B")
    lines.append(f"RUN: {view_run}   ID: TRAINING")
    lines.append("")

    # Summary per regime
    for r in REGIMES:
        if r not in data:
            continue
        m = data[r]
        lines.append("=" * 62)
        lines.append(f"REGIME: {REGIME_LABEL[r]}")
        lines.append(f"TRACK SPREAD: {track_spread(m):0.1f} mm   (limit {track_limit(r):0.0f} mm)")
        lines.append(
            f"BALANCE: {m.balance.amp_ips:0.3f} ips @ {clock_label(m.balance.phase_deg)}   (limit {balance_limit(r):0.2f} ips)"
        )
        lines.append("")

    # Suggested corrections (very simplified)
    lines.append("=" * 62)
    lines.append("SUGGESTED CORRECTIONS (training)")

    pl = suggest_pitchlink(data)
    tt = suggest_trimtabs(data)
    w_blade, w_g = suggest_weight(data)

    lines.append("")
    lines.append("Pitch links (turns)  [CW lowers tip / CCW raises tip]")
    for b in BLADES:
        lines.append(f"  {b}: {pl.get(b, 0.0):+0.2f}")

    lines.append("")
    lines.append("Trim tabs (mm)  [Down lowers tip / Up raises tip]  (horizontal only)")
    for b in BLADES:
        lines.append(f"  {b}: {tt.get(b, 0.0):+0.2f}")

    lines.append("")
    lines.append("Balance weight (ground/hover/horizontal: pick worst reading)")
    lines.append(f"  Add ~{w_g:0.0f} g at blade bolt: {w_blade}")

    lines.append("")
    lines.append("NOTE: Training output only. Not for real aircraft work.")
    return "\n".join(lines)


# ---------------------------
# Main Rotor procedure
# ---------------------------

def screen_mr_menu_window():
    run = int(st.session_state.vxp_run)
    win_caption(f"Main Rotor Balance Run {run}", active=True)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='display:flex; justify-content:space-between; font-weight:900;'>"
        "<div>Tracking &amp; Balance – Option B</div>"
        f"<div>Run {run}</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    _centered_buttons(
        [
            ("COLLECT", "collect"),
            ("MEASUREMENTS LIST", "meas_list"),
            ("MEASUREMENTS GRAPH", "meas_graph"),
            ("SETTINGS", "settings"),
            ("SOLUTION", "solution"),
            ("SOLUTION GRAPH", "solution_graph"),
            ("NEXT RUN", "next_run_prompt"),
            # Recuperados (existían en el prototipo inicial)
            ("TEST SENSORS", "test_sensors"),
            ("FASTRAK OPTIONS", "fastrak_options"),
        ]
    )

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    right_close_button("Close", on_click=lambda: go("home"))


def screen_collect_window():
    run = int(st.session_state.vxp_run)
    win_caption(f"Main Rotor: Run {run}    Day Mode", active=True)

    st.markdown(
        f"<div style='display:flex; justify-content:space-between; font-weight:900; margin-top:6px;'>"
        f"<div>RPM&nbsp;&nbsp;{BO105_DISPLAY_RPM:.1f}</div><div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    done = completed_set(run)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    for r in REGIMES:
        cols = st.columns([0.84, 0.16])
        with cols[0]:
            if st.button(REGIME_LABEL[r], use_container_width=True, key=f"reg_{run}_{r}"):
                st.session_state.vxp_pending_regime = r
                go("acquire")
                st.rerun()
        with cols[1]:
            st.markdown(
                f"<div style='font-size:22px; font-weight:900; padding-top:10px;'>{'✓' if r in done else ''}</div>",
                unsafe_allow_html=True,
            )

    if run == 3 and len(done) == 3 and all_ok(current_run_data(3)):
        st.markdown(
            "<div class='vxp-label' style='margin-top:10px;'>✓ RUN 3 COMPLETE — PARAMETERS OK</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    right_close_button("Close", on_click=lambda: go("mr_menu"))


def screen_acquire_window():
    win_caption("ACQUIRING …", active=True)
    run = int(st.session_state.vxp_run)
    regime = st.session_state.get("vxp_pending_regime")
    if not regime:
        right_close_button("Close", on_click=lambda: go("collect"))
        return

    st.markdown(
        f"<div class='vxp-label' style='margin-top:8px;'>{REGIME_LABEL[regime]}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='vxp-label'>RPM {BO105_DISPLAY_RPM:.1f}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='vxp-mono'>M/R LAT\t\tACQUIRING\n\nM/R OBT\t\tACQUIRING</div>", unsafe_allow_html=True)

    if not st.session_state.get("vxp_acq_in_progress", False):
        st.session_state.vxp_acq_in_progress = True
        p = st.progress(0)
        for i in range(80):
            time.sleep(0.01)
            p.progress(i + 1)

        meas = simulate_measurement(run, regime, st.session_state.vxp_adjustments)
        current_run_data(run)[regime] = meas
        completed_set(run).add(regime)

        _log(f"Acquire: run {run} / {regime}")

        st.session_state.vxp_pending_regime = None
        st.session_state.vxp_acq_in_progress = False
        go("collect")
        st.rerun()

    right_close_button("Close", on_click=lambda: go("collect"))


def screen_meas_list_window():
    win_caption("MEASUREMENTS LIST", active=True)
    view_run = run_selector_inline(key="run_selector_generic")
    data = current_run_data(view_run)
    if not data:
        st.write("No measurements for this run yet. Go to COLLECT.")
        right_close_button("Close", on_click=lambda: go("mr_menu"))
        return

    st.markdown(
        f"<div class='vxp-mono' style='height:380px; overflow:auto; margin-top:8px;'>{legacy_results_text(view_run, data)}</div>",
        unsafe_allow_html=True,
    )
    right_close_button("Close", on_click=lambda: go("mr_menu"))


def screen_meas_graph_window():
    win_caption("MEASUREMENTS GRAPH", active=True)

    ctrl = st.columns([0.22, 0.78], gap="small")
    with ctrl[0]:
        view_run = run_selector_inline(key="run_selector_meas_graph")

    data = current_run_data(view_run)
    if not data:
        st.write("No measurements for this run yet. Go to COLLECT.")
        right_close_button("Close", on_click=lambda: go("mr_menu"))
        return

    available = [r for r in REGIMES if r in data]
    with ctrl[1]:
        sel = st.selectbox(
            "Select Measurement",
            available,
            format_func=lambda rr: REGIME_LABEL[rr],
            key=f"meas_sel_run_{view_run}",
        )

    m = data[sel]
    compare = {r: data[r] for r in REGIMES if r in data}

    left, right = st.columns([0.56, 0.44], gap="medium")
    with left:
        st.markdown(
            f"<div class='vxp-mono' style='height:330px; overflow:auto;'>{legacy_results_text(view_run, data)}</div>",
            unsafe_allow_html=True,
        )
    with right:
        st.pyplot(plot_track_marker(m), clear_figure=True)
        st.pyplot(plot_track_graph(compare), clear_figure=True)
        st.pyplot(plot_polar_compare(compare), clear_figure=True)

    right_close_button("Close", on_click=lambda: go("mr_menu"))


def screen_settings_window():
    win_caption("SETTINGS", active=True)
    run_selector_inline(key="run_selector_settings")

    regime = st.selectbox(
        "Regime",
        options=REGIMES,
        format_func=lambda r: REGIME_LABEL[r],
        key="settings_regime",
    )
    adj = st.session_state.vxp_adjustments[regime]

    hdr = st.columns([0.20, 0.27, 0.27, 0.26])
    hdr[0].markdown("**Blade**")
    hdr[1].markdown("**Pitch link (turns)**")
    hdr[2].markdown("**Trim tab (mm)**")
    hdr[3].markdown("**Bolt weight (g)**")

    for b in BLADES:
        row = st.columns([0.20, 0.27, 0.27, 0.26])
        row[0].markdown(b)
        adj["pitch_turns"][b] = float(
            row[1].number_input("", value=float(adj["pitch_turns"][b]), step=0.25, key=f"pl_{regime}_{b}")
        )
        adj["trim_mm"][b] = float(
            row[2].number_input("", value=float(adj["trim_mm"][b]), step=0.5, key=f"tt_{regime}_{b}")
        )
        adj["bolt_g"][b] = float(
            row[3].number_input("", value=float(adj["bolt_g"][b]), step=5.0, key=f"wt_{regime}_{b}")
        )

    right_close_button("Close", on_click=lambda: go("mr_menu"))


def screen_solution_window():
    win_caption("SOLUTION", active=True)
    view_run = run_selector_inline(key="run_selector_solution")
    data = current_run_data(view_run)
    if not data:
        st.write("No measurements for this run yet. Go to COLLECT.")
        right_close_button("Close", on_click=lambda: go("mr_menu"))
        return

    st.selectbox("", options=["BALANCE ONLY", "TRACK ONLY", "TRACK + BALANCE"], index=2, key="sol_type")

    _centered_buttons(
        [
            ("SHOW SOLUTION (TEXT)", "solution_text"),
            ("SHOW SOLUTION (GRAPH)", "solution_graph"),
            ("Close", "mr_menu"),
        ]
    )


def screen_solution_text_window():
    win_caption("SOLUTION", active=True)
    view_run = run_selector_inline(key="run_selector_solution_text")
    data = current_run_data(view_run)
    if not data:
        st.write("No measurements for this run yet. Go to COLLECT.")
        right_close_button("Close", on_click=lambda: go("mr_menu"))
        return

    txt = _solution_text(view_run, data)
    st.markdown(
        f"<div class='vxp-mono' style='height:380px; overflow:auto; margin-top:8px;'>{txt}</div>",
        unsafe_allow_html=True,
    )
    right_close_button("Close", on_click=lambda: go("mr_menu"))


def screen_solution_graph_window():
    win_caption("SOLUTION GRAPH", active=True)
    view_run = run_selector_inline(key="run_selector_solution_graph")
    data = current_run_data(view_run)
    if not data:
        st.write("No measurements for this run yet. Go to COLLECT.")
        right_close_button("Close", on_click=lambda: go("mr_menu"))
        return

    compare = {r: data[r] for r in REGIMES if r in data}

    left, right = st.columns([0.55, 0.45], gap="medium")

    with left:
        st.markdown(
            f"<div class='vxp-mono' style='height:360px; overflow:auto;'>{_solution_text(view_run, data)}</div>",
            unsafe_allow_html=True,
        )

    with right:
        # Show one polar per available regime (stacked), plus compare.
        for r in REGIMES:
            if r not in compare:
                continue
            st.pyplot(plot_polar(compare[r]), clear_figure=True)
        if compare:
            st.pyplot(plot_polar_compare(compare), clear_figure=True)

    right_close_button("Close", on_click=lambda: go("mr_menu"))


def screen_next_run_window():
    run = int(st.session_state.vxp_run)
    win_caption("NEXT RUN", active=True)
    st.write(f"Current run: {run}. This simulator supports up to 3 runs.")
    cols = st.columns([0.5, 0.5])

    with cols[0]:
        if st.button(
            "Start Next Run",
            use_container_width=True,
            disabled=(run >= 3),
            key=f"next_run_start_{run}",
        ):
            st.session_state.vxp_run = run + 1
            ensure_run(run + 1)
            go("mr_menu")
            _log(f"Next run: {run + 1}")
            st.rerun()
    with cols[1]:
        if st.button("Cancel", use_container_width=True, key=f"next_run_cancel_{run}"):
            go("mr_menu")
            st.rerun()


# ---------------------------
# Aircraft Info / Note Codes
# ---------------------------

def screen_aircraft_info_window():
    win_caption("AIRCRAFT INFO", active=True)

    info: Dict[str, object] = st.session_state.vxp_aircraft

    c1, c2 = st.columns([0.35, 0.65], gap="large")
    with c1:
        st.write("WEIGHT:")
        st.write("C.G.:")
        st.write("HOURS:")
        st.write("INITIALS:")
    with c2:
        info["weight"] = float(st.number_input("", value=float(info.get("weight", 0.0)), key="weight_in"))
        info["cg"] = float(st.number_input("", value=float(info.get("cg", 0.0)), key="cg_in"))
        info["hours"] = float(st.number_input("", value=float(info.get("hours", 0.0)), key="hrs_in"))
        info["initials"] = str(st.text_input("", value=str(info.get("initials", "")), key="init_in"))

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    if st.button("Note Codes", use_container_width=True, key="aircraft_note_codes"):
        go("note_codes")
        st.rerun()

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    right_close_button("Close", on_click=lambda: go("home"))


def screen_note_codes_window():
    win_caption("NOTE CODES", active=True)

    codes = [
        (0, "Scheduled Insp"),
        (1, "Balance"),
        (2, "Troubleshooting"),
        (3, "Low Freq Vib"),
        (4, "Med Freq Vib"),
        (5, "High Freq Vib"),
        (6, "Component Change"),
    ]

    selected: set = st.session_state.vxp_note_codes

    for code, name in codes:
        label = f"{code:02d} {name}"
        checked = "✓" if code in selected else ""
        cols = st.columns([0.85, 0.15])
        with cols[0]:
            if st.button(label, use_container_width=True, key=f"nc_{code}"):
                if code in selected:
                    selected.remove(code)
                else:
                    selected.add(code)
                _log(f"Note code toggle: {code:02d} {name} -> {'ON' if code in selected else 'OFF'}")
                st.rerun()
        with cols[1]:
            st.markdown(
                f"<div style='font-size:20px; font-weight:900; padding-top:10px;'>{checked}</div>",
                unsafe_allow_html=True,
            )

    right_close_button("Close", on_click=lambda: go("aircraft_info"))


# ---------------------------
# Recovered menu items
# ---------------------------

def screen_test_sensors_window():
    win_caption("TEST SENSORS", active=True)

    st.markdown("<div class='vxp-label' style='margin-top:8px;'>SIMULATED SENSOR CHECK</div>", unsafe_allow_html=True)

    # Fake live values (training)
    col1, col2 = st.columns([0.5, 0.5], gap="medium")
    with col1:
        st.markdown("<div class='vxp-mono' style='height:220px; overflow:auto;'>", unsafe_allow_html=True)
        st.markdown(
            "\n".join(
                [
                    "MAG PICKUP: OK",
                    f"PHASE: {random.randint(0, 359):03d} deg",
                    f"RPM: {BO105_DISPLAY_RPM:0.1f}",
                    "",
                    "ACCEL (LAT): OK",
                    f"1P: {random.uniform(0.02, 0.20):0.3f} IPS",
                    "",
                    "ACCEL (OBT): OK",
                    f"1P: {random.uniform(0.02, 0.20):0.3f} IPS",
                ]
            ),
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.write("(Training) This is a basic functional check placeholder.")
        st.write("Later we can map this to your simulated channels and diagnostics.")

    right_close_button("Close", on_click=lambda: go("mr_menu"))


def screen_fastrak_options_window():
    win_caption("FASTRAK OPTIONS", active=True)

    st.write("(Placeholder) FASTRAK options were present in the legacy menu.")
    st.write("We can wire these to presets (limits, templates, report formats, etc.).")

    right_close_button("Close", on_click=lambda: go("mr_menu"))


# ---------------------------
# Other procedures (placeholders)
# ---------------------------

def screen_tail_rotor_menu_window():
    win_caption("Tail Rotor Balance Run 1", active=True)
    st.write("(Placeholder) Tail Rotor procedure UI goes here.")
    right_close_button("Close", on_click=lambda: go("home"))


def screen_driveshaft_menu_window():
    win_caption("T/R Driveshaft Balance Run 1", active=True)
    st.write("(Placeholder) Driveshaft procedure UI goes here.")
    right_close_button("Close", on_click=lambda: go("home"))


def screen_vibration_signatures_window():
    win_caption("Vibration Signatures", active=True)
    st.write("(Placeholder) Signature library, comparison and classification screens.")
    right_close_button("Close", on_click=lambda: go("home"))


def screen_measurements_only_window():
    win_caption("Measurements Only", active=True)
    st.write("(Placeholder) Measurement acquisition without solution.")
    right_close_button("Close", on_click=lambda: go("home"))


def screen_setup_utils_window():
    win_caption("Setup / Utilities", active=True)
    st.write("(Placeholder) Setup utilities, calibration and device configuration.")
    right_close_button("Close", on_click=lambda: go("home"))


# ---------------------------
# Toolbar windows
# ---------------------------

def screen_viewlog_window():
    win_caption("VIEW LOG", active=True)
    log: List[str] = st.session_state.vxp_event_log
    if not log:
        st.write("(No events yet)")
    else:
        st.markdown(
            "<div class='vxp-mono' style='height:380px; overflow:auto; margin-top:8px;'>"
            + "\n".join(log)
            + "</div>",
            unsafe_allow_html=True,
        )
    right_close_button("Close", on_click=lambda: go("home"))


def screen_download_window():
    win_caption("DOWNLOAD", active=True)

    view_run = run_selector_inline(key="run_selector_download")
    data = current_run_data(view_run)

    txt = legacy_results_text(view_run, data) if data else "(No measurements)"
    blob = {
        "run": view_run,
        "aircraft": st.session_state.vxp_aircraft,
        "note_codes": sorted(list(st.session_state.vxp_note_codes)),
        "measurements": {
            r: {
                "regime": r,
                "balance": {
                    "amp_ips": float(data[r].balance.amp_ips),
                    "phase_deg": float(data[r].balance.phase_deg),
                    "rpm": float(data[r].balance.rpm),
                },
                "track_mm": {b: float(data[r].track_mm[b]) for b in BLADES},
            }
            for r in data.keys()
        },
    }

    st.download_button(
        "Download measurements (text)",
        data=txt,
        file_name=f"vxp_run_{view_run}_measurements.txt",
        use_container_width=True,
        key=f"dl_txt_{view_run}",
    )

    st.download_button(
        "Download run (json)",
        data=json.dumps(blob, indent=2),
        file_name=f"vxp_run_{view_run}.json",
        use_container_width=True,
        key=f"dl_json_{view_run}",
    )

    right_close_button("Close", on_click=lambda: go("home"))


def screen_upload_window():
    win_caption("UPLOAD", active=True)

    up = st.file_uploader("Import run JSON", type=["json"], key="uploader_run_json")
    if up is not None:
        try:
            blob = json.loads(up.read().decode("utf-8"))
            run = int(blob.get("run", 1))
            ensure_run(run)
            # We only restore metadata here. Measurements import can be added once we freeze a stable schema.
            st.session_state.vxp_aircraft.update(blob.get("aircraft", {}))
            st.session_state.vxp_note_codes = set(blob.get("note_codes", []))
            _log(f"Upload: imported metadata for run {run}")
            st.success(f"Imported aircraft + note codes (run {run}).")
        except Exception as e:
            st.error(f"Could not import: {e}")

    st.write("(Training) This upload currently restores aircraft info + note codes.")
    right_close_button("Close", on_click=lambda: go("home"))


def screen_print_au_window():
    win_caption("PRINT AU", active=True)
    st.write("(Placeholder) Print AU report.")
    st.write("We can generate a PDF from current run data once you confirm the legacy layout.")
    right_close_button("Close", on_click=lambda: go("home"))


def screen_print_pc_window():
    win_caption("PRINT PC", active=True)
    st.write("(Placeholder) Print PC report (disabled in toolbar icon set).")
    right_close_button("Close", on_click=lambda: go("home"))


def screen_help_window():
    win_caption("HELP", active=True)
    st.write("Shortcuts:")
    st.write("- Use the left toolbar icons to open LOG / HELP / DOWNLOAD / UPLOAD.")
    st.write("- Start in Select Procedure, then go to Main Rotor → COLLECT.")
    st.write("- Use NEXT RUN after applying simulated corrections.")
    right_close_button("Close", on_click=lambda: go("home"))


def screen_exit_window():
    win_caption("EXIT", active=True)
    st.write("Streamlit cannot close the browser window programmatically.")
    st.write("Close this tab/window to exit.")
    right_close_button("Close", on_click=lambda: go("home"))


# ---------------------------
# Fallback
# ---------------------------

def screen_not_impl_window():
    win_caption("VXP", active=True)
    st.write("Pantalla en desarrollo.")
    right_close_button("Close", on_click=lambda: go("home"))
