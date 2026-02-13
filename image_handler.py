# image_handler.py - Separate module for image handling
import streamlit as st
import json
import os
import hashlib
import base64
from datetime import datetime
from PIL import Image
import io
import re

class ImageHandler:
    """Handle image uploads, storage, and embedding for Tell My Story"""
    
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.base_path = "uploads"
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories"""
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(f"{self.base_path}/thumbnails", exist_ok=True)
        os.makedirs(f"{self.base_path}/metadata", exist_ok=True)
    
    def get_user_path(self):
        """Get user-specific upload path"""
        if self.user_id:
            user_hash = hashlib.md5(self.user_id.encode()).hexdigest()[:8]
            path = f"{self.base_path}/user_{user_hash}"
            os.makedirs(path, exist_ok=True)
            os.makedirs(f"{path}/thumbnails", exist_ok=True)
            return path
        return self.base_path
    
    def save_image(self, uploaded_file, session_id, question_text, caption=""):
        """Save uploaded image and return image data structure"""
        try:
            # Read and process image
            image_data = uploaded_file.read()
            
            # Generate unique ID for the image
            image_id = hashlib.md5(
                f"{self.user_id}{session_id}{question_text}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            
            # Resize for storage
            img = Image.open(io.BytesIO(image_data))
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # Create main image (optimized)
            main_buffer = io.BytesIO()
            img.save(main_buffer, format="JPEG", quality=85, optimize=True)
            main_data = main_buffer.getvalue()
            
            # Create thumbnail
            img.thumbnail((200, 200))
            thumb_buffer = io.BytesIO()
            img.save(thumb_buffer, format="JPEG", quality=70, optimize=True)
            thumb_data = thumb_buffer.getvalue()
            
            # Save files
            user_path = self.get_user_path()
            main_path = f"{user_path}/{image_id}.jpg"
            thumb_path = f"{user_path}/thumbnails/{image_id}.jpg"
            
            with open(main_path, 'wb') as f:
                f.write(main_data)
            with open(thumb_path, 'wb') as f:
                f.write(thumb_data)
            
            # Create metadata
            image_metadata = {
                "id": image_id,
                "session_id": session_id,
                "question": question_text,
                "caption": caption,
                "alt_text": caption[:100] if caption else f"Image for {question_text[:50]}",
                "filename": f"{image_id}.jpg",
                "timestamp": datetime.now().isoformat(),
                "file_size": len(main_data),
                "dimensions": f"{img.width}x{img.height}",
                "user_id": self.user_id
            }
            
            # Save metadata
            metadata_path = f"{self.base_path}/metadata/{image_id}.json"
            with open(metadata_path, 'w') as f:
                json.dump(image_metadata, f, indent=2)
            
            # Return data structure for embedding
            return {
                "has_images": True,
                "images": [{
                    "id": image_id,
                    "caption": caption,
                    "alt_text": image_metadata["alt_text"],
                    "timestamp": image_metadata["timestamp"],
                    "position": "inline"
                }]
            }
            
        except Exception as e:
            print(f"Error saving image: {e}")
            return None
    
    def get_image_html(self, image_id, thumbnail=False):
        """Get HTML for displaying an image"""
        try:
            user_path = self.get_user_path()
            
            if thumbnail:
                image_path = f"{user_path}/thumbnails/{image_id}.jpg"
            else:
                image_path = f"{user_path}/{image_id}.jpg"
            
            if not os.path.exists(image_path):
                return None
            
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            base64_image = base64.b64encode(image_data).decode()
            
            # Get metadata for caption
            metadata_path = f"{self.base_path}/metadata/{image_id}.json"
            caption = ""
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    caption = metadata.get("caption", "")
            
            return {
                "html": f'<img src="data:image/jpeg;base64,{base64_image}" style="max-width:100%; border-radius:8px; margin:10px 0;" alt="{caption}">',
                "caption": caption,
                "base64": base64_image
            }
            
        except Exception as e:
            print(f"Error getting image: {e}")
            return None
    
    def get_images_for_answer(self, session_id, question_text):
        """Get all images associated with a specific answer"""
        images = []
        metadata_dir = f"{self.base_path}/metadata"
        
        if not os.path.exists(metadata_dir):
            return images
        
        for filename in os.listdir(metadata_dir):
            if filename.endswith('.json'):
                try:
                    with open(f"{metadata_dir}/{filename}", 'r') as f:
                        metadata = json.load(f)
                    
                    if (metadata.get("session_id") == session_id and 
                        metadata.get("question") == question_text and
                        metadata.get("user_id") == self.user_id):
                        
                        # Get thumbnail for display
                        thumb_html = self.get_image_html(metadata["id"], thumbnail=True)
                        if thumb_html:
                            images.append({
                                **metadata,
                                "thumb_html": thumb_html["html"],
                                "full_html": self.get_image_html(metadata["id"])["html"]
                            })
                except Exception as e:
                    print(f"Error loading metadata: {e}")
        
        return sorted(images, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def delete_image(self, image_id):
        """Delete an image and its metadata"""
        try:
            user_path = self.get_user_path()
            
            # Delete main image
            main_path = f"{user_path}/{image_id}.jpg"
            if os.path.exists(main_path):
                os.remove(main_path)
            
            # Delete thumbnail
            thumb_path = f"{user_path}/thumbnails/{image_id}.jpg"
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            
            # Delete metadata
            metadata_path = f"{self.base_path}/metadata/{image_id}.json"
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            return True
        except Exception as e:
            print(f"Error deleting image: {e}")
            return False
    
    def embed_images_in_export(self, export_data):
        """Embed full-size images in export data"""
        if not isinstance(export_data, dict):
            return export_data
        
        # Process stories that have images
        if "stories" in export_data:
            for story in export_data["stories"]:
                if story.get("has_images") and story.get("images"):
                    for img in story["images"]:
                        image_data = self.get_image_html(img["id"])
                        if image_data:
                            img["base64_data"] = image_data["base64"]
                            img["embedded_html"] = image_data["html"]
        
        # Also process any embedded image data in answers
        if "responses" in export_data:
            for session_id, session_data in export_data["responses"].items():
                for question, answer_data in session_data.get("questions", {}).items():
                    if isinstance(answer_data, dict) and answer_data.get("has_images"):
                        images = self.get_images_for_answer(session_id, question)
                        answer_data["embedded_images"] = images
                        for img in images:
                            full_img = self.get_image_html(img["id"])
                            if full_img:
                                img["base64_data"] = full_img["base64"]
        
        return export_data
    
    def render_image_uploader(self, session_id, question_text, existing_images=None):
        """Render image upload interface with caption field"""
        st.markdown("### 📸 Add Photos")
        st.caption("Upload photos that illustrate this memory (JPG, PNG)")
        
        # Show existing images
        if existing_images:
            st.markdown("**Your Photos:**")
            cols = st.columns(min(len(existing_images), 3))
            for idx, img in enumerate(existing_images):
                col_idx = idx % 3
                with cols[col_idx]:
                    st.markdown(img.get("thumb_html", ""), unsafe_allow_html=True)
                    if img.get("caption"):
                        st.caption(f"📝 {img['caption']}")
                    
                    # Delete button for each image
                    if st.button(f"🗑️ Delete", key=f"del_img_{img['id']}"):
                        if self.delete_image(img['id']):
                            st.rerun()
        
        # Upload new image
        uploaded_file = st.file_uploader(
            "Choose an image...",
            type=['jpg', 'jpeg', 'png', 'gif'],
            key=f"uploader_{session_id}_{hash(question_text)}",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            caption = st.text_input(
                "Caption / Description:",
                placeholder="What does this photo show? When was it taken?",
                key=f"caption_{session_id}_{hash(question_text)}"
            )
            
            if st.button("📤 Upload Photo", key=f"upload_btn_{session_id}_{hash(question_text)}"):
                with st.spinner("Uploading..."):
                    result = self.save_image(uploaded_file, session_id, question_text, caption)
                    if result:
                        st.success("Photo uploaded!")
                        st.rerun()
                    else:
                        st.error("Upload failed")
        
        return existing_images or []

# Initialize in session state
def init_image_handler():
    if 'image_handler' not in st.session_state:
        st.session_state.image_handler = ImageHandler(st.session_state.get('user_id'))
    else:
        # Update user_id if it changed
        st.session_state.image_handler.user_id = st.session_state.get('user_id')
    return st.session_state.image_handler
