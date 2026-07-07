import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]

from backend.app.services.dashboard_service import DashboardService
from backend.app.models.call import CallStatus

# Backend URL for upload actions
BACKEND_URL = "http://127.0.0.1:8000"

def render_home_view(db: Session):
    """
    Renders the minimal, modern Home landing page view with the processing pipeline
    flow diagram, the file upload action, and current background status.
    """
    st.markdown('<h2 style="font-family:\'Outfit\',sans-serif;color:#1e293b;">⚡ Standalone Call Intelligence</h2>', unsafe_allow_html=True)
    st.markdown(
        "Upload audio recordings of your sales conversations to automatically transcribe, "
        "differentiate advisor/customer speakers, and perform a multi-agent AI compliance audit."
    )
    st.markdown("---")

    # 1. Pipeline Visualization Flowcard
    st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>AI Processing Pipeline</h4>", unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(
            "<div style='background-color:#f1f5f9;border:1px solid #cbd5e1;padding:12px;border-radius:6px;text-align:center;'>"
            "<strong>1. Upload</strong><br><small style='color:#64748b;'>Audio File Ingest</small>"
            "</div>", unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            "<div style='background-color:#f1f5f9;border:1px solid #cbd5e1;padding:12px;border-radius:6px;text-align:center;'>"
            "<strong>2. Transcribe</strong><br><small style='color:#64748b;'>Whisper Model</small>"
            "</div>", unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            "<div style='background-color:#f1f5f9;border:1px solid #cbd5e1;padding:12px;border-radius:6px;text-align:center;'>"
            "<strong>3. Diarize</strong><br><small style='color:#64748b;'>Pyannote separating</small>"
            "</div>", unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            "<div style='background-color:#f1f5f9;border:1px solid #cbd5e1;padding:12px;border-radius:6px;text-align:center;'>"
            "<strong>4. Analyze</strong><br><small style='color:#64748b;'>Gemini Audit</small>"
            "</div>", unsafe_allow_html=True
        )
    with col5:
        st.markdown(
            "<div style='background-color:#ecfdf5;border:1px solid #a7f3d0;padding:12px;border-radius:6px;text-align:center;'>"
            "<strong style='color:#065f46;'>5. Visualize</strong><br><small style='color:#047857;'>Scorecard & History</small>"
            "</div>", unsafe_allow_html=True
        )
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Prominent Upload Action Button and Form
    if "show_upload" not in st.session_state:
        st.session_state["show_upload"] = False

    if not st.session_state["show_upload"]:
        if st.button("📤 Upload New Call", type="primary", use_container_width=True):
            st.session_state["show_upload"] = True
            st.rerun()
    else:
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>Upload Call Recording</h4>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose an audio file (.wav, .mp3, .m4a)", type=["wav", "mp3", "m4a"])
        
        btn_col1, btn_col2 = st.columns([1, 4])
        with btn_col1:
            if st.button("Cancel", use_container_width=True):
                st.session_state["show_upload"] = False
                st.rerun()
        with btn_col2:
            if st.button("Process Recording", type="primary", use_container_width=True, disabled=(not uploaded_file)):
                with st.spinner("Uploading and initializing background processing..."):
                    try:
                        files = {"audio_file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        response = requests.post(f"{BACKEND_URL}/calls/upload", files=files, timeout=60)
                        
                        if response.status_code == 200:
                            st.success("Successfully uploaded! Call processing triggered in background.")
                            st.session_state["show_upload"] = False
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error connecting to backend: {e}")

    st.markdown("---")

    # 3. System Health and Processing Statuses
    st.markdown("<h4 style='color:#1e293b;font-weight:600;'>System Status & Recent Pipeline Activity</h4>", unsafe_allow_html=True)
    
    history = DashboardService.get_history(db)
    active_runs = [c for c in history if c["status"] in [CallStatus.Uploaded.value, CallStatus.Queued.value, CallStatus.Processing.value]]

    if active_runs:
        st.info(f"🔄 Currently processing {len(active_runs)} call recording(s) in the pipeline.")
        for run in active_runs:
            status_color = "#3b82f6" if run["status"] == "Processing" else "#f59e0b"
            st.markdown(
                f"<div style='border-left: 4px solid {status_color}; background-color:#f8fafc; padding:8px 16px; border-radius:4px; margin-bottom:8px;'>"
                f"<strong>{run['filename']}</strong> — State: <span style='color:{status_color};font-weight:600;'>{run['status']}</span>"
                f"</div>", unsafe_allow_html=True
            )
    else:
        st.success("🟢 Pipeline idle. All uploaded recordings have been successfully completed.")


def render_dashboard_view(db: Session):
    """
    Renders the dedicated analytics page with metrics and visual charts.
    """
    metrics = DashboardService.get_dashboard_metrics(db)

    if metrics["total_calls"] == 0:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("💡 **No calls have been analyzed yet.** Go to the Home view and upload your first recording to populate analytics.")
        return

    st.markdown('<h2 style="font-family:\'Outfit\',sans-serif;color:#1e293b;">📈 Platform Dashboard</h2>', unsafe_allow_html=True)
    st.markdown("---")

    # Top KPI Metrics Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(label="Total Processed Recordings", value=metrics["total_calls"])
    with kpi2:
        st.metric(label="Successfully Completed", value=metrics["completed_calls"])
    with kpi3:
        st.metric(label="Average Quality Score", value=f"{metrics['average_score']}/100")
    with kpi4:
        min_sec = f"{int(metrics['average_duration'] // 60)}m {int(metrics['average_duration'] % 60)}s"
        st.metric(label="Average Call Duration", value=min_sec)

    st.markdown("---")

    # Plotly Charts
    trends = DashboardService.get_score_trends(db)
    issues_data = DashboardService.get_issue_distribution(db)
    proc_stats = DashboardService.get_processing_statistics(db)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("<h5 style='font-weight:600;'>Average Quality Score Over Time</h5>", unsafe_allow_html=True)
        if trends:
            df_trends = pd.DataFrame(trends)
            fig_trend = px.line(
                df_trends, 
                x="date", 
                y="score", 
                hover_data=["filename"],
                labels={"date": "Upload Date", "score": "AI Score"},
                markers=True,
                color_discrete_sequence=["#6366f1"]
            )
            fig_trend.update_layout(yaxis_range=[0, 100], margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Not enough data to calculate timeline trends.")

    with chart_col2:
        st.markdown("<h5 style='font-weight:600;'>Pipeline Executions Status</h5>", unsafe_allow_html=True)
        df_stats = pd.DataFrame([{"Status": k, "Count": v} for k, v in proc_stats.items()])
        fig_stats = px.bar(
            df_stats, 
            x="Status", 
            y="Count", 
            color="Status",
            labels={"Status": "Pipeline State", "Count": "Quantity"},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_stats.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_stats, use_container_width=True)

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.markdown("<h5 style='font-weight:600;'>Most Common Audit Violations</h5>", unsafe_allow_html=True)
        if issues_data["top_issues"]:
            df_issues = pd.DataFrame(issues_data["top_issues"])
            fig_issues = px.bar(
                df_issues, 
                x="count", 
                y="tag", 
                orientation="h",
                labels={"count": "Frequency", "tag": "Violation Tag"},
                color_discrete_sequence=["#ec4899"]
            )
            fig_issues.update_layout(margin=dict(l=20, r=20, t=20, b=20), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_issues, use_container_width=True)
        else:
            st.success("No compliance violations flagged yet!")

    with chart_col4:
        st.markdown("<h5 style='font-weight:600;'>Flagged Severity Breakdown</h5>", unsafe_allow_html=True)
        sev_counts = issues_data["severity_breakdown"]
        if sum(sev_counts.values()) > 0:
            df_sev = pd.DataFrame([{"Severity": k, "Count": v} for k, v in sev_counts.items() if v > 0])
            fig_sev = px.pie(
                df_sev, 
                names="Severity", 
                values="Count", 
                hole=0.4,
                color="Severity",
                color_discrete_map={"Low": "#10b981", "Medium": "#3b82f6", "High": "#f59e0b", "Critical": "#ef4444"}
            )
            fig_sev.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_sev, use_container_width=True)
        else:
            st.info("No compliance issues to classify.")


def render_history_view(db: Session):
    """
    Renders the call log history list with filter options and select hooks.
    """
    history = DashboardService.get_history(db)

    if not history:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("💡 **No calls have been analyzed yet.** Head over to the Home view to upload an audio conversation.")
        return

    st.markdown('<h2 style="font-family:\'Outfit\',sans-serif;color:#1e293b;">📋 Call Audit Logs</h2>', unsafe_allow_html=True)
    st.markdown("---")

    # Filters and Search tools
    search_query = st.text_input("🔍 Search by filename...", "").strip().lower()
    
    # Filter list
    filtered_history = [
        c for c in history if search_query in c["filename"].lower()
    ]

    if not filtered_history:
        st.warning("No call logs match your query filters.")
        return

    # Render History items inside expander/cards
    for run in filtered_history:
        score_badge = f"<span style='background-color:#f1f5f9;color:#475569;font-weight:600;padding:4px 8px;border-radius:4px;'>None</span>"
        if run["score"] is not None:
            color = "#10b981" if run["score"] >= 80 else ("#f59e0b" if run["score"] >= 65 else "#ef4444")
            score_badge = f"<span style='background-color:{color}22;color:{color};font-weight:700;padding:4px 8px;border-radius:4px;'>{run['score']}/100</span>"
        
        status_color = "#10b981" if run["status"] == "Completed" else ("#ef4444" if run["status"] == "Failed" else "#f59e0b")
        status_badge = f"<span style='color:{status_color};font-weight:600;'>{run['status']}</span>"
        
        min_sec = f"{int(run['duration'] // 60)}m {int(run['duration'] % 60)}s"

        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(
                f"<div style='margin-bottom:4px;'>"
                f"<strong style='font-size:1.1rem;color:#0f172a;'>{run['filename']}</strong><br>"
                f"<small style='color:#64748b;'>Uploaded on: {run['upload_time'][:16].replace('T', ' ')} | Duration: {min_sec}</small>"
                f"</div>", unsafe_allow_html=True
            )
        with col2:
            st.markdown(f"<div style='margin-top:8px;'>Score: {score_badge} | Status: {status_badge}</div>", unsafe_allow_html=True)
        with col3:
            if st.button("View Audit Scorecard 🔍", key=f"btn_view_{run['id']}", use_container_width=True):
                st.session_state["selected_call_id"] = run["id"]
                st.rerun()
        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)


def render_call_details_view(call_id: int, db: Session):
    """
    Renders the unified scorecard tabs for a specific call analysis output.
    """
    details = DashboardService.get_call_details(db, call_id)
    if not details:
        st.error("Call metadata or details JSON files could not be found.")
        if st.button("⬅ Back to History"):
            if "selected_call_id" in st.session_state:
                del st.session_state["selected_call_id"]
            st.rerun()
        return

    # Breadcrumbs & Title
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("⬅ Back to History", use_container_width=True):
            if "selected_call_id" in st.session_state:
                del st.session_state["selected_call_id"]
            st.rerun()
    
    meta = details["metadata"]
    
    st.markdown(f"<h3 style='margin-top:10px;'>🔍 Scorecard: {meta['original_filename']}</h3>", unsafe_allow_html=True)
    st.markdown("---")

    # Renders 5 Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Speech Transcript", "Advisor/Customer Chat", "Gemini Process Trace", "Pipeline Timeline"])

    with tab1:
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>AI Audit Summary</h4>", unsafe_allow_html=True)
        
        analysis = details["analysis"]
        if not analysis:
            st.warning("AI analysis scorecard has not been generated for this recording yet.")
        else:
            col_score, col_summary = st.columns([1, 3])
            with col_score:
                score_color = "#10b981" if analysis["overall_score"] >= 80 else ("#f59e0b" if analysis["overall_score"] >= 65 else "#ef4444")
                st.markdown(
                    f"<div style='text-align:center;background-color:#f8fafc;border:2px solid {score_color}44;padding:24px;border-radius:8px;'>"
                    f"<small style='text-transform:uppercase;color:#64748b;font-weight:600;'>Overall Score</small>"
                    f"<div style='font-size:3rem;font-weight:800;color:{score_color};'>{int(analysis['overall_score'])}</div>"
                    f"<span style='color:#64748b;'>out of 100</span>"
                    f"</div>", unsafe_allow_html=True
                )
            with col_summary:
                st.markdown(f"**Analysis Summary**:<br>{analysis.get('summary', 'No summary generated.')}", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Strengths, Weaknesses, Recommendations
            col_str, col_weak = st.columns(2)
            with col_str:
                st.markdown("<div style='background-color:#f0fdf4;border:1px solid #bbf7d0;padding:16px;border-radius:6px;min-height:150px;'>"
                            "<h6 style='color:#166534;margin:0 0 10px 0;font-weight:600;'>🌟 Key Strengths</h6>", unsafe_allow_html=True)
                for s_item in analysis.get("strengths", []):
                    st.markdown(f"<span style='color:#14532d;'>• {s_item}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with col_weak:
                st.markdown("<div style='background-color:#fef2f2;border:1px solid #fecaca;padding:16px;border-radius:6px;min-height:150px;'>"
                            "<h6 style='color:#991b1b;margin:0 0 10px 0;font-weight:600;'>🚨 Identified Weaknesses</h6>", unsafe_allow_html=True)
                for w_item in analysis.get("weaknesses", []):
                    st.markdown(f"<span style='color:#7f1d1d;'>• {w_item}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<h5 style='color:#4f46e5;font-weight:600;'>Auditor Recommendations</h5>", unsafe_allow_html=True)
            for rec in analysis.get("recommendations", []):
                st.markdown(f"- {rec}")

            # Flagged Issue Violations
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<h5 style='color:#ef4444;font-weight:600;'>Compliance Violations</h5>", unsafe_allow_html=True)
            
            # Fetch tags dynamically from DB analysis details mapping
            db_analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == call_id).first()
            if db_analysis and db_analysis.issue_tags:
                for tag in db_analysis.issue_tags:
                    badge_color = "#ef4444" if tag.severity.value in ["Critical", "High"] else "#f59e0b"
                    st.markdown(
                        f"<div style='border:1px solid #f1f5f9;background-color:#fafafa;padding:12px;border-radius:6px;margin-bottom:8px;'>"
                        f"<strong>Tag:</strong> {tag.tag} | "
                        f"Severity: <span style='color:{badge_color};font-weight:700;'>{tag.severity.value}</span> | "
                        f"Timestamp: <span style='color:#64748b;'>{tag.timestamp}s</span><br>"
                        f"<em>Quote: \"{tag.quote}\"</em><br>"
                        f"<small style='color:#64748b;'><strong>Reason:</strong> {tag.reason}</small>"
                        f"</div>", unsafe_allow_html=True
                    )
            else:
                st.success("Clean compliance audit. No issue tags flagged.")

    with tab2:
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>Full Speech Transcription</h4>", unsafe_allow_html=True)
        transcript = details["transcript"]
        if not transcript or "segments" not in transcript:
            st.warning("Speech transcription segment JSON not available yet.")
        else:
            for seg in transcript["segments"]:
                min_sec = f"{int(seg['start'] // 60)}:{int(seg['start'] % 60):02d}"
                st.markdown(f"**[{min_sec}]** {seg['text']}")

    with tab3:
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>Advisor vs. Customer Conversation</h4>", unsafe_allow_html=True)
        conv = details["conversation"]
        if not conv or "segments" not in conv:
            st.warning("Diarized conversation dialogue script not available yet.")
        else:
            for turn in conv["segments"]:
                speaker = turn.get("speaker", "Speaker")
                bg_color = "#e0f2fe" if speaker == "Advisor" else "#f3f4f6"
                border_color = "#3b82f6" if speaker == "Advisor" else "#cbd5e1"
                text_color = "#0369a1" if speaker == "Advisor" else "#475569"
                
                st.markdown(
                    f"<div style='background-color:{bg_color};border-left:5px solid {border_color};padding:8px 16px;border-radius:4px;margin-bottom:6px;'>"
                    f"<strong style='color:{text_color};'>{speaker}:</strong> {turn['text']}"
                    f"</div>", unsafe_allow_html=True
                )

    with tab4:
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>Multi-Agent Gemini Process Log</h4>", unsafe_allow_html=True)
        analysis = details["analysis"]
        if not analysis or "analysis_metadata" not in analysis:
            st.warning("Gemini execution metadata logs not available.")
        else:
            st.json(analysis["analysis_metadata"])

    with tab5:
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>Pipeline Progression Timeline</h4>", unsafe_allow_html=True)
        timeline = details["timeline"]
        if not timeline:
            st.warning("State transition logs are empty.")
        else:
            for event in timeline:
                st.markdown(f"✔️ **{event['event']}** — <small style='color:#64748b;'>{event['timestamp']}</small>", unsafe_allow_html=True)
