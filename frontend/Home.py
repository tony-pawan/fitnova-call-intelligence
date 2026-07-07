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
    role = st.session_state.get("role", "Manager")

    st.markdown('<h1 class="main-title">FitNova Sales Intelligence</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">SaaS Evaluation Dashboard for Sales Needs Discovery, Script Compliance, and Call Processing Pipelines.</p>', unsafe_allow_html=True)

    # 1. Gather filter list from service
    filter_opts = DashboardService.get_filter_options(db)
    advisors_list = filter_opts["advisors"]
    advisors_map = {a["id"]: a["name"] for a in advisors_list}

    # 2. Render Dashboards based on simulated active role
    if role == "Manager":
        # -----------------------------
        # MANAGER OVERVIEW FLOW
        # -----------------------------
        st.subheader("Platform Metrics")
        
        # Aggregation calculations
        dashboard_data = DashboardService.get_manager_dashboard(db)
        
        # Render Metrics
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        with m1:
            st.metric(label="Total Ingested", value=dashboard_data["total_calls"])
        with m2:
            st.metric(label="Processed Calls", value=dashboard_data["completed_calls"])
        with m3:
            st.metric(label="Queue Backlog", value=dashboard_data["queue_calls"])
        with m4:
            st.metric(label="Avg AI Score", value=f"{dashboard_data['average_score']}%")
        with m5:
            st.metric(label="Compliance Score", value=f"{dashboard_data['compliance_score']}%")
        with m6:
            st.metric(label="Pending Appeals", value="0", delta="Mock")

        # Filters Sidebar/Header Row
        st.markdown("---")
        st.subheader("Global Activity Registry")
        
        with st.expander("🔍 Filter & Search Call Records", expanded=True):
            col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
            with col_f1:
                search_id = st.text_input("Search by Call ID:", value="", placeholder="e.g. 1")
            with col_f2:
                adv_id_choice = st.selectbox(
                    "Filter by Advisor:",
                    options=[None] + [a["id"] for a in advisors_list],
                    format_func=lambda x: "All Advisors" if x is None else advisors_map.get(x, f"ID {x}")
                )
            with col_f3:
                status_choice = st.selectbox(
                    "Filter by Status:",
                    options=[None] + filter_opts["statuses"],
                    format_func=lambda x: "All Statuses" if x is None else str(x)
                )
            with col_f4:
                min_score = st.slider("Minimum Score:", min_value=0, max_value=100, value=0, step=5)
            with col_f5:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Clear All Filters", use_container_width=True):
                    st.rerun()

        # Dynamic Filters Packaging
        active_filters = {
            "search_id": search_id.strip() if search_id.strip() else None,
            "advisor_id": adv_id_choice,
            "status": status_choice,
            "min_score": min_score if min_score > 0 else None
        }

        # Query dynamic registry list
        filtered_data = DashboardService.get_manager_dashboard(db, active_filters)
        recent_calls = filtered_data["recent_calls"]

        # Main display layout
        col_table, col_pipeline = st.columns([5, 3])

        with col_table:
            st.markdown("##### Filtered Records")
            if recent_calls:
                call_df = pd.DataFrame(recent_calls)
                # Format dataframe for SaaS display
                call_df = call_df.rename(columns={
                    "id": "Call ID",
                    "advisor_name": "Advisor",
                    "status": "Pipeline Status",
                    "overall_score": "Overall Score",
                    "created_at": "Ingestion Date",
                    "duration_seconds": "Duration"
                })
                call_df["Overall Score"] = call_df["Overall Score"].apply(lambda x: f"{x}%" if x is not None else "--")
                call_df["Duration"] = call_df["Duration"].apply(lambda x: f"{x:.1f}s" if x is not None else "--")
                call_df["Ingestion Date"] = call_df["Ingestion Date"].apply(lambda x: x.split("T")[0] if "T" in x else x)
                
                st.dataframe(call_df, use_container_width=True, hide_index=True)
                
                # Navigate selector
                st.markdown("##### Quick Inspect")
                inspect_call_id = st.selectbox(
                    "Choose Call ID to inspect in detail:",
                    options=[c["id"] for c in recent_calls]
                )
                if st.button("View Detailed Scorecard", type="primary"):
                    st.info(f"Please head to the **Call Details** page in the sidebar and select Call ID: `{inspect_call_id}`")
            else:
                st.info("No matching call records found in database.")

        with col_pipeline:
            st.markdown("##### Ingestion Pipelines Status")
            
            # Count statuses
            status_summary = {
                "Uploaded": len([c for c in recent_calls if c["status"] == CallStatus.Uploaded.value]),
                "Queued": len([c for c in recent_calls if c["status"] == CallStatus.Queued.value]),
                "Processing": len([c for c in recent_calls if c["status"] == CallStatus.Processing.value]),
                "Completed": len([c for c in recent_calls if c["status"] == CallStatus.Completed.value]),
                "Failed": len([c for c in recent_calls if c["status"] == CallStatus.Failed.value])
            }
            
            for status, count in status_summary.items():
                st.markdown(f"""
                <div class="saas-card" style="padding: 10px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; font-size: 0.85rem;">{status}</span>
                        <span class="status-badge" style="background-color: #f1f5f9; padding: 2px 8px;">{count} calls</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("##### Latest Ingestion Activity")
            # Collect timeline items
            latest_activities = []
            for c in recent_calls[:5]:
                details = DashboardService.get_call_details(db, c["id"])
                if details and details["timeline"]:
                    latest_ev = details["timeline"][-1]
                    latest_activities.append(f"Call {c['id']}: {latest_ev['event']} ({latest_ev['timestamp'].split('T')[1][:8] if 'T' in latest_ev['timestamp'] else str(latest_ev['timestamp'])})")
            
            if latest_activities:
                for act in latest_activities:
                    st.caption(f"⚡ {act}")
            else:
                st.caption("No recent timeline events found.")

    else:
        # -----------------------------
        # ADVISOR OVERVIEW FLOW
        # -----------------------------
        advisor_id = st.session_state.get("advisor_id")
        if not advisor_id:
            st.warning("Please select a simulated advisor profile from the sidebar.")
        else:
            adv_name = advisors_map.get(advisor_id, "Unknown Advisor")
            st.subheader(f"Advisor Overview: {adv_name}")

            # Grab stats
            adv_data = DashboardService.get_advisor_dashboard(db, advisor_id)
            
            # Show Metrics
            a1, a2, a3, a4 = st.columns(4)
            with a1:
                st.metric(label="Simulated Profile", value=adv_name)
            with a2:
                st.metric(label="My Total Calls", value=len(adv_data["recent_calls"]))
            with a3:
                st.metric(label="My Average Score", value=f"{adv_data['average_score']}%")
            with a4:
                st.metric(label="Pending Appeals", value="0", delta="Mock")

            st.markdown("---")
            col_adv_table, col_adv_recs = st.columns([5, 3])

            with col_adv_table:
                st.markdown("##### My Recent Ingested Calls")
                my_calls = adv_data["recent_calls"]
                if my_calls:
                    my_df = pd.DataFrame(my_calls)
                    my_df = my_df.rename(columns={
                        "id": "Call ID",
                        "status": "Pipeline Status",
                        "overall_score": "Overall Score",
                        "created_at": "Ingestion Date",
                        "duration_seconds": "Duration"
                    })
                    my_df["Overall Score"] = my_df["Overall Score"].apply(lambda x: f"{x}%" if x is not None else "--")
                    my_df["Duration"] = my_df["Duration"].apply(lambda x: f"{x:.1f}s" if x is not None else "--")
                    my_df["Ingestion Date"] = my_df["Ingestion Date"].apply(lambda x: x.split("T")[0] if "T" in x else x)
                    
                    st.dataframe(my_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No calls uploaded for your advisor profile yet.")

            with col_adv_recs:
                st.markdown("##### Recent Action Items & Training Suggestions")
                if adv_data["recent_recommendations"]:
                    for rec in adv_data["recent_recommendations"]:
                        st.markdown(f"""
                        <div class="saas-card" style="padding: 12px; margin-bottom: 8px; border-left: 4px solid #6366f1;">
                            <span style="font-size: 0.85rem; font-weight: 500;">{rec}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Upload completed analysis recordings to view suggestions.")

finally:
    db.close()
