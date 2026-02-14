# biographer.py – Tell My Story App (FIXED VERSION)
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
                 "uploads", "uploads/thumbnails", "uploads/metadata", "accounts", "sessions", "backups"]:
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

# Initialize session state - FIXED: use_container_width removed, using width parameter instead
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
    "image_handler": None, "show_image_manager": False, "show_ai_suggestions": False,
    "current_ai_suggestions": None, "current_suggestion_topic": None, "editor_content": {},
    "show_privacy_settings": False, "show_cover_designer": False
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
# BACKUP AND RESTORE FUNCTIONS
# ============================================================================
def create_backup():
    """Create a complete backup of user data"""
    if not st.session_state.user_id:
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_data = {
            "user_id": st.session_state.user_id,
            "user_account": st.session_state.user_account,
            "responses": st.session_state.responses,
            "backup_date": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        # Save to backups folder
        backup_file = f"backups/{st.session_state.user_id}_{timestamp}.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        # Also create downloadable version
        return json.dumps(backup_data, indent=2)
    except Exception as e:
        st.error(f"Backup failed: {e}")
        return None

def restore_from_backup(backup_json):
    """Restore user data from backup"""
    try:
        backup_data = json.loads(backup_json)
        if backup_data.get("user_id") != st.session_state.user_id:
            st.error("Backup belongs to a different user")
            return False
        
        st.session_state.user_account = backup_data.get("user_account", st.session_state.user_account)
        st.session_state.responses = backup_data.get("responses", st.session_state.responses)
        
        # Save to files
        save_account_data(st.session_state.user_account)
        save_user_data(st.session_state.user_id, st.session_state.responses)
        
        return True
    except Exception as e:
        st.error(f"Restore failed: {e}")
        return False

def list_backups():
    """List all backups for current user"""
    if not st.session_state.user_id:
        return []
    
    backups = []
    try:
        for f in os.listdir("backups"):
            if f.startswith(st.session_state.user_id) and f.endswith(".json"):
                filepath = f"backups/{f}"
                with open(filepath, 'r') as file:
                    data = json.load(file)
                    backups.append({
                        "filename": f,
                        "date": data.get("backup_date", "Unknown"),
                        "size": os.path.getsize(filepath)
                    })
    except:
        pass
    
    return sorted(backups, key=lambda x: x["date"], reverse=True)

# ============================================================================
# IMAGE HANDLER - COMPLETE WORKING VERSION WITH AUTO-RESIZE
# ============================================================================
class ImageHandler:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.base_path = "uploads"
        
        # Kindle-optimized settings
        self.settings = {
            "full_width": 1600,      # Max width for full-page images
            "inline_width": 800,      # Width for inline images
            "thumbnail_size": 200,     # Thumbnail size
            "dpi": 300,                # Target DPI (will be maintained during resize)
            "quality": 85,              # JPEG quality (85 is good balance)
            "max_file_size_mb": 5,      # Warn if original > 5MB
            "aspect_ratio": 1.6         # Kindle ideal ratio (height/width = 1.6)
        }
    
    def get_user_path(self):
        if self.user_id:
            user_hash = hashlib.md5(self.user_id.encode()).hexdigest()[:8]
            path = f"{self.base_path}/user_{user_hash}"
            os.makedirs(f"{path}/thumbnails", exist_ok=True)
            return path
        return self.base_path
    
    def optimize_image(self, image, max_width=1600, is_thumbnail=False):
        """Optimize image for Kindle with automatic resizing"""
        try:
            # Convert to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                bg = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                if image.mode == 'RGBA':
                    bg.paste(image, mask=image.split()[-1])
                else:
                    bg.paste(image)
                image = bg
            
            # Calculate new dimensions while maintaining aspect ratio
            width, height = image.size
            aspect = height / width
            
            # For thumbnails, use square crop
            if is_thumbnail:
                # Crop to square first
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                right = left + size
                bottom = top + size
                image = image.crop((left, top, right, bottom))
                # Resize to thumbnail size
                image.thumbnail((self.settings["thumbnail_size"], self.settings["thumbnail_size"]), Image.Resampling.LANCZOS)
                return image
            
            # For regular images, resize based on max_width
            if width > max_width:
                new_width = max_width
                new_height = int(max_width * aspect)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            print(f"Error optimizing image: {e}")
            return image
    
    def save_image(self, uploaded_file, session_id, question_text, caption="", usage="full_page"):
        """
        Save image with automatic optimization
        usage: "full_page" (1600px) or "inline" (800px)
        """
        try:
            # Read and open image
            image_data = uploaded_file.read()
            original_size = len(image_data) / (1024 * 1024)  # Size in MB
            
            # Warn if image is very large
            if original_size > self.settings["max_file_size_mb"]:
                print(f"Warning: Large image ({original_size:.1f}MB). Will be optimized.")
            
            img = Image.open(io.BytesIO(image_data))
            
            # Determine target width based on usage
            target_width = self.settings["full_width"] if usage == "full_page" else self.settings["inline_width"]
            
            # Generate unique ID
            image_id = hashlib.md5(f"{self.user_id}{session_id}{question_text}{datetime.now()}".encode()).hexdigest()[:16]
            
            # Create optimized version for main storage
            optimized_img = self.optimize_image(img, target_width, is_thumbnail=False)
            
            # Create thumbnail
            thumb_img = self.optimize_image(img, is_thumbnail=True)
            
            # Save optimized main image
            main_buffer = io.BytesIO()
            optimized_img.save(main_buffer, format="JPEG", quality=self.settings["quality"], optimize=True)
            main_size = len(main_buffer.getvalue()) / (1024 * 1024)
            
            # Save thumbnail
            thumb_buffer = io.BytesIO()
            thumb_img.save(thumb_buffer, format="JPEG", quality=70, optimize=True)
            
            # Write files
            user_path = self.get_user_path()
            with open(f"{user_path}/{image_id}.jpg", 'wb') as f: 
                f.write(main_buffer.getvalue())
            with open(f"{user_path}/thumbnails/{image_id}.jpg", 'wb') as f: 
                f.write(thumb_buffer.getvalue())
            
            # Save metadata with optimization info
            metadata = {
                "id": image_id, 
                "session_id": session_id, 
                "question": question_text,
                "caption": caption, 
                "alt_text": caption[:100] if caption else "",
                "timestamp": datetime.now().isoformat(),
                "user_id": self.user_id,
                "usage": usage,
                "original_size_mb": round(original_size, 2),
                "optimized_size_mb": round(main_size, 2),
                "dimensions": f"{optimized_img.width}x{optimized_img.height}",
                "optimized": True,
                "format": "JPEG",
                "dpi": self.settings["dpi"]
            }
            with open(f"{self.base_path}/metadata/{image_id}.json", 'w') as f: 
                json.dump(metadata, f, indent=2)
            
            # Show optimization stats if significant reduction
            reduction = ((original_size - main_size) / original_size) * 100 if original_size > 0 else 0
            if reduction > 20:  # If we saved more than 20%
                print(f"✅ Image optimized: {original_size:.1f}MB → {main_size:.1f}MB ({reduction:.0f}% reduction)")
            
            return {
                "has_images": True, 
                "images": [{
                    "id": image_id, 
                    "caption": caption,
                    "dimensions": f"{optimized_img.width}x{optimized_img.height}",
                    "size_mb": round(main_size, 2)
                }]
            }
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
            dimensions = ""
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                    caption = metadata.get("caption", "")
                    dimensions = metadata.get("dimensions", "")
            
            # Add dimension info as data attribute for debugging
            return {
                "html": f'<img src="data:image/jpeg;base64,{b64}" style="max-width:100%; border-radius:8px; margin:5px 0;" alt="{caption}" data-dimensions="{dimensions}">',
                "caption": caption, 
                "base64": b64,
                "dimensions": dimensions
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

def init_image_handler():
    if not st.session_state.image_handler or st.session_state.image_handler.user_id != st.session_state.get('user_id'):
        st.session_state.image_handler = ImageHandler(st.session_state.get('user_id'))
    return st.session_state.image_handler

# ============================================================================
# AUTHENTICATION FUNCTIONS
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
                "timeline_start": user_data.get("birthdate", ""),
                "occupation": user_data.get("occupation", ""),
                "hometown": user_data.get("hometown", ""),
                "current_location": user_data.get("current_location", ""),
                "family": user_data.get("family", ""),
                "education": user_data.get("education", ""),
                "life_philosophy": user_data.get("life_philosophy", ""),
                "legacy_hopes": user_data.get("legacy_hopes", "")
            },
            "narrative_gps": {},  # Add Narrative GPS storage
            "privacy_settings": {
                "profile_public": False,
                "stories_public": False,
                "allow_sharing": False,
                "data_collection": True,
                "encryption": True
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
        <p>Please keep this information safe. You can change your password anytime in settings.</p>
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
            'editing_bank_id', 'editing_bank_name', 'show_image_manager', 'editor_content']
    for key in keys:
        if key in st.session_state: 
            del st.session_state[key]
    st.query_params.clear()
    st.rerun()

# ============================================================================
# PRIVACY SETTINGS MODAL
# ============================================================================
def show_privacy_settings():
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    st.title("🔒 Privacy & Security Settings")
    
    if st.button("← Back", key="privacy_back"):
        st.session_state.show_privacy_settings = False
        st.rerun()
    
    st.markdown("### Ethical AI & Data Privacy")
    st.info("Your stories are private and secure. We use AI ethically to help you write better, never to train models on your personal data.")
    
    if 'privacy_settings' not in st.session_state.user_account:
        st.session_state.user_account['privacy_settings'] = {
            "profile_public": False,
            "stories_public": False,
            "allow_sharing": False,
            "data_collection": True,
            "encryption": True
        }
    
    privacy = st.session_state.user_account['privacy_settings']
    
    privacy['profile_public'] = st.checkbox("Make profile public", value=privacy.get('profile_public', False),
                                           help="Allow others to see your basic profile information")
    privacy['stories_public'] = st.checkbox("Share stories publicly", value=privacy.get('stories_public', False),
                                           help="Make your stories visible to the public (coming soon)")
    privacy['allow_sharing'] = st.checkbox("Allow sharing via link", value=privacy.get('allow_sharing', False),
                                          help="Generate shareable links to your stories")
    privacy['data_collection'] = st.checkbox("Allow anonymous usage data", value=privacy.get('data_collection', True),
                                            help="Help us improve by sharing anonymous usage statistics")
    privacy['encryption'] = st.checkbox("Enable encryption", value=privacy.get('encryption', True),
                                       disabled=True, help="Your data is always encrypted at rest")
    
    st.markdown("---")
    st.markdown("### 🔐 Security")
    st.markdown("- All data encrypted at rest")
    st.markdown("- No third-party data sharing")
    st.markdown("- You own all your content")
    st.markdown("- AI analysis is temporary and private")
    
    if st.button("💾 Save Privacy Settings", type="primary", width='stretch'):
        save_account_data(st.session_state.user_account)
        st.success("Privacy settings saved!")
        time.sleep(1)
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================================
# COVER DESIGNER MODAL
# ============================================================================
def show_cover_designer():
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    st.title("🎨 Cover Designer")
    
    if st.button("← Back", key="cover_back"):
        st.session_state.show_cover_designer = False
        st.rerun()
    
    st.markdown("### Design your book cover")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Cover Options**")
        cover_type = st.selectbox("Cover Style", ["Simple", "Elegant", "Modern", "Classic", "Vintage"])
        title_font = st.selectbox("Title Font", ["Georgia", "Arial", "Times New Roman", "Helvetica", "Calibri"])
        title_color = st.color_picker("Title Color", "#000000")
        background_color = st.color_picker("Background Color", "#FFFFFF")
        
        uploaded_cover = st.file_uploader("Upload Cover Image (optional)", type=['jpg', 'jpeg', 'png'])
        if uploaded_cover:
            st.image(uploaded_cover, caption="Your cover image", width=300)
    
    with col2:
        st.markdown("**Preview**")
        first_name = st.session_state.user_account.get('profile', {}).get('first_name', 'My')
        preview_title = st.text_input("Preview Title", value=f"{first_name}'s Story")
        
        # Simple preview box
        preview_style = f"""
        <div style="width:300px; height:400px; background-color:{background_color}; 
                    border:2px solid #ccc; border-radius:10px; padding:20px; 
                    display:flex; flex-direction:column; justify-content:center; 
                    align-items:center; text-align:center;">
            <h1 style="font-family:{title_font}; color:{title_color};">{preview_title}</h1>
            <p style="margin-top:50px;">by {st.session_state.user_account.get('profile', {}).get('first_name', '')}</p>
        </div>
        """
        st.markdown(preview_style, unsafe_allow_html=True)
    
    if st.button("💾 Save Cover Design", type="primary", width='stretch'):
        # Save cover design to user account
        if 'cover_design' not in st.session_state.user_account:
            st.session_state.user_account['cover_design'] = {}
        
        st.session_state.user_account['cover_design'].update({
            "cover_type": cover_type,
            "title_font": title_font,
            "title_color": title_color,
            "background_color": background_color,
            "title": preview_title
        })
        
        if uploaded_cover:
            # Save uploaded cover image
            cover_path = f"uploads/covers/{st.session_state.user_id}_cover.jpg"
            os.makedirs("uploads/covers", exist_ok=True)
            with open(cover_path, 'wb') as f:
                f.write(uploaded_cover.getbuffer())
            st.session_state.user_account['cover_design']['cover_image'] = cover_path
        
        save_account_data(st.session_state.user_account)
        st.success("Cover design saved!")
        time.sleep(1)
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================================
# NARRATIVE GPS HELPER FUNCTIONS (FOR AI INTEGRATION)
# ============================================================================
def get_narrative_gps_for_ai():
    """Format Narrative GPS data for AI prompts"""
    if not st.session_state.user_account or 'narrative_gps' not in st.session_state.user_account:
        return ""
    
    gps = st.session_state.user_account['narrative_gps']
    if not gps:
        return ""
    
    context = "\n\n=== BOOK PROJECT CONTEXT (From Narrative GPS) ===\n"
    
    # Section 1
    if gps.get('book_title') or gps.get('genre') or gps.get('book_length'):
        context += "\n📖 PROJECT SCOPE:\n"
        if gps.get('book_title'): context += f"- Book Title: {gps['book_title']}\n"
        if gps.get('genre'): 
            genre = gps['genre']
            if genre == "Other" and gps.get('genre_other'):
                genre = gps['genre_other']
            context += f"- Genre: {genre}\n"
        if gps.get('book_length'): context += f"- Length Vision: {gps['book_length']}\n"
        if gps.get('timeline'): context += f"- Timeline/Deadlines: {gps['timeline']}\n"
        if gps.get('completion_status'): context += f"- Current Status: {gps['completion_status']}\n"
    
    # Section 2
    if gps.get('purposes') or gps.get('reader_takeaway'):
        context += "\n🎯 PURPOSE & AUDIENCE:\n"
        if gps.get('purposes'): 
            context += f"- Core Purposes: {', '.join(gps['purposes'])}\n"
        if gps.get('purpose_other'): context += f"- Other Purpose: {gps['purpose_other']}\n"
        if gps.get('audience_family'): context += f"- Family Audience: {gps['audience_family']}\n"
        if gps.get('audience_industry'): context += f"- Industry Audience: {gps['audience_industry']}\n"
        if gps.get('audience_challenges'): context += f"- Audience Facing Similar Challenges: {gps['audience_challenges']}\n"
        if gps.get('audience_general'): context += f"- General Audience: {gps['audience_general']}\n"
        if gps.get('reader_takeaway'): context += f"- Reader Takeaway: {gps['reader_takeaway']}\n"
    
    # Section 3
    if gps.get('narrative_voices') or gps.get('emotional_tone'):
        context += "\n🎭 TONE & VOICE:\n"
        if gps.get('narrative_voices'): 
            context += f"- Narrative Voice: {', '.join(gps['narrative_voices'])}\n"
        if gps.get('voice_other'): context += f"- Other Voice: {gps['voice_other']}\n"
        if gps.get('emotional_tone'): context += f"- Emotional Tone: {gps['emotional_tone']}\n"
        if gps.get('language_style'): context += f"- Language Style: {gps['language_style']}\n"
    
    # Section 4
    if gps.get('time_coverage') or gps.get('sensitive_material') or gps.get('inclusions'):
        context += "\n📋 CONTENT PARAMETERS:\n"
        if gps.get('time_coverage'): context += f"- Time Coverage: {gps['time_coverage']}\n"
        if gps.get('sensitive_material'): context += f"- Sensitive Topics: {gps['sensitive_material']}\n"
        if gps.get('sensitive_people'): context += f"- Sensitive People: {gps['sensitive_people']}\n"
        if gps.get('inclusions'): 
            context += f"- Planned Inclusions: {', '.join(gps['inclusions'])}\n"
        if gps.get('locations'): context += f"- Key Locations: {gps['locations']}\n"
    
    # Section 5
    if gps.get('materials') or gps.get('people_to_interview'):
        context += "\n📦 RESOURCES:\n"
        if gps.get('materials'): 
            context += f"- Available Materials: {', '.join(gps['materials'])}\n"
        if gps.get('people_to_interview'): context += f"- People to Interview: {gps['people_to_interview']}\n"
        if gps.get('legal'): 
            context += f"- Legal Considerations: {', '.join(gps['legal'])}\n"
    
    # Section 6
    if gps.get('involvement') or gps.get('unspoken'):
        context += "\n🤝 COLLABORATION:\n"
        if gps.get('involvement'): 
            involvement = gps['involvement']
            if involvement == "Mixed approach: [explain]" and gps.get('involvement_explain'):
                involvement = f"Mixed approach: {gps['involvement_explain']}"
            context += f"- Working Style: {involvement}\n"
        if gps.get('feedback_style'): context += f"- Feedback Preference: {gps['feedback_style']}\n"
        if gps.get('unspoken'): context += f"- Hopes for Collaboration: {gps['unspoken']}\n"
    
    return context

# ============================================================================
# AI WRITING SUGGESTIONS FUNCTION
# ============================================================================
def generate_writing_suggestions(question, answer_text, session_title):
    """Generate immediate writing suggestions based on the answer and Narrative GPS context"""
    if not client:
        return {"error": "OpenAI client not available"}
    
    try:
        # Get Narrative GPS context
        gps_context = get_narrative_gps_for_ai()
        
        # Strip HTML from answer
        clean_answer = re.sub(r'<[^>]+>', '', answer_text)
        
        if len(clean_answer.split()) < 20:  # Don't suggest on very short answers
            return None
        
        system_prompt = """You are an expert writing coach and developmental editor. Your task is to provide focused, actionable suggestions for improving a piece of life story writing.

Based on the story context provided and the user's answer, offer 2-3 specific suggestions that will help strengthen this passage. Focus on:
1. Alignment with the book's stated purpose and audience
2. Consistency with the desired tone and voice
3. Opportunities to deepen emotional impact or add sensory details
4. Areas where the story could be expanded or clarified
5. Connections to broader themes in the book project

Keep suggestions positive, encouraging, and actionable. Format them as brief bullet points with a brief explanation for each."""

        user_prompt = f"""{gps_context}

SESSION: {session_title}
QUESTION: {question}
ANSWER: {clean_answer}

Based on the book project context above, provide 2-3 specific suggestions to improve this answer. Focus on making it more aligned with the book's purpose, audience, and desired tone."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        suggestions = response.choices[0].message.content
        return suggestions
    except Exception as e:
        return {"error": str(e)}

def show_ai_suggestions_modal():
    """Display AI writing suggestions in a modal"""
    if not st.session_state.get('current_ai_suggestions'):
        return
    
    # Use a container instead of modal overlay to prevent editor interference
    with st.container():
        st.markdown("### 💡 AI Writing Suggestions")
        
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("✕", key="close_suggestions"):
                st.session_state.show_ai_suggestions = False
                st.session_state.current_ai_suggestions = None
                st.rerun()
        
        st.markdown("---")
        
        suggestions = st.session_state.current_ai_suggestions
        if isinstance(suggestions, dict) and suggestions.get('error'):
            st.error(f"Could not generate suggestions: {suggestions['error']}")
        else:
            st.markdown("**Based on your book's context, here are some ideas to consider:**")
            st.markdown(suggestions)
            
            st.markdown("---")
            st.markdown("*These are suggestions only - trust your instincts and write the story only you can tell.*")
        
        if st.button("Close", key="close_suggestions_btn", width='stretch'):
            st.session_state.show_ai_suggestions = False
            st.session_state.current_ai_suggestions = None
            st.rerun()

# ============================================================================
# ENHANCED BIOGRAPHER PROFILE SECTION (EXPANDED QUESTIONS)
# ============================================================================
def render_enhanced_profile():
    """Render an expanded biographer-style questionnaire"""
    st.markdown("### 📋 The Biographer's Questions")
    st.info("A biographer would ask these questions to capture the full richness of your life story.")
    
    if 'enhanced_profile' not in st.session_state.user_account:
        st.session_state.user_account['enhanced_profile'] = {}
    
    ep = st.session_state.user_account['enhanced_profile']
    
    with st.expander("👶 Early Years & Family Origins", expanded=False):
        st.markdown("**Where and when were you born?**")
        ep['birth_place'] = st.text_input("Birth place", value=ep.get('birth_place', ''), key="ep_birth_place")
        
        st.markdown("**Tell me about your parents - who were they? What were their personalities, dreams, and life stories?**")
        ep['parents'] = st.text_area("Parents", value=ep.get('parents', ''), key="ep_parents", height=100)
        
        st.markdown("**Did you have siblings? What was your birth order and relationship with them?**")
        ep['siblings'] = st.text_area("Siblings", value=ep.get('siblings', ''), key="ep_siblings", height=100)
        
        st.markdown("**What was your childhood home like? The neighborhood, the house, the atmosphere?**")
        ep['childhood_home'] = st.text_area("Childhood home", value=ep.get('childhood_home', ''), key="ep_home", height=100)
        
        st.markdown("**What family traditions, values, or cultural background shaped your early years?**")
        ep['family_traditions'] = st.text_area("Family traditions", value=ep.get('family_traditions', ''), key="ep_traditions", height=100)
    
    with st.expander("🎓 Education & Formative Years", expanded=False):
        st.markdown("**What was your school experience like? Favorite teachers? Subjects you loved or hated?**")
        ep['school'] = st.text_area("School years", value=ep.get('school', ''), key="ep_school", height=100)
        
        st.markdown("**Did you pursue higher education? What influenced your choices?**")
        ep['higher_ed'] = st.text_area("Higher education", value=ep.get('higher_ed', ''), key="ep_higher_ed", height=100)
        
        st.markdown("**Who were your mentors or influential figures during these years?**")
        ep['mentors'] = st.text_area("Mentors", value=ep.get('mentors', ''), key="ep_mentors", height=100)
        
        st.markdown("**What books, ideas, or experiences shaped your worldview?**")
        ep['influences'] = st.text_area("Influences", value=ep.get('influences', ''), key="ep_influences", height=100)
    
    with st.expander("💼 Career & Life's Work", expanded=False):
        st.markdown("**What was your first job? What did you learn from it?**")
        ep['first_job'] = st.text_area("First job", value=ep.get('first_job', ''), key="ep_first_job", height=100)
        
        st.markdown("**Describe your career path - the twists, turns, and defining moments.**")
        ep['career_path'] = st.text_area("Career path", value=ep.get('career_path', ''), key="ep_career", height=100)
        
        st.markdown("**What achievements are you most proud of?**")
        ep['achievements'] = st.text_area("Achievements", value=ep.get('achievements', ''), key="ep_achievements", height=100)
        
        st.markdown("**What work or projects brought you the most fulfillment?**")
        ep['fulfillment'] = st.text_area("Fulfilling work", value=ep.get('fulfillment', ''), key="ep_fulfillment", height=100)
    
    with st.expander("❤️ Relationships & Love", expanded=False):
        st.markdown("**Tell me about your romantic relationships - first loves, significant partnerships.**")
        ep['romance'] = st.text_area("Romantic relationships", value=ep.get('romance', ''), key="ep_romance", height=100)
        
        st.markdown("**If married, how did you meet? What has the journey been like?**")
        ep['marriage'] = st.text_area("Marriage story", value=ep.get('marriage', ''), key="ep_marriage", height=100)
        
        st.markdown("**Tell me about your children, if any - their personalities, your relationship with them.**")
        ep['children'] = st.text_area("Children", value=ep.get('children', ''), key="ep_children", height=100)
        
        st.markdown("**Who are your closest friends? What makes those friendships special?**")
        ep['friends'] = st.text_area("Friendships", value=ep.get('friends', ''), key="ep_friends", height=100)
    
    with st.expander("🌟 Challenges & Triumphs", expanded=False):
        st.markdown("**What were the hardest moments in your life? How did you navigate them?**")
        ep['challenges'] = st.text_area("Challenges", value=ep.get('challenges', ''), key="ep_challenges", height=100)
        
        st.markdown("**What losses have you experienced and how did they change you?**")
        ep['losses'] = st.text_area("Losses", value=ep.get('losses', ''), key="ep_losses", height=100)
        
        st.markdown("**What are your proudest moments? Times when you felt truly alive?**")
        ep['proud_moments'] = st.text_area("Proud moments", value=ep.get('proud_moments', ''), key="ep_proud", height=100)
        
        st.markdown("**What obstacles did you overcome that defined who you are?**")
        ep['overcame'] = st.text_area("Obstacles overcome", value=ep.get('overcame', ''), key="ep_overcame", height=100)
    
    with st.expander("🌍 Life Philosophy & Wisdom", expanded=False):
        st.markdown("**What life lessons would you want to pass on to future generations?**")
        ep['life_lessons'] = st.text_area("Life lessons", value=ep.get('life_lessons', ''), key="ep_lessons", height=100)
        
        st.markdown("**What do you believe in? What are your core values?**")
        ep['values'] = st.text_area("Core values", value=ep.get('values', ''), key="ep_values", height=100)
        
        st.markdown("**If you could give your younger self advice, what would it be?**")
        ep['advice'] = st.text_area("Advice to younger self", value=ep.get('advice', ''), key="ep_advice", height=100)
        
        st.markdown("**How would you like to be remembered?**")
        ep['legacy'] = st.text_area("Legacy", value=ep.get('legacy', ''), key="ep_legacy", height=100)
    
    if st.button("💾 Save Biographer's Questions", type="primary", width='stretch'):
        save_account_data(st.session_state.user_account)
        st.success("Biographer's profile saved!")
        st.rerun()

# ============================================================================
# NARRATIVE GPS PROFILE SECTION (UPDATED - HEART OF YOUR STORY)
# ============================================================================
def render_narrative_gps():
    """Render the Narrative GPS questionnaire in the profile"""
    st.markdown("### ❤️ The Heart of Your Story")
    
    # New inspirational message
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #ff4b4b;">
    <p style="font-size: 1.1em; margin-bottom: 10px;">Before we write a single word, let's understand why this book matters.</p>
    
    <p>Your story deserves to be told with intention. These questions help us uncover:</p>
    
    <ul style="margin-left: 20px;">
        <li>Who needs to hear what you have to say</li>
        <li>What you want readers to feel when they close the book</li>
        <li>The legacy you're leaving behind</li>
    </ul>
    
    <p><strong>The more honest and detailed you are here, the more your true voice will shine through every page.</strong> Think of this as a conversation between you and your future reader—one where I'm just here to take notes and guide the way.</p>
    
    <p>Take your time. Come back and update whenever inspiration strikes. This is your story's foundation, and we want it solid.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if 'narrative_gps' not in st.session_state.user_account:
        st.session_state.user_account['narrative_gps'] = {}
    
    gps = st.session_state.user_account['narrative_gps']
    
    with st.expander("📖 Section 1: The Book Itself (Project Scope)", expanded=True):
        st.markdown("**BOOK TITLE (Working or Final):**")
        gps['book_title'] = st.text_input(
            "What's your working title? If unsure, what feeling or idea should the title convey?",
            value=gps.get('book_title', ''),
            label_visibility="collapsed",
            placeholder="What's your working title? If unsure, what feeling or idea should the title convey?",
            key="gps_title"
        )
        
        st.markdown("**BOOK GENRE/CATEGORY:**")
        genre_options = ["", "Memoir", "Autobiography", "Family History", "Business/Legacy Book", "Other"]
        genre_index = 0
        if gps.get('genre') in genre_options:
            genre_index = genre_options.index(gps['genre'])
        
        gps['genre'] = st.selectbox(
            "BOOK GENRE/CATEGORY:",
            options=genre_options,
            index=genre_index,
            label_visibility="collapsed",
            key="gps_genre"
        )
        if gps['genre'] == "Other":
            gps['genre_other'] = st.text_input("Please specify:", value=gps.get('genre_other', ''), key="gps_genre_other")
        
        st.markdown("**BOOK LENGTH VISION:**")
        length_options = ["", "A short book (100-150 pages)", "Standard length (200-300 pages)", "Comprehensive (300+ pages)"]
        length_index = 0
        if gps.get('book_length') in length_options:
            length_index = length_options.index(gps['book_length'])
        
        gps['book_length'] = st.selectbox(
            "BOOK LENGTH VISION:",
            options=length_options,
            index=length_index,
            label_visibility="collapsed",
            key="gps_length"
        )
        
        st.markdown("**TIMELINE & DEADLINES:**")
        gps['timeline'] = st.text_area(
            "Do you have a target publication date or event this book is tied to? (e.g., birthday, retirement, anniversary)",
            value=gps.get('timeline', ''),
            label_visibility="collapsed",
            placeholder="Do you have a target publication date or event this book is tied to? (e.g., birthday, retirement, anniversary)",
            key="gps_timeline"
        )
        
        st.markdown("**COMPLETION STATUS:**")
        completion_options = ["", "Notes only", "Partial chapters", "Full draft"]
        completion_index = 0
        if gps.get('completion_status') in completion_options:
            completion_index = completion_options.index(gps['completion_status'])
        
        gps['completion_status'] = st.selectbox(
            "COMPLETION STATUS:",
            options=completion_options,
            index=completion_index,
            label_visibility="collapsed",
            key="gps_completion"
        )
    
    with st.expander("🎯 Section 2: Purpose & Audience (The 'Why')", expanded=False):
        st.markdown("**THE CORE PURPOSE (Choose all that apply):**")
        
        if 'purposes' not in gps:
            gps['purposes'] = []
        
        purposes_options = [
            "Leave a legacy for family/future generations",
            "Share life lessons to help others",
            "Document professional/business journey",
            "Heal or process through writing",
            "Establish authority/expertise",
            "Entertain with entertaining stories"
        ]
        
        for purpose in purposes_options:
            if st.checkbox(
                purpose,
                value=purpose in gps.get('purposes', []),
                key=f"gps_purpose_{purpose}"
            ):
                if purpose not in gps['purposes']:
                    gps['purposes'].append(purpose)
            else:
                if purpose in gps['purposes']:
                    gps['purposes'].remove(purpose)
        
        gps['purpose_other'] = st.text_input("Other:", value=gps.get('purpose_other', ''), key="gps_purpose_other")
        
        st.markdown("---")
        st.markdown("**PRIMARY AUDIENCE:**")
        st.markdown("*Who is your ideal reader? Be specific:*")
        
        gps['audience_family'] = st.text_input(
            "Family members (which generations?):",
            value=gps.get('audience_family', ''),
            key="gps_audience_family"
        )
        
        gps['audience_industry'] = st.text_input(
            "People in your industry/profession:",
            value=gps.get('audience_industry', ''),
            key="gps_audience_industry"
        )
        
        gps['audience_challenges'] = st.text_input(
            "People facing similar challenges you overcame:",
            value=gps.get('audience_challenges', ''),
            key="gps_audience_challenges"
        )
        
        gps['audience_general'] = st.text_input(
            "The general public interested in:",
            value=gps.get('audience_general', ''),
            placeholder="your topic",
            key="gps_audience_general"
        )
        
        st.markdown("---")
        st.markdown("**THE READER TAKEAWAY:**")
        gps['reader_takeaway'] = st.text_area(
            "What do you want readers to feel, think, or do after finishing your book?",
            value=gps.get('reader_takeaway', ''),
            label_visibility="collapsed",
            placeholder="What do you want readers to feel, think, or do after finishing your book?",
            key="gps_takeaway"
        )
    
    with st.expander("🎭 Section 3: Tone & Voice (The 'How')", expanded=False):
        st.markdown("**NARRATIVE VOICE:**")
        
        if 'narrative_voices' not in gps:
            gps['narrative_voices'] = []
        
        voice_options = [
            "Warm and conversational (like talking to a friend)",
            "Professional and authoritative",
            "Raw and vulnerable",
            "Humorous/lighthearted",
            "Philosophical/reflective"
        ]
        
        for voice in voice_options:
            if st.checkbox(
                voice,
                value=voice in gps.get('narrative_voices', []),
                key=f"gps_voice_{voice}"
            ):
                if voice not in gps['narrative_voices']:
                    gps['narrative_voices'].append(voice)
            else:
                if voice in gps['narrative_voices']:
                    gps['narrative_voices'].remove(voice)
        
        gps['voice_other'] = st.text_input("Other:", value=gps.get('voice_other', ''), key="gps_voice_other")
        
        st.markdown("---")
        st.markdown("**EMOTIONAL TONE:**")
        gps['emotional_tone'] = st.text_area(
            "Should readers laugh? Cry? Feel inspired? Get angry? All of the above?",
            value=gps.get('emotional_tone', ''),
            label_visibility="collapsed",
            placeholder="Should readers laugh? Cry? Feel inspired? Get angry? All of the above?",
            key="gps_emotional"
        )
        
        st.markdown("---")
        st.markdown("**LANGUAGE STYLE:**")
        language_options = ["", "Simple, everyday language", "Rich, descriptive prose", "Short, punchy chapters", "Long, flowing narratives"]
        language_index = 0
        if gps.get('language_style') in language_options:
            language_index = language_options.index(gps['language_style'])
        
        gps['language_style'] = st.selectbox(
            "LANGUAGE STYLE:",
            options=language_options,
            index=language_index,
            label_visibility="collapsed",
            key="gps_language"
        )
    
    with st.expander("📋 Section 4: Content Parameters (The 'What')", expanded=False):
        st.markdown("**TIME COVERAGE:**")
        time_options = ["", "Your entire life", "A specific era/decade", "One defining experience", "Your career/business journey"]
        time_index = 0
        if gps.get('time_coverage') in time_options:
            time_index = time_options.index(gps['time_coverage'])
        
        gps['time_coverage'] = st.selectbox(
            "TIME COVERAGE:",
            options=time_options,
            index=time_index,
            label_visibility="collapsed",
            key="gps_time"
        )
        
        st.markdown("---")
        st.markdown("**SENSITIVE MATERIAL:**")
        gps['sensitive_material'] = st.text_area(
            "Are there topics, people, or events you want to handle carefully or omit entirely?",
            value=gps.get('sensitive_material', ''),
            label_visibility="collapsed",
            placeholder="Are there topics, people, or events you want to handle carefully or omit entirely?",
            key="gps_sensitive"
        )
        
        gps['sensitive_people'] = st.text_area(
            "Any living people whose portrayal requires sensitivity or legal consideration?",
            value=gps.get('sensitive_people', ''),
            label_visibility="collapsed",
            placeholder="Any living people whose portrayal requires sensitivity or legal consideration?",
            key="gps_sensitive_people"
        )
        
        st.markdown("---")
        st.markdown("**INCLUSIONS:**")
        
        if 'inclusions' not in gps:
            gps['inclusions'] = []
        
        inclusion_options = ["Photos", "Family trees", "Recipes", "Letters/documents", "Timelines", "Resources for readers"]
        for inc in inclusion_options:
            if st.checkbox(
                inc,
                value=inc in gps.get('inclusions', []),
                key=f"gps_inc_{inc}"
            ):
                if inc not in gps['inclusions']:
                    gps['inclusions'].append(inc)
            else:
                if inc in gps['inclusions']:
                    gps['inclusions'].remove(inc)
        
        st.markdown("---")
        st.markdown("**LOCATIONS:**")
        gps['locations'] = st.text_area(
            "List key places that must appear in the story (hometowns, meaningful travels, etc.)",
            value=gps.get('locations', ''),
            label_visibility="collapsed",
            placeholder="List key places that must appear in the story (hometowns, meaningful travels, etc.)",
            key="gps_locations"
        )
    
    with st.expander("📦 Section 5: Assets & Access (The 'Resources')", expanded=False):
        st.markdown("**EXISTING MATERIALS:**")
        
        if 'materials' not in gps:
            gps['materials'] = []
        
        material_options = [
            "Journals/diaries", "Letters or emails", "Photos (with dates/context)",
            "Video/audio recordings", "Newspaper clippings", "Awards/certificates",
            "Social media posts", "Previous interviews"
        ]
        
        for mat in material_options:
            if st.checkbox(
                mat,
                value=mat in gps.get('materials', []),
                key=f"gps_mat_{mat}"
            ):
                if mat not in gps['materials']:
                    gps['materials'].append(mat)
            else:
                if mat in gps['materials']:
                    gps['materials'].remove(mat)
        
        st.markdown("---")
        st.markdown("**PEOPLE TO INTERVIEW:**")
        gps['people_to_interview'] = st.text_area(
            "Are there family members, friends, or colleagues who should contribute their memories?",
            value=gps.get('people_to_interview', ''),
            label_visibility="collapsed",
            placeholder="Are there family members, friends, or colleagues who should contribute their memories?",
            key="gps_people"
        )
        
        st.markdown("---")
        st.markdown("**FINANCIAL & LEGAL:**")
        
        if 'legal' not in gps:
            gps['legal'] = []
        
        legal_options = ["ISBN registration", "Copyright", "Libel review", "Permissions for quoted material"]
        for leg in legal_options:
            if st.checkbox(
                leg,
                value=leg in gps.get('legal', []),
                key=f"gps_legal_{leg}"
            ):
                if leg not in gps['legal']:
                    gps['legal'].append(leg)
            else:
                if leg in gps['legal']:
                    gps['legal'].remove(leg)
    
    with st.expander("🤝 Section 6: Ghostwriter Relationship (The 'Collaboration')", expanded=False):
        st.markdown("**YOUR INVOLVEMENT:**")
        
        involvement_options = [
            "I'll answer questions, you write everything",
            "I'll write drafts, you polish",
            "We'll interview together, then you write",
            "Mixed approach: [explain]"
        ]
        
        involvement_index = 0
        if gps.get('involvement') in involvement_options:
            involvement_index = involvement_options.index(gps['involvement'])
        
        gps['involvement'] = st.radio(
            "How do you want to work together?",
            options=involvement_options,
            index=involvement_index,
            key="gps_involvement"
        )
        
        if gps.get('involvement') == "Mixed approach: [explain]":
            gps['involvement_explain'] = st.text_area(
                "Explain your preferred approach:",
                value=gps.get('involvement_explain', ''),
                key="gps_involvement_explain"
            )
        
        st.markdown("---")
        
        st.markdown("**FEEDBACK STYLE:**")
        feedback_options = ["", "Written comments", "Phone/video discussions", "Line-by-line edits"]
        feedback_index = 0
        if gps.get('feedback_style') in feedback_options:
            feedback_index = feedback_options.index(gps['feedback_style'])
        
        gps['feedback_style'] = st.selectbox(
            "FEEDBACK STYLE:",
            options=feedback_options,
            index=feedback_index,
            label_visibility="collapsed",
            key="gps_feedback"
        )
        
        st.markdown("---")
        st.markdown("**THE UNSPOKEN:**")
        gps['unspoken'] = st.text_area(
            "What are you hoping I'll bring to this project that you can't do yourself?",
            value=gps.get('unspoken', ''),
            label_visibility="collapsed",
            placeholder="What are you hoping I'll bring to this project that you can't do yourself?",
            key="gps_unspoken"
        )
    
    # Save button for Narrative GPS
    if st.button("💾 Save The Heart of Your Story", key="save_narrative_gps", type="primary", width='stretch'):
        save_account_data(st.session_state.user_account)
        st.success("✅ The Heart of Your Story saved!")
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
        
        # Generate AI writing suggestions after saving (but don't show modal immediately)
        session_title = st.session_state.responses[session_id].get("title", f"Session {session_id}")
        suggestions = generate_writing_suggestions(question, answer, session_title)
        if suggestions and not isinstance(suggestions, dict) or (isinstance(suggestions, dict) and not suggestions.get('error')):
            st.session_state.current_ai_suggestions = suggestions
            st.session_state.show_ai_suggestions = True
            st.session_state.current_suggestion_topic = question
    
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

def display_saved_feedback(user_id, session_id):
    """Display all saved beta feedback for a session"""
    user_data = load_user_data(user_id)
    feedback_data = user_data.get("beta_feedback", {})
    session_feedback = feedback_data.get(str(session_id), [])
    
    if not session_feedback:
        st.info("No saved feedback for this session yet.")
        return
    
    st.markdown("### 📚 Saved Beta Reader Feedback")
    
    # Sort by date, newest first
    session_feedback.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
    
    for i, fb in enumerate(session_feedback):
        with st.expander(f"Feedback from {datetime.fromisoformat(fb['generated_at']).strftime('%B %d, %Y at %I:%M %p')}"):
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                st.markdown(f"**Type:** {fb.get('feedback_type', 'comprehensive').title()}")
            with col2:
                st.markdown(f"**Overall Score:** {fb.get('overall_score', 'N/A')}/10")
            with col3:
                if st.button(f"🗑️ Delete", key=f"del_fb_{i}_{fb.get('generated_at')}"):
                    # Delete this feedback
                    session_feedback.pop(i)
                    user_data["beta_feedback"][str(session_id)] = session_feedback
                    save_user_data(user_id, user_data.get("responses", {}))
                    st.rerun()
            
            # Display the feedback content
            if 'summary' in fb:
                st.markdown("**Summary:**")
                st.markdown(fb['summary'])
            
            if 'strengths' in fb:
                st.markdown("**Strengths:**")
                for s in fb['strengths']:
                    st.markdown(f"✅ {s}")
            
            if 'areas_for_improvement' in fb:
                st.markdown("**Areas for Improvement:**")
                for a in fb['areas_for_improvement']:
                    st.markdown(f"📝 {a}")
            
            if 'suggestions' in fb:
                st.markdown("**Suggestions:**")
                for sug in fb['suggestions']:
                    st.markdown(f"💡 {sug}")

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
    if st.button("➕ Create New Vignette", type="primary", width='stretch'):
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
    if st.button("➕ Create New Session", type="primary", width='stretch'):
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
# PDF GENERATION FUNCTIONS
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
    if st.button("📋 Open Bank Manager", type="primary", width='stretch'): 
        st.session_state.show_bank_manager = True; 
        st.rerun()
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
        st.button("🔐 Login", width='stretch', type="primary" if st.session_state.auth_tab=='login' else "secondary", 
                        on_click=lambda: st.session_state.update(auth_tab='login'))
    with col2: 
        st.button("📝 Sign Up", width='stretch', type="primary" if st.session_state.auth_tab=='signup' else "secondary",
                        on_click=lambda: st.session_state.update(auth_tab='signup'))
    st.divider()
    
    if st.session_state.auth_tab == 'login':
        with st.form("login_form"):
            st.subheader("Welcome Back")
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary", width='stretch'):
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
            
            if st.form_submit_button("Create Account", type="primary", width='stretch'):
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
# PROFILE SETUP MODAL (COMPREHENSIVE BIOGRAPHER PROFILE)
# ============================================================================
if st.session_state.get('show_profile_setup', False):
    st.markdown('<div class="profile-setup-modal">', unsafe_allow_html=True)
    st.title("👤 Your Complete Life Story Profile")
    
    # Basic Profile Section
    st.markdown("### 📝 Basic Information")
    with st.form("profile_setup_form"):
        col1, col2 = st.columns(2)
        with col1:
            gender = st.radio("Gender", ["Male", "Female", "Other", "Prefer not to say"], horizontal=True, key="modal_gender")
        with col2:
            account_for = st.radio("Account Type", ["For me", "For someone else"], key="modal_account_type", horizontal=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: 
            birth_month = st.selectbox("Birth Month", ["January","February","March","April","May","June","July","August","September","October","November","December"], key="modal_month")
        with col2: 
            birth_day = st.selectbox("Birth Day", list(range(1,32)), key="modal_day")
        with col3: 
            birth_year = st.selectbox("Birth Year", list(range(datetime.now().year, datetime.now().year-120, -1)), key="modal_year")
        
        # Save Basic Profile button - now blue
        if st.form_submit_button("💾 Save Basic Information", type="primary", width='stretch'):
            if birth_month and birth_day and birth_year:
                birthdate = f"{birth_month} {birth_day}, {birth_year}"
                if st.session_state.user_account:
                    st.session_state.user_account['profile'].update({
                        'gender': gender, 
                        'birthdate': birthdate, 
                        'timeline_start': birthdate
                    })
                    st.session_state.user_account['account_type'] = "self" if account_for == "For me" else "other"
                    save_account_data(st.session_state.user_account)
                st.success("Basic information saved!")
                st.rerun()
    
    st.divider()
    
    # Enhanced Biographer Profile
    render_enhanced_profile()
    
    st.divider()
    
    # Narrative GPS Section
    render_narrative_gps()
    
    st.divider()
    
    # Privacy Settings (collapsible)
    with st.expander("🔒 Privacy & Security Settings", expanded=False):
        if 'privacy_settings' not in st.session_state.user_account:
            st.session_state.user_account['privacy_settings'] = {
                "profile_public": False,
                "stories_public": False,
                "allow_sharing": False,
                "data_collection": True,
                "encryption": True
            }
        
        privacy = st.session_state.user_account['privacy_settings']
        
        privacy['profile_public'] = st.checkbox("Make profile public", value=privacy.get('profile_public', False),
                                               help="Allow others to see your basic profile information")
        privacy['stories_public'] = st.checkbox("Share stories publicly", value=privacy.get('stories_public', False),
                                               help="Make your stories visible to the public (coming soon)")
        privacy['allow_sharing'] = st.checkbox("Allow sharing via link", value=privacy.get('allow_sharing', False),
                                              help="Generate shareable links to your stories")
        privacy['data_collection'] = st.checkbox("Allow anonymous usage data", value=privacy.get('data_collection', True),
                                                help="Help us improve by sharing anonymous usage statistics")
        
        st.markdown("**🔐 Security Status:** Your data is encrypted at rest and never shared with third parties.")
        
        if st.button("💾 Save Privacy Settings", type="primary", width='stretch'):
            save_account_data(st.session_state.user_account)
            st.success("Privacy settings saved!")
            st.rerun()
    
    st.divider()
    
    # Backup and Restore Section
    with st.expander("💾 Backup & Restore", expanded=False):
        st.markdown("**Create a complete backup of all your data:**")
        backup_json = create_backup()
        if backup_json:
            st.download_button(
                label="📥 Download Complete Backup",
                data=backup_json,
                file_name=f"tell_my_story_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                width='stretch'
            )
        
        st.markdown("---")
        st.markdown("**Restore from backup:**")
        backup_file = st.file_uploader("Upload backup file", type=['json'])
        if backup_file and st.button("🔄 Restore from Backup", type="primary", width='stretch'):
            backup_content = backup_file.read().decode('utf-8')
            if restore_from_backup(backup_content):
                st.success("Backup restored successfully!")
                st.rerun()
            else:
                st.error("Failed to restore backup")
        
        st.markdown("---")
        st.markdown("**Previous backups:**")
        backups = list_backups()
        if backups:
            for b in backups:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"📅 {b['date']} ({(b['size']/1024):.1f} KB)")
                with col2:
                    if st.button(f"Restore", key=f"restore_{b['filename']}"):
                        with open(f"backups/{b['filename']}", 'r') as f:
                            backup_content = f.read()
                        if restore_from_backup(backup_content):
                            st.success("Restored!")
                            st.rerun()
        else:
            st.info("No previous backups found")
    
    # Close button at the bottom
    if st.button("← Close Profile", key="close_profile", width='stretch'):
        st.session_state.show_profile_setup = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================================
# MODAL HANDLING (including AI suggestions)
# ============================================================================
if st.session_state.show_ai_suggestions and st.session_state.current_ai_suggestions:
    show_ai_suggestions_modal()

if st.session_state.show_privacy_settings:
    show_privacy_settings()

if st.session_state.show_cover_designer:
    show_cover_designer()

if st.session_state.show_bank_manager: 
    show_bank_manager()
if st.session_state.show_bank_editor: 
    show_bank_editor()
if st.session_state.show_beta_reader and st.session_state.current_beta_feedback: 
    if beta_reader:
        beta_reader.show_modal(st.session_state.current_beta_feedback, 
                              {"id": SESSIONS[st.session_state.current_session]["id"], 
                               "title": SESSIONS[st.session_state.current_session]["title"]},
                              st.session_state.user_id, 
                              save_beta_feedback, 
                              lambda: st.session_state.update(show_beta_reader=False, current_beta_feedback=None))
if st.session_state.show_vignette_detail: 
    show_vignette_detail()
if st.session_state.show_vignette_manager: 
    show_vignette_manager()
if st.session_state.show_vignette_modal: 
    show_vignette_modal()
if st.session_state.show_topic_browser: 
    show_topic_browser()
if st.session_state.show_session_manager: 
    show_session_manager()
if st.session_state.show_session_creator: 
    show_session_creator()

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
    if st.button("📝 Complete Profile", width='stretch'): 
        st.session_state.show_profile_setup = True; 
        st.rerun()
    if st.button("🚪 Log Out", width='stretch'): 
        logout_user()
    
    st.divider()
    st.header("🔧 Tools")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔒 Privacy", width='stretch'):
            st.session_state.show_privacy_settings = True
            st.rerun()
    with col2:
        if st.button("🎨 Cover", width='stretch'):
            st.session_state.show_cover_designer = True
            st.rerun()
    
    st.divider()
    st.header("📚 Question Banks")
    if st.button("📋 Bank Manager", width='stretch', type="primary"): 
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
            if st.button(f"{status} Session {sid}: {s['title']}", key=f"sel_sesh_{i}", width='stretch'):
                st.session_state.update(current_session=i, current_question=0, editing=False, current_question_override=None); 
                st.rerun()
    
    st.divider()
    st.header("✨ Vignettes")
    if st.button("📝 New Vignette", width='stretch'): 
        st.session_state.show_vignette_modal = True; 
        st.session_state.editing_vignette_id = None; 
        st.rerun()
    if st.button("📖 View All Vignettes", width='stretch'): 
        st.session_state.show_vignette_manager = True; 
        st.rerun()
    
    st.divider()
    st.header("📖 Session Management")
    if st.button("📋 All Sessions", width='stretch'): 
        st.session_state.show_session_manager = True; 
        st.rerun()
    if st.button("➕ Custom Session", width='stretch'): 
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
                "narrative_gps": st.session_state.user_account.get('narrative_gps', {}),
                "enhanced_profile": st.session_state.user_account.get('enhanced_profile', {}),
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
                              width='stretch')
            
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
                if st.button("📊 DOCX", type="primary", width='stretch'):
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
                            label="📥 Download DOCX", 
                            data=docx_bytes, 
                            file_name=filename, 
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                            width='stretch',
                            key="docx_download"
                        )

            with col2:
                if st.button("🌐 HTML", type="primary", width='stretch'):
                    with st.spinner("Creating HTML page..."):
                        html_content = generate_html(book_title, author_name, export_data)
                        filename = f"{book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html"
                        st.download_button(
                            label="📥 Download HTML", 
                            data=html_content, 
                            file_name=filename, 
                            mime="text/html", 
                            width='stretch',
                            key="html_download"
                        )

            with col3:
                if st.button("📦 ZIP", type="primary", width='stretch'):
                    with st.spinner("Creating ZIP package..."):
                        zip_data = generate_zip(book_title, author_name, export_data)
                        filename = f"{book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.zip"
                        st.download_button(
                            label="📥 Download ZIP", 
                            data=zip_data, 
                            file_name=filename, 
                            mime="application/zip", 
                            width='stretch',
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
        if st.button("✅ Confirm", type="primary", key="conf_sesh", width='stretch'): 
            sid = SESSIONS[st.session_state.current_session]["id"]
            st.session_state.responses[sid]["questions"] = {}
            save_user_data(st.session_state.user_id, st.session_state.responses)
            st.session_state.confirming_clear = None; 
            st.rerun()
        if st.button("❌ Cancel", key="can_sesh", width='stretch'): 
            st.session_state.confirming_clear = None; 
            st.rerun()
    elif st.session_state.confirming_clear == "all":
        st.warning("**Delete ALL answers for ALL sessions?**")
        if st.button("✅ Confirm All", type="primary", key="conf_all", width='stretch'): 
            for s in SESSIONS:
                st.session_state.responses[s["id"]]["questions"] = {}
            save_user_data(st.session_state.user_id, st.session_state.responses)
            st.session_state.confirming_clear = None; 
            st.rerun()
        if st.button("❌ Cancel", key="can_all", width='stretch'): 
            st.session_state.confirming_clear = None; 
            st.rerun()
    else:
        if st.button("🗑️ Clear Session", width='stretch'): 
            st.session_state.confirming_clear = "session"; 
            st.rerun()
        if st.button("🔥 Clear All", width='stretch'): 
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
                    if st.button(f"Go to Session", key=f"srch_go_{i}_{r['session_id']}", width='stretch'):
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
        st.progress(answered/total)
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
# QUILL EDITOR
# ============================================================================
editor_key = f"quill_{current_session_id}_{current_question_text[:20]}"
content_key = f"{editor_key}_content"

# Initialize session state for this editor's content
if content_key not in st.session_state:
    if existing_answer and existing_answer != "<p>Start writing your story here...</p>":
        st.session_state[content_key] = existing_answer
    else:
        st.session_state[content_key] = "<p>Start writing your story here...</p>"

st.markdown("### ✍️ Your Story")
st.markdown("""
<div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #36cfc9;">
    📸 <strong>Drag & drop images</strong> directly into the editor, or use the uploader below.
</div>
""", unsafe_allow_html=True)

# ONE Quill editor - FIXED: No modal interference
content = st_quill(
    st.session_state[content_key],
    key=editor_key,
    placeholder="Write your story here...",
    html=True
)

# Update session state when editor changes
if content is not None:
    st.session_state[content_key] = content

user_input = st.session_state[content_key]

st.markdown("---")

# ============================================================================
# IMAGE UPLOAD SECTION
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
                    match = re.search(r'src="data:image/jpeg;base64,([^"]+)"', html_content)
                    if match:
                        b64 = match.group(1)
                        st.image(f"data:image/jpeg;base64,{b64}", width=150)
            
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
                        if current_content and current_content != "<p><br></p>" and current_content != "<p>Start writing your story here...</p>":
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
                usage = st.radio(
                    "Image size:",
                    ["Full Page", "Inline"],
                    horizontal=True,
                    key=f"usage_{current_session_id}_{hash(current_question_text)}",
                    help="Full Page: 1600px wide, Inline: 800px wide"
                )
            with col2:
                if st.button("📤 Upload", key=f"btn_{current_session_id}_{hash(current_question_text)}", type="primary", width='stretch'):
                    with st.spinner("Uploading and optimizing..."):
                        usage_type = "full_page" if usage == "Full Page" else "inline"
                        result = st.session_state.image_handler.save_image(
                            uploaded_file, 
                            current_session_id, 
                            current_question_text, 
                            caption,
                            usage_type
                        )
                        if result:
                            st.success("✅ Photo uploaded and optimized!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Upload failed")
    
    st.markdown("---")

# ============================================================================
# SAVE BUTTONS (FIXED NAVIGATION)
# ============================================================================
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("💾 Save Story", key="save_ans", type="primary", width='stretch'):
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
        if st.button("🗑️ Delete Story", key="del_ans", width='stretch'):
            if delete_response(current_session_id, current_question_text):
                st.success("✅ Story deleted!")
                st.rerun()
    else: 
        st.button("🗑️ Delete", key="del_dis", disabled=True, width='stretch')
with col3:
    nav1, nav2 = st.columns(2)
    with nav1: 
        prev_disabled = st.session_state.current_question == 0
        if st.button("← Previous Topic", disabled=prev_disabled, key="prev_btn", width='stretch'):
            if not prev_disabled:
                st.session_state.current_question -= 1
                st.session_state.current_question_override = None
                st.rerun()
    with nav2:
        next_disabled = st.session_state.current_question >= len(current_session["questions"]) - 1
        if st.button("Next Topic →", disabled=next_disabled, key="next_btn", width='stretch'):
            if not next_disabled:
                st.session_state.current_question += 1
                st.session_state.current_question_override = None
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
# BETA READER FEEDBACK SECTION
# ============================================================================
st.subheader("🦋 Beta Reader Feedback")

# Create tabs for Current Session and Feedback History
tab1, tab2 = st.tabs(["📝 Current Session", "📚 Feedback History"])

with tab1:
    sdata = st.session_state.responses.get(current_session_id, {})
    answered_cnt = len(sdata.get("questions", {}))
    total_q = len(current_session["questions"])

    if answered_cnt == total_q and total_q > 0:
        st.success("✅ Session complete - ready for beta reading!")
        
        col1, col2 = st.columns([2, 1])
        with col1: 
            fb_type = st.selectbox("Feedback Type", ["comprehensive", "concise", "developmental"], key="beta_type")
        with col2:
            if st.button("🦋 Get Beta Reader Feedback", width='stretch', type="primary"):
                with st.spinner("Analyzing your stories..."):
                    if beta_reader:
                        # Get all answers for this session, strip HTML
                        session_text = ""
                        for q, a in sdata.get("questions", {}).items():
                            text_only = re.sub(r'<[^>]+>', '', a.get("answer", ""))
                            session_text += f"Question: {q}\nAnswer: {text_only}\n\n"
                        
                        # Add Narrative GPS context for AI suggestions
                        gps_context = get_narrative_gps_for_ai()
                        
                        if session_text.strip():
                            # Combine session text with GPS context
                            full_text = gps_context + "\n\n" + session_text if gps_context else session_text
                            fb = generate_beta_reader_feedback(current_session["title"], full_text, fb_type)
                            if "error" not in fb: 
                                st.session_state.current_beta_feedback = fb
                                st.session_state.show_beta_reader = True
                                st.rerun()
                            else: 
                                st.error(f"Failed: {fb['error']}")
                        else: 
                            st.error("No content to analyze")
    else: 
        st.info(f"Complete all {total_q} topics in this session to get beta reader feedback.")

with tab2:
    st.markdown("### 📚 Your Saved Feedback (Forever)")
    
    # Load all feedback
    user_data = load_user_data(st.session_state.user_id) if st.session_state.user_id else {}
    all_feedback = user_data.get("beta_feedback", {})
    
    if not all_feedback:
        st.info("No saved feedback yet. Generate feedback from any completed session and it will appear here forever.")
    else:
        # Create a reverse chronological list of all feedback
        all_entries = []
        for session_id_str, feedback_list in all_feedback.items():
            # Find session title
            session_title = "Unknown Session"
            for s in SESSIONS:
                if str(s["id"]) == session_id_str:
                    session_title = s["title"]
                    break
            
            for fb in feedback_list:
                all_entries.append({
                    "session_id": session_id_str,
                    "session_title": session_title,
                    "date": fb.get('generated_at', datetime.now().isoformat()),
                    "feedback": fb
                })
        
        # Sort by date, newest first
        all_entries.sort(key=lambda x: x['date'], reverse=True)
        
        # Display each feedback entry
        for i, entry in enumerate(all_entries):
            fb = entry['feedback']
            fb_date = datetime.fromisoformat(entry['date']).strftime('%B %d, %Y at %I:%M %p')
            
            with st.expander(f"📖 {entry['session_title']} - {fb_date} ({fb.get('feedback_type', 'comprehensive').title()})"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**Session:** {entry['session_title']}")
                with col2:
                    st.markdown(f"**Type:** {fb.get('feedback_type', 'comprehensive').title()}")
                with col3:
                    if st.button(f"🗑️ Delete", key=f"del_fb_{i}_{entry['date']}", width='stretch'):
                        # Delete this specific feedback
                        session_id_str = entry['session_id']
                        feedback_list = all_feedback.get(session_id_str, [])
                        
                        # Remove the matching feedback
                        feedback_list = [f for f in feedback_list if f.get('generated_at') != entry['date']]
                        
                        if feedback_list:
                            all_feedback[session_id_str] = feedback_list
                        else:
                            del all_feedback[session_id_str]
                        
                        # Save updated data
                        user_data["beta_feedback"] = all_feedback
                        save_user_data(st.session_state.user_id, user_data.get("responses", {}))
                        st.success("Feedback deleted!")
                        st.rerun()
                
                # Overall score if available
                if fb.get('overall_score'):
                    st.markdown(f"**Overall Score:** {fb['overall_score']}/10")
                
                # Display the feedback content
                if 'summary' in fb and fb['summary']:
                    st.markdown("**Summary:**")
                    st.markdown(fb['summary'])
                
                if 'strengths' in fb and fb['strengths']:
                    st.markdown("**Strengths:**")
                    for s in fb['strengths']:
                        st.markdown(f"✅ {s}")
                
                if 'areas_for_improvement' in fb and fb['areas_for_improvement']:
                    st.markdown("**Areas for Improvement:**")
                    for a in fb['areas_for_improvement']:
                        st.markdown(f"📝 {a}")
                
                if 'suggestions' in fb and fb['suggestions']:
                    st.markdown("**Suggestions:**")
                    for sug in fb['suggestions']:
                        st.markdown(f"💡 {sug}")
                
                # Raw feedback if nothing else
                if not any([fb.get('summary'), fb.get('strengths'), fb.get('areas_for_improvement'), fb.get('suggestions')]):
                    st.json(fb)

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

if st.button("✏️ Change Word Target", key="edit_target", width='stretch'): 
    st.session_state.editing_word_target = not st.session_state.editing_word_target
    st.rerun()

if st.session_state.editing_word_target:
    new_target = st.number_input("Target words:", min_value=100, max_value=5000, value=progress_info['target'], key="target_edit")
    col_s, col_c = st.columns(2)
    with col_s:
        if st.button("💾 Save", key="save_target", type="primary", width='stretch'):
            st.session_state.responses[current_session_id]["word_target"] = new_target
            save_user_data(st.session_state.user_id, st.session_state.responses)
            st.session_state.editing_word_target = False
            st.rerun()
    with col_c:
        if st.button("❌ Cancel", key="cancel_target", width='stretch'): 
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
