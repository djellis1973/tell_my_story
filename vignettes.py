# vignettes.py - COMPLETE WORKING VERSION
import streamlit as st
import json
from datetime import datetime
import os
import uuid

class VignetteManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.file = f"user_vignettes/{user_id}_vignettes.json"
        os.makedirs("user_vignettes", exist_ok=True)
        
        self.standard_themes = [
            "Life Lesson",
            "Achievement",
            "Work Experience",
            "Loss of Life",
            "Illness",
            "New Child",
            "Marriage",
            "Travel",
            "Relationship",
            "Interests",
            "Education",
            "Childhood Memory",
            "Family Story",
            "Career Moment",
            "Personal Growth"
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
            json.dump(self.vignettes, f, indent=2)
    
    def create_vignette(self, title, content, theme, is_draft=False):
        vignette = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "theme": theme,
            "word_count": len(content.split()),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_draft": is_draft,
            "is_published": not is_draft
        }
        self.vignettes.append(vignette)
        self._save()
        return vignette
    
    def update_vignette(self, id, title, content, theme):
        for v in self.vignettes:
            if v["id"] == id:
                v["title"] = title
                v["content"] = content
                v["theme"] = theme
                v["word_count"] = len(content.split())
                v["updated_at"] = datetime.now().isoformat()
                self._save()
                return True
        return False
    
    def delete_vignette(self, id):
        self.vignettes = [v for v in self.vignettes if v["id"] != id]
        self._save()
        return True
    
    def publish_vignette(self, id):
        for v in self.vignettes:
            if v["id"] == id:
                v["is_draft"] = False
                v["is_published"] = True
                v["published_at"] = datetime.now().isoformat()
                self._save()
                return True
        return False
    
    def get_vignette_by_id(self, id):
        for v in self.vignettes:
            if v["id"] == id:
                return v
        return None
    
    def get_all_vignettes(self):
        return self.vignettes
    
    def display_vignette_creator(self, on_publish=None, edit_vignette=None):
        if edit_vignette:
            st.subheader("✏️ Edit Vignette")
            
            initial_theme = edit_vignette.get("theme", "")
            theme_index = 0
            if initial_theme in self.standard_themes:
                theme_index = self.standard_themes.index(initial_theme)
            else:
                theme_index = len(self.standard_themes)
            
            theme_options = self.standard_themes + ["Custom Theme"]
            selected_theme = st.selectbox("Theme", theme_options, index=theme_index)
            
            if selected_theme == "Custom Theme":
                theme = st.text_input("Custom Theme", value=initial_theme if initial_theme not in self.standard_themes else "")
            else:
                theme = selected_theme
            
            title = st.text_input("Title", value=edit_vignette.get("title", ""))
            content = st.text_area("Story", value=edit_vignette.get("content", ""), height=300)
            
            if st.button("💾 Save Changes", type="primary"):
                if title and content:
                    self.update_vignette(edit_vignette["id"], title, content, theme)
                    st.success("✅ Vignette saved successfully!")
                    st.balloons()
                    st.session_state.show_vignette_modal = False
                    st.session_state.editing_vignette_id = None
                    st.rerun()
                    return True
        else:
            st.subheader("✍️ Create New Vignette")
            
            selected_theme = st.selectbox("Theme", self.standard_themes + ["Custom Theme"])
            
            if selected_theme == "Custom Theme":
                theme = st.text_input("Custom Theme")
            else:
                theme = selected_theme
            
            title = st.text_input("Title", placeholder="Give your story a title...")
            content = st.text_area("Story", height=300, placeholder="Write your story here...")
            
            if content:
                word_count = len(content.split())
                st.caption(f"📝 {word_count} words")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Publish", type="primary", use_container_width=True):
                    if title and content:
                        v = self.create_vignette(title, content, theme, is_draft=False)
                        if on_publish:
                            on_publish(v)
                        st.success("🎉 Your vignette has been published!")
                        st.balloons()
                        st.session_state.show_vignette_modal = False
                        st.rerun()
                        return True
                    else:
                        st.warning("⚠️ Please add a title and story content")
            with col2:
                if st.button("💾 Save as Draft", use_container_width=True):
                    if content:
                        title = title if title else "Untitled Draft"
                        self.create_vignette(title, content, theme, is_draft=True)
                        st.success("💾 Draft saved successfully!")
                        st.session_state.show_vignette_modal = False
                        st.rerun()
                        return True
                    else:
                        st.warning("⚠️ Cannot save an empty story")
        return False
    
    def display_vignette_gallery(self, filter_by="all", on_select=None, on_edit=None, on_delete=None):
        if filter_by == "published":
            vignettes = [v for v in self.vignettes if v.get("is_published")]
        elif filter_by == "drafts":
            vignettes = [v for v in self.vignettes if v.get("is_draft")]
        else:
            vignettes = self.vignettes
        
        if not vignettes:
            if filter_by == "published":
                st.info("📭 No published vignettes yet.")
            elif filter_by == "drafts":
                st.info("📭 No drafts yet.")
            else:
                st.info("📭 No vignettes yet.")
            return
        
        for v in vignettes:
            with st.container():
                st.markdown(f"### {v['title']}")
                st.markdown(f"**Theme:** {v['theme']}")
                st.markdown(v['content'][:150] + "..." if len(v['content']) > 150 else v['content'])
                st.markdown(f"📝 {v['word_count']} words")
                st.markdown(f"**{'✅ Published' if v.get('is_published') else '📝 Draft'}**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📖 Read", key=f"read_{v['id']}", use_container_width=True):
                        if on_select:
                            on_select(v['id'])
                with col2:
                    if st.button("✏️ Edit", key=f"edit_{v['id']}", use_container_width=True):
                        if on_edit:
                            on_edit(v['id'])
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{v['id']}", use_container_width=True):
                        if on_delete:
                            on_delete(v['id'])
                st.divider()
    
    def display_full_vignette(self, vignette_id, on_back=None, on_edit=None):
        v = self.get_vignette_by_id(vignette_id)
        if not v:
            st.error("Vignette not found")
            return
        
        if st.button("← Back to Vignettes"):
            if on_back:
                on_back()
            st.rerun()
        
        st.title(v['title'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Theme:** {v['theme']}")
        with col2:
            st.markdown(f"**Words:** {v['word_count']}")
        
        if v.get('is_published'):
            st.markdown(f"**Published:** {v.get('published_at', v['created_at'])[:10]}")
        else:
            st.markdown(f"**Created:** {v['created_at'][:10]}")
        
        st.markdown("---")
        st.write(v['content'])
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Edit Story", use_container_width=True):
                if on_edit:
                    on_edit(v['id'])
        with col2:
            if st.button("📋 Back to Gallery", use_container_width=True):
                if on_back:
                    on_back()
                st.rerun()
        
        if v.get('is_draft'):
            st.divider()
            if st.button("🚀 Publish Story", type="primary", use_container_width=True):
                self.publish_vignette(v['id'])
                st.success("✅ Vignette published successfully!")
                st.balloons()
                st.rerun()
