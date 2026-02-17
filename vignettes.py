# vignettes.py - WITH QUILL RICH TEXT EDITOR SUPPORT
import streamlit as st
import json
from datetime import datetime
import os
import uuid
import re
import base64
import hashlib
import time

try:
    from streamlit_quill import st_quill
    QUILL_AVAILABLE = True
except ImportError:
    QUILL_AVAILABLE = False
    st_quill = None

class VignetteManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.file = f"user_vignettes/{user_id}_vignettes.json"
        os.makedirs("user_vignettes", exist_ok=True)
        # Create images directory for vignette images
        os.makedirs(f"user_vignettes/{user_id}_images", exist_ok=True)
        self.standard_themes = [
            "Life Lesson", "Achievement", "Work Experience", "Loss of Life",
            "Illness", "New Child", "Marriage", "Travel", "Relationship",
            "Interests", "Education", "Childhood Memory", "Family Story",
            "Career Moment", "Personal Growth"
        ]
        self._load()
    
    def _load(self):
        try:
            if os.path.exists(self.file):
                with open(self.file, 'r') as f:
                    self.vignettes = json.load(f)
            else:
                self.vignettes = []
        except:
            self.vignettes = []
    
    def _save(self):
        with open(self.file, 'w') as f:
            json.dump(self.vignettes, f)
    
    def save_vignette_image(self, uploaded_file, vignette_id):
        """Save an image for a vignette and return base64"""
        try:
            # Create a unique filename
            file_ext = uploaded_file.name.split('.')[-1].lower()
            image_id = hashlib.md5(f"{vignette_id}{uploaded_file.name}{datetime.now()}".encode()).hexdigest()[:12]
            filename = f"{image_id}.{file_ext}"
            filepath = f"user_vignettes/{self.user_id}_images/{filename}"
            
            # Save the file
            with open(filepath, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            # Also return base64 for embedding
            img_bytes = uploaded_file.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
            
            return {
                "id": image_id,
                "filename": filename,
                "base64": img_base64,
                "path": filepath,
                "caption": ""
            }
        except Exception as e:
            st.error(f"Error saving image: {e}")
            return None
    
    def create_vignette(self, title, content, theme, is_draft=False, images=None):
        v = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,  # This now contains HTML from Quill
            "theme": theme,
            "word_count": len(re.sub(r'<[^>]+>', '', content).split()),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_draft": is_draft,
            "is_published": not is_draft,
            "images": images or []  # Store references to uploaded images
        }
        self.vignettes.append(v)
        self._save()
        return v
    
    def update_vignette(self, id, title, content, theme, images=None):
        for v in self.vignettes:
            if v["id"] == id:
                v.update({
                    "title": title, 
                    "content": content, 
                    "theme": theme, 
                    "word_count": len(re.sub(r'<[^>]+>', '', content).split()), 
                    "updated_at": datetime.now().isoformat(),
                    "images": images or v.get("images", [])
                })
                self._save()
                return True
        return False
    
    def delete_vignette(self, id):
        self.vignettes = [v for v in self.vignettes if v["id"] != id]
        self._save()
        return True
    
    def get_vignette_by_id(self, id):
        for v in self.vignettes:
            if v["id"] == id:
                return v
        return None
    
    def display_vignette_creator(self, on_publish=None, edit_vignette=None):
        """Display the vignette creation form with Quill rich text editor"""
        
        st.markdown("""
        <style>
        .vignette-editor-container {
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .vignette-toolbar {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 8px 8px 0 0;
            border: 1px solid #ddd;
            border-bottom: none;
        }
        .image-upload-info {
            background-color: #e8f4fd;
            padding: 10px 15px;
            border-radius: 8px;
            border-left: 4px solid #0066cc;
            margin: 15px 0;
            font-size: 0.9em;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if edit_vignette:
            st.subheader("✏️ Edit Vignette")
        else:
            st.subheader("✨ Create New Vignette")
        
        # Theme selection
        col1, col2 = st.columns(2)
        with col1:
            if edit_vignette:
                # For editing, show the current theme
                theme_options = self.standard_themes + ["Custom"]
                current_theme = edit_vignette.get("theme", "Life Lesson")
                
                if current_theme in self.standard_themes:
                    theme_index = self.standard_themes.index(current_theme) if current_theme in self.standard_themes else 0
                    theme = st.selectbox("Theme", theme_options, index=theme_index)
                else:
                    theme = st.selectbox("Theme", theme_options, index=len(theme_options)-1)
                    if theme == "Custom":
                        theme = st.text_input("Custom Theme", value=current_theme)
            else:
                theme = st.selectbox("Theme", self.standard_themes + ["Custom"])
                if theme == "Custom":
                    theme = st.text_input("Custom Theme")
        
        with col2:
            # Mood/Tone selector (new feature)
            mood_options = ["Reflective", "Joyful", "Bittersweet", "Humorous", "Serious", "Inspiring", "Nostalgic"]
            if edit_vignette:
                current_mood = edit_vignette.get("mood", "Reflective")
                mood_index = mood_options.index(current_mood) if current_mood in mood_options else 0
                mood = st.selectbox("Mood/Tone", mood_options, index=mood_index, key="vignette_mood")
            else:
                mood = st.selectbox("Mood/Tone", mood_options, key="vignette_mood")
        
        # Title input
        title = st.text_input(
            "Title", 
            value=edit_vignette.get("title", "") if edit_vignette else "",
            placeholder="Give your vignette a meaningful title",
            key="vignette_title"
        )
        
        # Content area with Quill editor
        st.markdown("### 📝 Your Story")
        
        if not QUILL_AVAILABLE or st_quill is None:
            st.warning("⚠️ Rich text editor not available. Using plain text area. Please install: pip install streamlit-quill")
            content = st.text_area(
                "Story", 
                value=re.sub(r'<[^>]+>', '', edit_vignette.get("content", "")) if edit_vignette else "",
                height=400,
                placeholder="Write your story here...",
                key="vignette_content_text"
            )
            # Wrap in paragraph tags for consistency
            if content and not content.startswith('<p>'):
                content = f'<p>{content}</p>'
        else:
            # Get existing content or default
            if edit_vignette and edit_vignette.get("content"):
                default_content = edit_vignette["content"]
            else:
                default_content = "<p>Write your story here... You can format text and drag & drop images directly into the editor.</p>"
            
            # Create a unique key for the editor
            vignette_id = edit_vignette.get('id', 'new') if edit_vignette else 'new'
            editor_key = f"quill_vignette_{vignette_id}_{int(time.time())}"
            
            # Display Quill editor
            st.markdown('<div class="image-upload-info">📸 <strong>Drag & drop images</strong> directly into the editor. You can also use the image upload section below.</div>', unsafe_allow_html=True)
            
            content = st_quill(
                value=default_content,
                key=editor_key,
                placeholder="Write your story here... You can format text and add images by dragging them in.",
                html=True,
                height=400
            )
        
        st.markdown("---")
        
        # Image upload section (separate from Quill's drag-and-drop)
        with st.expander("📸 Upload Photos (optional - these will be added to your vignette)", expanded=False):
            st.markdown("**Add images to your vignette:**")
            
            # Initialize session state for temporary images if not exists
            temp_images_key = f"vignette_temp_images_{edit_vignette.get('id', 'new')}"
            if temp_images_key not in st.session_state:
                if edit_vignette and edit_vignette.get("images"):
                    st.session_state[temp_images_key] = edit_vignette["images"].copy()
                else:
                    st.session_state[temp_images_key] = []
            
            uploaded_file = st.file_uploader(
                "Choose an image...",
                type=['jpg', 'jpeg', 'png', 'gif'],
                key=f"vignette_upload_{edit_vignette.get('id', 'new')}",
                label_visibility="collapsed"
            )
            
            if uploaded_file:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.image(uploaded_file, width=150)
                with col2:
                    caption = st.text_input(
                        "Caption (optional):", 
                        key=f"vignette_cap_{edit_vignette.get('id', 'new')}",
                        placeholder="What does this image show?"
                    )
                with col3:
                    if st.button("📥 Add", key=f"add_img_{edit_vignette.get('id', 'new')}"):
                        # Save the image
                        img_data = self.save_vignette_image(uploaded_file, edit_vignette.get('id', 'new') if edit_vignette else 'new')
                        if img_data:
                            img_data['caption'] = caption
                            st.session_state[temp_images_key].append(img_data)
                            st.success("✅ Image added!")
                            st.rerun()
            
            # Display temporary images
            if st.session_state[temp_images_key]:
                st.markdown("**Images to include:**")
                cols = st.columns(3)
                for i, img in enumerate(st.session_state[temp_images_key]):
                    with cols[i % 3]:
                        if img.get('base64'):
                            st.image(f"data:image/jpeg;base64,{img['base64']}", use_column_width=True)
                        elif img.get('path') and os.path.exists(img['path']):
                            st.image(img['path'], use_column_width=True)
                        
                        if img.get('caption'):
                            st.caption(img['caption'])
                        
                        if st.button("❌ Remove", key=f"remove_img_{i}_{edit_vignette.get('id', 'new')}"):
                            st.session_state[temp_images_key].pop(i)
                            st.rerun()
        
        # Word count display
        if content:
            text_only = re.sub(r'<[^>]+>', '', content)
            word_count = len(text_only.split())
            st.caption(f"📝 Word count: {word_count}")
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Save Draft", type="primary", use_container_width=True):
                if not content or content == "<p><br></p>" or content == "<p></p>":
                    st.error("Please write some content")
                else:
                    # Use title or default
                    final_title = title.strip() or "Untitled"
                    
                    # Get images from session state
                    images = st.session_state.get(temp_images_key, []) if temp_images_key in st.session_state else []
                    
                    if edit_vignette:
                        # Update existing
                        self.update_vignette(edit_vignette["id"], final_title, content, theme, images)
                        st.session_state.edit_success = True
                    else:
                        # Create new draft
                        self.create_vignette(final_title, content, theme, is_draft=True, images=images)
                        st.session_state.draft_success = True
                    
                    # Clear temp images
                    if temp_images_key in st.session_state:
                        del st.session_state[temp_images_key]
                    
                    st.session_state.show_vignette_modal = False
                    st.session_state.show_vignette_manager = True
                    st.rerun()
        
        with col2:
            if st.button("📢 Publish Now", use_container_width=True):
                if not content or content == "<p><br></p>" or content == "<p></p>":
                    st.error("Please write some content")
                else:
                    final_title = title.strip() or "Untitled"
                    images = st.session_state.get(temp_images_key, []) if temp_images_key in st.session_state else []
                    
                    if edit_vignette:
                        # Update and publish
                        edit_vignette["is_draft"] = False
                        edit_vignette["is_published"] = True
                        edit_vignette["published_at"] = datetime.now().isoformat()
                        self.update_vignette(edit_vignette["id"], final_title, content, theme, images)
                        st.session_state.publish_success = True
                    else:
                        # Create new published
                        v = self.create_vignette(final_title, content, theme, is_draft=False, images=images)
                        v["published_at"] = datetime.now().isoformat()
                        self.update_vignette(v["id"], final_title, content, theme, images)
                        st.session_state.publish_success = True
                    
                    # Call on_publish callback if provided
                    if on_publish:
                        vignette_data = edit_vignette if edit_vignette else v
                        on_publish(vignette_data)
                    
                    # Clear temp images
                    if temp_images_key in st.session_state:
                        del st.session_state[temp_images_key]
                    
                    st.session_state.show_vignette_modal = False
                    st.session_state.show_vignette_manager = True
                    st.rerun()
        
        with col3:
            if st.button("👁️ Preview", use_container_width=True):
                if content and content != "<p><br></p>":
                    st.session_state[f"preview_{edit_vignette.get('id', 'new')}"] = True
                    st.rerun()
        
        with col4:
            if st.button("❌ Cancel", use_container_width=True):
                # Clear temp images
                if temp_images_key in st.session_state:
                    del st.session_state[temp_images_key]
                st.session_state.show_vignette_modal = False
                st.session_state.editing_vignette_id = None
                st.rerun()
        
        # Preview section
        preview_key = f"preview_{edit_vignette.get('id', 'new')}"
        if st.session_state.get(preview_key, False) and content and content != "<p><br></p>":
            st.markdown("---")
            st.markdown("### 👁️ Preview")
            
            # Create a preview card
            st.markdown(f"## {title or 'Untitled'}")
            st.markdown(f"**Theme:** {theme}  |  **Mood:** {mood}")
            st.markdown("---")
            st.markdown(content, unsafe_allow_html=True)
            
            # Show images in preview
            temp_images_key = f"vignette_temp_images_{edit_vignette.get('id', 'new')}"
            if temp_images_key in st.session_state and st.session_state[temp_images_key]:
                st.markdown("### 📸 Images")
                cols = st.columns(3)
                for i, img in enumerate(st.session_state[temp_images_key]):
                    with cols[i % 3]:
                        if img.get('base64'):
                            st.image(f"data:image/jpeg;base64,{img['base64']}", use_column_width=True)
                        if img.get('caption'):
                            st.caption(img['caption'])
            
            if st.button("✕ Close Preview", key=f"close_preview_{edit_vignette.get('id', 'new')}"):
                st.session_state[preview_key] = False
                st.rerun()
    
    def display_vignette_gallery(self, filter_by="all", on_select=None, on_edit=None, on_delete=None):
        """Display vignettes in a gallery view"""
        
        # Filter vignettes
        if filter_by == "published":
            vs = [v for v in self.vignettes if not v.get("is_draft", True)]
        elif filter_by == "drafts":
            vs = [v for v in self.vignettes if v.get("is_draft", False)]
        else:
            vs = self.vignettes
        
        # Sort by updated_at (newest first)
        vs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        # Show success messages
        if st.session_state.get("publish_success"):
            st.success("🎉 Published successfully!")
            del st.session_state.publish_success
        if st.session_state.get("draft_success"):
            st.success("💾 Draft saved!")
            del st.session_state.draft_success
        if st.session_state.get("edit_success"):
            st.success("✅ Changes saved!")
            del st.session_state.edit_success
        if st.session_state.get("delete_success"):
            st.success("🗑️ Deleted!")
            del st.session_state.delete_success
        
        if not vs:
            st.info("No vignettes yet. Click 'Create New Vignette' to start writing!")
            return
        
        # Display as cards
        for i, v in enumerate(vs):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    status_emoji = "📢" if not v.get("is_draft") else "📝"
                    st.markdown(f"### {status_emoji} {v['title']}")
                    st.markdown(f"*{v['theme']}*")
                    
                    # Show a preview of content (strip HTML)
                    content_preview = re.sub(r'<[^>]+>', '', v['content'])
                    if len(content_preview) > 100:
                        content_preview = content_preview[:100] + "..."
                    st.markdown(content_preview)
                    
                    # Show metadata
                    date_str = datetime.fromisoformat(v.get('updated_at', v.get('created_at', ''))).strftime('%b %d, %Y')
                    st.caption(f"📝 {v['word_count']} words • Last updated: {date_str}")
                    
                    # Show image count if any
                    if v.get('images'):
                        st.caption(f"📸 {len(v['images'])} image(s)")
                
                with col2:
                    if st.button("📖 Read", key=f"read_{v['id']}", use_container_width=True):
                        if on_select:
                            on_select(v['id'])
                
                with col3:
                    if st.button("✏️ Edit", key=f"edit_{v['id']}", use_container_width=True):
                        if on_edit:
                            on_edit(v['id'])
                
                with col4:
                    if st.button("🗑️ Delete", key=f"del_{v['id']}", use_container_width=True):
                        self.delete_vignette(v['id'])
                        st.session_state.delete_success = True
                        st.rerun()
                
                st.divider()
    
    def display_full_vignette(self, id, on_back=None, on_edit=None):
        """Display a full vignette with HTML rendering"""
        v = self.get_vignette_by_id(id)
        if not v:
            st.error("Vignette not found")
            return
        
        # Back button
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← Back", use_container_width=True):
                if on_back:
                    on_back()
        
        # Status and metadata
        status_emoji = "📢" if not v.get("is_draft") else "📝"
        status_text = "Published" if not v.get("is_draft") else "Draft"
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.caption(f"{status_emoji} **{status_text}**")
        with col2:
            st.caption(f"🎭 **{v.get('mood', 'Reflective')}**")
        with col3:
            st.caption(f"📝 **{v['word_count']} words**")
        with col4:
            created = datetime.fromisoformat(v.get('created_at', '')).strftime('%b %d, %Y')
            st.caption(f"📅 **{created}**")
        
        st.markdown("---")
        
        # Title
        st.markdown(f"# {v['title']}")
        st.markdown(f"*Theme: {v['theme']}*")
        
        st.markdown("---")
        
        # Content - render as HTML
        st.markdown(v['content'], unsafe_allow_html=True)
        
        # Display images if any
        if v.get('images'):
            st.markdown("---")
            st.markdown("### 📸 Images")
            cols = st.columns(3)
            for i, img in enumerate(v['images']):
                with cols[i % 3]:
                    if img.get('base64'):
                        st.image(f"data:image/jpeg;base64,{img['base64']}", use_column_width=True)
                    elif img.get('path') and os.path.exists(img['path']):
                        st.image(img['path'], use_column_width=True)
                    
                    if img.get('caption'):
                        st.caption(img['caption'])
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✏️ Edit This Vignette", use_container_width=True, type="primary"):
                if on_edit:
                    on_edit(v['id'])
        
        with col2:
            if v.get("is_draft"):
                if st.button("📢 Publish Now", use_container_width=True):
                    v["is_draft"] = False
                    v["is_published"] = True
                    v["published_at"] = datetime.now().isoformat()
                    self.update_vignette(v["id"], v["title"], v["content"], v["theme"], v.get("images"))
                    st.success("✅ Published!")
                    st.rerun()
            else:
                if st.button("📝 Unpublish", use_container_width=True):
                    v["is_draft"] = True
                    v["is_published"] = False
                    self.update_vignette(v["id"], v["title"], v["content"], v["theme"], v.get("images"))
                    st.success("📝 Moved to drafts")
                    st.rerun()
        
        with col3:
            if st.button("🗑️ Delete", use_container_width=True):
                self.delete_vignette(v['id'])
                st.session_state.delete_success = True
                if on_back:
                    on_back()
                st.rerun()

