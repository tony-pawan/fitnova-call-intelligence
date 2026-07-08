import os
import requests
# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import plotly.express as px  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]

from backend.app.services.dashboard_service import DashboardService
from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.utils.json_storage import load_json

# Backend URL for upload actions
BACKEND_URL = "http://127.0.0.1:8000"

def render_home_view(db: Session):
    """
    Renders the modern, dynamic Source-Agnostic Ingestion Hub.
    Handles uploads, WATCH directories, CRM CSV datasets, APIs, and simulated telephony/dialers.
    """
    st.markdown('<h2 style="font-family:\'Outfit\',sans-serif;color:#1e293b;">⚡ Standalone Call Ingestion Hub</h2>', unsafe_allow_html=True)
    st.markdown(
        "Ingest call recordings from multiple enterprise sources. Every connector normalizes "
        "incoming audio streams to trigger the background automated AI pipeline."
    )
    st.markdown("---")

    # Check if last ingested call is completed
    if "last_ingested_call_id" in st.session_state:
        last_id = st.session_state["last_ingested_call_id"]
        call_record = db.query(Call).filter(Call.id == last_id).first()
        if call_record and call_record.status == CallStatus.Completed:
            st.markdown(
                f"<div style='background-color:#ecfdf5; border:1px solid #10b981; padding:16px; border-radius:8px; margin-bottom:20px;'>"
                f"🎉 <strong>Ingestion & AI Analysis Completed!</strong> Call record #{call_record.id} (<code>{call_record.original_filename}</code>) is ready for review."
                f"</div>", unsafe_allow_html=True
            )
            col_b, col_sp = st.columns([1.5, 3])
            with col_b:
                if st.button("👁️ View Call Analysis scorecard", type="primary", use_container_width=True):
                    st.session_state["selected_call_id"] = call_record.id
                    st.session_state["current_page"] = "History"
                    del st.session_state["last_ingested_call_id"]
                    st.rerun()

    # Dynamic pipeline tracking queue for currently processing calls
    active_calls = db.query(Call).filter(Call.status.in_([CallStatus.Uploaded, CallStatus.Queued, CallStatus.Processing])).all()

    if active_calls:
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>🔄 Processing Queue Timeline</h4>", unsafe_allow_html=True)
        for call_record in active_calls:
            st.markdown(f"<div style='background-color:#faf5ff;border:1px solid #e9d5ff;padding:16px;border-radius:8px;margin-bottom:15px;'>", unsafe_allow_html=True)
            col_lbl, col_pct = st.columns([3, 1])
            with col_lbl:
                st.markdown(f"📁 **File:** `{call_record.original_filename}` | Source: `{call_record.source}` | Vendor: `{call_record.vendor}`")
                st.markdown(f"⚙️ **Status:** `{call_record.status.value}`")
            with col_pct:
                st.markdown(f"<div style='text-align:right;font-size:1.5rem;font-weight:800;color:#7c3aed;'>{call_record.progress}%</div>", unsafe_allow_html=True)
            st.progress(call_record.progress / 100.0)
            
            # Stages visualization timeline
            stages = ["Normalizing", "Transcribing", "Diarizing", "Redacting PII", "Analyzing"]
            current_stage_idx = 0
            if call_record.progress >= 90:
                current_stage_idx = 4
            elif call_record.progress >= 70:
                current_stage_idx = 3
            elif call_record.progress >= 50:
                current_stage_idx = 2
            elif call_record.progress >= 30:
                current_stage_idx = 1
            
            stage_html = ""
            for idx, stage in enumerate(stages):
                color = "#4f46e5" if idx == current_stage_idx else ("#10b981" if idx < current_stage_idx else "#64748b")
                bullet = "🔵" if idx == current_stage_idx else ("🟢" if idx < current_stage_idx else "⚪")
                stage_html += f"<span style='color:{color};font-weight:{'700' if idx==current_stage_idx else 'normal'};margin-right:15px;'>{bullet} {stage}</span>"
            st.markdown(f"<div style='margin-top:10px;'>{stage_html}</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
        import time
        time.sleep(1.5)
        st.rerun()

    # Ingestion Source Tile Selector
    st.markdown("<h4 style='color:#1e293b;font-weight:600;'>Choose Audio Source</h4>", unsafe_allow_html=True)
    
    if "active_source" not in st.session_state:
        st.session_state["active_source"] = "upload"

    col_s1, col_s2, col_s3, col_s4, col_s5, col_s6 = st.columns(6)
    with col_s1:
        if st.button("📤 Upload\nFile", use_container_width=True, type="primary" if st.session_state["active_source"] == "upload" else "secondary"):
            st.session_state["active_source"] = "upload"
            st.rerun()
    with col_s2:
        if st.button("📁 Folder\nImport", use_container_width=True, type="primary" if st.session_state["active_source"] == "folder" else "secondary"):
            st.session_state["active_source"] = "folder"
            st.rerun()
    with col_s3:
        if st.button("📊 CRM\nExport", use_container_width=True, type="primary" if st.session_state["active_source"] == "crm" else "secondary"):
            st.session_state["active_source"] = "crm"
            st.rerun()
    with col_s4:
        if st.button("🔌 REST\nAPI", use_container_width=True, type="primary" if st.session_state["active_source"] == "api" else "secondary"):
            st.session_state["active_source"] = "api"
            st.rerun()
    with col_s5:
        if st.button("📞 Telephony\nPlatform", use_container_width=True, type="primary" if st.session_state["active_source"] == "telephony" else "secondary"):
            st.session_state["active_source"] = "telephony"
            st.rerun()
    with col_s6:
        if st.button("🤖 Dialer\nPlatform", use_container_width=True, type="primary" if st.session_state["active_source"] == "dialer" else "secondary"):
            st.session_state["active_source"] = "dialer"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    active_src = st.session_state["active_source"]

    # 1. Manual Upload View
    if active_src == "upload":
        st.markdown("<h5 style='color:#4f46e5;'>Direct Manual Call Upload</h5>", unsafe_allow_html=True)
        # Load Dynamic hierarchy dropdowns
        from backend.app.services.org_team_advisor_service import OrgTeamAdvisorService
        from backend.app.schemas.org_team_advisor import OrganizationCreate, TeamCreate, AdvisorCreate
        
        # 1. Resolve Organization: FitNova
        orgs = OrgTeamAdvisorService.list_organizations(db)
        fitnova_org = next((o for o in orgs if o.name == "FitNova"), None)
        if not fitnova_org:
            org_in = OrganizationCreate(name="FitNova")
            fitnova_org = OrgTeamAdvisorService.create_organization(db, org_in)
        selected_org_id = fitnova_org.id
        
        # 2. Team dropdown with dynamic creation option
        teams = OrgTeamAdvisorService.list_teams(db, org_id=selected_org_id)
        team_names = ["Select Team...", "➕ Add New Team..."] + [t.name for t in teams]
        selected_team_name = st.selectbox("Team:", team_names)
        
        selected_team_id = None
        if selected_team_name == "➕ Add New Team...":
            new_team_name = st.text_input("Enter New Team Name:", key="new_team_name_input")
            if st.button("Create Team", type="secondary"):
                if new_team_name.strip():
                    team_in = TeamCreate(name=new_team_name.strip(), organization_id=selected_org_id)
                    new_team = OrgTeamAdvisorService.create_team(db, team_in)
                    st.success(f"Team '{new_team.name}' created successfully!")
                    st.rerun()
                else:
                    st.warning("Please enter a team name.")
        elif selected_team_name != "Select Team...":
            team_obj = next((t for t in teams if t.name == selected_team_name), None)
            if team_obj:
                selected_team_id = team_obj.id
                
        # 3. Advisor dropdown with dynamic creation option
        selected_advisor_id = None
        if selected_team_id is not None:
            advisors = OrgTeamAdvisorService.list_advisors(db, team_id=selected_team_id)
            advisor_names = ["Select Advisor...", "➕ Add New Advisor..."] + [a.name for a in advisors]
            selected_advisor_name = st.selectbox("Advisor:", advisor_names)
            
            if selected_advisor_name == "➕ Add New Advisor...":
                new_advisor_name = st.text_input("Enter New Advisor Name:", key="new_adv_name_input")
                new_advisor_code = st.text_input("Enter Employee Code (e.g. ADV123):", key="new_adv_code_input")
                if st.button("Create Advisor", type="secondary"):
                    if new_advisor_name.strip() and new_advisor_code.strip():
                        adv_in = AdvisorCreate(
                            name=new_advisor_name.strip(),
                            employee_code=new_advisor_code.strip(),
                            team_id=selected_team_id
                        )
                        new_adv = OrgTeamAdvisorService.create_advisor(db, adv_in)
                        st.success(f"Advisor '{new_adv.name}' created successfully!")
                        st.rerun()
                    else:
                        st.warning("Please fill in both name and employee code.")
            elif selected_advisor_name != "Select Advisor...":
                adv_obj = next((a for a in advisors if a.name == selected_advisor_name), None)
                if adv_obj:
                    selected_advisor_id = adv_obj.id
        else:
            st.selectbox("Advisor:", ["Select Advisor..."], disabled=True)
            
        # 4. Resolve Ingestion Source: Manual Upload
        sources = OrgTeamAdvisorService.list_ingestion_sources(db)
        upload_source = next((s for s in sources if s.name in ["Upload", "Manual Upload"]), None)
        selected_source_id = upload_source.id if upload_source else None

        uploaded_file = st.file_uploader("Choose a WAV, MP3, or M4A call recording file", type=["wav", "mp3", "m4a", "aac"])
        if st.button("Process Uploaded Call", type="primary", use_container_width=True, disabled=not uploaded_file):
            with st.spinner("Processing manually uploaded call..."):
                try:
                    files = {"api_audio_file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {
                        "source_type": "Upload",
                        "organization_id": selected_org_id if selected_org_id else "",
                        "team_id": selected_team_id if selected_team_id else "",
                        "advisor_id": selected_advisor_id if selected_advisor_id else "",
                        "source_id": selected_source_id if selected_source_id else ""
                    }
                    response = requests.post(f"{BACKEND_URL}/calls/ingest", files=files, data=data, timeout=60)
                    if response.status_code == 200:
                        res = response.json()
                        st.success("Successfully ingested uploaded call!")
                        if res.get("ingested_calls"):
                            st.session_state["last_ingested_call_id"] = res["ingested_calls"][0]["id"]
                        st.rerun()
                    else:
                        st.error(f"Ingestion failed: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 2. Folder watch scanner View
    elif active_src == "folder":
        st.markdown("<h5 style='color:#4f46e5;'>Local Directory Watcher Connector</h5>", unsafe_allow_html=True)
        st.info("Watch a local directory path to scan, filter, and ingest new sales call recordings automatically.")
        folder_path = st.text_input("Enter watch absolute directory path (e.g. C:/Users/Admin/Desktop/novafit/sample_calls)", "C:/Users/Admin/Desktop/novafit")
        if st.button("Scan and Ingest Folder Files", type="primary", use_container_width=True):
            with st.spinner("Scanning directory watch path..."):
                try:
                    data = {"source_type": "Folder", "folder_path": folder_path}
                    response = requests.post(f"{BACKEND_URL}/calls/ingest", data=data, timeout=60)
                    if response.status_code == 200:
                        res = response.json()
                        st.success(f"Successfully scanned folder! Ingested {res.get('count', 0)} new call(s).")
                        if res.get("ingested_calls"):
                            st.session_state["last_ingested_call_id"] = res["ingested_calls"][0]["id"]
                        st.rerun()
                    else:
                        st.error(f"Failed to scan: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 3. CRM Spreadsheet Parser View
    elif active_src == "crm":
        st.markdown("<h5 style='color:#4f46e5;'>CRM Dataset Spreadsheet Connector</h5>", unsafe_allow_html=True)
        st.info("Load dataset records from exported CRM sheets (CSV format) and map them to audio files inside a directory folder.")
        crm_csv_file = st.file_uploader("Upload CRM dataset metadata export file (.csv)", type=["csv"])
        audio_dir = st.text_input("Enter local folder path containing the call recordings", "C:/Users/Admin/Desktop/novafit")
        
        if crm_csv_file:
            try:
                import io
                df = pd.read_csv(io.StringIO(crm_csv_file.getvalue().decode('utf-8-sig')))
                st.markdown("###### Previewing CRM sheet metadata rows:")
                st.dataframe(df.head(5), use_container_width=True)
            except Exception as pe:
                st.error(f"Failed to parse preview: {pe}")

        if st.button("Parse and Ingest CRM Dataset", type="primary", use_container_width=True, disabled=not crm_csv_file):
            with st.spinner("Validating files and mapping metadata..."):
                try:
                    files = {"crm_metadata_file": (crm_csv_file.name, crm_csv_file.getvalue(), "text/csv")}
                    data = {"source_type": "CRM", "crm_audio_dir": audio_dir}
                    response = requests.post(f"{BACKEND_URL}/calls/ingest", files=files, data=data, timeout=60)
                    if response.status_code == 200:
                        res = response.json()
                        st.success(f"CRM Ingestion complete! Imported {res.get('count', 0)} calls.")
                        if res.get("ingested_calls"):
                            st.session_state["last_ingested_call_id"] = res["ingested_calls"][0]["id"]
                        st.rerun()
                    else:
                        st.error(f"Failed: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 4. Developer REST API View
    elif active_src == "api":
        st.markdown("<h5 style='color:#4f46e5;'>External REST API Ingestion</h5>", unsafe_allow_html=True)
        st.markdown(
            "Integrate external webhooks or programmatic ingestion services. Exposes an authenticated "
            f"endpoint at `POST {BACKEND_URL}/calls/ingest` supporting multipart Form/File uploads."
        )
        st.markdown("###### JSON Payload details:")
        st.json({
            "source_type": "API (Required, Form string)",
            "external_call_id": "Unique vendor identifier (Required, Form string)",
            "api_audio_file": "Multipart file binaries (Required, Audio file stream)",
            "api_metadata_json": "Serialized metadata attributes (Optional, JSON Form string: advisor_name, customer_name, call_time)"
        })
        st.markdown("###### Example cURL command:")
        st.code(
            f'curl -X POST "{BACKEND_URL}/calls/ingest" \\\n'
            '  -F "source_type=API" \\\n'
            '  -F "external_call_id=DL987654" \\\n'
            '  -F "api_audio_file=@call_recording.mp3" \\\n'
            '  -F "api_metadata_json={\\"customer_name\\":\\"Neha\\",\\"advisor_name\\":\\"Arjun\\",\\"vendor\\":\\"Salesforce Integration\\"}"',
            language="bash"
        )

    # 5. Telephony simulation View
    elif active_src == "telephony":
        st.markdown("<h5 style='color:#4f46e5;'>Telephony Platform Connector Simulator</h5>", unsafe_allow_html=True)
        st.info("Trigger a simulated incoming webhook callback event from major telephony vendors. "
                "The connector fetches call SID identifiers and redirects audio to the processing pipeline.")
        vendor_choice = st.selectbox("Select Telephony Vendor Platform Adapter:", ["Twilio", "Aircall", "RingCentral", "Genesys", "CloudTalk", "Dialpad"])
        
        st.markdown(f"Status: 🟢 **Simulator Sandbox Enabled ({vendor_choice})**")
        st.markdown(
            "<div style='border-left:4px solid #3b82f6; background-color:#eff6ff; padding:12px; border-radius:4px; margin-bottom:15px;'>"
            "<strong>Twilio Webhook Flow:</strong> Event trigger ➔ Fetch call SID recording stream ➔ Normalize AudioInput ➔ Trigger Pipeline"
            "</div>", unsafe_allow_html=True
        )

        if st.button(f"Trigger Simulated {vendor_choice} Event", type="primary", use_container_width=True):
            with st.spinner("Simulating incoming callback..."):
                try:
                    data = {"source_type": "Telephony", "vendor": vendor_choice}
                    response = requests.post(f"{BACKEND_URL}/calls/ingest", data=data, timeout=60)
                    if response.status_code == 200:
                        res = response.json()
                        st.success(f"Simulated telephony event ingested call: ID {res.get('ingested_calls', [{}])[0].get('id')}!")
                        if res.get("ingested_calls"):
                            st.session_state["last_ingested_call_id"] = res["ingested_calls"][0]["id"]
                        st.rerun()
                    else:
                        st.error(f"Simulation failed: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # 6. Dialer simulation View
    elif active_src == "dialer":
        st.markdown("<h5 style='color:#4f46e5;'>Outbound Dialer Platform Connector Simulator</h5>", unsafe_allow_html=True)
        st.info("Trigger simulated outbound call events completed inside call center dialers.")
        vendor_choice = st.selectbox("Select Outbound Dialer Vendor Platform Adapter:", ["Five9", "Salesforce Dialer", "Vicidial"])
        
        st.markdown(f"Status: 🟢 **Simulator Sandbox Enabled ({vendor_choice})**")
        st.markdown(
            "<div style='border-left:4px solid #f59e0b; background-color:#fffbeb; padding:12px; border-radius:4px; margin-bottom:15px;'>"
            "<strong>Five9 Agent Event Flow:</strong> Call completion disposition ➔ Fetch CRM lead details ➔ Normalize AudioInput DTO ➔ Trigger Pipeline"
            "</div>", unsafe_allow_html=True
        )

        if st.button(f"Trigger Simulated {vendor_choice} Event", type="primary", use_container_width=True):
            with st.spinner("Simulating dialer completed event..."):
                try:
                    data = {"source_type": "Dialer", "vendor": vendor_choice}
                    response = requests.post(f"{BACKEND_URL}/calls/ingest", data=data, timeout=60)
                    if response.status_code == 200:
                        res = response.json()
                        st.success(f"Simulated dialer event ingested call: ID {res.get('ingested_calls', [{}])[0].get('id')}!")
                        if res.get("ingested_calls"):
                            st.session_state["last_ingested_call_id"] = res["ingested_calls"][0]["id"]
                        st.rerun()
                    else:
                        st.error(f"Simulation failed: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {e}")


def render_dashboard_view(db: Session):
    """
    Renders the redesigned, assignment-focused operational dashboard.
    """
    st.markdown('<h2 style="font-family:\'Outfit\',sans-serif;color:#1e293b;">📈 Conversational Intelligence Dashboard</h2>', unsafe_allow_html=True)
    
    # Load dynamic filter selectors
    from backend.app.services.org_team_advisor_service import OrgTeamAdvisorService
    orgs = OrgTeamAdvisorService.list_organizations(db)
    org_names = ["All Organizations"] + [o.name for o in orgs]
    
    st.markdown("<div style='background-color:#f8fafc; border:1px solid #e2e8f0; padding:16px; border-radius:8px; margin-bottom:20px;'>", unsafe_allow_html=True)
    st.markdown("<strong style='color:#475569;'>🔍 Filter Dashboard Metrics</strong>", unsafe_allow_html=True)
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        f_org_name = st.selectbox("Organization Filter:", org_names)
        
    f_org_id = None
    team_names = ["All Teams"]
    if f_org_name != "All Organizations":
        org_ref = next(o for o in orgs if o.name == f_org_name)
        f_org_id = org_ref.id
        teams = OrgTeamAdvisorService.list_teams(db, org_id=org_ref.id)
        team_names += [t.name for t in teams]
        
    with col_f2:
        f_team_name = st.selectbox("Team Filter:", team_names, disabled=(f_org_id is None))
        
    f_team_id = None
    advisor_names = ["All Advisors"]
    if f_team_name != "All Teams":
        teams_list = OrgTeamAdvisorService.list_teams(db, org_id=f_org_id)
        team_ref = next(t for t in teams_list if t.name == f_team_name)
        f_team_id = team_ref.id
        advisors = OrgTeamAdvisorService.list_advisors(db, team_id=team_ref.id)
        advisor_names += [a.name for a in advisors]
        
    with col_f3:
        f_advisor_name = st.selectbox("Advisor Filter:", advisor_names, disabled=(f_team_id is None))
        
    f_advisor_id = None
    if f_advisor_name != "All Advisors":
        advisors_list = OrgTeamAdvisorService.list_advisors(db, team_id=f_team_id)
        adv_ref = next(a for a in advisors_list if a.name == f_advisor_name)
        f_advisor_id = adv_ref.id
        
    sources = OrgTeamAdvisorService.list_ingestion_sources(db)
    source_names = ["All Ingestion Sources"] + [s.name for s in sources]
    with col_f4:
        f_source_name = st.selectbox("Ingestion Source Filter:", source_names)
        
    f_source_id = None
    if f_source_name != "All Ingestion Sources":
        src_ref = next(s for s in sources if s.name == f_source_name)
        f_source_id = src_ref.id
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Load filtered metrics
    metrics = DashboardService.get_dashboard_metrics(db, f_org_id, f_team_id, f_advisor_id, f_source_id)

    if metrics["total_calls"] == 0:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("💡 **No calls match the selected filters or have been analyzed yet.** Adjust filters or go to the Home view to ingest recordings.")
        return

    st.markdown("---")

    # Section 1: Sales Performance
    st.markdown("#### 🏆 1. Sales Performance")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("<h5 style='font-weight:600;'>AI Quality Score Trend</h5>", unsafe_allow_html=True)
        trends = DashboardService.get_score_trends(db, f_org_id, f_team_id, f_advisor_id, f_source_id)
        if trends:
            df_trends = pd.DataFrame(trends)
            fig_trend = px.line(
                df_trends, 
                x="date", 
                y="score", 
                hover_data=["filename"],
                labels={"date": "Upload Date", "score": "AI Score"},
                markers=True,
                color_discrete_sequence=["#4f46e5"]
            )
            fig_trend.update_layout(yaxis_range=[0, 100], margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Not enough data to calculate timeline trends.")
            
    with col_t2:
        st.markdown("<h5 style='font-weight:600;'>Score Breakdown by Category</h5>", unsafe_allow_html=True)
        cat_data = metrics.get("category_scores", {})
        if cat_data:
            df_cat = pd.DataFrame([{"Evaluation Category": k, "Average Score": v} for k, v in cat_data.items()])
            fig_cat = px.bar(
                df_cat,
                x="Average Score",
                y="Evaluation Category",
                orientation="h",
                color="Evaluation Category",
                color_discrete_sequence=["#10b981"]
            )
            fig_cat.update_layout(xaxis_range=[0, 100], margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No category scores aggregated yet.")

    st.markdown(
        "<div style='background-color:#fafafa; border:1px solid #e2e8f0; padding:16px; border-radius:8px; margin-top:20px;'>"
        "<strong>💡 Sales Coaching Tip:</strong><br><small style='color:#475569;'>"
        "Objection Handling and Needs Discovery segments represent primary quality bottlenecks. "
        "Focus on training agents to identify budget triggers and ask open-ended questions.</small>"
        "</div>", unsafe_allow_html=True
    )

    st.markdown("---")

    # Section 2: Compliance & Risk
    st.markdown("#### ⚠️ 2. Compliance & Risk")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("<h5 style='font-weight:600;'>Compliance & Violations Categories</h5>", unsafe_allow_html=True)
        issues_data = DashboardService.get_issue_distribution(db, f_org_id, f_team_id, f_advisor_id, f_source_id)
        if issues_data["top_issues"]:
            df_issues = pd.DataFrame(issues_data["top_issues"])
            fig_issues = px.bar(
                df_issues,
                x="count",
                y="tag",
                orientation="h",
                labels={"count": "Occurrences", "tag": "Issue Category"},
                color_discrete_sequence=["#ef4444"]
            )
            fig_issues.update_layout(margin=dict(l=20, r=20, t=20, b=20), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_issues, use_container_width=True)
        else:
            st.success("No compliance issue violations flagged yet!")
            
    with col_c2:
        st.markdown("<h5 style='font-weight:600;'>Audit Issues Severity Distribution</h5>", unsafe_allow_html=True)
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

    st.markdown("---")

    # Section 3: Recent Activity Table
    st.markdown("#### 📋 3. Recent Activity")
    history = DashboardService.get_history(db, f_org_id, f_team_id, f_advisor_id, f_source_id)
    if history:
        # Get top 5 recent processed calls
        recent = history[:5]
        
        # Display as columns table layout
        st.markdown("<br>", unsafe_allow_html=True)
        col_h1, col_h2, col_h3, col_h4, col_h5, col_h6, col_h7 = st.columns([1, 2.5, 1.2, 1.2, 1.2, 1.2, 1.2])
        with col_h1: st.markdown("**Call ID**")
        with col_h2: st.markdown("**Filename**")
        with col_h3: st.markdown("**Upload Time**")
        with col_h4: st.markdown("**Duration**")
        with col_h5: st.markdown("**Overall Score**")
        with col_h6: st.markdown("**Status**")
        with col_h7: st.markdown("**Issues Flagged**")
        
        st.markdown("<hr style='margin: 5px 0 10px 0;'>", unsafe_allow_html=True)
        
        for c in recent:
            col_d1, col_d2, col_d3, col_d4, col_d5, col_d6, col_d7 = st.columns([1, 2.5, 1.2, 1.2, 1.2, 1.2, 1.2])
            min_sec = f"{int(c['duration'] // 60)}m {int(c['duration'] % 60):02d}s"
            upload_date = c["upload_time"][:10] + " " + c["upload_time"][11:16]
            score_str = f"{int(c['score'])}/100" if c['score'] is not None else "N/A"
            
            with col_d1:
                if st.button(f"#{c['id']}", key=f"btn_nav_dash_{c['id']}", help="Open Analysis Scorecard"):
                    st.session_state["selected_call_id"] = c["id"]
                    st.session_state["current_page"] = "History"
                    st.rerun()
            with col_d2:
                st.write(c["filename"])
            with col_d3:
                st.write(upload_date)
            with col_d4:
                st.write(min_sec)
            with col_d5:
                st.write(score_str)
            with col_d6:
                st.write(c["status"])
            with col_d7:
                st.write(c.get("issues_flagged", 0))
                
            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
    else:
        st.info("No recent call activity logs.")


def render_history_view(db: Session):
    """
    Renders the call log history list with filter options and select hooks.
    """
    # Title & Action columns
    col_title, col_actions = st.columns([3, 1.5])
    with col_title:
        st.markdown('<h2 style="font-family:\'Outfit\',sans-serif;color:#1e293b;margin:0;">📋 Call Audit Logs</h2>', unsafe_allow_html=True)
    with col_actions:
        if "delete_mode" not in st.session_state:
            st.session_state["delete_mode"] = False
            
        btn_label = "❌ Cancel Selection" if st.session_state["delete_mode"] else "🗑️ Delete History"
        if st.button(btn_label, use_container_width=True):
            st.session_state["delete_mode"] = not st.session_state["delete_mode"]
            st.rerun()

    st.markdown("---")

    # Load dynamic filter selectors
    from backend.app.services.org_team_advisor_service import OrgTeamAdvisorService
    orgs = OrgTeamAdvisorService.list_organizations(db)
    org_names = ["All Organizations"] + [o.name for o in orgs]
    
    st.markdown("<div style='background-color:#f8fafc; border:1px solid #e2e8f0; padding:16px; border-radius:8px; margin-bottom:20px;'>", unsafe_allow_html=True)
    st.markdown("<strong style='color:#475569;'>🔍 Filter Call Logs</strong>", unsafe_allow_html=True)
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        f_org_name = st.selectbox("Organization Filter:", org_names)
        
    f_org_id = None
    team_names = ["All Teams"]
    if f_org_name != "All Organizations":
        org_ref = next(o for o in orgs if o.name == f_org_name)
        f_org_id = org_ref.id
        teams = OrgTeamAdvisorService.list_teams(db, org_id=org_ref.id)
        team_names += [t.name for t in teams]
        
    with col_f2:
        f_team_name = st.selectbox("Team Filter:", team_names, disabled=(f_org_id is None))
        
    f_team_id = None
    advisor_names = ["All Advisors"]
    if f_team_name != "All Teams":
        teams_list = OrgTeamAdvisorService.list_teams(db, org_id=f_org_id)
        team_ref = next(t for t in teams_list if t.name == f_team_name)
        f_team_id = team_ref.id
        advisors = OrgTeamAdvisorService.list_advisors(db, team_id=team_ref.id)
        advisor_names += [a.name for a in advisors]
        
    with col_f3:
        f_advisor_name = st.selectbox("Advisor Filter:", advisor_names, disabled=(f_team_id is None))
        
    f_advisor_id = None
    if f_advisor_name != "All Advisors":
        advisors_list = OrgTeamAdvisorService.list_advisors(db, team_id=f_team_id)
        adv_ref = next(a for a in advisors_list if a.name == f_advisor_name)
        f_advisor_id = adv_ref.id
        
    sources = OrgTeamAdvisorService.list_ingestion_sources(db)
    source_names = ["All Ingestion Sources"] + [s.name for s in sources]
    with col_f4:
        f_source_name = st.selectbox("Ingestion Source Filter:", source_names)
        
    f_source_id = None
    if f_source_name != "All Ingestion Sources":
        src_ref = next(s for s in sources if s.name == f_source_name)
        f_source_id = src_ref.id
        
    st.markdown("</div>", unsafe_allow_html=True)

    history = DashboardService.get_history(db, f_org_id, f_team_id, f_advisor_id, f_source_id)

    if not history:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("💡 **No calls match the selected filters or have been analyzed yet.** Adjust filters or go to the Home view to ingest recordings.")
        return

    # Suggestion alert to export before deleting
    if st.session_state["delete_mode"]:
        st.warning("💡 **Suggestion:** We highly recommend exporting the cumulative history report (PDF) before permanently deleting data.")

    # Cumulative PDF Export Button
    try:
        from datetime import datetime
        from backend.app.services.pdf_service import PDFService
        pdf_bytes = PDFService.generate_cumulative_pdf(db)
        if pdf_bytes:
            st.download_button(
                label="📥 Export Cumulative History Report (PDF)",
                data=pdf_bytes,
                file_name=f"fitnova_cumulative_history_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading PDF exporter: {e}")

    # Filters and Search tools
    search_query = st.text_input("🔍 Search by filename...", "").strip().lower()
    
    # Filter list
    filtered_history = [
        c for c in history if search_query in c["filename"].lower()
    ]

    if not filtered_history:
        st.warning("No call logs match your query filters.")
        return

    # Delete mode controls (Select All & Delete Selected)
    if st.session_state["delete_mode"]:
        c_sel, c_space = st.columns([2, 3])
        with c_sel:
            def toggle_select_all():
                val = st.session_state["select_all_logs_checkbox"]
                for r in filtered_history:
                    st.session_state[f"sel_del_{r['id']}"] = val
            st.checkbox("Select All Logs", key="select_all_logs_checkbox", on_change=toggle_select_all)
            
        # Compile selected IDs
        selected_ids = []
        for run in filtered_history:
            if st.session_state.get(f"sel_del_{run['id']}", False):
                selected_ids.append(run["id"])
                
        if selected_ids:
            st.markdown(f"<div style='background-color:#fff5f5;border:1px solid #fecaca;padding:16px;border-radius:8px;margin-bottom:15px;'>", unsafe_allow_html=True)
            col_msg, col_wipe = st.columns([3, 1])
            with col_msg:
                st.markdown(f"<span style='color:#991b1b;font-weight:700;'>Selected {len(selected_ids)} call recording(s) for permanent deletion.</span>", unsafe_allow_html=True)
                confirm_del = st.checkbox("Confirm permanent deletion.", key="confirm_delete_selected_checkbox")
            with col_wipe:
                if st.button("🗑️ Wipe Selected", type="primary", use_container_width=True, disabled=not confirm_del):
                    try:
                        DashboardService.delete_calls(db, selected_ids)
                        st.toast(f"Successfully deleted {len(selected_ids)} calls!", icon="🗑️")
                        st.session_state["delete_mode"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during deletion: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

    # Render History items inside expander/cards
    for run in filtered_history:
        score_badge = f"<span style='background-color:#f1f5f9;color:#475569;font-weight:600;padding:4px 8px;border-radius:4px;'>None</span>"
        if run["score"] is not None:
            color = "#10b981" if run["score"] >= 80 else ("#f59e0b" if run["score"] >= 65 else "#ef4444")
            score_badge = f"<span style='background-color:{color}22;color:{color};font-weight:700;padding:4px 8px;border-radius:4px;'>{run['score']}/100</span>"
        
        status_color = "#10b981" if run["status"] == "Completed" else ("#ef4444" if run["status"] == "Failed" else "#f59e0b")
        status_badge = f"<span style='color:{status_color};font-weight:600;'>{run['status']}</span>"
        
        min_sec = f"{int(run['duration'] // 60)}m {int(run['duration'] % 60)}s"

        if st.session_state["delete_mode"]:
            col_chk, col_info, col_badge, col_btn = st.columns([0.4, 2.6, 1, 1])
            with col_chk:
                st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                st.checkbox("", key=f"sel_del_{run['id']}", label_visibility="collapsed")
            with col_info:
                st.markdown(
                    f"<div style='margin-bottom:4px;'>"
                    f"<strong style='font-size:1.1rem;color:#0f172a;'>{run['filename']}</strong><br>"
                    f"<small style='color:#64748b;'>Uploaded on: {run['upload_time'][:16].replace('T', ' ')} | Duration: {min_sec}</small>"
                    f"</div>", unsafe_allow_html=True
                )
            with col_badge:
                st.markdown(f"<div style='margin-top:8px;'>Score: {score_badge} | Status: {status_badge}</div>", unsafe_allow_html=True)
            with col_btn:
                if st.button("View Audit Scorecard 🔍", key=f"btn_view_{run['id']}", use_container_width=True):
                    st.session_state["selected_call_id"] = run["id"]
                    st.rerun()
        else:
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
    Supports historical versions, corrections, reviews, and overrides.
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
    col_back, col_export, col_title = st.columns([1.2, 1.5, 4.3])
    with col_back:
        if st.button("⬅ Back to History", use_container_width=True):
            if "selected_call_id" in st.session_state:
                del st.session_state["selected_call_id"]
            st.rerun()
    with col_export:
        try:
            from backend.app.services.pdf_service import PDFService
            pdf_bytes = PDFService.generate_single_call_pdf(db, call_id)
            if pdf_bytes:
                st.download_button(
                    label="📥 Export Scorecard (PDF)",
                    data=pdf_bytes,
                    file_name=f"fitnova_scorecard_call_{call_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Export error: {e}")
    
    meta = details["metadata"]
    st.markdown(f"<h3 style='margin-top:10px;'>🔍 Scorecard: {meta['original_filename']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<small style='color:#64748b;'>Source: `{meta.get('source', 'Upload')}` | Vendor: `{meta.get('vendor', 'Direct')}` | Created At: {meta['created_at']}</small>", unsafe_allow_html=True)
    st.markdown("---")

    # Load version histories
    from backend.app.services.feedback_service import FeedbackService
    history_versions = FeedbackService.get_version_history(db, call_id)

    # Only render version revision selectors if there is actually more than 1 version!
    if len(history_versions["transcripts"]) > 1 or len(history_versions["analyses"]) > 1:
        # Revision Selectors
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            t_vers = ["Active Version"] + [f"v{v['version']} (Saved {v['created_at'][11:16]})" for v in history_versions["transcripts"]]
            selected_ver = st.selectbox("📂 Dialogue revision:", t_vers)
            if selected_ver != "Active Version":
                v_num = int(selected_ver.split(" ")[0][1:])
                for v_record in history_versions["transcripts"]:
                    if v_record["version"] == v_num:
                        details["transcript"] = load_json(v_record["file_path"])
                for v_record in history_versions["conversations"]:
                    if v_record["version"] == v_num:
                        details["conversation"] = load_json(v_record["file_path"])

        with col_v2:
            a_vers = ["Active Scorecard"] + [f"v{v['version']} (Score: {v['overall_score']})" for v in history_versions["analyses"]]
            selected_a_ver = st.selectbox("📊 Scorecard revision:", a_vers)
            if selected_a_ver != "Active Scorecard":
                av_num = int(selected_a_ver.split(" ")[0][1:])
                for v_record in history_versions["analyses"]:
                    if v_record["version"] == av_num:
                        details["analysis"] = load_json(v_record["file_path"])

    # Initialize active tab from session state to support cross-tab navigation/scrolling
    if "active_detail_tab" not in st.session_state:
        st.session_state["active_detail_tab"] = "Overview"
    elif st.session_state["active_detail_tab"] in ["Gemini Process Trace", "Pipeline Timeline"]:
        st.session_state["active_detail_tab"] = "Overview"
        
    active_tab = st.session_state["active_detail_tab"]
    
    # Render tab bar using button group
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        if st.button("📊 Overview", use_container_width=True, type="primary" if active_tab == "Overview" else "secondary", key=f"btn_tab_overview_{call_id}"):
            st.session_state["active_detail_tab"] = "Overview"
            st.rerun()
    with col_t2:
        if st.button("📝 Speech Transcript", use_container_width=True, type="primary" if active_tab == "Speech Transcript" else "secondary", key=f"btn_tab_transcript_{call_id}"):
            st.session_state["active_detail_tab"] = "Speech Transcript"
            st.rerun()
    with col_t3:
        if st.button("💬 Advisor/Customer Chat", use_container_width=True, type="primary" if active_tab == "Advisor/Customer Chat" else "secondary", key=f"btn_tab_chat_{call_id}"):
            st.session_state["active_detail_tab"] = "Advisor/Customer Chat"
            st.rerun()
    with col_t4:
        if st.button("✍️ Human Feedback Loop", use_container_width=True, type="primary" if active_tab == "✍️ Human Feedback Loop" else "secondary", key=f"btn_tab_feedback_{call_id}"):
            st.session_state["active_detail_tab"] = "✍️ Human Feedback Loop"
            st.rerun()

    selected_section = active_tab

    if selected_section == "Overview":
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
            
            from backend.app.models.analysis import CallAnalysis
            db_analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == call_id).first()
            if db_analysis and db_analysis.issue_tags:
                for tag in db_analysis.issue_tags:
                    badge_color = "#ef4444" if tag.severity.value in ["Critical", "High"] else "#f59e0b"
                    comment_html = f"<br><small style='color:#6366f1;'><strong>Feedback Status:</strong> {tag.review_status} | <strong>Comments:</strong> {tag.reviewer_comments or 'None'}</small>" if getattr(tag, "review_status", None) else ""
                    
                    st.markdown(
                        f"<div style='border:1px solid #f1f5f9;background-color:#fafafa;padding:12px;border-radius:6px;margin-bottom:8px;'>"
                        f"<strong>Tag:</strong> {tag.tag} | "
                        f"Severity: <span style='color:{badge_color};font-weight:700;'>{tag.severity.value}</span> | "
                        f"Timestamp: <span style='color:#64748b;'>{tag.timestamp}s</span><br>"
                        f"<em>Quote: \"{tag.quote}\"</em><br>"
                        f"<small style='color:#64748b;'><strong>Reason:</strong> {tag.reason}</small>"
                        f"{comment_html}"
                        f"</div>", unsafe_allow_html=True
                    )
            else:
                st.success("Clean compliance audit. No issue tags flagged.")

    elif selected_section == "Speech Transcript":
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>Full Speech Transcription</h4>", unsafe_allow_html=True)
        transcript = details["transcript"]
        if not transcript or "segments" not in transcript:
            st.warning("Speech transcription segment JSON not available yet.")
        else:
            highlight_time = st.session_state.get("highlight_timestamp", None)
            
            # Anchor element at top
            st.markdown("<div id='top-of-transcript'></div>", unsafe_allow_html=True)
            
            for seg in transcript["segments"]:
                min_sec = f"{int(seg['start'] // 60)}:{int(seg['start'] % 60):02d}"
                
                is_target = False
                if highlight_time is not None and abs(seg["start"] - highlight_time) <= 3.0:
                    is_target = True
                    
                if is_target:
                    st.markdown(
                        f"<div id='evidence-highlight' style='background-color: #fef08a; border: 2px solid #eab308; padding: 12px; border-radius: 6px; margin: 8px 0; font-weight: 600; color: #854d0e;'>"
                        f"👉 🚨 [TARGET EVIDENCE] [{min_sec}] {seg['text']}"
                        f"</div>"
                        f"<script>"
                        f"document.getElementById('evidence-highlight').scrollIntoView({{behavior: 'smooth', block: 'center'}});"
                        f"</script>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(f"**[{min_sec}]** {seg['text']}")
                    
            # Clear state immediately so subsequent tab checks don't repeat scrolling
            if "highlight_timestamp" in st.session_state:
                del st.session_state["highlight_timestamp"]

    elif selected_section == "Advisor/Customer Chat":
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



    elif selected_section == "✍️ Human Feedback Loop":
        st.markdown("<h4 style='color:#4f46e5;font-weight:600;'>✍️ Human Feedback Loop Panel</h4>", unsafe_allow_html=True)
        
        # Sub-tabs for the 3 sections (Dialogue Corrections removed)
        sub_tab1, sub_tab2, sub_tab3 = st.tabs([
            "⚠️ Violations Review",
            "⚙️ Score Override",
            "🔄 AI Re-Analysis"
        ])

        with sub_tab1:
            from backend.app.models.analysis import CallAnalysis
            db_analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == call_id).first()
            
            if not db_analysis or not db_analysis.issue_tags:
                st.markdown(
                    f"<div style='text-align: center; padding: 40px; background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; margin: 20px 0;'>"
                    f"<h2 style='color: #166534;'>✅ No pending violations</h2>"
                    f"<p style='color: #15803d; font-size: 1.1rem; margin-top: 10px; margin-bottom: 20px;'>The AI analysis did not detect any issues requiring review.</p>"
                    f"</div>", unsafe_allow_html=True
                )
                if st.button("👁️ View Analysis Report", type="primary", use_container_width=True):
                    st.session_state["active_detail_tab"] = "Overview"
                    st.rerun()
            else:
                # 1. Compact Status Line (subtle)
                app_c = sum(1 for t in db_analysis.issue_tags if t.review_status == "Approve")
                dsm_c = sum(1 for t in db_analysis.issue_tags if t.review_status == "Dismiss")
                fp_c = sum(1 for t in db_analysis.issue_tags if t.review_status == "False Positive")
                pending_c = sum(1 for t in db_analysis.issue_tags if t.review_status in ["Pending", "Needs Human Review"])
                
                st.markdown(
                    f"<p style='color: #64748b; font-size: 0.9rem; text-align: center; margin-bottom: 15px; font-weight: 500;'>"
                    f"Approved: <span style='color: #15803d;'>{app_c}</span> &nbsp;|&nbsp; "
                    f"Pending: <span style='color: #b45309;'>{pending_c}</span> &nbsp;|&nbsp; "
                    f"Dismissed: <span style='color: #475569;'>{dsm_c}</span> &nbsp;|&nbsp; "
                    f"False Positives: <span style='color: #b91c1c;'>{fp_c}</span>"
                    f"</p>", unsafe_allow_html=True
                )
                
                # Separate violations
                unapproved_tags = [t for t in db_analysis.issue_tags if t.review_status != "Approve"]
                approved_tags = [t for t in db_analysis.issue_tags if t.review_status == "Approve"]
                
                # Fixed split layout (approx 30% left sidebar, 70% right details)
                col_left, col_right = st.columns([1.3, 2.7])
                
                selected_tag_ids = []
                
                with col_left:
                    st.markdown("###### Category Group")
                    group_selection = st.radio(
                        "Category Group Selector:",
                        ["Pending & Active", "Approved Gaps"],
                        horizontal=True,
                        key=f"feed_group_radio_{call_id}",
                        label_visibility="collapsed"
                    )
                    
                    target_tags = unapproved_tags if group_selection == "Pending & Active" else approved_tags
                    
                    if not target_tags:
                        st.info("No violations in this section.")
                        selected_tag = None
                    else:
                        st.markdown("###### Violations Inbox")
                        # Build formatted labels for radio list (simulating inbox items)
                        violation_labels = []
                        violation_map = {}
                        
                        for tag in target_tags:
                            sev_icon = "🔴" if tag.severity.value == "Critical" else ("🟠" if tag.severity.value == "High" else ("🟡" if tag.severity.value == "Medium" else "🔵"))
                            conf_val = int(tag.confidence) if getattr(tag, "confidence", None) is not None else 85
                            m_sec = f"{int(tag.timestamp // 60):02d}:{int(tag.timestamp % 60):02d}"
                            
                            label_str = f"{sev_icon} {tag.tag} ({m_sec} | {conf_val}% | {tag.review_status})"
                            violation_labels.append(label_str)
                            violation_map[label_str] = tag
                            
                        # Single radio box acting as our inbox selection
                        selected_label = st.radio(
                            "Select violation to review:",
                            options=violation_labels,
                            key=f"inbox_select_{call_id}",
                            label_visibility="collapsed"
                        )
                        selected_tag = violation_map[selected_label]
                        
                        st.markdown("---")
                        st.markdown("###### Bulk Select List")
                        for tag in target_tags:
                            chk_val = st.checkbox(f"Select: {tag.tag}", key=f"chk_bulk_ref_{tag.id}", value=False)
                            if chk_val:
                                selected_tag_ids.append(tag.id)
                                
                    # Floating bulk actions toolbar (only visible if any are selected)
                    if selected_tag_ids:
                        st.markdown("##### 🛠️ Bulk Action Toolbar")
                        with st.form("bulk_actions_toolbar_inbox"):
                            bulk_action = st.selectbox("Action to Perform", ["Approve Selected", "Dismiss Selected", "Mark as False Positive", "Change Severity"])
                            bulk_sev = st.selectbox("Severity Override", ["Critical", "High", "Medium", "Low"])
                            bulk_comment = st.text_input("Comment (Optional)")
                            
                            if st.form_submit_button("Apply to Selected", use_container_width=True, type="primary"):
                                status_map = {
                                    "Approve Selected": "Approve",
                                    "Dismiss Selected": "Dismiss",
                                    "Mark as False Positive": "False Positive"
                                }
                                for t_id in selected_tag_ids:
                                    t_tag = next((t for t in db_analysis.issue_tags if t.id == t_id), None)
                                    if t_tag:
                                        status = status_map.get(bulk_action, t_tag.review_status)
                                        sev = bulk_sev if bulk_action == "Change Severity" else t_tag.severity.value
                                        FeedbackService.review_issue(
                                            db=db,
                                            issue_id=t_id,
                                            review_status=status,
                                            reviewer_comments=bulk_comment or t_tag.reviewer_comments,
                                            severity=sev
                                        )
                                st.success(f"Successfully applied bulk action!")
                                st.rerun()

                with col_right:
                    if not selected_tag:
                        st.info("Please select a violation from the Violations Inbox to audit.")
                    else:
                        def get_sev_color(sev: str) -> str:
                            s = sev.lower()
                            if s == "critical": return "#ef4444"
                            elif s == "high": return "#f97316"
                            elif s == "medium": return "#f59e0b"
                            else: return "#3b82f6"
                            
                        sev_color = get_sev_color(selected_tag.severity.value)
                        sev_icon = "🔴" if selected_tag.severity.value == "Critical" else ("🟠" if selected_tag.severity.value == "High" else ("🟡" if selected_tag.severity.value == "Medium" else "🔵"))
                        conf_pct = int(selected_tag.confidence) if getattr(selected_tag, "confidence", None) is not None else 85
                        conf_label = "High Confidence" if conf_pct >= 80 else ("Medium Confidence" if conf_pct >= 50 else "Low Confidence")

                        # 2. Compact Information Header
                        st.markdown(
                            f"<div style='border-bottom: 2px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px;'>"
                            f"<h3 style='margin: 0; color: #0f172a;'>{sev_icon} {selected_tag.tag}</h3>"
                            f"<p style='color: #64748b; font-size: 0.9rem; margin: 4px 0 0 0; font-weight: 500;'>"
                            f"<span style='color: {sev_color};'>{selected_tag.severity.value} Severity</span> &nbsp;•&nbsp; "
                            f"{conf_label} ({conf_pct}%) &nbsp;•&nbsp; "
                            f"<span style='color: #4f46e5;'>{selected_tag.review_status}</span> &nbsp;•&nbsp; "
                            f"AI Flagged"
                            f"</p>"
                            f"</div>", unsafe_allow_html=True
                        )

                        # 3. Transcript Evidence (Largest visual section)
                        st.markdown("##### 💬 Conversation Evidence")
                        
                        import json
                        evidence = []
                        if getattr(selected_tag, "evidence_segments", None):
                            try:
                                evidence = json.loads(selected_tag.evidence_segments)
                            except:
                                pass
                                
                        if evidence:
                            for seg in evidence:
                                raw_start = seg.get("start_time", 0.0)
                                raw_end = seg.get("end_time", 0.0)
                                m_start = f"{int(raw_start // 60):02d}:{int(raw_start % 60):02d}"
                                m_end = f"{int(raw_end // 60):02d}:{int(raw_end % 60):02d}"
                                
                                # Highlight quote inside the segment text
                                raw_text = seg.get("transcript_text", "")
                                quote = selected_tag.quote
                                if quote and quote.strip().lower() in raw_text.lower():
                                    import re
                                    highlighted_text = re.sub(
                                        re.escape(quote),
                                        f"<span style='background-color:#fee2e2; border-bottom: 2px solid #ef4444; font-weight:600;'>{quote}</span>",
                                        raw_text,
                                        flags=re.IGNORECASE
                                    )
                                else:
                                    highlighted_text = raw_text

                                st.markdown(
                                    f"<div style='border-left: 4px solid {sev_color}; background-color: #f8fafc; padding: 12px 16px; border-radius: 6px; margin-bottom: 12px;'>"
                                    f"<div style='font-size: 0.8rem; color: #64748b; font-weight: bold; margin-bottom: 4px;'>⏱️ {m_start} – {m_end}</div>"
                                    f"<strong style='color: #0f172a;'>{seg.get('speaker', 'Speaker')}:</strong> "
                                    f"<span style='color: #1e293b;'>{highlighted_text}</span>"
                                    f"</div>", unsafe_allow_html=True
                                )
                        else:
                            m_sec = f"{int(selected_tag.timestamp // 60):02d}:{int(selected_tag.timestamp % 60):02d}"
                            st.markdown(
                                f"<div style='border-left: 4px solid {sev_color}; background-color: #f8fafc; padding: 12px 16px; border-radius: 6px; margin-bottom: 12px;'>"
                                f"<div style='font-size: 0.8rem; color: #64748b; font-weight: bold; margin-bottom: 4px;'>⏱️ {m_sec}</div>"
                                f"<span style='background-color:#fee2e2; border-bottom: 2px solid #ef4444; font-weight:600;'>{selected_tag.quote}</span>"
                                f"</div>", unsafe_allow_html=True
                            )
                            
                        # AI Explanation / Observation box
                        st.markdown(
                            f"<div style='background-color: #fafafa; border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; margin-top: 10px; margin-bottom: 25px;'>"
                            f"<strong style='color: #334155; font-size: 0.9rem;'>🔍 AI Explanation</strong>"
                            f"<p style='margin: 6px 0 0 0; color: #334155; font-size: 0.9rem;'>{selected_tag.reason}</p>"
                            f"</div>", unsafe_allow_html=True
                        )

                        # Navigation button
                        if st.button("📍 View in Full Transcript", key=f"btn_nav_tr_inbox_{selected_tag.id}", use_container_width=True):
                            st.session_state["active_detail_tab"] = "Speech Transcript"
                            st.session_state["highlight_timestamp"] = selected_tag.timestamp if not evidence else evidence[0]["start_time"]
                            st.rerun()

                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # 4. Coaching Section
                        st.markdown("##### 💡 AI Coaching Suggestion")
                        instead_text = selected_tag.quote if selected_tag.quote else (evidence[0].get("transcript_text", "") if evidence else "Generic violation behavior")
                        st.markdown(
                            f"<div style='background-color:#eff6ff; border: 1px solid #bfdbfe; padding: 14px; border-radius: 8px; margin-bottom: 25px;'>"
                            f"<span style='color: #ef4444; font-weight: bold;'>❌ Instead of saying:</span>"
                            f"<p style='margin: 4px 0 10px 18px; font-style: italic; color: #475569;'>\"{instead_text}\"</p>"
                            f"<span style='color: #10b981; font-weight: bold;'>✅ Try:</span>"
                            f"<p style='margin: 4px 0 0 18px; font-weight: 500; color: #1e293b;'>{selected_tag.recommendation}</p>"
                            f"</div>", unsafe_allow_html=True
                        )

                        st.markdown("<br>", unsafe_allow_html=True)

                        # 5. Reviewer Decision Form
                        st.markdown("##### ✍️ Auditor Review Decision")
                        with st.form(f"form_reviewer_decision_{selected_tag.id}"):
                            col_dec1, col_dec2 = st.columns(2)
                            with col_dec1:
                                dec_opts = ["Approve", "Dismiss", "False Positive", "Needs Investigation"]
                                cur_dec = selected_tag.review_status
                                dec_idx = dec_opts.index(cur_dec) if cur_dec in dec_opts else 0
                                decision_val = st.selectbox("Decision", dec_opts, index=dec_idx)
                            with col_dec2:
                                sev_opts = ["Critical", "High", "Medium", "Low"]
                                cur_sev = selected_tag.severity.value
                                sev_idx = sev_opts.index(cur_sev) if cur_sev in sev_opts else 2
                                severity_val = st.selectbox("Severity Override", sev_opts, index=sev_idx)
                                
                            comment_val = st.text_area("Auditor Comment", value=getattr(selected_tag, "reviewer_comments", "") or "")
                            
                            if st.form_submit_button("Save Audit Review", use_container_width=True, type="primary"):
                                FeedbackService.review_issue(
                                    db=db,
                                    issue_id=selected_tag.id,
                                    review_status=decision_val,
                                    reviewer_comments=comment_val,
                                    severity=severity_val
                                )
                                st.success("Review decisions successfully recorded!")
                                st.rerun()

        with sub_tab2:
            st.markdown("##### 2. Quality Score Manual Override")
            current_sc = int(round(details["analysis"]["overall_score"])) if details["analysis"] else 80
            
            # Number input with up/down spinner arrows (no horizontal scrollbar)
            h_score = st.number_input(
                "Human Evaluator Override Score (0 - 100):",
                min_value=0,
                max_value=100,
                value=current_sc,
                step=1
            )
            h_reason = st.text_area("Justification / Rationale for manual override:")
            h_reviewer = st.text_input("Reviewer Name:")
            
            if st.button("Apply Score Override", type="primary", use_container_width=True):
                if not h_reason.strip() or not h_reviewer.strip():
                    st.error("Reviewer name and override justification reason are required fields.")
                else:
                    FeedbackService.override_score(db, call_id, float(h_score), h_reason, h_reviewer)
                    st.success("Manual override scorecard score saved successfully!")
                    st.rerun()

        with sub_tab3:
            st.markdown("##### 3. Trigger Gemini AI Re-Evaluation")
            st.info("Re-run Needs Discovery checklist, Objection handling, and Compliance scorecards on the human dialogue transcripts.")
            
            # Always enabled re-analysis button
            if st.button("Run AI Re-analysis", type="primary", use_container_width=True):
                with st.spinner("Executing multi-agent Gemini scoring pipeline..."):
                    try:
                        FeedbackService.reanalyze(db, call_id)
                        st.success("Re-analysis complete! New scorecard revision created successfully.")
                        st.rerun()
                    except Exception as re_e:
                        st.error(f"Failed to execute re-analysis: {re_e}")
