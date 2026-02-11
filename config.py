# config.py
import os
import streamlit as st
from datetime import datetime

# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_WORD_TARGET = 500
LOGO_URL = "https://menuhunterai.com/wp-content/uploads/2026/02/tms_logo.png"

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

EMAIL_CONFIG = {
    "smtp_server": st.secrets.get("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(st.secrets.get("SMTP_PORT", 587)),
    "sender_email": st.secrets.get("SENDER_EMAIL", ""),
    "sender_password": st.secrets.get("SENDER_PASSWORD", ""),
    "use_tls": True
}

# ============================================================================
# DEFAULT SESSION STATE
# ============================================================================

DEFAULT_STATE = {
    "logged_in": False,
    "user_id": "",
    "user_account": None,
    "show_profile_setup": False,
    "current_session": 0,
    "current_question": 0,
    "responses": {},
    "editing": False,
    "editing_word_target": False,
    "confirming_clear": None,
    "data_loaded": False,
    "current_question_override": None,
    "show_vignette_modal": False,
    "vignette_topic": "",
    "vignette_content": "",
    "selected_vignette_type": "Standard Topic",
    "current_vignette_list": [],
    "editing_vignette_index": None,
    "show_vignette_manager": False,
    "custom_topic_input": "",
    "show_custom_topic_modal": False,
    "show_topic_browser": False,
    "show_session_manager": False,
    "show_session_creator": False,
    "editing_custom_session": None,
    "show_vignette_detail": False,
    "selected_vignette_id": None,
    "editing_vignette_id": None,
    "selected_vignette_for_session": None,
    "published_vignette": None,
    "show_beta_reader": False,
    "current_beta_feedback": None,
}
