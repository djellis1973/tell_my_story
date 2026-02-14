# biographer.py – Tell My Story App (ORIGINAL WORKING + PUBLISH BUTTONS)
import streamlit as st
import json
from datetime import datetime, date
from openai import OpenAI
import os
import re
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
import time
import shutil
import base64
from PIL import Image
import io
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fpdf import FPDF
import zipfile

# ============================================================================
# IMPORT QUILL RICH TEXT EDITOR
# ============================================================================
try:
    from streamlit_quill import st_quill
    QUILL_AVAILABLE = True
except ImportError:
    st.error("❌ Please install streamlit-quill: pip install streamlit-quill")
    st.stop()

# ============================================================================
# FORCE DIRECTORY CREATION
# ============================================================================
for dir_path in ["question_banks/default", "question_banks/users", "question_banks", 
                 "uploads", "uploads/thumbnails", "uploads/metadata", "accounts", "sessions"]:
    os.makedirs(dir_path, exist_ok=True)

# ============================================================================
# IMPORTS
# ============================================================================
try:
    from topic_bank import TopicBank
    from session_manager import SessionManager
    from vignettes import VignetteManager
    from session_loader import SessionLoader
    from beta_reader import BetaReader
    from question_bank_manager import QuestionBankManager
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.info("Please ensure all .py files are in the same directory")
    TopicBank = SessionManager = VignetteManager = SessionLoader = BetaReader = QuestionBankManager = None

DEFAULT_WORD_TARGET = 500

# ============================================================================
# INITIALIZATION
# ============================================================================
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY")))
beta_reader = BetaReader(client) if BetaReader else None

# Initialize session state
default_state = {
    "qb_manager": None, "qb_manager_initialized": False, "user_id": None, "logged_in": False,
    "current_session": 0, "current_question": 0, "responses": {}, "editing": False,
    "editing_word_target": False, "confirming_clear": None, "data_loaded": False,
    "current_question_override": None, "show_vignette_modal": False, "vignette_topic": "",
    "vignette_content": "", "selected_vignette_type": "Standard Topic", "current_vignette_list": [],
    "editing_vignette_index": None, "show_vignette_manager": False, "custom_topic_input": "",
    "show_custom_topic_modal": False, "show_topic_browser": False, "show_session_manager": False,
    "show_session_creator": False, "editing_custom_session": None, "show_vignette_detail": False,
    "selected_vignette_id": None, "editing_vignette_id": None, "selected_vignette_for_session": None,
    "published_vignette": None, "show_beta_reader": False, "current_beta_feedback": None,
    "current_question_bank": None, "current_bank_name": None, "current_bank_type": None,
    "current_bank_id": None, "show_bank_manager": False, "show_bank_editor": False,
    "editing_bank_id": None, "editing_bank_name": None, "qb_manager": None, "qb_manager_initialized": False,
    "confirm_delete": None, "user_account": None, "show_profile_setup": False,
    "image_handler": None, "show_image_manager": False
}
for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Load external CSS
try:
    with open("styles.css", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

LOGO_URL = "https://menuhunterai.com/wp-content/uploads/2026/02/tms_logo.png"

# ============================================================================
# EMAIL CONFIG
# ============================================================================
EMAIL_CONFIG = {
    "smtp_server": st.secrets.get("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(st.secrets.get("SMTP_PORT", 587)),
    "sender_email": st.secrets.get("SENDER_EMAIL", ""),
    "sender_password": st.secrets.get("SENDER_PASSWORD", ""),
    "use_tls": True
}

# ============================================================================
# IMAGE HANDLER - COMPLETE WORKING VERSION
# ============================================================================
class ImageHandler:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.base_path = "uploads"
    
    def get_user_path(self):
        if self.user_id:
            user_hash = hashlib.md5(self.user_id.encode()).hexdigest()[:8]
            path = f"{self.base_path}/user_{user_hash}"
            os.makedirs(f"{path}/thumbnails", exist_ok=True)
            return path
        return self.base_path
    
    def save_image(self, uploaded_file, session_id, question_text, caption=""):
        try:
            image_data = uploaded_file.read()
            image_id = hashlib.md5(f"{self.user_id}{session_id}{question_text}{datetime.now()}".encode()).hexdigest()[:16]
            
            img = Image.open(io.BytesIO(image_data))
            if img.mode == 'RGBA': 
                img = img.convert('RGB')
            
            # Save full image
            main_buffer = io.BytesIO()
            img.save(main_buffer, format="JPEG", quality=85, optimize=True)
            
            # Save thumbnail
            img.thumbnail((200, 200))
            thumb_buffer = io.BytesIO()
            img.save(thumb_buffer, format="JPEG", quality=70, optimize=True)
            
            user_path = self.get_user_path()
            with open(f"{user_path}/{image_id}.jpg", 'wb') as f: 
                f.write(main_buffer.getvalue())
            with open(f"{user_path}/thumbnails/{image_id}.jpg", 'wb') as f: 
                f.write(thumb_buffer.getvalue())
            
            # Save metadata
            metadata = {
                "id": image_id, 
                "session_id": session_id, 
                "question": question_text,
                "caption": caption, 
                "alt_text": caption[:100] if caption else "",
                "timestamp": datetime.now().isoformat(),
                "user_id": self.user_id
            }
            with open(f"{self.base_path}/metadata/{image_id}.json", 'w') as f: 
                json.dump(metadata, f)
            
            return {"has_images": True, "images": [{"id": image_id, "caption": caption}]}
        except Exception as e:
            print(f"Error saving image: {e}")
            return None
    
    def get_image_html(self, image_id, thumbnail=False):
        try:
            user_path = self.get_user_path()
            path = f"{user_path}/thumbnails/{image_id}.jpg" if thumbnail else f"{user_path}/{image_id}.jpg"
            if not os.path.exists(path): 
                return None
            
            with open(path, 'rb') as f: 
                image_data = f.read()
            b64 = base64.b64encode(image_data).decode()
            
            meta_path = f"{self.base_path}/metadata/{image_id}.json"
            caption = ""
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                    caption = metadata.get("caption", "")
            
            return {
                "html": f'<img src="data:image/jpeg;base64,{b64}" style="max-width:100%; border-radius:8px; margin:5px 0;" alt="{caption}">',
                "caption": caption, 
                "base64": b64
            }
        except:
            return None
    
    def get_image_base64(self, image_id):
        """Get base64 string of an image (for export)"""
        try:
            user_path = self.get_user_path()
            path = f"{user_path}/{image_id}.jpg"
            if not os.path.exists(path): 
                return None
            with open(path, 'rb') as f: 
                image_data = f.read()
            return base64.b64encode(image_data).decode()
        except:
            return None
    
    def get_image_caption(self, image_id):
        """Get caption for an image"""
        meta_path = f"{self.base_path}/metadata/{image_id}.json"
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                    return metadata.get("caption", "")
            except:
                pass
        return ""
    
    def get_images_for_answer(self, session_id, question_text):
        images = []
        metadata_dir = f"{self.base_path}/metadata"
        if not os.path.exists(metadata_dir): 
            return images
        
        for fname in os.listdir(metadata_dir):
            if fname.endswith('.json'):
                try:
                    with open(f"{metadata_dir}/{fname}") as f: 
                        meta = json.load(f)
                    if (meta.get("session_id") == session_id and 
                        meta.get("question") == question_text and 
                        meta.get("user_id") == self.user_id):
                        thumb = self.get_image_html(meta["id"], thumbnail=True)
                        full = self.get_image_html(meta["id"])
                        if thumb and full:
                            images.append({
                                **meta, 
                                "thumb_html": thumb["html"], 
                                "full_html": full["html"]
                            })
                except:
                    continue
        return sorted(images, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def delete_image(self, image_id):
        try:
            user_path = self.get_user_path()
            for p in [f"{user_path}/{image_id}.jpg", 
                     f"{user_path}/thumbnails/{image_id}.jpg", 
                     f"{self.base_path}/metadata/{image_id}.json"]:
                if os.path.exists(p): 
                    os.remove(p)
            return True
        except:
            return False
    
    def render_image_uploader(self, session_id, question_text, existing_images=None):
        st.markdown("### 📸 Add Photos")
        st.caption("Upload photos that illustrate this memory (JPG, PNG)")
        
        if existing_images:
            st.markdown("**Your Photos:**")
            cols = st.columns(min(len(existing_images), 3))
            for idx, img in enumerate(existing_images):
                with cols[idx % 3]:
                    st.markdown(img.get("thumb_html", ""), unsafe_allow_html=True)
                    if img.get("caption"): 
                        st.caption(f"📝 {img['caption']}")
                    if st.button(f"🗑️", key=f"del_{img['id']}"):
                        self.delete_image(img['id']); st.rerun()
        
        uploaded = st.file_uploader("Choose image...", type=['jpg','jpeg','png'], 
                                   key=f"up_{session_id}_{hash(question_text)}", label_visibility="collapsed")
        if uploaded:
            cap = st.text_input("Caption:", key=f"cap_{session_id}_{hash(question_text)}")
            if st.button("📤 Upload", key=f"btn_{session_id}_{hash(question_text)}"):
                with st.spinner("Uploading..."):
                    if self.save_image(uploaded, session_id, question_text, cap):
                        st.success("Uploaded!"); st.rerun()
        return existing_images or []

def init_image_handler():
    if not st.session_state.image_handler or st.session_state.image_handler.user_id != st.session_state.get('user_id'):
        st.session_state.image_handler = ImageHandler(st.session_state.get('user_id'))
    return st.session_state.image_handler

# ============================================================================
# AUTHENTICATION FUNCTIONS (YOUR ORIGINAL)
# ============================================================================
def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash, password):
    return stored_hash == hash_password(password)

def create_user_account(user_data, password=None):
    try:
        user_id = hashlib.sha256(f"{user_data['email']}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        if not password: 
            password = generate_password()
        user_record = {
            "user_id": user_id, 
            "email": user_data["email"].lower().strip(),
            "password_hash": hash_password(password), 
            "account_type": user_data.get("account_for", "self"),
            "created_at": datetime.now().isoformat(), 
            "last_login": datetime.now().isoformat(),
            "profile": {
                "first_name": user_data["first_name"], 
                "last_name": user_data["last_name"],
                "email": user_data["email"], 
                "gender": user_data.get("gender", ""),
                "birthdate": user_data.get("birthdate", ""), 
                "timeline_start": user_data.get("birthdate", "")
            },
            "settings": {
                "email_notifications": True, 
                "auto_save": True, 
                "privacy_level": "private",
                "theme": "light", 
                "email_verified": False
            },
            "stats": {
                "total_sessions": 0, 
                "total_words": 0, 
                "current_streak": 0, 
                "longest_streak": 0,
                "account_age_days": 0, 
                "last_active": datetime.now().isoformat()
            }
        }
        save_account_data(user_record)
        return {"success": True, "user_id": user_id, "password": password, "user_record": user_record}
    except Exception as e:
        return {"success": False, "error": str(e)}

def save_account_data(user_record):
    try:
        with open(f"accounts/{user_record['user_id']}_account.json", 'w') as f:
            json.dump(user_record, f, indent=2)
        update_accounts_index(user_record)
        return True
    except: 
        return False

def update_accounts_index(user_record):
    try:
        index_file = "accounts/accounts_index.json"
        index = json.load(open(index_file, 'r')) if os.path.exists(index_file) else {}
        index[user_record['user_id']] = {
            "email": user_record['email'], 
            "first_name": user_record['profile']['first_name'],
            "last_name": user_record['profile']['last_name'], 
            "created_at": user_record['created_at'],
            "account_type": user_record['account_type']
        }
        with open(index_file, 'w') as f: 
            json.dump(index, f, indent=2)
        return True
    except: 
        return False

def get_account_data(user_id=None, email=None):
    try:
        if user_id:
            fname = f"accounts/{user_id}_account.json"
            if os.path.exists(fname): 
                return json.load(open(fname, 'r'))
        if email:
            email = email.lower().strip()
            index = json.load(open("accounts/accounts_index.json", 'r')) if os.path.exists("accounts/accounts_index.json") else {}
            for uid, data in index.items():
                if data.get("email", "").lower() == email:
                    return json.load(open(f"accounts/{uid}_account.json", 'r'))
    except: 
        pass
    return None

def authenticate_user(email, password):
    try:
        account = get_account_data(email=email)
        if account and verify_password(account['password_hash'], password):
            account['last_login'] = datetime.now().isoformat()
            save_account_data(account)
            return {"success": True, "user_id": account['user_id'], "user_record": account}
        return {"success": False, "error": "Invalid email or password"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_welcome_email(user_data, credentials):
    try:
        if not EMAIL_CONFIG['sender_email'] or not EMAIL_CONFIG['sender_password']: 
            return False
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = user_data['email']
        msg['Subject'] = "Welcome to Tell My Story"
        
        body = f"""
        <html><body style="font-family: Arial;">
        <h2>Welcome to Tell My Story, {user_data['first_name']}!</h2>
        <div style="background: #f0f8ff; padding: 15px; border-left: 4px solid #3498db;">
            <h3>Your Account Details:</h3>
            <p><strong>Account ID:</strong> {credentials['user_id']}</p>
            <p><strong>Email:</strong> {user_data['email']}</p>
            <p><strong>Password:</strong> {credentials['password']}</p>
        </div>
        </body></html>
        """
        msg.attach(MIMEText(body, 'html'))
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            if EMAIL_CONFIG['use_tls']: 
                server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        return True
    except: 
        return False

def logout_user():
    st.session_state.qb_manager = None
    st.session_state.qb_manager_initialized = False
    st.session_state.image_handler = None
    keys = ['user_id', 'user_account', 'logged_in', 'show_profile_setup', 'current_session',
            'current_question', 'responses', 'session_conversations', 'data_loaded',
            'show_vignette_modal', 'vignette_topic', 'vignette_content', 'selected_vignette_type',
            'current_vignette_list', 'editing_vignette_index', 'show_vignette_manager',
            'custom_topic_input', 'show_custom_topic_modal', 'show_topic_browser',
            'show_session_manager', 'show_session_creator', 'editing_custom_session',
            'show_vignette_detail', 'selected_vignette_id', 'editing_vignette_id',
            'selected_vignette_for_session', 'published_vignette', 'show_beta_reader',
            'current_beta_feedback', 'current_question_bank', 'current_bank_name',
            'current_bank_type', 'current_bank_id', 'show_bank_manager', 'show_bank_editor',
            'editing_bank_id', 'editing_bank_name', 'show_image_manager']
    for key in keys:
        if key in st.session_state: 
            del st.session_state[key]
    st.query_params.clear()
    st.rerun()

# ============================================================================
# STORAGE FUNCTIONS
# ============================================================================
def get_user_filename(user_id):
    return f"user_data_{hashlib.md5(user_id.encode()).hexdigest()[:8]}.json"

def load_user_data(user_id):
    fname = get_user_filename(user_id)
    try:
        if os.path.exists(fname):
            return json.load(open(fname, 'r'))
        return {"responses": {}, "vignettes": [], "last_loaded": datetime.now().isoformat()}
    except: 
        return {"responses": {}, "vignettes": [], "last_loaded": datetime.now().isoformat()}

def save_user_data(user_id, responses_data):
    fname = get_user_filename(user_id)
    try:
        existing = load_user_data(user_id)
        data = {
            "user_id": user_id, 
            "responses": responses_data,
            "vignettes": existing.get("vignettes", []),
            "beta_feedback": existing.get("beta_feedback", {}),
            "last_saved": datetime.now().isoformat()
        }
        with open(fname, 'w') as f: 
            json.dump(data, f, indent=2)
        return True
    except: 
        return False

# ============================================================================
# CORE RESPONSE FUNCTIONS
# ============================================================================
def save_response(session_id, question, answer):
    user_id = st.session_state.user_id
    if not user_id: 
        return False
    
    # Strip HTML tags for word count
    text_only = re.sub(r'<[^>]+>', '', answer) if answer else ""
    
    if st.session_state.user_account:
        word_count = len(re.findall(r'\w+', text_only))
        st.session_state.user_account["stats"]["total_words"] = st.session_state.user_account["stats"].get("total_words", 0) + word_count
        st.session_state.user_account["stats"]["last_active"] = datetime.now().isoformat()
        save_account_data(st.session_state.user_account)
    
    if session_id not in st.session_state.responses:
        session_data = next((s for s in (st.session_state.current_question_bank or []) if s["id"] == session_id), 
                          {"title": f"Session {session_id}", "word_target": DEFAULT_WORD_TARGET})
        st.session_state.responses[session_id] = {
            "title": session_data.get("title", f"Session {session_id}"),
            "questions": {}, 
            "summary": "", 
            "completed": False,
            "word_target": session_data.get("word_target", DEFAULT_WORD_TARGET)
        }
    
    # Get images for this answer
    images = []
    if st.session_state.image_handler:
        images = st.session_state.image_handler.get_images_for_answer(session_id, question)
    
    st.session_state.responses[session_id]["questions"][question] = {
        "answer": answer,
        "question": question, 
        "timestamp": datetime.now().isoformat(),
        "answer_index": 1, 
        "has_images": len(images) > 0 or ('<img' in answer),
        "image_count": len(images),
        "images": [{"id": img["id"], "caption": img.get("caption", "")} for img in images]
    }
    
    success = save_user_data(user_id, st.session_state.responses)
    if success: 
        st.session_state.data_loaded = False
    return success

def delete_response(session_id, question):
    user_id = st.session_state.user_id
    if not user_id: 
        return False
    
    if session_id in st.session_state.responses and question in st.session_state.responses[session_id]["questions"]:
        del st.session_state.responses[session_id]["questions"][question]
        success = save_user_data(user_id, st.session_state.responses)
        if success: 
            st.session_state.data_loaded = False
        return success
    return False

def calculate_author_word_count(session_id):
    total = 0
    if session_id in st.session_state.responses:
        for q, d in st.session_state.responses[session_id].get("questions", {}).items():
            if d.get("answer"): 
                text_only = re.sub(r'<[^>]+>', '', d["answer"])
                total += len(re.findall(r'\w+', text_only))
    return total

def get_progress_info(session_id):
    current = calculate_author_word_count(session_id)
    if session_id not in st.session_state.responses:
        session_data = next((s for s in (st.session_state.current_question_bank or []) if s["id"] == session_id), {})
        st.session_state.responses[session_id] = {
            "title": session_data.get("title", f"Session {session_id}"),
            "questions": {}, 
            "summary": "", 
            "completed": False,
            "word_target": session_data.get("word_target", DEFAULT_WORD_TARGET)
        }
    
    target = st.session_state.responses[session_id].get("word_target", DEFAULT_WORD_TARGET)
    if target == 0: 
        percent = 100
    else: 
        percent = (current / target) * 100
    
    return {
        "current_count": current, 
        "target": target, 
        "progress_percent": percent,
        "emoji": "🟢" if percent >= 100 else "🟡" if percent >= 70 else "🔴",
        "color": "#27ae60" if percent >= 100 else "#f39c12" if percent >= 70 else "#e74c3c",
        "remaining_words": max(0, target - current),
        "status_text": "Target achieved!" if current >= target else f"{max(0, target - current)} words remaining"
    }

def auto_correct_text(text):
    if not text: 
        return text
    text_only = re.sub(r'<[^>]+>', '', text)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Fix spelling and grammar. Return only corrected text."},
                {"role": "user", "content": text_only}
            ],
            max_tokens=len(text_only) + 100, 
            temperature=0.1
        )
        return resp.choices[0].message.content
    except: 
        return text

# ============================================================================
# SEARCH FUNCTIONALITY
# ============================================================================
def search_all_answers(search_query):
    if not search_query or len(search_query) < 2: 
        return []
    
    results = []
    search_query = search_query.lower()
    
    for session in (st.session_state.current_question_bank or []):
        session_id = session["id"]
        session_data = st.session_state.responses.get(session_id, {})
        
        for question_text, answer_data in session_data.get("questions", {}).items():
            html_answer = answer_data.get("answer", "")
            text_answer = re.sub(r'<[^>]+>', '', html_answer)
            has_images = answer_data.get("has_images", False) or ('<img' in html_answer)
            
            if search_query in text_answer.lower() or search_query in question_text.lower():
                results.append({
                    "session_id": session_id, 
                    "session_title": session["title"],
                    "question": question_text, 
                    "answer": text_answer[:300] + "..." if len(text_answer) > 300 else text_answer,
                    "timestamp": answer_data.get("timestamp", ""), 
                    "word_count": len(text_answer.split()),
                    "has_images": has_images,
                    "image_count": answer_data.get("image_count", 0)
                })
    
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results

# ============================================================================
# QUESTION BANK LOADING
# ============================================================================
def initialize_question_bank():
    if 'current_question_bank' in st.session_state and st.session_state.current_question_bank:
        return True
    
    if QuestionBankManager:
        try:
            qb_manager = QuestionBankManager(st.session_state.get('user_id'))
            st.session_state.qb_manager = qb_manager
            
            if os.path.exists("sessions/sessions.csv"):
                shutil.copy("sessions/sessions.csv", "question_banks/default/life_story_comprehensive.csv")
            
            default = qb_manager.load_default_bank("life_story_comprehensive")
            if default:
                st.session_state.current_question_bank = default
                st.session_state.current_bank_name = "📖 Life Story - Comprehensive"
                st.session_state.current_bank_type = "default"
                st.session_state.current_bank_id = "life_story_comprehensive"
                st.session_state.qb_manager_initialized = True
                
                for s in default:
                    sid = s["id"]
                    if sid not in st.session_state.responses:
                        st.session_state.responses[sid] = {
                            "title": s["title"], 
                            "questions": {}, 
                            "summary": "",
                            "completed": False, 
                            "word_target": s.get("word_target", DEFAULT_WORD_TARGET)
                        }
                return True
        except: 
            pass
    
    if SessionLoader:
        try:
            legacy = SessionLoader().load_sessions_from_csv()
            if legacy:
                st.session_state.current_question_bank = legacy
                st.session_state.current_bank_name = "Legacy Bank"
                st.session_state.current_bank_type = "legacy"
                for s in legacy:
                    sid = s["id"]
                    if sid not in st.session_state.responses:
                        st.session_state.responses[sid] = {
                            "title": s["title"], 
                            "questions": {}, 
                            "summary": "",
                            "completed": False, 
                            "word_target": s.get("word_target", DEFAULT_WORD_TARGET)
                        }
                return True
        except: 
            pass
    return False

def load_question_bank(sessions, bank_name, bank_type, bank_id=None):
    st.session_state.current_question_bank = sessions
    st.session_state.current_bank_name = bank_name
    st.session_state.current_bank_type = bank_type
    st.session_state.current_bank_id = bank_id
    st.session_state.current_session = 0
    st.session_state.current_question = 0
    st.session_state.current_question_override = None
    
    for s in sessions:
        sid = s["id"]
        if sid not in st.session_state.responses:
            st.session_state.responses[sid] = {
                "title": s["title"], 
                "questions": {},
                "summary": "",
                "completed": False, 
                "word_target": s.get("word_target", DEFAULT_WORD_TARGET)
            }

# ============================================================================
# BETA READER FUNCTIONS
# ============================================================================
def generate_beta_reader_feedback(session_title, session_text, feedback_type="comprehensive"):
    if not beta_reader: 
        return {"error": "BetaReader not available"}
    return beta_reader.generate_feedback(session_title, session_text, feedback_type)

def save_beta_feedback(user_id, session_id, feedback_data):
    if not beta_reader: 
        return False
    return beta_reader.save_feedback(user_id, session_id, feedback_data, get_user_filename, load_user_data)

def get_previous_beta_feedback(user_id, session_id):
    if not beta_reader: 
        return None
    return beta_reader.get_previous_feedback(user_id, session_id, get_user_filename, load_user_data)

# ============================================================================
# VIGNETTE FUNCTIONS
# ============================================================================
def on_vignette_select(vignette_id):
    st.session_state.selected_vignette_id = vignette_id
    st.session_state.show_vignette_detail = True
    st.session_state.show_vignette_manager = False
    st.rerun()

def on_vignette_edit(vignette_id):
    st.session_state.editing_vignette_id = vignette_id
    st.session_state.show_vignette_detail = False
    st.session_state.show_vignette_manager = False
    st.session_state.show_vignette_modal = True
    st.rerun()

def on_vignette_delete(vignette_id):
    if VignetteManager and st.session_state.get('vignette_manager', VignetteManager(st.session_state.user_id)).delete_vignette(vignette_id):
        st.success("Deleted!"); 
        st.rerun()
    else: 
        st.error("Failed to delete")

def on_vignette_publish(vignette):
    st.session_state.published_vignette = vignette
    st.success(f"Published '{vignette['title']}'!"); 
    st.rerun()

def show_vignette_modal():
    if not VignetteManager: 
        st.error("Vignette module not available"); 
        st.session_state.show_vignette_modal = False; 
        return
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    if st.button("←", key="vign_modal_back"): 
        st.session_state.show_vignette_modal = False; 
        st.session_state.editing_vignette_id = None; 
        st.rerun()
    st.title("✏️ Edit Vignette" if st.session_state.get('editing_vignette_id') else "✍️ Create Vignette")
    if 'vignette_manager' not in st.session_state: 
        st.session_state.vignette_manager = VignetteManager(st.session_state.user_id)
    edit = st.session_state.vignette_manager.get_vignette_by_id(st.session_state.editing_vignette_id) if st.session_state.get('editing_vignette_id') else None
    st.session_state.vignette_manager.display_vignette_creator(on_publish=on_vignette_publish, edit_vignette=edit)
    st.markdown('</div>', unsafe_allow_html=True)

def show_vignette_manager():
    if not VignetteManager: 
        st.error("Vignette module not available"); 
        st.session_state.show_vignette_manager = False; 
        return
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    if st.button("←", key="vign_mgr_back"): 
        st.session_state.show_vignette_manager = False; 
        st.rerun()
    st.title("📚 Your Vignettes")
    if 'vignette_manager' not in st.session_state: 
        st.session_state.vignette_manager = VignetteManager(st.session_state.user_id)
    filter_map = {"All Stories": "all", "Published": "published", "Drafts": "drafts"}
    filter_option = st.radio("Show:", ["All Stories", "Published", "Drafts"], horizontal=True, key="vign_filter")
    st.session_state.vignette_manager.display_vignette_gallery(
        filter_by=filter_map.get(filter_option, "all"),
        on_select=on_vignette_select, 
        on_edit=on_vignette_edit, 
        on_delete=on_vignette_delete
    )
    st.divider()
    if st.button("➕ Create New Vignette", type="primary", use_container_width=True):
        st.session_state.show_vignette_manager = False; 
        st.session_state.show_vignette_modal = True; 
        st.session_state.editing_vignette_id = None; 
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def show_vignette_detail():
    if not VignetteManager or not st.session_state.get('selected_vignette_id'): 
        st.session_state.show_vignette_detail = False; 
        return
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    if st.button("←", key="vign_detail_back"): 
        st.session_state.show_vignette_detail = False; 
        st.session_state.selected_vignette_id = None; 
        st.rerun()
    st.title("📖 Read Vignette")
    if 'vignette_manager' not in st.session_state: 
        st.session_state.vignette_manager = VignetteManager(st.session_state.user_id)
    vignette = st.session_state.vignette_manager.get_vignette_by_id(st.session_state.selected_vignette_id)
    if not vignette: 
        st.error("Not found"); 
        st.session_state.show_vignette_detail = False; 
        return
    st.session_state.vignette_manager.display_full_vignette(
        st.session_state.selected_vignette_id,
        on_back=lambda: st.session_state.update(show_vignette_detail=False, selected_vignette_id=None),
        on_edit=on_vignette_edit
    )
    st.markdown('</div>', unsafe_allow_html=True)

def switch_to_vignette(vignette_topic, content=""):
    st.session_state.current_question_override = f"Vignette: {vignette_topic}"
    if content:
        save_response(st.session_state.current_question_bank[st.session_state.current_session]["id"], 
                     f"Vignette: {vignette_topic}", content)
    st.rerun()

def switch_to_custom_topic(topic_text):
    st.session_state.current_question_override = topic_text
    st.rerun()

# ============================================================================
# TOPIC BROWSER & SESSION MANAGER
# ============================================================================
def show_topic_browser():
    if not TopicBank: 
        st.error("Topic module not available"); 
        st.session_state.show_topic_browser = False; 
        return
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    if st.button("← Back", key="topic_back"): 
        st.session_state.show_topic_browser = False; 
        st.rerun()
    st.title("📚 Topic Browser")
    TopicBank(st.session_state.user_id).display_topic_browser(
        on_topic_select=lambda t: (switch_to_custom_topic(t), st.session_state.update(show_topic_browser=False)),
        unique_key=str(time.time())
    )
    st.markdown('</div>', unsafe_allow_html=True)

def show_session_creator():
    if not SessionManager: 
        st.error("Session module not available"); 
        st.session_state.show_session_creator = False; 
        return
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    if st.button("← Back", key="session_creator_back"): 
        st.session_state.show_session_creator = False; 
        st.rerun()
    st.title("📋 Create Custom Session")
    SessionManager(st.session_state.user_id, "sessions/sessions.csv").display_session_creator()
    st.markdown('</div>', unsafe_allow_html=True)

def show_session_manager():
    if not SessionManager: 
        st.error("Session module not available"); 
        st.session_state.show_session_manager = False; 
        return
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    if st.button("← Back", key="session_manager_back"): 
        st.session_state.show_session_manager = False; 
        st.rerun()
    st.title("📖 Session Manager")
    mgr = SessionManager(st.session_state.user_id, "sessions/sessions.csv")
    if st.button("➕ Create New Session", type="primary", use_container_width=True):
        st.session_state.show_session_manager = False; 
        st.session_state.show_session_creator = True; 
        st.rerun()
    st.divider()
    mgr.display_session_grid(cols=2, on_session_select=lambda sid: [st.session_state.update(
        current_session=i, current_question=0, current_question_override=None) for i, s in enumerate(st.session_state.current_question_bank) if s["id"] == sid][0])
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# QUESTION BANK UI FUNCTIONS
# ============================================================================
def show_bank_manager():
    if not QuestionBankManager: 
        st.error("Question Bank Manager not available"); 
        st.session_state.show_bank_manager = False; 
        return
    user_id = st.session_state.get('user_id')
    if st.session_state.qb_manager is None: 
        st.session_state.qb_manager = QuestionBankManager(user_id)
    else: 
        st.session_state.qb_manager.user_id = user_id
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    if st.button("←", key="bank_manager_back"): 
        st.session_state.show_bank_manager = False; 
        st.rerun()
    st.session_state.qb_manager.display_bank_selector()
    st.markdown('</div>', unsafe_allow_html=True)

def show_bank_editor():
    if not QuestionBankManager or not st.session_state.get('editing_bank_id'): 
        st.session_state.show_bank_editor = False; 
        return
    user_id = st.session_state.get('user_id')
    if st.session_state.qb_manager is None: 
        st.session_state.qb_manager = QuestionBankManager(user_id)
    else: 
        st.session_state.qb_manager.user_id = user_id
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    st.session_state.qb_manager.display_bank_editor(st.session_state.editing_bank_id)
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# PDF GENERATION FUNCTIONS - COMPLETELY REWRITTEN FOR RELIABILITY
# ============================================================================
class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, 'Tell My Story', 0, 0, 'L')
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')
            self.ln(15)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Generated by Tell My Story', 0, 0, 'C')

def generate_pdf(book_title, author_name, stories, format_style, include_toc, include_dates):
    pdf = PDF()
    pdf.add_page()
    
    # Cover page - simple, no special characters
    pdf.set_fill_color(102, 126, 234)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_text_color(255, 255, 255)
    
    # Use ASCII only
    safe_title = ''.join(c for c in book_title if ord(c) < 128)
    safe_author = ''.join(c for c in author_name if ord(c) < 128)
    
    pdf.set_font('Arial', 'B', 30)
    pdf.cell(0, 40, '', 0, 1)
    pdf.cell(0, 20, safe_title if safe_title else 'My Story', 0, 1, 'C')
    pdf.set_font('Arial', '', 16)
    pdf.cell(0, 10, f'by {safe_author}' if safe_author else 'by Author', 0, 1, 'C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, 'Generated by Tell My Story', 0, 1, 'C')
    pdf.add_page()
    
    # Simple content - just text, no images in PDF for now
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 11)
    
    for story in stories:
        question = story.get('question', '')
        answer = story.get('answer_text', '')
        
        # Clean text
        safe_q = ''.join(c for c in question if ord(c) < 128)
        safe_a = ''.join(c for c in answer if ord(c) < 128)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.multi_cell(0, 6, safe_q)
        pdf.ln(2)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 6, safe_a)
        pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# ============================================================================
# DOCX GENERATION FUNCTIONS
# ============================================================================
def generate_docx(book_title, author_name, stories, format_style, include_toc, include_dates):
    doc = Document()
    
    # Title page
    title = doc.add_heading(book_title, 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    author = doc.add_paragraph(f'by {author_name}')
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para = doc.add_paragraph(f'Generated on {datetime.now().strftime("%B %d, %Y")}')
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()
    
    # TOC
    if include_toc:
        doc.add_heading('Table of Contents', 1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        if isinstance(stories, list):
            current_session = None
            for i, story in enumerate(stories, 1):
                session_id = story.get('session_id', '1')
                if session_id != current_session:
                    session_title = story.get('session_title', f'Session {session_id}')
                    doc.add_heading(session_title, 2)
                    current_session = session_id
                question = story.get('question', f'Story {i}')
                p = doc.add_paragraph(f'{i}. {question}')
                p.style = 'List Bullet'
        doc.add_page_break()
    
    # Content
    if isinstance(stories, list):
        current_session = None
        story_counter = 1
        for story in stories:
            session_id = story.get('session_id', '1')
            if session_id != current_session:
                session_title = story.get('session_title', f'Session {session_id}')
                doc.add_heading(session_title, 1)
                current_session = session_id
            question = story.get('question', '')
            answer_text = story.get('answer_text', '')
            images = story.get('images', [])
            
            if format_style == 'interview':
                doc.add_heading(f'Q: {question}', 3)
                doc.add_paragraph(answer_text)
            elif format_style == 'biography':
                doc.add_paragraph(answer_text)
            else:
                doc.add_heading(f'Chapter {story_counter}: {question}', 2)
                doc.add_paragraph(answer_text)
            
            # Embed images
            for img_data in images:
                b64 = img_data.get('base64')
                caption = img_data.get('caption', '')
                if b64:
                    try:
                        img_bytes = base64.b64decode(b64)
                        img_stream = io.BytesIO(img_bytes)
                        doc.add_picture(img_stream, width=Inches(4))
                        if caption:
                            cap = doc.add_paragraph(caption)
                            cap.style = 'Caption'
                    except:
                        pass
            doc.add_paragraph()
            story_counter += 1
    
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    return docx_bytes

# ============================================================================
# HTML GENERATION FUNCTION
# ============================================================================
def generate_html(book_title, author_name, stories):
    """Generate a beautiful HTML file with images"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{book_title}</title>
    <style>
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
            background: #fff;
        }}
        h1 {{
            color: #667eea;
            text-align: center;
            font-size: 2.5em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #764ba2;
            margin-top: 40px;
        }}
        .author {{
            text-align: center;
            font-size: 1.2em;
            color: #666;
            margin-bottom: 40px;
        }}
        .story {{
            margin-bottom: 50px;
            padding: 25px;
            background: #f9f9f9;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .question {{
            font-size: 1.4em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
            padding-left: 15px;
        }}
        .answer {{
            font-size: 1.1em;
            white-space: pre-wrap;
            margin-bottom: 20px;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 15px 0;
            display: block;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .caption {{
            font-style: italic;
            color: #666;
            text-align: center;
            margin-top: -10px;
            margin-bottom: 20px;
            font-size: 0.95em;
        }}
        hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 40px 0;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 0.9em;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
        .image-gallery {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            margin: 20px 0;
        }}
        .image-item {{
            flex: 0 1 auto;
            max-width: 300px;
        }}
    </style>
</head>
<body>
    <h1>{book_title}</h1>
    <div class="author">by {author_name}</div>
"""
    
    for i, story in enumerate(stories):
        html += f"""
    <div class="story">
        <div class="question">{story['question']}</div>
        <div class="answer">{story['answer_text']}</div>
"""
        # Add images if any
        if story.get('images'):
            html += '        <div class="image-gallery">\n'
            for img in story.get('images', []):
                if img.get('base64'):
                    html += f'            <div class="image-item">\n'
                    html += f'                <img src="data:image/jpeg;base64,{img["base64"]}" alt="{img.get("caption", "")}">\n'
                    if img.get('caption'):
                        html += f'                <div class="caption">📝 {img["caption"]}</div>\n'
                    html += f'            </div>\n'
            html += '        </div>\n'
        
        html += f"""
    </div>
    <hr>
"""
    
    html += f"""
    <div class="footer">
        Generated by Tell My Story • {datetime.now().strftime("%B %d, %Y")}
    </div>
</body>
</html>"""
    return html

# ============================================================================
# ZIP GENERATION FUNCTION (HTML + Images)
# ============================================================================
def generate_zip(book_title, author_name, stories):
    """Generate a ZIP file containing HTML and all images as separate files"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Generate HTML that links to image files
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{book_title}</title>
    <style>
        body {{
            font-family: 'Georgia', serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{ color: #667eea; text-align: center; }}
        .story {{ margin-bottom: 50px; padding: 20px; background: #f9f9f9; border-radius: 10px; }}
        .question {{ font-size: 1.3em; font-weight: bold; color: #2c3e50; margin-bottom: 15px; }}
        img {{ max-width: 100%; border-radius: 8px; margin: 10px 0; }}
        .caption {{ font-style: italic; color: #666; text-align: center; }}
    </style>
</head>
<body>
    <h1>{book_title}</h1>
    <div style="text-align: center;">by {author_name}</div>
"""
        
        image_counter = 0
        for i, story in enumerate(stories):
            html += f"""
    <div class="story">
        <div class="question">{story['question']}</div>
        <div>{story['answer_text']}</div>
"""
            # Add images as separate files
            for j, img in enumerate(story.get('images', [])):
                if img.get('base64'):
                    # Save image to zip
                    img_data = base64.b64decode(img['base64'])
                    img_filename = f"images/image_{i}_{j}.jpg"
                    zip_file.writestr(img_filename, img_data)
                    
                    # Add image reference to HTML
                    html += f'        <img src="{img_filename}" alt="{img.get("caption", "")}">\n'
                    if img.get('caption'):
                        html += f'        <div class="caption">📝 {img["caption"]}</div>\n'
                    image_counter += 1
            
            html += f"""
    </div>
    <hr>
"""
        
        html += f"""
    <div class="footer">
        Generated by Tell My Story • {datetime.now().strftime("%B %d, %Y")}<br>
        Contains {image_counter} images
    </div>
</body>
</html>"""
        
        # Add HTML file to zip
        zip_file.writestr(f"{book_title.replace(' ', '_')}.html", html)
    
    return zip_buffer.getvalue()

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(page_title="Tell My Story - Your Life Timeline", page_icon="📖", layout="wide", initial_sidebar_state="expanded")

# Initialize question bank
if not st.session_state.qb_manager_initialized: 
    initialize_question_bank()
SESSIONS = st.session_state.get('current_question_bank', [])

# Load user data
if st.session_state.logged_in and st.session_state.user_id and not st.session_state.data_loaded:
    user_data = load_user_data(st.session_state.user_id)
    if "responses" in user_data:
        for sid_str, sdata in user_data["responses"].items():
            try: 
                sid = int(sid_str)
            except: 
                continue
            if sid in st.session_state.responses and "questions" in sdata and sdata["questions"]:
                st.session_state.responses[sid]["questions"] = sdata["questions"]
    st.session_state.data_loaded = True
    init_image_handler()

if not SESSIONS:
    st.error("❌ No question bank loaded. Use Bank Manager.")
    if st.button("📋 Open Bank Manager", type="primary"): 
        st.session_state.show_bank_manager = True; 
        st.rerun()
    st.stop()

# ============================================================================
# PROFILE SETUP MODAL
# ============================================================================
if st.session_state.get('show_profile_setup', False):
    st.markdown('<div class="profile-setup-modal">', unsafe_allow_html=True)
    st.title("👤 Complete Your Profile")
    with st.form("profile_setup_form"):
        gender = st.radio("Gender", ["Male", "Female", "Other", "Prefer not to say"], horizontal=True, key="modal_gender", label_visibility="collapsed")
        col1, col2, col3 = st.columns(3)
        with col1: 
            birth_month = st.selectbox("Month", ["January","February","March","April","May","June","July","August","September","October","November","December"], key="modal_month")
        with col2: 
            birth_day = st.selectbox("Day", list(range(1,32)), key="modal_day")
        with col3: 
            birth_year = st.selectbox("Year", list(range(datetime.now().year, datetime.now().year-120, -1)), key="modal_year")
        account_for = st.radio("Account Type", ["For me", "For someone else"], key="modal_account_type", horizontal=True)
        
        if st.form_submit_button("Complete Profile", type="primary", use_container_width=True):
            if birth_month and birth_day and birth_year:
                birthdate = f"{birth_month} {birth_day}, {birth_year}"
                if st.session_state.user_account:
                    st.session_state.user_account['profile'].update({'gender': gender, 'birthdate': birthdate, 'timeline_start': birthdate})
                    st.session_state.user_account['account_type'] = "self" if account_for == "For me" else "other"
                    save_account_data(st.session_state.user_account)
                st.session_state.show_profile_setup = False; 
                st.rerun()
        if st.form_submit_button("Skip for Now", use_container_width=True):
            st.session_state.show_profile_setup = False; 
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True); 
    st.stop()

# ============================================================================
# AUTHENTICATION UI
# ============================================================================
if not st.session_state.logged_in:
    st.markdown('<div class="auth-container"><h1>Tell My Story</h1><p>Your Life Timeline • Preserve Your Legacy</p></div>', unsafe_allow_html=True)
    if 'auth_tab' not in st.session_state: 
        st.session_state.auth_tab = 'login'
    
    col1, col2 = st.columns(2)
    with col1: 
        st.button("🔐 Login", use_container_width=True, type="primary" if st.session_state.auth_tab=='login' else "secondary", 
                        on_click=lambda: st.session_state.update(auth_tab='login'))
    with col2: 
        st.button("📝 Sign Up", use_container_width=True, type="primary" if st.session_state.auth_tab=='signup' else "secondary",
                        on_click=lambda: st.session_state.update(auth_tab='signup'))
    st.divider()
    
    if st.session_state.auth_tab == 'login':
        with st.form("login_form"):
            st.subheader("Welcome Back")
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary", use_container_width=True):
                if email and password:
                    result = authenticate_user(email, password)
                    if result["success"]:
                        st.session_state.update(user_id=result["user_id"], 
                                              user_account=result["user_record"],
                                              logged_in=True, 
                                              data_loaded=False, 
                                              qb_manager=None, 
                                              qb_manager_initialized=False)
                        st.success("Login successful!"); 
                        st.rerun()
                    else: 
                        st.error(f"Login failed: {result.get('error', 'Unknown error')}")
    else:
        with st.form("signup_form"):
            st.subheader("Create New Account")
            col1, col2 = st.columns(2)
            with col1: 
                first_name = st.text_input("First Name*")
            with col2: 
                last_name = st.text_input("Last Name*")
            email = st.text_input("Email Address*")
            col1, col2 = st.columns(2)
            with col1: 
                password = st.text_input("Password*", type="password")
            with col2: 
                confirm = st.text_input("Confirm Password*", type="password")
            accept = st.checkbox("I agree to the Terms*")
            
            if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                errors = []
                if not first_name: errors.append("First name required")
                if not last_name: errors.append("Last name required")
                if not email or "@" not in email: errors.append("Valid email required")
                if not password or len(password) < 8: errors.append("Password must be 8+ characters")
                if password != confirm: errors.append("Passwords don't match")
                if not accept: errors.append("Must accept terms")
                if get_account_data(email=email): errors.append("Email already exists")
                
                if errors: 
                    [st.error(e) for e in errors]
                else:
                    result = create_user_account({"first_name": first_name, "last_name": last_name, "email": email, "account_for": "self"}, password)
                    if result["success"]:
                        send_welcome_email({"first_name": first_name, "email": email}, 
                                         {"user_id": result["user_id"], "password": password})
                        st.session_state.update(user_id=result["user_id"], 
                                              user_account=result["user_record"],
                                              logged_in=True, 
                                              data_loaded=False, 
                                              show_profile_setup=True,
                                              qb_manager=None, 
                                              qb_manager_initialized=False)
                        st.success("Account created!"); 
                        st.balloons(); 
                        st.rerun()
                    else: 
                        st.error(f"Error: {result.get('error', 'Unknown error')}")
    st.stop()

# ============================================================================
# MODAL HANDLING
# ============================================================================
if st.session_state.show_bank_manager: 
    show_bank_manager(); 
    st.stop()
if st.session_state.show_bank_editor: 
    show_bank_editor(); 
    st.stop()
if st.session_state.show_beta_reader and st.session_state.current_beta_feedback: 
    if beta_reader:
        beta_reader.show_modal(st.session_state.current_beta_feedback, 
                              {"id": SESSIONS[st.session_state.current_session]["id"], 
                               "title": SESSIONS[st.session_state.current_session]["title"]},
                              st.session_state.user_id, 
                              save_beta_feedback, 
                              lambda: st.session_state.update(show_beta_reader=False, current_beta_feedback=None))
    st.stop()
if st.session_state.show_vignette_detail: 
    show_vignette_detail(); 
    st.stop()
if st.session_state.show_vignette_manager: 
    show_vignette_manager(); 
    st.stop()
if st.session_state.show_vignette_modal: 
    show_vignette_modal(); 
    st.stop()
if st.session_state.show_topic_browser: 
    show_topic_browser(); 
    st.stop()
if st.session_state.show_session_manager: 
    show_session_manager(); 
    st.stop()
if st.session_state.show_session_creator: 
    show_session_creator(); 
    st.stop()

# ============================================================================
# MAIN HEADER
# ============================================================================
st.markdown(f'<div class="main-header"><img src="{LOGO_URL}" class="logo-img"></div>', unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown('<div style="text-align: center; padding: 1rem 0;"><h2 style="color: #0066cc;">Tell My Story</h2><p style="color: #36cfc9;">Your Life Timeline</p></div>', unsafe_allow_html=True)
    
    st.header("👤 Your Profile")
    if st.session_state.user_account:
        profile = st.session_state.user_account['profile']
        st.success(f"✓ **{profile['first_name']} {profile['last_name']}**")
    if st.button("📝 Edit Profile", use_container_width=True): 
        st.session_state.show_profile_setup = True; 
        st.rerun()
    if st.button("🚪 Log Out", use_container_width=True): 
        logout_user()
    
    st.divider()
    st.header("📚 Question Banks")
    if st.button("📋 Bank Manager", use_container_width=True, type="primary"): 
        st.session_state.show_bank_manager = True; 
        st.rerun()
    if st.session_state.get('current_bank_name'): 
        st.info(f"**Current Bank:**\n{st.session_state.current_bank_name}")
    
    st.divider()
    st.header("📖 Sessions")
    if st.session_state.current_question_bank:
        for i, s in enumerate(st.session_state.current_question_bank):
            sid = s["id"]
            sdata = st.session_state.responses.get(sid, {})
            resp_cnt = len(sdata.get("questions", {}))
            total_q = len(s["questions"])
            status = "🟢" if resp_cnt == total_q and total_q > 0 else "🟡" if resp_cnt > 0 else "🔴"
            if i == st.session_state.current_session: 
                status = "▶️"
            if st.button(f"{status} Session {sid}: {s['title']}", key=f"sel_sesh_{i}", use_container_width=True):
                st.session_state.update(current_session=i, current_question=0, editing=False, current_question_override=None); 
                st.rerun()
    
    st.divider()
    st.header("✨ Vignettes")
    if st.button("📝 New Vignette", use_container_width=True): 
        st.session_state.show_vignette_modal = True; 
        st.session_state.editing_vignette_id = None; 
        st.rerun()
    if st.button("📖 View All Vignettes", use_container_width=True): 
        st.session_state.show_vignette_manager = True; 
        st.rerun()
    
    st.divider()
    st.header("📖 Session Management")
    if st.button("📋 All Sessions", use_container_width=True): 
        st.session_state.show_session_manager = True; 
        st.rerun()
    if st.button("➕ Custom Session", use_container_width=True): 
        st.session_state.show_session_creator = True; 
        st.rerun()
    
    st.divider()
    st.subheader("📤 Export Options")
    total_answers = sum(len(st.session_state.responses.get(s["id"], {}).get("questions", {})) for s in SESSIONS)
    st.caption(f"Total answers: {total_answers}")
    
    if st.session_state.logged_in and st.session_state.user_id:
        # Prepare export data with images
        export_data = []
        for session in SESSIONS:
            sid = session["id"]
            sdata = st.session_state.responses.get(sid, {})
            for q, a in sdata.get("questions", {}).items():
                # Get images with base64 data
                images_with_data = []
                if a.get("images"):
                    for img_ref in a.get("images", []):
                        img_id = img_ref.get("id")
                        b64 = st.session_state.image_handler.get_image_base64(img_id) if st.session_state.image_handler else None
                        caption = img_ref.get("caption", "")
                        if b64:
                            images_with_data.append({
                                "id": img_id,
                                "base64": b64,
                                "caption": caption
                            })
                
                export_item = {
                    "question": q,
                    "answer_text": re.sub(r'<[^>]+>', '', a.get("answer", "")),
                    "timestamp": a.get("timestamp", ""),
                    "session_id": sid,
                    "session_title": session["title"],
                    "has_images": a.get("has_images", False),
                    "image_count": a.get("image_count", 0),
                    "images": images_with_data
                }
                export_data.append(export_item)
        
        if export_data:
            # JSON backup option
            complete_data = {
                "user": st.session_state.user_id, 
                "user_profile": st.session_state.user_account.get('profile', {}),
                "stories": export_data, 
                "export_date": datetime.now().isoformat(),
                "summary": {
                    "total_stories": len(export_data), 
                    "total_sessions": len(set(s['session_id'] for s in export_data))
                }
            }
            json_data = json.dumps(complete_data, indent=2)
            
            st.download_button(label="📥 Download JSON Backup", 
                              data=json_data,
                              file_name=f"Tell_My_Story_Backup_{st.session_state.user_id}.json",
                              mime="application/json", 
                              use_container_width=True)
            
            st.divider()
            
            # ===== PUBLISH BUTTONS =====
            st.markdown("### 🖨️ Publish Your Book")
            
            # Book settings
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.session_state.user_account.get('profile', {}).get('first_name', 'My')
                book_title = st.text_input("Book Title", value=f"{first_name}'s Story")
            with col2:
                author_name = st.text_input("Author Name", value=f"{st.session_state.user_account.get('profile', {}).get('first_name', '')} {st.session_state.user_account.get('profile', {}).get('last_name', '')}".strip())
            
            format_style = st.selectbox("Format Style", ["interview", "biography", "memoir"], 
                                       format_func=lambda x: {"interview": "📝 Interview Q&A", 
                                                             "biography": "📖 Continuous Biography", 
                                                             "memoir": "📚 Chapter-based Memoir"}[x])
            
            col1, col2 = st.columns(2)
            with col1:
                include_toc = st.checkbox("Table of Contents", value=True)
            with col2:
                include_dates = st.checkbox("Include Dates", value=False)
            
            # Three publish options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 DOCX", type="primary", use_container_width=True):
                    with st.spinner("Creating Word document..."):
                        docx_bytes = generate_docx(
                            book_title,
                            author_name,
                            export_data,
                            format_style,
                            include_toc,
                            include_dates
                        )
                        filename = f"{book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.docx"
                        st.download_button(
                            "📥 Download DOCX", 
                            data=docx_bytes, 
                            file_name=filename, 
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                            use_container_width=True,
                            key="docx_download"
                        )

            with col2:
                if st.button("🌐 HTML", type="primary", use_container_width=True):
                    with st.spinner("Creating HTML page..."):
                        html_content = generate_html(book_title, author_name, export_data)
                        filename = f"{book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html"
                        st.download_button(
                            "📥 Download HTML", 
                            data=html_content, 
                            file_name=filename, 
                            mime="text/html", 
                            use_container_width=True,
                            key="html_download"
                        )

            with col3:
                if st.button("📦 ZIP", type="primary", use_container_width=True):
                    with st.spinner("Creating ZIP package..."):
                        zip_data = generate_zip(book_title, author_name, export_data)
                        filename = f"{book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.zip"
                        st.download_button(
                            "📥 Download ZIP", 
                            data=zip_data, 
                            file_name=filename, 
                            mime="application/zip", 
                            use_container_width=True,
                            key="zip_download"
                        )
        else: 
            st.warning("No stories yet! Start writing to publish.")
    else: 
        st.warning("Please log in to export your data.")
    
    st.divider()
    st.subheader("⚠️ Clear Data")
    if st.session_state.confirming_clear == "session":
        st.warning("**Delete ALL answers in current session?**")
        if st.button("✅ Confirm", type="primary", key="conf_sesh"): 
            sid = SESSIONS[st.session_state.current_session]["id"]
            st.session_state.responses[sid]["questions"] = {}
            save_user_data(st.session_state.user_id, st.session_state.responses)
            st.session_state.confirming_clear = None; 
            st.rerun()
        if st.button("❌ Cancel", key="can_sesh"): 
            st.session_state.confirming_clear = None; 
            st.rerun()
    elif st.session_state.confirming_clear == "all":
        st.warning("**Delete ALL answers for ALL sessions?**")
        if st.button("✅ Confirm All", type="primary", key="conf_all"): 
            for s in SESSIONS:
                st.session_state.responses[s["id"]]["questions"] = {}
            save_user_data(st.session_state.user_id, st.session_state.responses)
            st.session_state.confirming_clear = None; 
            st.rerun()
        if st.button("❌ Cancel", key="can_all"): 
            st.session_state.confirming_clear = None; 
            st.rerun()
    else:
        if st.button("🗑️ Clear Session", use_container_width=True): 
            st.session_state.confirming_clear = "session"; 
            st.rerun()
        if st.button("🔥 Clear All", use_container_width=True): 
            st.session_state.confirming_clear = "all"; 
            st.rerun()
    
    st.divider()
    st.subheader("🔍 Search Your Stories")
    search_query = st.text_input("Search answers & captions...", placeholder="e.g., childhood, wedding, photo", key="global_search")
    if search_query and len(search_query) >= 2:
        results = search_all_answers(search_query)
        if results:
            st.success(f"Found {len(results)} matches")
            with st.expander(f"📖 {len(results)} Results", expanded=True):
                for i, r in enumerate(results[:10]):
                    st.markdown(f"**Session {r['session_id']}: {r['session_title']}**  \n*{r['question']}*")
                    if r.get('has_images'):
                        st.caption(f"📸 Contains {r.get('image_count', 1)} photo(s)")
                    st.markdown(f"{r['answer'][:150]}...")
                    if st.button(f"Go to Session", key=f"srch_go_{i}_{r['session_id']}"):
                        for idx, s in enumerate(SESSIONS):
                            if s["id"] == r['session_id']:
                                st.session_state.update(current_session=idx, current_question_override=r['question']); 
                                st.rerun()
                    st.divider()
                if len(results) > 10: 
                    st.info(f"... and {len(results)-10} more matches")
        else: 
            st.info("No matches found")

# ============================================================================
# MAIN CONTENT AREA
# ============================================================================
if st.session_state.current_session >= len(SESSIONS): 
    st.session_state.current_session = 0

current_session = SESSIONS[st.session_state.current_session]
current_session_id = current_session["id"]

if st.session_state.current_question_override:
    current_question_text = st.session_state.current_question_override
    question_source = "custom"
else:
    if st.session_state.current_question >= len(current_session["questions"]): 
        st.session_state.current_question = 0
    current_question_text = current_session["questions"][st.session_state.current_question]
    question_source = "regular"

st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(f"Session {current_session_id}: {current_session['title']}")
    sdata = st.session_state.responses.get(current_session_id, {})
    answered = len(sdata.get("questions", {}))
    total = len(current_session["questions"])
    if total > 0: 
        st.progress(min(answered/total, 1.0))
        st.caption(f"📝 Topics explored: {answered}/{total} ({answered/total*100:.0f}%)")
with col2:
    if question_source == "custom":
        st.markdown(f'<div style="margin-top:1rem;color:{"#9b59b6" if "Vignette:" in st.session_state.current_question_override else "#ff6b00"};">{"📝 Vignette" if "Vignette:" in st.session_state.current_question_override else "✨ Custom Topic"}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="margin-top:1rem;">Topic {st.session_state.current_question+1} of {len(current_session["questions"])}</div>', unsafe_allow_html=True)

st.markdown(f'<div class="question-box">{current_question_text}</div>', unsafe_allow_html=True)

if question_source == "regular":
    st.markdown(f'<div class="chapter-guidance">{current_session.get("guidance", "")}</div>', unsafe_allow_html=True)
else:
    if "Vignette:" in current_question_text:
        st.info("📝 **Vignette Mode** - Write a short, focused story about a specific moment or memory.")
    else:
        st.info("✨ **Custom Topic** - Write about whatever comes to mind!")

st.write("")
st.write("")

# Get existing answer
existing_answer = ""
if current_session_id in st.session_state.responses:
    if current_question_text in st.session_state.responses[current_session_id]["questions"]:
        existing_answer = st.session_state.responses[current_session_id]["questions"][current_question_text]["answer"]

# Initialize image handler
if st.session_state.logged_in:
    init_image_handler()
    existing_images = st.session_state.image_handler.get_images_for_answer(current_session_id, current_question_text) if st.session_state.image_handler else []

# ============================================================================
# QUILL EDITOR - YOUR ORIGINAL WORKING VERSION
# ============================================================================
editor_key = f"quill_{current_session_id}_{current_question_text[:20]}"
content_key = f"{editor_key}_content"

# Initialize session state for this editor's content
if content_key not in st.session_state:
    if existing_answer and existing_answer != "<p>Start writing your story here...</p>":
        st.session_state[content_key] = existing_answer
    else:
        st.session_state[content_key] = ""

st.markdown("### ✍️ Your Story")
st.markdown("""
<div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #36cfc9;">
    📸 <strong>Drag & drop images</strong> directly into the editor.
</div>
""", unsafe_allow_html=True)

# ONE Quill editor
content = st_quill(
    st.session_state[content_key],
    editor_key
)

# Update session state when editor changes
if content is not None:
    st.session_state[content_key] = content

user_input = st.session_state[content_key]

st.markdown("---")

# ============================================================================
# IMAGE UPLOAD SECTION - YOUR ORIGINAL WITH INSERT BUTTON
# ============================================================================
if st.session_state.logged_in and st.session_state.image_handler:
    
    if existing_images:
        st.markdown("### 📸 Your Uploaded Photos")
        st.markdown("*Click Insert to add the photo and caption to your story*")
        
        for idx, img in enumerate(existing_images):
            col1, col2, col3 = st.columns([2, 3, 1])
            
            with col1:
                # Use st.image instead of raw HTML for reliable display
                if img.get("thumb_html"):
                    # Extract base64 from the HTML
                    html_content = img.get("thumb_html", "")
                    import re
                    match = re.search(r'src="data:image/jpeg;base64,([^"]+)"', html_content)
                    if match:
                        b64 = match.group(1)
                        st.image(f"data:image/jpeg;base64,{b64}", use_container_width=True)
            
            with col2:
                caption_text = img.get("caption", "")
                if caption_text:
                    st.markdown(f"**📝 Caption:** {caption_text}")
                else:
                    st.markdown("*No caption*")
            
            with col3:
                if st.button(f"➕ Insert", key=f"insert_img_{img['id']}_{idx}"):
                    # Get full image HTML
                    full_html = img.get("full_html", "")
                    if full_html:
                        current_content = st.session_state.get(content_key, "")
                        if current_content and current_content != "<p><br></p>":
                            new_content = current_content + "<br><br>" + full_html
                        else:
                            new_content = full_html
                        st.session_state[content_key] = new_content
                        st.rerun()
        
        st.markdown("---")
    
    # Upload new images
    with st.expander("📤 Upload New Photos", expanded=len(existing_images) == 0):
        st.markdown("**Add new photos to your story:**")
        
        uploaded_file = st.file_uploader(
            "Choose an image...", 
            type=['jpg', 'jpeg', 'png'], 
            key=f"up_{current_session_id}_{hash(current_question_text)}",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            col1, col2 = st.columns([3, 1])
            with col1:
                caption = st.text_input(
                    "Caption / Description:",
                    placeholder="What does this photo show? When was it taken?",
                    key=f"cap_{current_session_id}_{hash(current_question_text)}"
                )
            with col2:
                if st.button("📤 Upload", key=f"btn_{current_session_id}_{hash(current_question_text)}", type="primary", use_container_width=True):
                    with st.spinner("Uploading..."):
                        result = st.session_state.image_handler.save_image(
                            uploaded_file, 
                            current_session_id, 
                            current_question_text, 
                            caption
                        )
                        if result:
                            st.success("✅ Photo uploaded!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Upload failed")
    
    st.markdown("---")

# ============================================================================
# SAVE BUTTONS
# ============================================================================
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("💾 Save Story", key="save_ans", type="primary", use_container_width=True):
        if user_input and user_input.strip() and user_input != "<p><br></p>" and user_input != "<p>Start writing your story here...</p>":
            with st.spinner("Saving your story..."):
                if save_response(current_session_id, current_question_text, user_input):
                    st.success("✅ Story saved!")
                    time.sleep(0.5)
                    st.rerun()
                else: 
                    st.error("Failed to save")
        else: 
            st.warning("Please write something!")
with col2:
    if existing_answer and existing_answer != "<p>Start writing your story here...</p>":
        if st.button("🗑️ Delete Story", key="del_ans", use_container_width=True):
            if delete_response(current_session_id, current_question_text):
                st.success("✅ Story deleted!")
                st.rerun()
    else: 
        st.button("🗑️ Delete", key="del_dis", disabled=True, use_container_width=True)
with col3:
    nav1, nav2 = st.columns(2)
    with nav1: 
        prev_dis = st.session_state.current_question == 0
        if st.button("← Previous Topic", disabled=prev_dis, key="prev_btn", use_container_width=True):
            if not prev_dis: 
                st.session_state.update(current_question=st.session_state.current_question-1, editing=False, current_question_override=None)
                st.rerun()
    with nav2:
        next_dis = st.session_state.current_question >= len(current_session["questions"]) - 1
        if st.button("Next Topic →", disabled=next_dis, key="next_btn", use_container_width=True):
            if not next_dis: 
                st.session_state.update(current_question=st.session_state.current_question+1, editing=False, current_question_override=None)
                st.rerun()

st.divider()

# ============================================================================
# PREVIEW SECTION
# ============================================================================
if user_input and user_input != "<p><br></p>" and user_input != "<p>Start writing your story here...</p>":
    with st.expander("👁️ Preview your story", expanded=False):
        st.markdown("### 📖 Preview")
        st.markdown(user_input, unsafe_allow_html=True)
        st.markdown("---")

# ============================================================================
# BETA READER SECTION
# ============================================================================
st.subheader("🦋 Beta Reader Feedback")
sdata = st.session_state.responses.get(current_session_id, {})
answered_cnt = len(sdata.get("questions", {}))
total_q = len(current_session["questions"])

if answered_cnt == total_q and total_q > 0:
    st.success("✅ Session complete - ready for beta reading!")
    prev_fb = get_previous_beta_feedback(st.session_state.user_id, current_session_id)
    if prev_fb: 
        st.info(f"📖 Previous feedback from {datetime.fromisoformat(prev_fb['generated_at']).strftime('%B %d')}")
    
    col1, col2 = st.columns([2, 1])
    with col1: 
        fb_type = st.selectbox("Feedback Type", ["comprehensive", "concise", "developmental"], key="beta_type")
    with col2:
        if st.button("🦋 Get Beta Reader Feedback", use_container_width=True, type="primary"):
            with st.spinner("Analyzing..."):
                if beta_reader:
                    # Get all answers for this session, strip HTML
                    session_text = ""
                    for q, a in sdata.get("questions", {}).items():
                        text_only = re.sub(r'<[^>]+>', '', a.get("answer", ""))
                        session_text += f"Question: {q}\nAnswer: {text_only}\n\n"
                    
                    if session_text.strip():
                        fb = generate_beta_reader_feedback(current_session["title"], session_text, fb_type)
                        if "error" not in fb: 
                            st.session_state.current_beta_feedback = fb
                            st.session_state.show_beta_reader = True
                            st.rerun()
                        else: 
                            st.error(f"Failed: {fb['error']}")
                    else: 
                        st.error("No content to analyze")
    if prev_fb and st.button("📖 View Previous Feedback", use_container_width=True):
        st.session_state.current_beta_feedback = prev_fb
        st.session_state.show_beta_reader = True
        st.rerun()
else: 
    st.info(f"Complete all {total_q} topics in this session to get beta reader feedback.")

st.divider()

# ============================================================================
# SESSION PROGRESS
# ============================================================================
progress_info = get_progress_info(current_session_id)
st.markdown(f"""
<div class="progress-container">
<div class="progress-header">📊 Session Progress</div>
<div class="progress-status">{progress_info['emoji']} {progress_info['progress_percent']:.0f}% complete • {progress_info['remaining_words']} words remaining</div>
<div class="progress-bar-container"><div class="progress-bar-fill" style="width: {min(progress_info['progress_percent'], 100)}%; background-color: {progress_info['color']};"></div></div>
<div style="text-align:center;font-size:0.9rem;color:#666;">{progress_info['current_count']} / {progress_info['target']} words</div>
</div>
""", unsafe_allow_html=True)

if st.button("✏️ Change Word Target", key="edit_target", use_container_width=True): 
    st.session_state.editing_word_target = not st.session_state.editing_word_target
    st.rerun()

if st.session_state.editing_word_target:
    new_target = st.number_input("Target words:", min_value=100, max_value=5000, value=progress_info['target'], key="target_edit")
    col_s, col_c = st.columns(2)
    with col_s:
        if st.button("💾 Save", key="save_target", type="primary", use_container_width=True):
            st.session_state.responses[current_session_id]["word_target"] = new_target
            save_user_data(st.session_state.user_id, st.session_state.responses)
            st.session_state.editing_word_target = False
            st.rerun()
    with col_c:
        if st.button("❌ Cancel", key="cancel_target", use_container_width=True): 
            st.session_state.editing_word_target = False
            st.rerun()

st.divider()

# Stats
col1, col2, col3, col4 = st.columns(4)
with col1: 
    st.metric("Total Words", sum(calculate_author_word_count(s["id"]) for s in SESSIONS))
with col2: 
    unique_q = set()
    for s in SESSIONS:
        for q, _ in st.session_state.responses.get(s["id"], {}).get("questions", {}).items():
            unique_q.add((s["id"], q))
    comp = sum(1 for s in SESSIONS if len([x for (sid,x) in unique_q if sid == s["id"]]) == len(s["questions"]))
    st.metric("Completed Sessions", f"{comp}/{len(SESSIONS)}")
with col3: 
    st.metric("Topics Explored", f"{len(unique_q)}/{sum(len(s['questions']) for s in SESSIONS)}")
with col4: 
    st.metric("Total Answers", sum(len(st.session_state.responses.get(s["id"], {}).get("questions", {})) for s in SESSIONS))

st.markdown("---")
if st.session_state.user_account:
    profile = st.session_state.user_account['profile']
    age = (datetime.now() - datetime.fromisoformat(st.session_state.user_account['created_at'])).days
    st.caption(f"Tell My Story Timeline • 👤 {profile['first_name']} {profile['last_name']} • 📅 Account Age: {age} days • 📚 Bank: {st.session_state.get('current_bank_name', 'None')}")
else: 
    st.caption(f"Tell My Story Timeline • User: {st.session_state.user_id}")
