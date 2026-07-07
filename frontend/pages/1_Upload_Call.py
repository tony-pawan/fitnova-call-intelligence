import streamlit as st
import requests
import os
from frontend.sidebar import render_sidebar

st.set_page_config(
    page_title="FitNova - Upload Call Recording",
    page_icon="📤",
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

# Render unified sidebar
render_sidebar()

# Role Access Control check
if st.session_state.get("role", "Manager") != "Manager":
    st.warning("⚠️ Access Denied: The Call Upload feature is restricted to Managers. Please switch your role to Manager in the sidebar.")
    st.stop()

# -----------------
# API CONFIGURATION
# -----------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def get_advisors():
    try:
        resp = requests.get(f"{BACKEND_URL}/advisors", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Failed to connect to backend service: {e}")
    return []

# Fetch live advisors list
advisors_list = get_advisors()

# -----------------
# MAIN INTERFACE
# -----------------
st.markdown('<h1 class="main-title">Ingest Sales Call Recording</h1>', unsafe_allow_html=True)
st.markdown("Upload call audio files for automatic ingestion, metadata extraction, and storage mapping.")

# Form Layout split into form and statistics summary
col_form, col_guideline = st.columns([5, 3])

with col_form:
    st.subheader("Upload Ingestion form")
    
    if not advisors_list:
        st.warning("⚠️ No advisors found in the database. Ensure backend is running and the database has been seeded.")
    else:
        # Create map labels for dropdown selection
        advisor_choices = {a["id"]: f"{a['name']} ({a['email']})" for a in advisors_list}
        
        selected_advisor_id = st.selectbox(
            "Assigned Sales Advisor:",
            options=list(advisor_choices.keys()),
            format_func=lambda x: advisor_choices[x]
        )
        
        uploaded_audio = st.file_uploader(
            "Select Audio File (Supported: .wav, .mp3, .m4a)",
            type=["wav", "mp3", "m4a"],
            help="Maximum allowed file size is 100 MB."
        )
        
        if st.button("Upload Recording", type="primary"):
            if not uploaded_audio:
                st.error("❌ Please select an audio file to upload.")
            else:
                file_bytes = uploaded_audio.getvalue()
                file_size_mb = len(file_bytes) / (1024 * 1024)
                
                if file_size_mb > 100.0:
                    st.error(f"❌ File size exceeds 100 MB maximum limit (Current: {file_size_mb:.2f} MB).")
                else:
                    # Execute API upload request
                    files_payload = {
                        "audio_file": (uploaded_audio.name, file_bytes, uploaded_audio.type)
                    }
                    data_payload = {
                        "advisor_id": str(selected_advisor_id)
                    }
                    
                    with st.spinner("Processing upload and parsing audio metadata..."):
                        progress_bar = st.progress(0)
                        try:
                            # Simulate progress animation
                            progress_bar.progress(30)
                            
                            response = requests.post(
                                f"{BACKEND_URL}/calls/upload",
                                data=data_payload,
                                files=files_payload,
                                timeout=30
                            )
                            
                            progress_bar.progress(80)
                            
                            if response.status_code == 200:
                                progress_bar.progress(100)
                                call_id = response.json().get("call_id")
                                st.success(f"✅ Ingestion successful! Call ID: `{call_id}` has been queued for background transcribing & quality analysis.")
                            else:
                                error_msg = response.json().get("detail", "Unknown server error.")
                                st.error(f"❌ Upload failed: {error_msg}")
                        except Exception as e:
                            st.error(f"❌ Failed to submit audio file to backend upload: {e}")
                        finally:
                            progress_bar.empty()

with col_guideline:
    st.subheader("Ingestion Guidelines")
    st.markdown("""
    <div class="saas-card" style="background-color: #f8fafc; font-size: 0.9rem;">
        <strong>Supported Audio Formats:</strong>
        <ul style="margin-top: 10px; padding-left: 20px;">
            <li><strong>WAV</strong> - standard wave files</li>
            <li><strong>MP3</strong> - compressed audio recordings</li>
            <li><strong>M4A</strong> - AAC compressed format files</li>
        </ul>
        <br>
        <strong>Pipeline Stages:</strong>
        <ol style="padding-left: 20px;">
            <li>UUID generation and storage write</li>
            <li>Mutagen metadata duration analysis</li>
            <li>FastAPI background process scheduling</li>
            <li>Whisper transcribing</li>
            <li>Pyannote diarizing</li>
            <li>Gemini quality auditing</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
