import streamlit as st

from vxp.styles import XP_CSS
from vxp.toolbar import render_toolbar
from vxp.ui import init_state, handle_nav_from_query_params, render_desktop

def main():
    # La máquina objetivo es XGA 1024×768 (4:3). El CSS fuerza el marco a esa geometría.
    st.set_page_config(page_title="Chadwick-Helmuth VXP", layout="wide")
    init_state()

    st.markdown(XP_CSS, unsafe_allow_html=True)

    # Procesa navegación por query params (toolbar / menús)
    # tras init_state para que pueda tocar session_state.
    handle_nav_from_query_params()

    # --- Shell superior (título + menús) ---
    st.markdown(
        "<div class='vxp-shell-titlebar'>"
        "<div>Chadwick-Helmuth VXP  —  TORMES</div>"
        "<div class='vxp-winbtns'>"
        "<div class='vxp-winbtn'>_</div>"
        "<div class='vxp-winbtn'>□</div>"
        "<div class='vxp-winbtn'>✕</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    # Menú: SOLO visual (sin links, sin pestañas nuevas)
    st.markdown(
        "<div class='vxp-shell-menubar'>"
        "<span>File</span><span>View</span><span>Log</span><span>Test AU</span><span>Settings</span><span>Help</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Cuerpo: icon bar + escritorio (MDI) ---
    left, right = st.columns([0.10, 0.90], gap="small")
    with left:
        # Mantiene apariencia (iconos) pero permite navegación interna.
        render_toolbar(interactive=True)
    with right:
        render_desktop()

    # Barra de estado (simple)
    st.markdown(
        "<div class='vxp-shell-statusbar'><div>READY</div><div>XGA 1024×768</div></div>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
