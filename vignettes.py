# vignettes.py - ULTRA SIMPLE VERSION
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
    
    def create_vignette(self, title, content, theme, is_draft=False):
        v = {
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
        self.vignettes.append(v)
        self._save()
        return v
    
    def update_vignette(self, id, title, content, theme):
        for v in self.vignettes:
            if v["id"] == id:
                v.update({"title": title, "content": content, "theme": theme, 
                         "word_count": len(content.split()), "updated_at": datetime.now().isoformat()})
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
        if edit_vignette:
            st.subheader("Edit Vignette")
            theme = st.text_input("Theme", edit_vignette.get("theme", ""))
            title = st.text_input("Title", edit_vignette.get("title", ""))
            content = st.text_area("Story", edit_vignette.get("content", ""), height=300)
            if st.button("Save Changes"):
                if title and content:
                    self.update_vignette(edit_vignette["id"], title, content, theme)
                    st.session_state.edit_success = True
                    st.session_state.show_vignette_modal = False
                    st.session_state.show_vignette_manager = True
                    st.rerun()
        else:
            st.subheader("New Vignette")
            theme = st.selectbox("Theme", self.standard_themes + ["Custom"])
            if theme == "Custom":
                theme = st.text_input("Custom Theme")
            title = st.text_input("Title")
            content = st.text_area("Story", height=300)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Publish"):
                    if title and content:
                        self.create_vignette(title, content, theme, False)
                        st.session_state.publish_success = True
                        st.session_state.show_vignette_modal = False
                        st.session_state.show_vignette_manager = True
                        st.rerun()
            with col2:
                if st.button("Save Draft"):
                    if content:
                        title = title or "Untitled"
                        self.create_vignette(title, content, theme, True)
                        st.session_state.draft_success = True
                        st.session_state.show_vignette_modal = False
                        st.session_state.show_vignette_manager = True
                        st.rerun()
    
    def display_vignette_gallery(self, filter_by="all", on_select=None, on_edit=None, on_delete=None):
        if filter_by == "published":
            vs = [v for v in self.vignettes if v.get("is_published")]
        elif filter_by == "drafts":
            vs = [v for v in self.vignettes if v.get("is_draft")]
        else:
            vs = self.vignettes
        
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
            st.markdown(f"### {v['title']}")
            st.markdown(f"*{v['theme']}*")
            st.markdown(v['content'][:150] + "...")
            st.markdown(f"📝 {v['word_count']} words")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Read", key=f"r_{v['id']}"):
                    on_select(v['id'])
            with col2:
                if st.button("Edit", key=f"e_{v['id']}"):
                    on_edit(v['id'])
            with col3:
                if st.button("Delete", key=f"d_{v['id']}"):
                    self.delete_vignette(v['id'])
                    st.session_state.delete_success = True
                    st.rerun()
            st.divider()
    
    def display_full_vignette(self, id, on_back=None, on_edit=None):
        v = self.get_vignette_by_id(id)
        if not v:
            return
        if st.button("← Back"):
            on_back()
        st.title(v['title'])
        st.markdown(f"**Theme:** {v['theme']}  |  **Words:** {v['word_count']}")
        st.markdown("---")
        st.write(v['content'])
        st.markdown("---")
        if st.button("Edit"):
            on_edit(v['id'])

