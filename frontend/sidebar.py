import streamlit as st
import os
import sys

# Ensure project root is in sys.path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.dashboard_service import DashboardService  # pyrefly: ignore [missing-import]
from backend.app.database.session import SessionLocal  # pyrefly: ignore [missing-import]

def render_sidebar():
    """
    Renders the custom single-user navigation sidebar.
    """
    st.markdown('<div class="sidebar-header">⚡ FitNova AI</div>', unsafe_allow_html=True)
    st.markdown("---")

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Home"

    menu_options = ["Home", "Dashboard", "History"]
    icons = {"Home": "🏠", "Dashboard": "📈", "History": "📋"}

    # Single-user navigation radio
    selected_page = st.radio(
        "Navigation:",
        options=menu_options,
        index=menu_options.index(st.session_state["current_page"]),
        format_func=lambda x: f"{icons.get(x, '')} {x}",
        key="navigation_selector"
    )

    # Force view routing changes to refresh active views
    if selected_page != st.session_state["current_page"]:
        st.session_state["current_page"] = selected_page
        # Clear selected call when navigating away from history/details
        if "selected_call_id" in st.session_state and selected_page != "History":
            del st.session_state["selected_call_id"]
        st.rerun()
