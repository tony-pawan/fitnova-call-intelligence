import os
import sys

# Ensure project root is in sys.path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import SessionLocal
from backend.app.services.dashboard_service import DashboardService
from backend.app.models.call import CallStatus
from frontend.sidebar import render_sidebar

# Page config
st.set_page_config(
    page_title="FitNova Sales Call Intelligence System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom SaaS dashboard styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }
    
    .main-title {
        font-size: 2.2rem;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        font-size: 1rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    
    .saas-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.02);
        margin-bottom: 1rem;
    }
    
    .stat-label {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        margin-top: 2px;
    }
    
    .sidebar-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize sidebar
render_sidebar()

# Establish DB Session context
db: Session = SessionLocal()

try:
    current_page = st.session_state.get("current_page", "Home")
    selected_call_id = st.session_state.get("selected_call_id", None)

    st.markdown('<h1 class="main-title">FitNova Sales Intelligence</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">AI-Powered Sales Call Audit, Compliance, and Analysis Platform.</p>', unsafe_allow_html=True)

    from frontend.views import render_home_view, render_dashboard_view, render_history_view, render_call_details_view

    # Route views dynamically
    if selected_call_id is not None:
        render_call_details_view(selected_call_id, db)
    elif current_page == "Home":
        render_home_view(db)
    elif current_page == "Dashboard":
        render_dashboard_view(db)
    elif current_page == "History":
        render_history_view(db)

finally:
    db.close()
