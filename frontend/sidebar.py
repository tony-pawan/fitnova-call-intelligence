import streamlit as st
import os
from backend.app.services.dashboard_service import DashboardService
from backend.app.database.session import SessionLocal

def render_sidebar():
    """
    Renders the custom dynamic SaaS sidebar containing role switches,
    advisor simulation selectors, and contextual page links.
    """
    st.markdown('<div class="sidebar-header">⚡ FitNova AI</div>', unsafe_allow_html=True)
    st.markdown("---")

    # 1. Role Selection Mock Authentication
    if "role" not in st.session_state:
        st.session_state["role"] = "Manager"

    # Save active selected role index to prevent selector jumping
    role_options = ["Manager", "Advisor"]
    current_role_index = role_options.index(st.session_state["role"])

    role = st.selectbox(
        "Active Role Mode:",
        options=role_options,
        index=current_role_index,
        key="role_selector_sidebar"
    )

    if role != st.session_state["role"]:
        st.session_state["role"] = role
        st.rerun()

    # 2. Simulated Advisor selectbox if in Advisor role
    if st.session_state["role"] == "Advisor":
        db = SessionLocal()
        try:
            filter_opts = DashboardService.get_filter_options(db)
            advisors = filter_opts["advisors"]
            if advisors:
                if "advisor_id" not in st.session_state:
                    st.session_state["advisor_id"] = advisors[0]["id"]

                adv_ids = [a["id"] for a in advisors]
                try:
                    current_adv_index = adv_ids.index(st.session_state["advisor_id"])
                except ValueError:
                    current_adv_index = 0
                    st.session_state["advisor_id"] = adv_ids[0]

                selected_adv_id = st.selectbox(
                    "Simulated Advisor Profile:",
                    options=adv_ids,
                    format_func=lambda x: next((a["name"] for a in advisors if a["id"] == x), str(x)),
                    index=current_adv_index,
                    key="advisor_selector_sidebar"
                )

                if selected_adv_id != st.session_state["advisor_id"]:
                    st.session_state["advisor_id"] = selected_adv_id
                    st.rerun()
            else:
                st.warning("No advisors seeded in DB.")
        finally:
            db.close()

    st.markdown("---")

    # 3. Dynamic Page Links filtered contextually based on the active role
    st.page_link("Home.py", label="Dashboard Overview", icon="📊")

    if st.session_state["role"] == "Manager":
        st.page_link("pages/1_Upload_Call.py", label="Call Upload", icon="📤")
        st.page_link("pages/2_Call_Details.py", label="Call Details", icon="🔍")
        st.page_link("pages/4_Manager_Dashboard.py", label="Manager Analytics", icon="📈")
    else:
        st.page_link("pages/2_Call_Details.py", label="Call Details", icon="🔍")
        st.page_link("pages/3_Advisor_Dashboard.py", label="Advisor Performance", icon="👤")

    st.markdown("---")
    st.markdown("🔒 **Future Modules (Locked)**")
    st.page_link("Home.py", label="Transcripts Center", icon="📝", disabled=True)
    st.page_link("Home.py", label="Quality Analytics", icon="📈", disabled=True)
    st.page_link("Home.py", label="Compliance Audits", icon="🛡️", disabled=True)
    st.page_link("Home.py", label="Advisor Appeals", icon="⚖️", disabled=True)
