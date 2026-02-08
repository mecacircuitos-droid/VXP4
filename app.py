import streamlit as st

from vxp.styles import XP_CSS
from vxp.toolbar import render_toolbar
from vxp.ui import init_state, handle_nav_from_query_params, render_desktop


def main():
    st.set_page_config(page_title="Chadwick-Helmuth VXP", layout="wide")
    init_state()

    st.markdown(XP_CSS, unsafe_allow_html=True)

    # Procesa navegación por query params (toolbar / menús)
    handle_nav_from_query_params()

    # --- Shell superior (título + menús) ---
    # (1) Quitado “AS350B1 ID: Untitled”
    st.markdown(
        "<div class='vxp-shell-titlebar'>"
        "<div>Chadwick-Helmuth VXP</div>"
        "<div class='vxp-winbtns'>"
        "<div class='vxp-winbtn'>_</div>"
        "<div class='vxp-winbtn'>□</div>"
        "<div class='vxp-winbtn'>✕</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='vxp-shell-menubar'>"
        "<span>File</span><span>View</span><span>Log</span><span>Test AU</span><span>Settings</span><span>Help</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # --- Cuerpo: icon bar + escritorio (MDI) ---
    left, right = st.columns([0.10, 0.90], gap="small")
    with left:
        render_toolbar(interactive=True)
    with right:
        render_desktop()

    # (2) Barra inferior: se mantiene “READY” pero se quita la resolución
    st.markdown(
        "<div class='vxp-shell-statusbar'><div>READY</div><div></div></div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
