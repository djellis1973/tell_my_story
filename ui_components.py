# ui_components.py
import streamlit as st
from datetime import datetime

class UIComponents:
    def __init__(self, vignette_manager=None):
        self.vignette_manager = vignette_manager
    
    def show_vignette_modal(self, user_id, on_publish_callback=None, on_add_to_session_callback=None):
        """Display the vignette creation modal"""
        if not self.vignette_manager:
            st.error("Vignette module not available")
            st.session_state.show_vignette_modal = False
            return
        
        st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
        
        if st.button("← Back", key="vignette_modal_back"):
            st.session_state.show_vignette_modal = False
            if 'editing_vignette_id' in st.session_state:
                st.session_state.pop('editing_vignette_id')
            st.rerun()
        
        if 'published_vignette' not in st.session_state:
            st.session_state.published_vignette = None
        
        def on_publish(vignette):
            st.session_state.published_vignette = vignette
            st.success(f"Vignette '{vignette['title']}' published!")
            if on_publish_callback:
                on_publish_callback(vignette)
            st.rerun()
        
        self.vignette_manager.display_vignette_creator(on_publish=on_publish)
        
        if st.session_state.published_vignette:
            vignette = st.session_state.published_vignette
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📚 Add to Session", key="add_to_session_after", use_container_width=True):
                    st.session_state.selected_vignette_for_session = vignette
                    st.session_state.show_vignette_modal = False
                    st.session_state.published_vignette = None
                    if on_add_to_session_callback:
                        on_add_to_session_callback(vignette)
                    st.rerun()
            
            with col2:
                if st.button("📖 View All Vignettes", key="view_all_after", use_container_width=True):
                    st.session_state.show_vignette_modal = False
                    st.session_state.show_vignette_manager = True
                    st.session_state.published_vignette = None
                    st.rerun()
            
            with col3:
                if st.button("✏️ Keep Writing", key="keep_writing", use_container_width=True):
                    st.session_state.show_vignette_modal = False
                    st.session_state.published_vignette = None
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def show_vignette_manager(self, user_id, on_select_callback=None):
        """Display the vignette manager modal"""
        if not self.vignette_manager:
            st.error("Vignette module not available")
            st.session_state.show_vignette_manager = False
            return
        
        st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
        
        if st.button("← Back", key="vignette_manager_back"):
            st.session_state.show_vignette_manager = False
            st.rerun()
        
        st.title("📚 Your Vignettes")
        
        filter_option = st.radio(
            "Show:",
            ["All Stories", "Published", "Drafts", "Most Popular"],
            horizontal=True,
            key="vignette_filter"
        )
        
        def on_vignette_select(vignette_id):
            st.session_state.show_vignette_detail = True
            st.session_state.selected_vignette_id = vignette_id
            if on_select_callback:
                on_select_callback(vignette_id)
            st.rerun()
        
        filter_map = {
            "All Stories": "all",
            "Published": "published",
            "Drafts": "drafts",
            "Most Popular": "popular"
        }
        
        self.vignette_manager.display_vignette_gallery(
            filter_by=filter_map.get(filter_option, "all"),
            on_select=on_vignette_select
        )
        
        st.divider()
        if st.button("➕ Create New Vignette", type="primary", use_container_width=True):
            st.session_state.show_vignette_manager = False
            st.session_state.show_vignette_modal = True
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def show_vignette_detail(self, user_id, on_add_to_session_callback=None, on_edit_callback=None):
        """Display the vignette detail modal"""
        if not self.vignette_manager or not st.session_state.get('selected_vignette_id'):
            st.session_state.show_vignette_detail = False
            return
        
        st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
        
        if st.button("← Back", key="vignette_detail_back"):
            st.session_state.show_vignette_detail = False
            st.rerun()
        
        vignette = self.vignette_manager.get_vignette_by_id(st.session_state.selected_vignette_id)
        
        if not vignette:
            st.error("Vignette not found")
            st.session_state.show_vignette_detail = False
            return
        
        st.title(vignette['title'])
        st.caption(f"Theme: {vignette.get('theme', 'Uncategorized')}")
        
        if vignette.get('tags'):
            tags = " ".join([f"`{tag}`" for tag in vignette.get('tags', [])])
            st.caption(f"Tags: {tags}")
        
        st.divider()
        st.write(vignette['content'])
        st.divider()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Words", vignette.get('word_count', 0))
        with col2:
            st.metric("Views", vignette.get('views', 0))
        with col3:
            st.metric("Likes", vignette.get('likes', 0))
        with col4:
            if vignette.get('is_draft'):
                if st.button("🚀 Publish", use_container_width=True, type="primary"):
                    if self.vignette_manager.publish_vignette(vignette['id']):
                        st.success("Published!")
                        st.rerun()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📚 Add to Session", type="primary", use_container_width=True):
                st.session_state.selected_vignette_for_session = vignette
                st.session_state.show_vignette_detail = False
                if on_add_to_session_callback:
                    on_add_to_session_callback(vignette)
                st.rerun()
        
        with col2:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state.editing_vignette_id = vignette['id']
                st.session_state.show_vignette_detail = False
                st.session_state.show_vignette_modal = True
                if on_edit_callback:
                    on_edit_callback(vignette['id'])
                st.rerun()
        
        with col3:
            if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                st.warning("Delete functionality to be implemented")
        
        st.markdown('</div>', unsafe_allow_html=True)
