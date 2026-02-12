import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Optional
import os
import uuid

class VignetteManager:
    """Manages vignettes (short stories) - Authoring Tool"""
    
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
                       tags: List[str] = None, is_draft: bool = False) -> Dict:
        """Create a new vignette"""
        if tags is None:
            tags = []
        
        vignette_id = str(uuid.uuid4())[:8]
        
        new_vignette = {
            "id": vignette_id,
            "title": title,
            "content": content,
            "theme": theme,
            "tags": tags,
            "word_count": len(content.split()),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_draft": is_draft,
            "is_published": False
        }
        
        self.vignettes.append(new_vignette)
        self._save_vignettes()
        return new_vignette
    
    def update_vignette(self, vignette_id: str, title: str, content: str, 
                       theme: str, tags: List[str] = None) -> bool:
        """Update an existing vignette"""
        if tags is None:
            tags = []
            
        for vignette in self.vignettes:
            if vignette["id"] == vignette_id:
                vignette["title"] = title
                vignette["content"] = content
                vignette["theme"] = theme
                vignette["tags"] = tags
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
        """Delete a vignette"""
        # Remove from vignettes
        self.vignettes = [v for v in self.vignettes if v["id"] != vignette_id]
        
        # Remove from published if exists
        self.published = [v for v in self.published if v["id"] != vignette_id]
        
        self._save_vignettes()
        self._save_published()
        return True
    
    def publish_vignette(self, vignette_id: str) -> bool:
        """Publish a vignette"""
        for vignette in self.vignettes:
            if vignette["id"] == vignette_id:
                vignette["is_published"] = True
                vignette["is_draft"] = False
                vignette["published_at"] = datetime.now().isoformat()
                
                # Check if already in published list
                found = False
                for i, pub in enumerate(self.published):
                    if pub["id"] == vignette_id:
                        self.published[i] = vignette.copy()
                        found = True
                        break
                
                if not found:
                    self.published.append(vignette.copy())
                
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
    
    def get_vignettes_by_theme(self, theme: str) -> List[Dict]:
        """Get vignettes by theme"""
        return [v for v in self.vignettes 
                if v["theme"].lower() == theme.lower() and not v["is_draft"]]
    
    def search_vignettes(self, query: str) -> List[Dict]:
        """Search vignettes by title or content"""
        results = []
        query_lower = query.lower()
        
        for vignette in self.vignettes:
            if (query_lower in vignette["title"].lower() or 
                query_lower in vignette["content"].lower() or
                any(query_lower in tag.lower() for tag in vignette.get("tags", []))):
                results.append(vignette)
        
        return results
    
    def display_vignette_creator(self, on_publish=None, on_save_draft=None, edit_vignette=None):
        """Display vignette creation/editing interface"""
        st.subheader("✍️ " + ("Edit Story" if edit_vignette else "Write a Short Story"))
        
        # Pre-populate form if editing
        initial_title = edit_vignette.get("title", "") if edit_vignette else ""
        initial_content = edit_vignette.get("content", "") if edit_vignette else ""
        initial_theme = edit_vignette.get("theme", "") if edit_vignette else ""
        initial_tags = ", ".join(edit_vignette.get("tags", [])) if edit_vignette else ""
        
        with st.form("create_vignette_form"):
            # Theme selection
            theme_options = self.standard_themes + ["Custom Theme"]
            
            # Set initial theme index
            theme_index = 0
            if initial_theme in self.standard_themes:
                theme_index = self.standard_themes.index(initial_theme)
            elif initial_theme:
                theme_index = len(self.standard_themes)  # Custom Theme
            
            selected_theme = st.selectbox("Choose a Theme", theme_options, index=theme_index)
            
            if selected_theme == "Custom Theme":
                custom_theme = st.text_input("Your Custom Theme", 
                                           value=initial_theme if initial_theme and initial_theme not in self.standard_themes else "")
                theme = custom_theme if custom_theme.strip() else "Personal Story"
            else:
                theme = selected_theme
            
            # Title
            title = st.text_input("Title", 
                                value=initial_title,
                                placeholder="Give your story a compelling title")
            
            # Content
            content = st.text_area("Your Story", 
                                 value=initial_content,
                                 height=300,
                                 placeholder="Write your short story here...\n\nTip: Focus on a single moment or experience. Be descriptive and emotional.")
            
            # Tags
            tags_input = st.text_input("Tags (comma-separated)",
                                     value=initial_tags,
                                     placeholder="e.g., family, travel, achievement")
            
            # Word count display
            if content:
                word_count = len(content.split())
                st.caption(f"📝 {word_count} words")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if edit_vignette:
                    save_button = st.form_submit_button("💾 Save Changes", 
                                                       type="primary",
                                                       use_container_width=True)
                else:
                    publish_button = st.form_submit_button("🚀 Publish Now", 
                                                         type="primary",
                                                         use_container_width=True)
            with col2:
                if edit_vignette:
                    cancel_button = st.form_submit_button("Cancel",
                                                        type="secondary",
                                                        use_container_width=True)
                else:
                    draft_button = st.form_submit_button("💾 Save as Draft",
                                                       use_container_width=True)
            with col3:
                cancel_button = st.form_submit_button("Cancel",
                                                    type="secondary",
                                                    use_container_width=True)
            
            # Handle form submission
            if not edit_vignette:
                if publish_button and content.strip() and title.strip():
                    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                    vignette = self.create_vignette(title, content, theme, tags, is_draft=False)
                    self.publish_vignette(vignette["id"])
                    
                    if on_publish:
                        on_publish(vignette)
                    
                    st.success("🎉 Published! Your story is now live.")
                    st.balloons()
                    return True
                
                elif draft_button and content.strip():
                    title_to_use = title if title.strip() else f"Draft: {theme}"
                    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                    vignette = self.create_vignette(title_to_use, content, theme, tags, is_draft=True)
                    
                    if on_save_draft:
                        on_save_draft(vignette)
                    
                    st.success("💾 Saved as draft!")
                    return True
                
                elif cancel_button:
                    st.rerun()
            
            else:  # Editing mode
                if save_button and content.strip() and title.strip():
                    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                    self.update_vignette(edit_vignette["id"], title, content, theme, tags)
                    
                    # Auto-publish if it was published before
                    if edit_vignette.get("is_published", False):
                        self.publish_vignette(edit_vignette["id"])
                    
                    st.success("✅ Changes saved successfully!")
                    return True
                
                elif cancel_button:
                    st.rerun()
            
            return False
    
    def display_vignette_gallery(self, filter_by: str = "all", on_select=None, on_edit=None, on_delete=None):
        """Display vignettes in a gallery - NO social features, NO Most Popular"""
        
        # Filter options - NO "Most Popular"
        filter_options = {
            "all": "All Stories",
            "published": "Published",
            "drafts": "Drafts"
        }
        
        # Filter vignettes
        if filter_by == "published":
            vignettes_to_show = [v for v in self.vignettes if v.get("is_published", False)]
        elif filter_by == "drafts":
            vignettes_to_show = [v for v in self.vignettes if v.get("is_draft", False)]
        else:
            vignettes_to_show = self.vignettes
        
        if not vignettes_to_show:
            filter_name = filter_options.get(filter_by, "stories")
            st.info(f"No {filter_name.lower()} yet. Create your first story!")
            return
        
        # Display in grid
        cols = st.columns(2)
        
        for i, vignette in enumerate(vignettes_to_show):
            col_idx = i % 2
            with cols[col_idx]:
                self._display_vignette_card(vignette, on_select, on_edit, on_delete)
    
    def _display_vignette_card(self, vignette: Dict, on_select=None, on_edit=None, on_delete=None):
        """Display a single vignette card - NO views, NO likes"""
        with st.container():
            # Card container
            st.markdown(f"""
            <div style="
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 1rem;
                margin-bottom: 1rem;
                background-color: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            ">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #333;">{vignette['title']}</h4>
                    {self._get_status_badge(vignette)}
                </div>
            """, unsafe_allow_html=True)
            
            # Theme badge
            st.markdown(f"""
            <div style="
                background-color: #E8F5E9;
                color: #2E7D32;
                padding: 0.2rem 0.5rem;
                border-radius: 10px;
                font-size: 0.8rem;
                display: inline-block;
                margin-bottom: 0.5rem;
            ">
                {vignette['theme']}
            </div>
            """, unsafe_allow_html=True)
            
            # Preview (first 100 chars)
            preview = vignette['content'][:100] + "..." if len(vignette['content']) > 100 else vignette['content']
            st.write(preview)
            
            # Stats - ONLY word count (NO views, NO likes)
            st.caption(f"📝 {vignette['word_count']} words")
            
            # Last updated
            updated_date = datetime.fromisoformat(vignette.get('updated_at', vignette['created_at']))
            st.caption(f"🕒 Updated: {updated_date.strftime('%b %d, %Y')}")
            
            # Action buttons - ONLY authoring tools (NO Like button)
            button_cols = st.columns(3)
            
            with button_cols[0]:
                if st.button("📖 Read", key=f"read_{vignette['id']}", 
                           use_container_width=True):
                    if on_select:
                        on_select(vignette['id'])
            
            with button_cols[1]:
                if st.button("✏️ Edit", key=f"edit_{vignette['id']}", 
                           use_container_width=True):
                    if on_edit:
                        on_edit(vignette['id'])
            
            with button_cols[2]:
                if st.button("🗑️ Delete", key=f"delete_{vignette['id']}", 
                           use_container_width=True, type="secondary"):
                    if on_delete:
                        on_delete(vignette['id'])
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def _get_status_badge(self, vignette: Dict) -> str:
        """Get HTML badge for vignette status"""
        if vignette.get("is_published"):
            return """
            <span style="
                background-color: #4CAF50;
                color: white;
                padding: 0.2rem 0.5rem;
                border-radius: 12px;
                font-size: 0.7rem;
            ">
                Published
            </span>
            """
        elif vignette.get("is_draft"):
            return """
            <span style="
                background-color: #FF9800;
                color: white;
                padding: 0.2rem 0.5rem;
                border-radius: 12px;
                font-size: 0.7rem;
            ">
                Draft
            </span>
            """
        return ""
    
    def display_full_vignette(self, vignette_id: str, on_back=None, on_edit=None):
        """Display a full vignette for reading - NO social features"""
        vignette = self.get_vignette_by_id(vignette_id)
        
        if not vignette:
            st.error("Vignette not found")
            return
        
        # Back button
        col1, col2 = st.columns([1, 11])
        with col1:
            if st.button("←"):
                if on_back:
                    on_back()
        
        with col2:
            st.title(vignette["title"])
        
        # Metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"Theme: {vignette['theme']}")
        with col2:
            if vignette.get("is_published"):
                published_date = datetime.fromisoformat(vignette.get('published_at', vignette['created_at']))
                st.caption(f"Published: {published_date.strftime('%b %d, %Y')}")
            else:
                created_date = datetime.fromisoformat(vignette['created_at'])
                st.caption(f"Created: {created_date.strftime('%b %d, %Y')}")
        with col3:
            st.caption(f"Words: {vignette['word_count']}")
        
        # Tags
        if vignette.get("tags"):
            tags_html = " ".join([f'<span style="background-color: #f0f2f6; padding: 0.2rem 0.5rem; border-radius: 10px; margin-right: 0.5rem;">{tag}</span>' for tag in vignette["tags"]])
            st.markdown(f"<div style='margin-bottom: 1rem;'>{tags_html}</div>", unsafe_allow_html=True)
        
        # Content
        st.markdown("---")
        st.markdown(vignette["content"])
        st.markdown("---")
        
        # Authoring actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Edit this story", use_container_width=True):
                if on_edit:
                    on_edit(vignette_id)
        with col2:
            if st.button("📋 Back to Gallery", use_container_width=True):
                if on_back:
                    on_back()
