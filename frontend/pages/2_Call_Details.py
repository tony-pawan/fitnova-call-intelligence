import os
import sys

# Ensure project root is in sys.path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import SessionLocal  # pyrefly: ignore [missing-import]
from backend.app.services.dashboard_service import DashboardService  # pyrefly: ignore [missing-import]
from frontend.sidebar import render_sidebar

st.set_page_config(
    page_title="FitNova - Call Details Scorecard",
    page_icon="🔍",
    layout="wide"
)

# Custom premium styling
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
    
    .detail-label {
        font-weight: 600;
        color: #64748b;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .detail-value {
        font-size: 1.1rem;
        color: #0f172a;
        margin-bottom: 1rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Render sidebar
render_sidebar()

# Establish DB Session context
db: Session = SessionLocal()

try:
    st.markdown('<h1 class="main-title">Call Details Scorecard</h1>', unsafe_allow_html=True)
    st.markdown("Completely audit call recordings, check transcript segments, view chats, and check AI analysis results.")

    # Refresh
    if st.button("🔄 Refresh Scorecard", type="secondary"):
        st.rerun()

    # Load calls list for lookup selector
    filter_opts = DashboardService.get_filter_options(db)
    # Fetch recent dashboard calls to get list
    manager_dash = DashboardService.get_manager_dashboard(db)
    recent_calls = manager_dash["recent_calls"]

    if not recent_calls:
        st.info("📂 **No calls found.** Go to the **Call Upload** page to upload a recording first.")
    else:
        # Build options mapping for dropdown selection
        call_options = {c["id"]: f"Call ID: {c['id']} | Advisor: {c['advisor_name']} | Status: {c['status']}" for c in recent_calls}
        
        selected_call_id = st.selectbox(
            "Select Call Recording to Inspect:",
            options=list(call_options.keys()),
            format_func=lambda x: call_options[x]
        )

        if selected_call_id:
            # Query call details from DashboardService
            call_detail = DashboardService.get_call_details(db, selected_call_id)
            
            if not call_detail:
                st.error("❌ Failed to load details for the selected Call ID.")
            else:
                metadata = call_detail["metadata"]
                
                # Render structured tabs
                tab_overview, tab_transcript, tab_conversation, tab_analysis, tab_timeline = st.tabs([
                    "📋 Overview", 
                    "📝 Transcript", 
                    "💬 Conversation", 
                    "📊 AI Analysis", 
                    "⏱️ Timeline"
                ])

                # -----------------------------
                # 1. OVERVIEW TAB
                # -----------------------------
                with tab_overview:
                    st.markdown("### Metadata Profile")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown('<span class="detail-label">Call ID</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{metadata["id"]}</div>', unsafe_allow_html=True)
                        
                        st.markdown('<span class="detail-label">Advisor Assigned</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{metadata["advisor_name"]} (ID: {metadata["advisor_id"]})</div>', unsafe_allow_html=True)
                        
                        st.markdown('<span class="detail-label">Duration</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{metadata["duration_seconds"]:.1f} seconds</div>', unsafe_allow_html=True)
                        
                    with col2:
                        st.markdown('<span class="detail-label">Original Filename</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{metadata["original_filename"]}</div>', unsafe_allow_html=True)
                        
                        st.markdown('<span class="detail-label">Mime Type</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{metadata["mime_type"]}</div>', unsafe_allow_html=True)
                        
                        st.markdown('<span class="detail-label">Upload Date</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{metadata["created_at"]}</div>', unsafe_allow_html=True)
                        
                    with col3:
                        st.markdown('<span class="detail-label">Language Code</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{metadata["language"] if metadata["language"] else "Unknown"}</div>', unsafe_allow_html=True)
                        
                        st.markdown('<span class="detail-label">Current Pipeline Status</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value">{metadata["status"]}</div>', unsafe_allow_html=True)
                        
                        # Score summary
                        score_val = call_detail["analysis"].get("overall_score") if call_detail["analysis"] else None
                        st.markdown('<span class="detail-label">Overall AI Quality Score</span>', unsafe_allow_html=True)
                        st.markdown(f'<div class="detail-value" style="font-size:1.5rem; color:#4f46e5; font-weight:700;">{f"{score_val}%" if score_val is not None else "--"}</div>', unsafe_allow_html=True)

                # -----------------------------
                # 2. TRANSCRIPT TAB
                # -----------------------------
                with tab_transcript:
                    st.markdown("### Raw Speech Transcript")
                    transcript_data = call_detail["transcript"]
                    
                    if not transcript_data:
                        st.info("📝 **No transcript generated yet.** Ensure the call completes the Whisper transcription stage.")
                    else:
                        st.caption(f"Model: {transcript_data.get('model', 'Whisper')} | Duration: {transcript_data.get('duration', 0.0):.1f}s")
                        st.markdown("---")
                        
                        for idx, seg in enumerate(transcript_data.get("segments", [])):
                            start = seg.get("start", 0.0)
                            end = seg.get("end", 0.0)
                            text = seg.get("text", "")
                            st.write(f"**[{start:.2f}s - {end:.2f}s]** {text}")

                # -----------------------------
                # 3. CONVERSATION TAB
                # -----------------------------
                with tab_conversation:
                    st.markdown("### Reconstructed Speaker Diarization Conversation")
                    conv_data = call_detail["conversation"]
                    
                    if not conv_data:
                        st.info("👥 **Diarization is incomplete.** Ensure the pipeline completes the Pyannote speaker diarization stage.")
                    else:
                        st.caption(f"Diarizer Model: {conv_data.get('model', 'Pyannote')} | Detected Speakers Count: {len(set(s.get('speaker') for s in conv_data.get('segments', [])))}")
                        st.markdown("---")
                        
                        for seg in conv_data.get("segments", []):
                            speaker = seg.get("speaker", "Speaker")
                            text = seg.get("text", "")
                            avatar = "👤" if speaker == "Advisor" else "👥"
                            with st.chat_message(speaker, avatar=avatar):
                                st.write(f"**{speaker}**: {text}")

                # -----------------------------
                # 4. ANALYSIS TAB
                # -----------------------------
                with tab_analysis:
                    st.markdown("### Multi-Agent Gemini Analysis Report")
                    analysis_data = call_detail["analysis"]
                    
                    if not analysis_data:
                        st.info("📊 **AI analysis report is not generated yet.** Ensure the call completes the AI Analysis stage successfully.")
                    else:
                        st.subheader(f"Overall Quality Score: {analysis_data['overall_score']}%")
                        st.markdown(f"**Performance Summary:** {analysis_data['summary']}")
                        st.markdown("---")
                        
                        # Strengths, Weaknesses, Recommendations columns
                        col_str, col_weak, col_rec = st.columns(3)
                        with col_str:
                            st.success("🌟 Key Strengths")
                            if analysis_data.get("strengths"):
                                for item in analysis_data["strengths"]:
                                    st.write(f"- {item}")
                            else:
                                st.write("*No strengths recorded.*")
                                
                        with col_weak:
                            st.error("⚠️ Identified Weaknesses")
                            if analysis_data.get("weaknesses"):
                                for item in analysis_data["weaknesses"]:
                                    st.write(f"- {item}")
                            else:
                                st.write("*No weaknesses recorded.*")
                                
                        with col_rec:
                            st.info("💡 Training Recommendations")
                            if analysis_data.get("recommendations"):
                                for item in analysis_data["recommendations"]:
                                    st.write(f"- {item}")
                            else:
                                st.write("*No recommendations recorded.*")

                        # Issue Tags evidence
                        st.markdown("---")
                        st.subheader("Audited Risk & Issue Tags")
                        
                        # Fetch issue tags from DB (which carries quote/reasons details)
                        from backend.app.models.issue_tag import IssueTag as DB_IssueTag
                        from backend.app.models.analysis import CallAnalysis as DB_CallAnalysis
                        
                        db_analysis = db.query(DB_CallAnalysis).filter(DB_CallAnalysis.call_id == selected_call_id).first()
                        issue_tags = db_analysis.issue_tags if db_analysis else []
                        
                        if not issue_tags:
                            st.success("✅ **No compliance or technique risks flagged.** Good job!")
                        else:
                            for tag in issue_tags:
                                severity_color = {
                                    "Low": "#3b82f6",
                                    "Medium": "#eab308",
                                    "High": "#f97316",
                                    "Critical": "#ef4444"
                                }.get(tag.severity.value, "#64748b")
                                
                                # Render styled badge
                                badge_html = f"""
                                <span style="background-color: {severity_color}; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; margin-left: 10px;">
                                    {tag.severity.value}
                                </span>
                                """
                                with st.expander(f"🚫 {tag.tag}"):
                                    st.markdown(f"**Severity:** {badge_html}", unsafe_allow_html=True)
                                    st.markdown(f"**Flagged Quote:** *\"{tag.quote}\"*")
                                    st.markdown(f"**Auditor Reason:** {tag.reason}")

                                    # Appeals integration
                                    from backend.app.models.appeal import Appeal as DB_Appeal
                                    db_appeal = db.query(DB_Appeal).filter(DB_Appeal.issue_tag_id == tag.id).first()

                                    if db_appeal:
                                        status_color = {
                                            "Pending": "#eab308",
                                            "Approved": "#10b981",
                                            "Rejected": "#ef4444"
                                        }.get(db_appeal.status.value, "#64748b")

                                        st.markdown(f"""
                                        <div style="margin-top: 10px; padding: 10px; border-radius: 6px; background-color: #f8fafc; border-left: 4px solid {status_color};">
                                            <strong>Appeal Status:</strong> 
                                            <span style="color: {status_color}; font-weight: 700;">{db_appeal.status.value}</span>
                                            <br>
                                            <strong>Reason Filed:</strong> {db_appeal.reason}
                                        </div>
                                        """, unsafe_allow_html=True)
                                    else:
                                        if st.session_state.get("role") == "Advisor":
                                            st.markdown("---")
                                            st.markdown("**Dispute AI Audit Tag**")
                                            with st.form(key=f"appeal_form_{tag.id}"):
                                                reason = st.text_area("Reason for Dispute (required):", key=f"reason_{tag.id}")
                                                submit_btn = st.form_submit_button("Submit Dispute Appeal")

                                                if submit_btn:
                                                    if not reason.strip():
                                                        st.error("Please enter a valid reason.")
                                                    else:
                                                        # Send API request
                                                        try:
                                                            import requests
                                                            payload = {
                                                                "issue_tag_id": int(tag.id),
                                                                "advisor_id": int(metadata["advisor_id"]),
                                                                "reason": reason.strip()
                                                            }
                                                            resp = requests.post(f"{BACKEND_URL}/appeals", json=payload, timeout=5)
                                                            if resp.status_code == 201:
                                                                st.success("Dispute appeal submitted successfully!")
                                                                st.rerun()
                                                            else:
                                                                st.error(f"Submission failed: {resp.json().get('detail', 'Unknown error')}")
                                                        except Exception as err:
                                                            st.error(f"Error submitting appeal: {err}")
                                        else:
                                            st.caption("No appeals filed for this tag by the Advisor.")

                # -----------------------------
                # 5. TIMELINE TAB
                # -----------------------------
                with tab_timeline:
                    st.markdown("### Process Timeline Logs")
                    timeline_data = call_detail["timeline"]
                    
                    if not timeline_data:
                        st.info("⏱️ **No timeline records found.** Ensure processing has begun.")
                    else:
                        st.markdown("The sequence of state transitions logged by the system background orchestrator:")
                        
                        timeline_html = ""
                        for idx, ev in enumerate(timeline_data):
                            dt_str = ev["timestamp"]
                            try:
                                if "T" in dt_str:
                                    dt_str = dt_str.split("T")[0] + " " + dt_str.split("T")[1][:8]
                            except Exception:
                                pass
                                
                            timeline_html += f"""
                            <div style="padding: 10px; border-left: 3px solid #6366f1; margin-left: 12px; position: relative;">
                                <div style="position: absolute; left: -7px; top: 12px; width: 11px; height: 11px; border-radius: 50%; background-color: #6366f1;"></div>
                                <strong style="font-size: 0.95rem; color: #0f172a;">{ev['event']}</strong>
                                <span style="font-size: 0.8rem; color: #64748b; margin-left: 15px;">⏱️ {dt_str}</span>
                            </div>
                            """
                        st.markdown(timeline_html, unsafe_allow_html=True)

finally:
    db.close()
