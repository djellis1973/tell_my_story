import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Optional
import os
import uuid

class VignetteManager:
    """Manages vignettes (short stories)"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.vignettes_file = f"user_vignettes/{user_id}_vignettes.json"
        self.published_file = f"published_vignettes/{user_id}_published.json"
        self._ensure_directories()
        self._load_vignettes()
        self._load_published()
        
        # Standard vignette themes
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
    
    def _ensure_directories(self):
        """Create necessary directories"""
        os.makedirs("user_vignettes", exist_ok=True)
        os.makedirs("published_vignettes", exist_ok=True)
    
    def _load_vignettes(self):
        """Load vignettes from file"""
        try:
            if os.path.exists(self.vignettes_file):
                with open(self.vignettes_file, 'r') as f:
                    self.vignettes = json.load(f)
            else:
                self.vignettes = []
        except Exception as e:
            print(f"Error loading vignettes: {e}")
            self.vignettes = []
    
    def _save_vignettes(self):
        """Save vignettes to file"""
        try:
            with open(self.vignettes_file, 'w') as f:
                json.dump(self.vignettes, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving vignettes: {e}")
            return False
    
    def _load_published(self):
        """Load published vignettes"""
        try:
            if os.path.exists(self.published_file):
                with open(self.published_file, 'r') as f:
                    self.published = json.load(f)
            else:
                self.published = []
        except Exception as e:
            print(f"Error loading published vignettes: {e}")
            self.published = []
    
    def _save_published(self):
        """Save published vignettes"""
        try:
            with open(self.published_file, 'w') as f:
                json.dump(self.published, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving published: {e}")
            return False
    
    def create_vignette(self, title: str, content: str, theme: str, 
                       is_draft: bool = False) -> Dict:
        """Create a new vignette - REMOVED tags parameter"""
        vignette_id = str(uuid.uuid4())[:8]
        
        new_vignette = {
            "id": vignette_id,
            "title": title,
            "content": content,
            "theme": theme,
            "word_count": len(content.split()),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_draft": is_draft,
            "is_published": False,
            "views": 0,
            "likes": 0
        }
        
        self.vignettes.append(new_vignette)
        self._save_vignettes()
        return new_vignette
    
    def update_vignette(self, vignette_id: str, title: str, content: str, theme: str) -> bool:
        """Update an existing vignette - REMOVED tags parameter"""
        for vignette in self.vignettes:
            if vignette["id"] == vignette_id:
                vignette["title"] = title
                vignette["content"] = content
                vignette["theme"] = theme
                vignette["word_count"] = len(content.split())
                vignette["updated_at"] = datetime.now().isoformat()
                
                self._save_vignettes()
                
                # Also update in published if it exists there
                for pub in self.published:
                    if pub["id"] == vignette_id:
                        pub.update(vignette)
                        self._save_published()
                        break
                return True
        return False
    
    def delete_vignette(self, vignette_id: str) -> bool:
        """Delete a vignette - FIXED: Now actually works"""
        # Remove from vignettes
        self.vignettes = [v for v in self.vignettes if v["id"] != vignette_id]
        
        # Remove from published if exists
        self.published = [v for v in self.published if v["id"] != vignette_id]
        
        self._save_vignettes()
        self._save_published()
        return True
    
    def publish_vignette(self, vignette_id: str) -> bool:
        """Publish a vignette - FIXED: Now actually works"""
        for vignette in self.vignettes:
            if vignette["id"] == vignette_id:
                vignette["is_published"] = True
                vignette["is_draft"] = False
                vignette["published_at"] = datetime.now().isoformat()
                
                # Add to published list
                published_copy = vignette.copy()
                self.published.append(published_copy)
                
                self._save_vignettes()
                self._save_published()
                return True
        return False
    
    def get_vignette_by_id(self, vignette_id: str) -> Optional[Dict]:
        """Get a vignette by ID"""
        for vignette in self.vignettes:
            if vignette["id"] == vignette_id:
                return vignette
        return None
    
    def get_all_vignettes(self, include_drafts: bool = False) -> List[Dict]:
        """Get all vignettes"""
        if include_drafts:
            return self.vignettes
        return [v for v in self.vignettes if not v["is_draft"]]
    
    def get_published_vignettes(self) -> List[Dict]:
        """Get published vignettes"""
        return self.published
    
    def display_vignette_creator(self, on_publish=None, edit_vignette=None):
        """Display vignette creation/editing interface - NO TAGS, NO EXTRA FEATURES"""
        if edit_vignette:
            st.subheader("✏️ Edit Vignette")
        else:
            st.subheader("✍️ Create New Vignette")
        
        # Pre-populate form if editing
        initial_title = edit_vignette.get("title", "") if edit_vignette else ""
        initial_content = edit_vignette.get("content", "") if edit_vignette else ""
        initial_theme = edit_vignette.get("theme", "") if edit_vignette else ""
        
        with st.form("create_vignette_form"):
            # Theme selection - SIMPLIFIED
            theme_options = self.standard_themes + ["Custom Theme"]
            
            theme_index = 0
            if initial_theme in self.standard_themes:
                theme_index = self.standard_themes.index(initial_theme)
            elif initial_theme:
                theme_index = len(self.standard_themes)
            
            selected_theme = st.selectbox("Theme", theme_options, index=theme_index)
            
            if selected_theme == "Custom Theme":
                custom_theme = st.text_input("Custom Theme", 
                                           value=initial_theme if initial_theme and initial_theme not in self.standard_themes else "")
                theme = custom_theme if custom_theme.strip() else "Personal Story"
            else:
                theme = selected_theme
            
            # Title
            title = st.text_input("Title", value=initial_title)
            
            # Content
            content = st.text_area("Story", value=initial_content, height=200)
            
            # Word count
            if content:
                st.caption(f"Words: {len(content.split())}")
            
            # Buttons
            col1, col2 = st.columns(2)
            
            if edit_vignette:
                with col1:
                    save_button = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
                with col2:
                    cancel_button = st.form_submit_button("Cancel", use_container_width=True)
                
                if save_button and title.strip() and content.strip():
                    self.update_vignette(edit_vignette["id"], title, content, theme)
                    st.success("✅ Saved!")
                    st.rerun()
                    return True
                
                if cancel_button:
                    st.rerun()
                    return False
            else:
                with col1:
                    publish_button = st.form_submit_button("🚀 Publish", type="primary", use_container_width=True)
                with col2:
                    draft_button = st.form_submit_button("💾 Draft", use_container_width=True)
                
                if publish_button and title.strip() and content.strip():
                    vignette = self.create_vignette(title, content, theme, is_draft=False)
                    self.publish_vignette(vignette["id"])
                    if on_publish:
                        on_publish(vignette)
                    st.success("🎉 Published!")
                    st.rerun()
                    return True
                
                if draft_button and content.strip():
                    title_to_use = title if title.strip() else f"Draft: {theme}"
                    vignette = self.create_vignette(title_to_use, content, theme, is_draft=True)
                    st.success("💾 Draft saved!")
                    st.rerun()
                    return True
            
            return False
    
    def display_vignette_gallery(self, filter_by: str = "all", on_select=None, on_edit=None, on_delete=None):
        """Display vignettes - NO Most Popular, NO Tags, NO Views/Likes display"""
        
        # Filter options - REMOVED "Most Popular"
        if filter_by == "published":
            vignettes_to_show = [v for v in self.vignettes if v.get("is_published", False)]
        elif filter_by == "drafts":
            vignettes_to_show = [v for v in self.vignettes if v.get("is_draft", False)]
        else:
            vignettes_to_show = self.vignettes
        
        if not vignettes_to_show:
            if filter_by == "published":
                st.info("No published stories yet.")
            elif filter_by == "drafts":
                st.info("No drafts yet.")
            else:
                st.info("No stories yet. Create your first one!")
            return
        
        # Display in simple grid
        for i in range(0, len(vignettes_to_show), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(vignettes_to_show):
                    vignette = vignettes_to_show[i + j]
                    with cols[j]:
                        self._display_vignette_card(vignette, on_select, on_edit, on_delete)
    
    def _display_vignette_card(self, vignette: Dict, on_select=None, on_edit=None, on_delete=None):
        """Display a single vignette card - SIMPLE, NO Views/Likes display"""
        with st.container():
            st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:5px; padding:10px; margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between;">
                    <h4 style="margin:0;">{vignette['title']}</h4>
                    <span style="background:{'#4CAF50' if vignette.get('is_published') else '#FF9800'}; 
                         color:white; padding:2px 8px; border-radius:10px; font-size:12px;">
                        {'Published' if vignette.get('is_published') else 'Draft'}
                    </span>
                </div>
                <div style="background:#E8F5E9; color:#2E7D32; padding:2px 8px; border-radius:10px; 
                     display:inline-block; font-size:12px; margin:5px 0;">
                    {vignette['theme']}
                </div>
                <p>{vignette['content'][:100]}{'...' if len(vignette['content']) > 100 else ''}</p>
                <p style="color:#666; font-size:12px;">📝 {vignette['word_count']} words</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Read", key=f"read_{vignette['id']}", use_container_width=True):
                    if on_select:
                        on_select(vignette['id'])
            
            with col2:
                if st.button("Edit", key=f"edit_{vignette['id']}", use_container_width=True):
                    if on_edit:
                        on_edit(vignette['id'])
            
            with col3:
                if st.button("Delete", key=f"delete_{vignette['id']}", use_container_width=True):
                    if on_delete:
                        on_delete(vignette['id'])
    
    def display_full_vignette(self, vignette_id: str, on_back=None, on_edit=None):
        """Display a full vignette for reading"""
        vignette = self.get_vignette_by_id(vignette_id)
        
        if not vignette:
            st.error("Vignette not found")
            return
        
        # Back button
        if st.button("← Back"):
            if on_back:
                on_back()
        
        # Title
        st.title(vignette['title'])
        
        # Metadata
        st.caption(f"Theme: {vignette['theme']} | Words: {vignette['word_count']}")
        
        # Content
        st.markdown("---")
        st.write(vignette['content'])
        st.markdown("---")
        
        # Actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Edit", use_container_width=True):
                if on_edit:
                    on_edit(vignette_id)
        with col2:
            if st.button("📋 Gallery", use_container_width=True):
                if on_back:
                    on_back()
