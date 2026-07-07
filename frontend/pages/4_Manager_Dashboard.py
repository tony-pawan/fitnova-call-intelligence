import os
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from sqlalchemy.orm import Session
from backend.app.database.session import SessionLocal
from backend.app.services.dashboard_service import DashboardService
from frontend.sidebar import render_sidebar

st.set_page_config(
    page_title="FitNova - Manager Analytics",
    page_icon="📈",
    layout="wide"
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
    
    .saas-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Render sidebar
render_sidebar()

# Role Access Control check
if st.session_state.get("role", "Manager") != "Manager":
    st.warning("⚠️ Access Denied: The Manager Dashboard is restricted to Managers. Please switch your role to Manager in the sidebar.")
    st.stop()

# Establish DB Session context
db: Session = SessionLocal()

# Backend API config
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

try:
    st.markdown('<h1 class="main-title">Manager Quality Analytics Portal</h1>', unsafe_allow_html=True)
    st.markdown("Track advisor performance leaderboards, analyze script compliance rates, and explore issue severities distributions.")

    # 1. Filters block
    filter_opts = DashboardService.get_filter_options(db)
    advisors_list = filter_opts["advisors"]
    advisors_map = {a["id"]: a["name"] for a in advisors_list}

    with st.expander("🔍 Filter Manager Analytics Dashboard", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            adv_id_choice = st.selectbox(
                "Filter by Advisor Profile:",
                options=[None] + [a["id"] for a in advisors_list],
                format_func=lambda x: "All Advisors" if x is None else advisors_map.get(x, f"ID {x}")
            )
        with col_f2:
            status_choice = st.selectbox(
                "Filter by Call status:",
                options=[None] + filter_opts["statuses"],
                format_func=lambda x: "All Statuses" if x is None else str(x)
            )
        with col_f3:
            min_score = st.slider("Minimum Quality Score:", min_value=0, max_value=100, value=0, step=5)

    # Dynamics Filters packaging
    active_filters = {
        "advisor_id": adv_id_choice,
        "status": status_choice,
        "min_score": min_score if min_score > 0 else None
    }

    # Aggregate filtered stats from DashboardService
    dashboard_data = DashboardService.get_manager_dashboard(db, active_filters)

    # 2. Metric Cards Row (Updated to carry dynamic dispute statistics)
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric(label="Ingested Calls", value=dashboard_data["total_calls"])
    with m2:
        st.metric(label="Completed Audits", value=dashboard_data["completed_calls"])
    with m3:
        st.metric(label="Average AI Score", value=f"{dashboard_data['average_score']}%")
    with m4:
        st.metric(label="Compliance Rate", value=f"{dashboard_data['compliance_score']}%")
    with m5:
        st.metric(label="Pending Disputes", value=dashboard_data["pending_appeals"])

    # 3. Leaderboard Table
    st.markdown("---")
    st.subheader("Advisor Audits Leaderboard")
    leaderboard = dashboard_data["leaderboard"]
    if leaderboard:
        df_leader = pd.DataFrame(leaderboard)
        df_leader = df_leader.rename(columns={
            "advisor_id": "Advisor ID",
            "advisor_name": "Sales Advisor Name",
            "calls_processed": "Completed Calls Audited",
            "average_score": "Average Quality Score (%)"
        })
        df_leader["Average Quality Score (%)"] = df_leader["Average Quality Score (%)"].apply(lambda x: f"{x}%")
        st.dataframe(df_leader, use_container_width=True, hide_index=True)
    else:
        st.info("No active sales advisor records found.")

    # 4. Visualizations Section
    st.markdown("---")
    st.subheader("SaaS Visual Analytics Charts")
    
    col_dist, col_sev = st.columns(2)

    with col_dist:
        st.markdown("##### Quality Scores Distribution")
        # Build score distribution using recent calls data
        recent_calls = dashboard_data["recent_calls"]
        completed_calls = [c for c in recent_calls if c["overall_score"] is not None]
        
        if completed_calls:
            df_calls = pd.DataFrame(completed_calls)
            # Plotly Histogram
            fig_hist = px.histogram(
                df_calls, 
                x="overall_score", 
                nbins=10, 
                labels={"overall_score": "Quality Score (%)", "count": "Calls Count"},
                color_discrete_sequence=["#6366f1"]
            )
            fig_hist.update_layout(
                yaxis_title="Volume",
                margin=dict(l=20, r=20, t=10, b=20),
                height=250,
                plot_bgcolor="white"
            )
            fig_hist.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
            fig_hist.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No completed quality scores found to plot distribution.")

    with col_sev:
        st.markdown("##### Flagged Issue Severity Breakdown")
        severity_data = dashboard_data["severity_breakdown"]
        
        if any(v > 0 for v in severity_data.values()):
            df_sev = pd.DataFrame([{"Severity": k, "Volume": v} for k, v in severity_data.items() if v > 0])
            # Plotly Pie Chart
            fig_pie = px.pie(
                df_sev, 
                values="Volume", 
                names="Severity", 
                color="Severity",
                color_discrete_map={
                    "Low": "#3b82f6",
                    "Medium": "#eab308",
                    "High": "#f97316",
                    "Critical": "#ef4444"
                }
            )
            fig_pie.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                height=250
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.success("✅ No issues flagged. Compliance rate at 100%.")

    # 5. Top Issues and Calls Volume by Advisor Row
    st.markdown("---")
    col_issues, col_vol = st.columns(2)

    with col_issues:
        st.subheader("Top Flagged Compliance Risks")
        top_issues = dashboard_data["top_issues"]
        if top_issues:
            df_issues = pd.DataFrame(top_issues)
            df_issues = df_issues.rename(columns={
                "tag": "Compliance Risk / Issue Tag",
                "count": "Occurrences Count"
            })
            st.dataframe(df_issues, use_container_width=True, hide_index=True)
        else:
            st.info("No compliance issues flagged yet.")

    with col_vol:
        st.subheader("Audits Volume by Advisor")
        if leaderboard:
            df_vol = pd.DataFrame(leaderboard)
            # Plotly Bar Chart
            fig_bar = px.bar(
                df_vol, 
                x="advisor_name", 
                y="calls_processed",
                labels={"advisor_name": "Advisor", "calls_processed": "Calls Processed"},
                color_discrete_sequence=["#7c3aed"]
            )
            fig_bar.update_layout(
                yaxis_title="Volume",
                margin=dict(l=20, r=20, t=10, b=20),
                height=220,
                plot_bgcolor="white"
            )
            fig_bar.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
            fig_bar.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No calls processed count found.")

    # 6. Appeals Review Queue Section
    st.markdown("---")
    st.subheader("⚖️ Disputes & Appeals Review Queue")
    
    manager_queue = DashboardService.get_manager_queue(db)
    if not manager_queue:
        st.info("No dispute appeals submitted by sales advisors yet.")
    else:
        # Build queue dataframe
        queue_df = pd.DataFrame(manager_queue)
        queue_df = queue_df.rename(columns={
            "id": "Appeal ID",
            "call_id": "Call ID",
            "advisor_name": "Sales Advisor",
            "tag": "Flagged Issue Tag",
            "severity": "Severity",
            "reason": "Dispute Reason Given",
            "status": "Appeal Status",
            "created_at": "File Date"
        })
        queue_df = queue_df.drop(columns=["quote"], errors="ignore")
        queue_df["File Date"] = queue_df["File Date"].apply(lambda x: x.split("T")[0] if "T" in x else x)
        
        st.dataframe(queue_df, use_container_width=True, hide_index=True)
        
        # Display review selector for Pending items
        pending_appeals = [a for a in manager_queue if a["status"] == "Pending"]
        if pending_appeals:
            st.markdown("##### Resolve Pending Appeals")
            
            review_options = {a["id"]: f"Appeal ID {a['id']} | Call ID {a['call_id']} | Advisor: {a['advisor_name']} | Tag: {a['tag']}" for a in pending_appeals}
            selected_appeal_id = st.selectbox(
                "Select Appeal to Review & Resolve:",
                options=list(review_options.keys()),
                format_func=lambda x: review_options[x]
            )
            
            if selected_appeal_id:
                selected_appeal = next((a for a in pending_appeals if a["id"] == selected_appeal_id), None)
                if selected_appeal:
                    st.markdown(f"""
                    <div class="saas-card" style="background-color: #f8fafc; border-left: 4px solid #eab308;">
                        <strong>Advisor disputing tag:</strong> {selected_appeal['advisor_name']}
                        <br><strong>Flagged Issue Tag:</strong> {selected_appeal['tag']} (Severity: {selected_appeal['severity']})
                        <br><strong>Original Transcript Quote:</strong> <em>"{selected_appeal['quote']}"</em>
                        <hr style="margin: 8px 0;">
                        <strong>Advisor Dispute Reason:</strong> {selected_appeal['reason']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Review action buttons
                    col_approve, col_reject = st.columns([1, 1])
                    
                    with col_approve:
                        if st.button("✅ Approve Appeal", type="primary", use_container_width=True):
                            try:
                                resp = requests.patch(
                                    f"{BACKEND_URL}/appeals/{selected_appeal_id}",
                                    json={"status": "Approved"},
                                    timeout=5
                                )
                                if resp.status_code == 200:
                                    st.success(f"Appeal ID {selected_appeal_id} successfully APPROVED.")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to resolve appeal: {resp.text}")
                            except Exception as err:
                                st.error(f"Network error resolving appeal: {err}")
                                
                    with col_reject:
                        if st.button("❌ Reject Appeal", type="secondary", use_container_width=True):
                            try:
                                resp = requests.patch(
                                    f"{BACKEND_URL}/appeals/{selected_appeal_id}",
                                    json={"status": "Rejected"},
                                    timeout=5
                                )
                                if resp.status_code == 200:
                                    st.warning(f"Appeal ID {selected_appeal_id} successfully REJECTED.")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to resolve appeal: {resp.text}")
                            except Exception as err:
                                st.error(f"Network error resolving appeal: {err}")
        else:
            st.success("✅ **All submitted disputes have been resolved.** Review queue is empty.")

finally:
    db.close()
