# biographer.py – Tell My Story App (MINIMAL FIX - WORKING VERSION)
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
    "image_handler": None, "show_image_manager": False, "show_ai_suggestions": False,
    "current_ai_suggestions": None, "current_suggestion_topic": None, "editor_content": {}
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
            usage = st.radio("Image size:", ["Full Page", "Inline"], horizontal=True, key=f"usage_{session_id}_{hash(question_text)}")
            if st.button("📤 Upload", key=f"btn_{session_id}_{hash(question_text)}"):
                with st.spinner("Uploading and optimizing..."):
                    usage_type = "full_page" if usage == "Full Page" else "inline"
                    if self.save_image(uploaded, session_id, question_text, cap, usage_type):
                        st.success("✅ Uploaded and optimized!")
                        st.rerun()
        return existing_images or []

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
                "timeline_start": user_data.get("birthdate", "")
            },
            "narrative_gps": {},
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
# NARRATIVE GPS HELPER FUNCTIONS (FOR AI INTEGRATION)
# ============================================================================
def get_narrative_gps_for_ai():
    """Format Narrative GPS data for AI prompts"""
    if not st.session_state.user_account or 'narrative_gps' not in st.session_state.user_account:
        return ""
    
    gps = st.session_state.user_account['narrative_gps']
    if not gps:
        return ""
    
    context = "\n\n=== BOOK PROJECT CONTEXT ===\n"
    
    if gps.get('book_title'): context += f"- Book Title: {gps['book_title']}\n"
    if gps.get('genre'): 
        genre = gps['genre']
        if genre == "Other" and gps.get('genre_other'):
            genre = gps['genre_other']
        context += f"- Genre: {genre}\n"
    if gps.get('purposes'): context += f"- Purposes: {', '.join(gps['purposes'])}\n"
    if gps.get('reader_takeaway'): context += f"- Reader Takeaway: {gps['reader_takeaway']}\n"
    if gps.get('narrative_voices'): context += f"- Voice: {', '.join(gps['narrative_voices'])}\n"
    
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
        
        if len(clean_answer.split()) < 20:
            return None
        
        system_prompt = """You are an expert writing coach. Provide 2-3 specific, actionable suggestions to improve this life story passage. Focus on alignment with the book's purpose and opportunities to deepen the narrative."""
        
        user_prompt = f"""{gps_context}

SESSION: {session_title}
QUESTION: {question}
ANSWER: {clean_answer}

Provide 2-3 specific suggestions to improve this answer."""
        
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

def show_ai_suggestions():
    """Display AI writing suggestions inline (not modal)"""
    if st.session_state.get('current_ai_suggestions'):
        st.info("💡 **AI Suggestion**")
        st.markdown(st.session_state.current_ai_suggestions)
        if st.button("Dismiss", key="dismiss_suggestions"):
            st.session_state.show_ai_suggestions = False
            st.session_state.current_ai_suggestions = None
            st.rerun()

# ============================================================================
# NARRATIVE GPS PROFILE SECTION
# ============================================================================
def render_narrative_gps():
    """Render the Narrative GPS questionnaire in the profile"""
    st.markdown("### ❤️ The Heart of Your Story")
    
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #ff4b4b;">
    Before we write a single word, let's understand why this book matters. The more honest and detailed you are here, the more your true voice will shine through every page.
    </div>
    """, unsafe_allow_html=True)
    
    if 'narrative_gps' not in st.session_state.user_account:
        st.session_state.user_account['narrative_gps'] = {}
    
    gps = st.session_state.user_account['narrative_gps']
    
    with st.expander("📖 Section 1: The Book Itself (Project Scope)", expanded=True):
        gps['book_title'] = st.text_input(
            "BOOK TITLE (Working or Final):",
            value=gps.get('book_title', ''),
            placeholder="What's your working title?",
            key="gps_title"
        )
        
        genre_options = ["", "Memoir", "Autobiography", "Family History", "Business/Legacy Book", "Other"]
        genre_index = 0
        if gps.get('genre') in genre_options:
            genre_index = genre_options.index(gps['genre'])
        
        gps['genre'] = st.selectbox(
            "BOOK GENRE/CATEGORY:",
            options=genre_options,
            index=genre_index,
            key="gps_genre"
        )
        if gps['genre'] == "Other":
            gps['genre_other'] = st.text_input("Please specify:", value=gps.get('genre_other', ''), key="gps_genre_other")
        
        length_options = ["", "A short book (100-150 pages)", "Standard length (200-300 pages)", "Comprehensive (300+ pages)"]
        length_index = 0
        if gps.get('book_length') in length_options:
            length_index = length_options.index(gps['book_length'])
        
        gps['book_length'] = st.selectbox(
            "BOOK LENGTH VISION:",
            options=length_options,
            index=length_index,
            key="gps_length"
        )
        
        gps['timeline'] = st.text_area(
            "TIMELINE & DEADLINES:",
            value=gps.get('timeline', ''),
            placeholder="Target publication date or event?",
            key="gps_timeline"
        )
        
        completion_options = ["", "Notes only", "Partial chapters", "Full draft"]
        completion_index = 0
        if gps.get('completion_status') in completion_options:
            completion_index = completion_options.index(gps['completion_status'])
        
        gps['completion_status'] = st.selectbox(
            "COMPLETION STATUS:",
            options=completion_options,
            index=completion_index,
            key="gps_completion"
        )
    
    with st.expander("🎯 Section 2: Purpose & Audience (The 'Why')", expanded=False):
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
        
        gps['reader_takeaway'] = st.text_area(
            "What do you want readers to feel, think, or do after finishing your book?",
            value=gps.get('reader_takeaway', ''),
            key="gps_takeaway"
        )
    
    with st.expander("🎭 Section 3: Tone & Voice (The 'How')", expanded=False):
        if 'narrative_voices' not in gps:
            gps['narrative_voices'] = []
        
        voice_options = [
            "Warm and conversational",
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
        
        gps['emotional_tone'] = st.text_area(
            "EMOTIONAL TONE:",
            value=gps.get('emotional_tone', ''),
            placeholder="Should readers laugh? Cry? Feel inspired?",
            key="gps_emotional"
        )
        
        language_options = ["", "Simple/everyday language", "Rich/descriptive prose", "Short/punchy chapters", "Long/flowing narratives"]
        language_index = 0
        if gps.get('language_style') in language_options:
            language_index = language_options.index(gps['language_style'])
        
        gps['language_style'] = st.selectbox(
            "LANGUAGE STYLE:",
            options=language_options,
            index=language_index,
            key="gps_language"
        )
    
    with st.expander("📋 Section 4: Content Parameters (The 'What')", expanded=False):
        time_options = ["", "Your entire life", "A specific era/decade", "One defining experience", "Your career/business journey"]
        time_index = 0
        if gps.get('time_coverage') in time_options:
            time_index = time_options.index(gps['time_coverage'])
        
        gps['time_coverage'] = st.selectbox(
            "TIME COVERAGE:",
            options=time_options,
            index=time_index,
            key="gps_time"
        )
        
        gps['sensitive_material'] = st.text_area(
            "SENSITIVE MATERIAL:",
            value=gps.get('sensitive_material', ''),
            placeholder="Topics to handle carefully?",
            key="gps_sensitive"
        )
        
        gps['sensitive_people'] = st.text_area(
            "Living people requiring sensitivity?",
            value=gps.get('sensitive_people', ''),
            key="gps_sensitive_people"
        )
        
        if 'inclusions' not in gps:
            gps['inclusions'] = []
        
        inclusion_options = ["Photos", "Family trees", "Recipes", "Letters/documents", "Timelines"]
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
        
        gps['locations'] = st.text_area(
            "Key locations that must appear:",
            value=gps.get('locations', ''),
            key="gps_locations"
        )
    
    with st.expander("📦 Section 5: Assets & Access", expanded=False):
        if 'materials' not in gps:
            gps['materials'] = []
        
        material_options = [
            "Journals/diaries", "Letters/emails", "Photos", "Video/audio recordings",
            "Newspaper clippings", "Awards/certificates", "Previous interviews"
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
        
        gps['people_to_interview'] = st.text_area(
            "People to interview:",
            value=gps.get('people_to_interview', ''),
            key="gps_people"
        )
    
    with st.expander("🤝 Section 6: Collaboration", expanded=False):
        involvement_options = [
            "I'll answer questions, you write",
            "I'll write drafts, you polish",
            "We'll interview together, then you write"
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
        
        feedback_options = ["", "Written comments", "Video discussions", "Line-by-line edits"]
        feedback_index = 0
        if gps.get('feedback_style') in feedback_options:
            feedback_index = feedback_options.index(gps['feedback_style'])
        
        gps['feedback_style'] = st.selectbox(
            "FEEDBACK STYLE:",
            options=feedback_options,
            index=feedback_index,
            key="gps_feedback"
        )
        
        gps['unspoken'] = st.text_area(
            "What do you hope I'll bring to this project?",
            value=gps.get('unspoken', ''),
            key="gps_unspoken"
        )"gps_unspoken"
        )
    
    if st.button("💾 Save The Heart of Your Story", key="save_narrative_gps", type="primary"):
        save_account_data(st.session_state.user_account)
        st.success("✅ Saved!")
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
        
        # Generate AI writing suggestions
        session_title = st.session_state.responses[session_id].get("title", f"Session {session_id}")
        suggestions = generate_writing_suggestions(question, answer, session_title)
        if suggestions and not isinstance(suggestions, dict):
            st.session_state.current_ai_suggestions = suggestions
            st.session_state.show_ai_suggestions = True
    
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
# VIGNETTE FUNCTIONS (SIMPLIFIED)
# ============================================================================
def show_vignette_modal():
    st.info("Vignette feature coming soon")

def show_vignette_manager():
    st.info("Vignette manager coming soon")

def show_vignette_detail():
    pass

# ============================================================================
# TOPIC BROWSER & SESSION MANAGER (SIMPLIFIED)
# ============================================================================
def show_topic_browser():
    st.info("Topic browser coming soon")

def show_session_creator():
    st.info("Session creator coming soon")

def show_session_manager():
    st.info("Session manager coming soon")

# ============================================================================
# QUESTION BANK UI FUNCTIONS (SIMPLIFIED)
# ============================================================================
def show_bank_manager():
    st.info("Bank manager coming soon")

def show_bank_editor():
    st.info("Bank editor coming soon")

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
    
    # Cover page
    pdf.set_fill_color(102, 126, 234)
    pdf.rect(0, 0, 210, 297, 'F')
    pdf.set_text_color(255, 255, 255)
    
    safe_title = ''.join(c for c in book_title if ord(c) < 128)
    safe_author = ''.join(c for c in author_name if ord(c) < 128)
    
    pdf.set_font('Arial', 'B', 30)
    pdf.cell(0, 40, '', 0, 1)
    pdf.cell(0, 20, safe_title if safe_title else 'My Story', 0, 1, 'C')
    pdf.set_font('Arial', '', 16)
    pdf.cell(0, 10, f'by {safe_author}' if safe_author else 'by Author', 0, 1, 'C')
    pdf.add_page()
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 11)
    
    for story in stories:
        question = story.get('question', '')
        answer = story.get('answer_text', '')
        
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
    doc.add_page_break()
    
    # Content
    for story in stories:
        question = story.get('question', '')
        answer_text = story.get('answer_text', '')
        images = story.get('images', [])
        
        doc.add_heading(question, 2)
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
                        doc.add_paragraph(caption, style='Caption')
                except:
                    pass
        doc.add_paragraph()
    
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    return docx_bytes

# ============================================================================
# HTML GENERATION FUNCTION
# ============================================================================
def generate_html(book_title, author_name, stories):
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{book_title}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #667eea; text-align: center; }}
        .story {{ margin-bottom: 50px; padding: 20px; background: #f9f9f9; border-radius: 10px; }}
        .question {{ font-size: 1.3em; font-weight: bold; color: #2c3e50; }}
        img {{ max-width: 100%; border-radius: 8px; margin: 10px 0; }}
        .caption {{ font-style: italic; color: #666; text-align: center; }}
    </style>
</head>
<body>
    <h1>{book_title}</h1>
    <div style="text-align: center;">by {author_name}</div>
"""
    
    for story in stories:
        html += f"""
    <div class="story">
        <div class="question">{story['question']}</div>
        <div>{story['answer_text']}</div>
"""
        for img in story.get('images', []):
            if img.get('base64'):
                html += f'        <img src="data:image/jpeg;base64,{img["base64"]}" alt="{img.get("caption", "")}">\n'
                if img.get('caption'):
                    html += f'        <div class="caption">{img["caption"]}</div>\n'
        
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
# ZIP GENERATION FUNCTION
# ============================================================================
def generate_zip(book_title, author_name, stories):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        html = generate_html(book_title, author_name, stories)
        zip_file.writestr(f"{book_title.replace(' ', '_')}.html", html)
        
        # Add images
        for i, story in enumerate(stories):
            for j, img in enumerate(story.get('images', [])):
                if img.get('base64'):
                    img_data = base64.b64decode(img['base64'])
                    zip_file.writestr(f"images/image_{i}_{j}.jpg", img_data)
    
    return zip_buffer.getvalue()

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(page_title="Tell My Story", page_icon="📖", layout="wide")

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
    st.error("❌ No question bank loaded.")
    st.stop()

# ============================================================================
# AUTHENTICATION UI
# ============================================================================
if not st.session_state.logged_in:
    st.markdown('<div class="auth-container"><h1>Tell My Story</h1><p>Your Life Timeline</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary"):
                if email and password:
                    result = authenticate_user(email, password)
                    if result["success"]:
                        st.session_state.update(user_id=result["user_id"], 
                                              user_account=result["user_record"],
                                              logged_in=True, 
                                              data_loaded=False)
                        st.rerun()
                    else: 
                        st.error("Login failed")
    
    with tab2:
        with st.form("signup_form"):
            col1, col2 = st.columns(2)
            with col1: 
                first_name = st.text_input("First Name*")
            with col2: 
                last_name = st.text_input("Last Name*")
            email = st.text_input("Email*")
            password = st.text_input("Password*", type="password")
            confirm = st.text_input("Confirm Password*", type="password")
            
            if st.form_submit_button("Create Account", type="primary"):
                if password != confirm:
                    st.error("Passwords don't match")
                elif get_account_data(email=email):
                    st.error("Email already exists")
                else:
                    result = create_user_account({"first_name": first_name, "last_name": last_name, "email": email})
                    if result["success"]:
                        st.session_state.update(user_id=result["user_id"], 
                                              user_account=result["user_record"],
                                              logged_in=True, 
                                              data_loaded=False)
                        st.success("Account created!")
                        st.rerun()
    st.stop()

# ============================================================================
# PROFILE SETUP MODAL (FIXED - NO TABS)
# ============================================================================
if st.session_state.get('show_profile_setup', False):
    st.markdown("---")
    st.title("👤 Your Profile")
    
    # Basic Profile
    with st.form("profile_setup_form"):
        st.subheader("Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            gender = st.radio("Gender", ["Male", "Female", "Other", "Prefer not to say"], horizontal=True)
        with col2:
            account_for = st.radio("Account Type", ["For me", "For someone else"], horizontal=True)
        
        col1, col2, col3 = st.columns(3)
        with col1: 
            birth_month = st.selectbox("Month", ["January","February","March","April","May","June","July","August","September","October","November","December"])
        with col2: 
            birth_day = st.selectbox("Day", list(range(1,32)))
        with col3: 
            birth_year = st.selectbox("Year", list(range(datetime.now().year, datetime.now().year-100, -1)))
        
        if st.form_submit_button("💾 Save Basic Info", type="primary"):
            if birth_month and birth_day and birth_year:
                birthdate = f"{birth_month} {birth_day}, {birth_year}"
                if st.session_state.user_account:
                    st.session_state.user_account['profile'].update({'gender': gender, 'birthdate': birthdate})
                    save_account_data(st.session_state.user_account)
                st.success("Saved!")
                st.rerun()
    
    st.divider()
    
    # Narrative GPS
    render_narrative_gps()
    
    if st.button("← Close", key="close_profile"):
        st.session_state.show_profile_setup = False
        st.rerun()
    
    st.stop()

# ============================================================================
# MODAL HANDLING
# ============================================================================
if st.session_state.show_bank_manager: 
    show_bank_manager()
    st.stop()
if st.session_state.show_bank_editor: 
    show_bank_editor()
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
    show_vignette_detail()
    st.stop()
if st.session_state.show_vignette_manager: 
    show_vignette_manager()
    st.stop()
if st.session_state.show_vignette_modal: 
    show_vignette_modal()
    st.stop()
if st.session_state.show_topic_browser: 
    show_topic_browser()
    st.stop()
if st.session_state.show_session_manager: 
    show_session_manager()
    st.stop()
if st.session_state.show_session_creator: 
    show_session_creator()
    st.stop()

# ============================================================================
# MAIN HEADER
# ============================================================================
st.markdown(f'<div class="main-header"><img src="{LOGO_URL}" style="height:60px"></div>', unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("### Tell My Story")
    
    st.header("👤 Profile")
    if st.session_state.user_account:
        profile = st.session_state.user_account['profile']
        st.write(f"**{profile.get('first_name', '')} {profile.get('last_name', '')}**")
    if st.button("📝 Edit Profile"):
        st.session_state.show_profile_setup = True
        st.rerun()
    if st.button("🚪 Log Out"):
        logout_user()
    
    st.divider()
    
    st.header("📖 Sessions")
    if st.session_state.current_question_bank:
        for i, s in enumerate(st.session_state.current_question_bank):
            sid = s["id"]
            sdata = st.session_state.responses.get(sid, {})
            resp_cnt = len(sdata.get("questions", {}))
            status = "🟢" if resp_cnt > 0 else "🔴"
            if st.button(f"{status} {s['title']}", key=f"sesh_{i}"):
                st.session_state.update(current_session=i, current_question=0)
                st.rerun()
    
    st.divider()
    
    st.header("📤 Export")
    if st.session_state.logged_in:
        export_data = []
        for session in SESSIONS:
            sid = session["id"]
            sdata = st.session_state.responses.get(sid, {})
            for q, a in sdata.get("questions", {}).items():
                images_with_data = []
                if a.get("images"):
                    for img_ref in a.get("images", []):
                        img_id = img_ref.get("id")
                        b64 = st.session_state.image_handler.get_image_base64(img_id) if st.session_state.image_handler else None
                        if b64:
                            images_with_data.append({
                                "base64": b64,
                                "caption": img_ref.get("caption", "")
                            })
                
                export_item = {
                    "question": q,
                    "answer_text": re.sub(r'<[^>]+>', '', a.get("answer", "")),
                    "session_title": session["title"],
                    "images": images_with_data
                }
                export_data.append(export_item)
        
        if export_data:
            book_title = st.text_input("Book Title", value="My Story")
            author = st.text_input("Author", value=profile.get('first_name', ''))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("DOCX"):
                    docx_bytes = generate_docx(book_title, author, export_data, "memoir", True, False)
                    st.download_button("Download", data=docx_bytes, file_name=f"{book_title}.docx")
            with col2:
                if st.button("HTML"):
                    html = generate_html(book_title, author, export_data)
                    st.download_button("Download", data=html, file_name=f"{book_title}.html")
            with col3:
                if st.button("ZIP"):
                    zip_data = generate_zip(book_title, author, export_data)
                    st.download_button("Download", data=zip_data, file_name=f"{book_title}.zip")

# ============================================================================
# MAIN CONTENT AREA
# ============================================================================
if st.session_state.current_session >= len(SESSIONS): 
    st.session_state.current_session = 0

current_session = SESSIONS[st.session_state.current_session]
current_session_id = current_session["id"]

if st.session_state.current_question_override:
    current_question_text = st.session_state.current_question_override
else:
    if st.session_state.current_question >= len(current_session["questions"]): 
        st.session_state.current_question = 0
    current_question_text = current_session["questions"][st.session_state.current_question]

st.subheader(f"Session: {current_session['title']}")

# Progress
sdata = st.session_state.responses.get(current_session_id, {})
answered = len(sdata.get("questions", {}))
total = len(current_session["questions"])
if total > 0: 
    st.progress(answered/total)

st.markdown(f"### {current_question_text}")

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
# QUILL EDITOR (FIXED)
# ============================================================================
editor_key = f"quill_{current_session_id}_{current_question_text[:20]}"
content_key = f"{editor_key}_content"

if content_key not in st.session_state:
    if existing_answer:
        st.session_state[content_key] = existing_answer
    else:
        st.session_state[content_key] = ""

st.markdown("### ✍️ Your Story")

# ONE Quill editor - NO MODALS INTERFERING
content = st_quill(
    st.session_state[content_key],
    key=editor_key,
    placeholder="Write your story here..."
)

if content is not None:
    st.session_state[content_key] = content

user_input = st.session_state[content_key]

# Show AI suggestions if available (inline, not modal)
if st.session_state.get('show_ai_suggestions'):
    show_ai_suggestions()

st.markdown("---")

# ============================================================================
# IMAGE UPLOAD SECTION (SIMPLIFIED)
# ============================================================================
if st.session_state.logged_in and st.session_state.image_handler:
    
    if existing_images:
        st.markdown("### 📸 Your Photos")
        for idx, img in enumerate(existing_images[:3]):
            if img.get("thumb_html"):
                st.markdown(img["thumb_html"], unsafe_allow_html=True)
                if st.button(f"Insert", key=f"ins_{img['id']}"):
                    full_html = img.get("full_html", "")
                    if full_html:
                        current = st.session_state.get(content_key, "")
                        st.session_state[content_key] = current + "<br><br>" + full_html
                        st.rerun()
    
    with st.expander("📤 Upload Photo"):
        uploaded = st.file_uploader("Choose image", type=['jpg','jpeg','png'], key=f"up_{current_session_id}")
        if uploaded:
            caption = st.text_input("Caption", key=f"cap_{current_session_id}")
            if st.button("Upload"):
                with st.spinner("Uploading..."):
                    st.session_state.image_handler.save_image(uploaded, current_session_id, current_question_text, caption)
                    st.success("Uploaded!")
                    st.rerun()

st.markdown("---")

# ============================================================================
# SAVE BUTTONS
# ============================================================================
col1, col2 = st.columns(2)
with col1:
    if st.button("💾 Save Story", type="primary"):
        if user_input and user_input.strip():
            if save_response(current_session_id, current_question_text, user_input):
                st.success("Saved!")
                st.rerun()
with col2:
    if existing_answer:
        if st.button("🗑️ Delete"):
            delete_response(current_session_id, current_question_text)
            st.rerun()

# Navigation
col1, col2, col3 = st.columns(3)
with col1:
    if st.session_state.current_question > 0:
        if st.button("← Previous"):
            st.session_state.current_question -= 1
            st.session_state.current_question_override = None
            st.rerun()
with col3:
    if st.session_state.current_question < len(current_session["questions"]) - 1:
        if st.button("Next →"):
            st.session_state.current_question += 1
            st.session_state.current_question_override = None
            st.rerun()

