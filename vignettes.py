# vignettes.py - SIMPLE WORKING VERSION
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
    
    def create(self, title, content, theme, is_draft):
        vignette = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "theme": theme,
            "word_count": len(content.split()),
            "created_at": datetime.now().isoformat(),
            "is_draft": is_draft,
            "is_published": not is_draft
        }
        self.vignettes.append(vignette)
        self._save()
        return vignette
    
    def update(self, id, title, content, theme):
        for v in self.vignettes:
            if v["id"] == id:
                v["title"] = title
                v["content"] = content
                v["theme"] = theme
                v["word_count"] = len(content.split())
                self._save()
                return True
        return False
    
    def delete(self, id):
        self.vignettes = [v for v in self.vignettes if v["id"] != id]
        self._save()
        return True
    
    def get(self, id):
        for v in self.vignettes:
            if v["id"] == id:
                return v
        return None
    
    def get_all(self):
        return self.vignettes

def show_vignette_modal():
    if 'vm' not in st.session_state:
        st.session_state.vm = VignetteManager(st.session_state.user_id)
    
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    
    if st.button("Back"):
        st.session_state.show_vignette_modal = False
        st.session_state.editing_vignette_id = None
        st.rerun()
    
    edit_id = st.session_state.get('editing_vignette_id')
    vignette = st.session_state.vm.get(edit_id) if edit_id else None
    
    if edit_id:
        st.title("Edit Vignette")
    else:
        st.title("New Vignette")
    
    with st.form("vignette_form"):
        theme = st.text_input("Theme", value=vignette["theme"] if vignette else "")
        title = st.text_input("Title", value=vignette["title"] if vignette else "")
        content = st.text_area("Story", value=vignette["content"] if vignette else "", height=300)
        
        col1, col2 = st.columns(2)
        
        if edit_id:
            with col1:
                saved = st.form_submit_button("Save")
            with col2:
                cancelled = st.form_submit_button("Cancel")
            
            if saved and title and content:
                st.session_state.vm.update(edit_id, title, content, theme)
                st.success("Saved!")
                st.session_state.show_vignette_modal = False
                st.session_state.editing_vignette_id = None
                st.rerun()
            
            if cancelled:
                st.session_state.show_vignette_modal = False
                st.session_state.editing_vignette_id = None
                st.rerun()
        else:
            with col1:
                published = st.form_submit_button("Publish")
            with col2:
                drafted = st.form_submit_button("Save Draft")
            
            if published and title and content:
                st.session_state.vm.create(title, content, theme, is_draft=False)
                st.success("Published!")
                st.session_state.show_vignette_modal = False
                st.rerun()
            
            if drafted and content:
                title = title if title else "Draft"
                st.session_state.vm.create(title, content, theme, is_draft=True)
                st.success("Draft saved!")
                st.session_state.show_vignette_modal = False
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_vignette_manager():
    if 'vm' not in st.session_state:
        st.session_state.vm = VignetteManager(st.session_state.user_id)
    
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    
    if st.button("Back"):
        st.session_state.show_vignette_manager = False
        st.rerun()
    
    st.title("Your Vignettes")
    
    filter = st.radio("Show", ["All", "Published", "Drafts"], horizontal=True)
    
    vignettes = st.session_state.vm.get_all()
    
    if filter == "Published":
        vignettes = [v for v in vignettes if v.get("is_published")]
    elif filter == "Drafts":
        vignettes = [v for v in vignettes if v.get("is_draft")]
    
    if not vignettes:
        st.info("No vignettes yet.")
    else:
        for v in vignettes:
            st.markdown(f"### {v['title']}")
            st.markdown(f"*{v['theme']}*")
            st.markdown(v['content'][:200] + "..." if len(v['content']) > 200 else v['content'])
            st.markdown(f"📝 {v['word_count']} words")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Read", key=f"read_{v['id']}"):
                    st.session_state.selected_vignette_id = v['id']
                    st.session_state.show_vignette_detail = True
                    st.session_state.show_vignette_manager = False
                    st.rerun()
            with col2:
                if st.button("Edit", key=f"edit_{v['id']}"):
                    st.session_state.editing_vignette_id = v['id']
                    st.session_state.show_vignette_modal = True
                    st.session_state.show_vignette_manager = False
                    st.rerun()
            with col3:
                if st.button("Delete", key=f"delete_{v['id']}"):
                    st.session_state.vm.delete(v['id'])
                    st.rerun()
            st.divider()
    
    if st.button("+ New Vignette"):
        st.session_state.show_vignette_manager = False
        st.session_state.show_vignette_modal = True
        st.session_state.editing_vignette_id = None
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_vignette_detail():
    if 'vm' not in st.session_state:
        st.session_state.vm = VignetteManager(st.session_state.user_id)
    
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    
    if st.button("Back"):
        st.session_state.show_vignette_detail = False
        st.session_state.selected_vignette_id = None
        st.rerun()
    
    v = st.session_state.vm.get(st.session_state.selected_vignette_id)
    
    if not v:
        st.error("Not found")
        st.session_state.show_vignette_detail = False
        st.rerun()
    
    st.title(v['title'])
    st.markdown(f"**Theme:** {v['theme']}")
    st.markdown(f"**Words:** {v['word_count']}")
    st.markdown("---")
    st.write(v['content'])
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Edit"):
            st.session_state.editing_vignette_id = v['id']
            st.session_state.show_vignette_detail = False
            st.session_state.show_vignette_modal = True
            st.rerun()
    with col2:
        if st.button("Delete"):
            st.session_state.vm.delete(v['id'])
            st.session_state.show_vignette_detail = False
            st.rerun()
    
    if v.get('is_draft'):
        if st.button("Publish"):
            v['is_draft'] = False
            v['is_published'] = True
            v['published_at'] = datetime.now().isoformat()
            st.session_state.vm._save()
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
