import os
import sys

# Ensure project root is in sys.path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
import plotly.express as px  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import SessionLocal  # pyrefly: ignore [missing-import]
from backend.app.services.dashboard_service import DashboardService  # pyrefly: ignore [missing-import]
from frontend.sidebar import render_sidebar

st.set_page_config(
    page_title="FitNova - Advisor Performance",
    page_icon="👤",
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
if st.session_state.get("role", "Manager") != "Advisor":
    st.warning("⚠️ Access Denied: The Advisor dashboard is restricted to Sales Advisors. Please switch your role to Advisor in the sidebar.")
    st.stop()

# Establish DB Session context
db: Session = SessionLocal()

try:
    advisor_id = st.session_state.get("advisor_id")
    if not advisor_id:
        st.warning("Please select a simulated advisor profile from the sidebar.")
    else:
        # Load advisor details
        filter_opts = DashboardService.get_filter_options(db)
        advisors_map = {a["id"]: a["name"] for a in filter_opts["advisors"]}
        advisor_name = advisors_map.get(advisor_id, "Unknown Advisor")

        st.markdown(f'<h1 class="main-title">Performance Portal: {advisor_name}</h1>', unsafe_allow_html=True)
        st.markdown("Monitor your sales audits quality scores, identify compliance gaps, and view custom training actions.")

        # Aggregate advisor dashboard data
        adv_data = DashboardService.get_advisor_dashboard(db, advisor_id)

        # 1. Metric Cards Row (Updated to carry dynamic dispute statistics)
        col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns(6)
        with col_m1:
            st.metric(label="Advisor Profile Name", value=advisor_name)
        with col_m2:
            st.metric(label="Total Calls Processed", value=len(adv_data["recent_calls"]))
        with col_m3:
            st.metric(label="My Average Score", value=f"{adv_data['average_score']}%")
        with col_m4:
            st.metric(label="Pending Disputes", value=adv_data["pending_appeals"])
        with col_m5:
            st.metric(label="Approved Disputes", value=adv_data["approved_appeals"])
        with col_m6:
            st.metric(label="Rejected Disputes", value=adv_data["rejected_appeals"])

        # 2. Main Analytics Plotly Visualizations & Recommendations
        st.markdown("---")
        col_chart, col_actions = st.columns([5, 3])

        with col_chart:
            st.subheader("Performance Trend Over Time")
            trend_data = adv_data["performance_trend"]
            if trend_data:
                df_trend = pd.DataFrame(trend_data)
                # Sort trend sequentially
                df_trend = df_trend.sort_values(by="date")
                
                # Plotly Line Chart
                fig = px.line(
                    df_trend, 
                    x="date", 
                    y="score", 
                    markers=True,
                    labels={"date": "Upload Date", "score": "AI Score (%)"}
                )
                fig.update_layout(
                    yaxis_range=[0, 105],
                    margin=dict(l=20, r=20, t=10, b=20),
                    height=300,
                    plot_bgcolor="white"
                )
                fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
                fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📈 **Trend data is empty.** Upload call recordings and complete AI evaluations first.")

        with col_actions:
            st.subheader("Top Suggestions & Insights")
            recs = adv_data["recent_recommendations"]
            if recs:
                for idx, item in enumerate(recs):
                    st.markdown(f"""
                    <div class="saas-card" style="padding: 12px; margin-bottom: 8px; border-left: 4px solid #4f46e5;">
                        <div style="font-weight: 600; font-size: 0.85rem; color: #4f46e5; margin-bottom: 4px;">Suggestion #{idx+1}</div>
                        <span style="font-size: 0.82rem; color: #334155;">{item}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("💡 No custom training insights generated yet.")

        # 3. List of Past Calls
        st.markdown("---")
        st.subheader("Recent Calls Registry")
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
            
            st.markdown("##### Inspect Call Details")
            inspect_call_id = st.selectbox(
                "Select Call ID to view raw transcript & conversation chat:",
                options=[c["id"] for c in my_calls]
            )
            if st.button("Open Call Details Scorecard", type="primary"):
                st.info(f"Please head to the **Call Details** page in the sidebar and select Call ID: `{inspect_call_id}`")
        else:
            st.info("No calls uploaded for your advisor profile yet.")

        # 4. List of Dispute Appeals History
        st.markdown("---")
        st.subheader("My Dispute Appeals History")
        my_appeals = DashboardService.get_advisor_appeals(db, advisor_id)
        if my_appeals:
            appeals_df = pd.DataFrame(my_appeals)
            appeals_df = appeals_df.rename(columns={
                "id": "Appeal ID",
                "call_id": "Call ID",
                "tag": "Disputed Issue Tag",
                "severity": "Severity",
                "reason": "Dispute Reason Given",
                "status": "Appeal Status",
                "created_at": "File Date"
            })
            appeals_df = appeals_df.drop(columns=["issue_tag_id", "quote"], errors="ignore")
            appeals_df["File Date"] = appeals_df["File Date"].apply(lambda x: x.split("T")[0] if "T" in x else x)
            st.dataframe(appeals_df, use_container_width=True, hide_index=True)
        else:
            st.info("⚖️ **No dispute appeals submitted.** You can file a dispute against any flagged issue tag in the **Call Details** page.")

finally:
    db.close()
