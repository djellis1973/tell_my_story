# vignettes.py - MATCHING BIOGRAPHER.PY EXACT PATTERN
import streamlit as st
import json
from datetime import datetime
import os
import uuid
import re
import base64
import hashlib
import time

from streamlit_quill import st_quill

class VignetteManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.file = f"user_vignettes/{user_id}_vignettes.json"
        os.makedirs("user_vignettes", exist_ok=True)
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
            file_ext = uploaded_file.name.split('.')[-1].lower()
            image_id = hashlib.md5(f"{vignette_id}{uploaded_file.name}{datetime.now()}".encode()).hexdigest()[:12]
            filename = f"{image_id}.{file_ext}"
            filepath = f"user_vignettes/{self.user_id}_images/{filename}"
            
            with open(filepath, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
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
    
    def create_vignette(self, title, content, theme, mood="Reflective", is_draft=False, images=None):
        v = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "theme": theme,
            "mood": mood,
            "word_count": len(re.sub(r'<[^>]+>', '', content).split()),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_draft": is_draft,
            "is_published": not is_draft,
            "images": images or []
        }
        self.vignettes.append(v)
        self._save()
        return v
    
    def update_vignette(self, id, title, content, theme, mood=None, images=None):
        for v in self.vignettes:
            if v["id"] == id:
                v.update({
                    "title": title, 
                    "content": content, 
                    "theme": theme, 
                    "mood": mood or v.get("mood", "Reflective"),
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
        """Display the vignette creation form matching biographer.py EXACT pattern"""
        
# Create unique keys for this vignette - MATCHING BIOGRAPHER.PY PATTERN
    if edit_vignette:
        vignette_id = edit_vignette['id']
        base_key = f"vignette_{vignette_id}"
    else:
        # Use a STABLE ID for new vignettes - just 'new' without timestamp
        vignette_id = "new"
        base_key = "vignette_new"
        
        # Editor key and content key - EXACTLY like biographer.py
        editor_key = f"quill_vignette_{vignette_id}"
        content_key = f"{editor_key}_content"
        
        # Title input
        title = st.text_input(
            "Title", 
            value=edit_vignette.get("title", "") if edit_vignette else "",
            placeholder="Give your vignette a meaningful title",
            key=f"{base_key}_title"
        )
        
        # Theme and mood in columns
        col1, col2 = st.columns(2)
        with col1:
            theme_options = self.standard_themes + ["Custom"]
            if edit_vignette and edit_vignette.get("theme"):
                current_theme = edit_vignette["theme"]
                if current_theme in self.standard_themes:
                    theme_index = self.standard_themes.index(current_theme)
                    theme = st.selectbox("Theme", theme_options, index=theme_index, key=f"{base_key}_theme")
                else:
                    theme = st.selectbox("Theme", theme_options, index=len(theme_options)-1, key=f"{base_key}_theme")
                    if theme == "Custom":
                        theme = st.text_input("Custom Theme", value=current_theme, key=f"{base_key}_custom_theme")
            else:
                theme = st.selectbox("Theme", theme_options, key=f"{base_key}_theme")
                if theme == "Custom":
                    theme = st.text_input("Custom Theme", key=f"{base_key}_custom_theme")
        
        with col2:
            mood_options = ["Reflective", "Joyful", "Bittersweet", "Humorous", "Serious", "Inspiring", "Nostalgic"]
            if edit_vignette:
                current_mood = edit_vignette.get("mood", "Reflective")
                mood_index = mood_options.index(current_mood) if current_mood in mood_options else 0
                mood = st.selectbox("Mood/Tone", mood_options, index=mood_index, key=f"{base_key}_mood")
            else:
                mood = st.selectbox("Mood/Tone", mood_options, key=f"{base_key}_mood")
        
        # Initialize content in session state - EXACTLY like biographer.py
        if edit_vignette and edit_vignette.get("content"):
            default_content = edit_vignette["content"]
        else:
            default_content = "<p>Write your story here...</p>"
        
        if content_key not in st.session_state:
            st.session_state[content_key] = default_content
        
        # Timestamp for spell check refresh - EXACTLY like biographer.py
        spell_check_key = f"{base_key}_spell_timestamp"
        if spell_check_key not in st.session_state:
            st.session_state[spell_check_key] = 0
        
        # Editor component key with timestamp - EXACTLY like biographer.py
        editor_component_key = f"quill_editor_{vignette_id}_{st.session_state[spell_check_key]}"
        
        st.markdown("### 📝 Your Story")
        st.markdown("""
        <div class="image-drop-info">
            📸 <strong>Drag & drop images</strong> directly into the editor.
        </div>
        """, unsafe_allow_html=True)
        
        # Display Quill editor - EXACT parameters as biographer.py
        content = st_quill(
            value=st.session_state[content_key],
            key=editor_component_key,
            placeholder="Write your story here...",
            html=True
        )
        
        # Update session state when content changes
        if content is not None and content != st.session_state[content_key]:
            st.session_state[content_key] = content
        
        st.markdown("---")
        
        # Image upload section
        with st.expander("📸 Upload Photos", expanded=False):
            temp_images_key = f"{base_key}_temp_images"
            if temp_images_key not in st.session_state:
                if edit_vignette and edit_vignette.get("images"):
                    st.session_state[temp_images_key] = edit_vignette["images"].copy()
                else:
                    st.session_state[temp_images_key] = []
            
            uploaded_file = st.file_uploader(
                "Choose an image...",
                type=['jpg', 'jpeg', 'png', 'gif'],
                key=f"{base_key}_upload",
                label_visibility="collapsed"
            )
            
            if uploaded_file:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.image(uploaded_file, width=150)
                with col2:
                    caption = st.text_input(
                        "Caption:", 
                        key=f"{base_key}_caption",
                        placeholder="What does this image show?"
                    )
                with col3:
                    if st.button("📥 Add", key=f"{base_key}_add_img"):
                        img_data = self.save_vignette_image(uploaded_file, vignette_id)
                        if img_data:
                            img_data['caption'] = caption
                            st.session_state[temp_images_key].append(img_data)
                            st.rerun()
            
            if st.session_state[temp_images_key]:
                st.markdown("**Images to include:**")
                cols = st.columns(3)
                for i, img in enumerate(st.session_state[temp_images_key]):
                    with cols[i % 3]:
                        if img.get('base64'):
                            st.image(f"data:image/jpeg;base64,{img['base64']}", use_column_width=True)
                        if img.get('caption'):
                            st.caption(img['caption'])
                        if st.button("❌", key=f"{base_key}_remove_{i}"):
                            st.session_state[temp_images_key].pop(i)
                            st.rerun()
        
        # Word count
        if st.session_state[content_key]:
            text_only = re.sub(r'<[^>]+>', '', st.session_state[content_key])
            word_count = len(text_only.split())
            st.caption(f"📝 Word count: {word_count}")
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Save Draft", type="primary", use_container_width=True, key=f"{base_key}_save_draft"):
                current_content = st.session_state[content_key]
                if not current_content or current_content == "<p><br></p>" or current_content == "<p></p>":
                    st.error("Please write some content")
                else:
                    final_title = title.strip() or "Untitled"
                    images = st.session_state.get(temp_images_key, [])
                    
                    if edit_vignette:
                        self.update_vignette(edit_vignette["id"], final_title, current_content, theme, mood, images)
                        st.session_state.edit_success = True
                    else:
                        self.create_vignette(final_title, current_content, theme, mood, is_draft=True, images=images)
                        st.session_state.draft_success = True
                    
                    # Clean up session state
                    for key in [content_key, temp_images_key, spell_check_key]:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.session_state.show_vignette_modal = False
                    st.session_state.show_vignette_manager = True
                    st.rerun()
        
        with col2:
            if st.button("📢 Publish", use_container_width=True, key=f"{base_key}_publish"):
                current_content = st.session_state[content_key]
                if not current_content or current_content == "<p><br></p>" or current_content == "<p></p>":
                    st.error("Please write some content")
                else:
                    final_title = title.strip() or "Untitled"
                    images = st.session_state.get(temp_images_key, [])
                    
                    if edit_vignette:
                        edit_vignette["is_draft"] = False
                        edit_vignette["published_at"] = datetime.now().isoformat()
                        self.update_vignette(edit_vignette["id"], final_title, current_content, theme, mood, images)
                        st.session_state.publish_success = True
                        vignette_data = edit_vignette
                    else:
                        v = self.create_vignette(final_title, current_content, theme, mood, is_draft=False, images=images)
                        v["published_at"] = datetime.now().isoformat()
                        self.update_vignette(v["id"], final_title, current_content, theme, mood, images)
                        st.session_state.publish_success = True
                        vignette_data = v
                    
                    if on_publish:
                        on_publish(vignette_data)
                    
                    # Clean up session state
                    for key in [content_key, temp_images_key, spell_check_key]:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.session_state.show_vignette_modal = False
                    st.session_state.show_vignette_manager = True
                    st.rerun()
        
        with col3:
            if st.button("👁️ Preview", use_container_width=True, key=f"{base_key}_preview"):
                st.session_state[f"{base_key}_show_preview"] = True
                st.rerun()
        
        with col4:
            if st.button("❌ Cancel", use_container_width=True, key=f"{base_key}_cancel"):
                # Clean up session state
                for key in [content_key, temp_images_key, spell_check_key]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.show_vignette_modal = False
                st.session_state.editing_vignette_id = None
                st.rerun()
        
        # Preview section
        if st.session_state.get(f"{base_key}_show_preview", False) and st.session_state[content_key]:
            st.markdown("---")
            st.markdown("### 👁️ Preview")
            st.markdown(f"## {title or 'Untitled'}")
            st.markdown(f"**Theme:** {theme}  |  **Mood:** {mood}")
            st.markdown("---")
            st.markdown(st.session_state[content_key], unsafe_allow_html=True)
            
            if st.button("✕ Close Preview", key=f"{base_key}_close_preview"):
                st.session_state[f"{base_key}_show_preview"] = False
                st.rerun()
    
    def display_vignette_gallery(self, filter_by="all", on_select=None, on_edit=None, on_delete=None):
        """Display vignettes in a gallery view"""
        
        if filter_by == "published":
            vs = [v for v in self.vignettes if not v.get("is_draft", True)]
        elif filter_by == "drafts":
            vs = [v for v in self.vignettes if v.get("is_draft", False)]
        else:
            vs = self.vignettes
        
        vs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        # Show success messages
        if st.session_state.get("publish_success"):
            st.success("🎉 Published!")
            del st.session_state.publish_success
        if st.session_state.get("draft_success"):
            st.success("💾 Draft saved!")
            del st.session_state.draft_success
        if st.session_state.get("edit_success"):
            st.success("✅ Saved!")
            del st.session_state.edit_success
        if st.session_state.get("delete_success"):
            st.success("🗑️ Deleted!")
            del st.session_state.delete_success
        
        if not vs:
            st.info("No vignettes yet.")
            return
        
        for v in vs:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    status_emoji = "📢" if not v.get("is_draft") else "📝"
                    st.markdown(f"### {status_emoji} {v['title']}")
                    st.markdown(f"*{v['theme']}*")
                    
                    content_preview = re.sub(r'<[^>]+>', '', v['content'])
                    if len(content_preview) > 100:
                        content_preview = content_preview[:100] + "..."
                    st.markdown(content_preview)
                    
                    date_str = datetime.fromisoformat(v.get('updated_at', v.get('created_at', ''))).strftime('%b %d, %Y')
                    st.caption(f"📝 {v['word_count']} words • {date_str}")
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
            return
        
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← Back", use_container_width=True):
                if on_back:
                    on_back()
        
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
        st.markdown(f"# {v['title']}")
        st.markdown(f"*Theme: {v['theme']}*")
        st.markdown("---")
        st.markdown(v['content'], unsafe_allow_html=True)
        
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
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✏️ Edit", use_container_width=True, type="primary"):
                if on_edit:
                    on_edit(v['id'])
        
        with col2:
            if v.get("is_draft"):
                if st.button("📢 Publish", use_container_width=True):
                    v["is_draft"] = False
                    v["published_at"] = datetime.now().isoformat()
                    self.update_vignette(v["id"], v["title"], v["content"], v["theme"], v.get("mood"), v.get("images"))
                    st.rerun()
            else:
                if st.button("📝 Unpublish", use_container_width=True):
                    v["is_draft"] = True
                    self.update_vignette(v["id"], v["title"], v["content"], v["theme"], v.get("mood"), v.get("images"))
                    st.rerun()
        
        with col3:
            if st.button("🗑️ Delete", use_container_width=True):
                self.delete_vignette(v['id'])
                st.session_state.delete_success = True
                if on_back:
                    on_back()
                st.rerun()
