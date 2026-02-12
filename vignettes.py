# app.py - THIS IS WHAT YOU NEED
import streamlit as st
from vignettes import VignetteManager

# Initialize session state
if 'vignette_manager' not in st.session_state:
    st.session_state.vignette_manager = VignetteManager("user123")
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'gallery'
if 'filter_by' not in st.session_state:
    st.session_state.filter_by = 'all'

# Callback functions - THESE MAKE EVERYTHING WORK
def on_select_vignette(vignette_id):
    st.session_state.current_vignette = vignette_id
    st.session_state.view_mode = 'read'

def on_edit_vignette(vignette_id):
    st.session_state.current_vignette = vignette_id
    st.session_state.view_mode = 'edit'

def on_delete_vignette(vignette_id):
    st.session_state.vignette_manager.delete_vignette(vignette_id)
    st.session_state.view_mode = 'gallery'
    st.rerun()

def on_publish_vignette(vignette):
    st.session_state.view_mode = 'gallery'
    st.session_state.filter_by = 'published'
    st.rerun()

def on_back_to_gallery():
    st.session_state.view_mode = 'gallery'
    st.rerun()

# Main app layout
st.title("📚 Your Vignettes")

# Filter tabs - NO Most Popular
tab1, tab2, tab3 = st.tabs(["All Stories", "Published", "Drafts"])

with tab1:
    st.session_state.filter_by = 'all'
with tab2:
    st.session_state.filter_by = 'published'
with tab3:
    st.session_state.filter_by = 'drafts'

# Sidebar for creating new vignettes
with st.sidebar:
    st.header("Create New")
    if st.button("+ New Vignette", use_container_width=True):
        st.session_state.view_mode = 'create'
        st.rerun()

# Main content area based on view mode
if st.session_state.view_mode == 'create':
    st.session_state.vignette_manager.display_vignette_creator(
        on_publish=on_publish_vignette
    )
    
elif st.session_state.view_mode == 'edit':
    vignette = st.session_state.vignette_manager.get_vignette_by_id(
        st.session_state.current_vignette
    )
    if vignette:
        st.session_state.vignette_manager.display_vignette_creator(
            edit_vignette=vignette,
            on_publish=on_publish_vignette
        )
    else:
        st.session_state.view_mode = 'gallery'
        st.rerun()
        
elif st.session_state.view_mode == 'read':
    st.session_state.vignette_manager.display_full_vignette(
        st.session_state.current_vignette,
        on_back=on_back_to_gallery,
        on_edit=on_edit_vignette
    )
    
else:  # gallery view
    st.session_state.vignette_manager.display_vignette_gallery(
        filter_by=st.session_state.filter_by,
        on_select=on_select_vignette,
        on_edit=on_edit_vignette,
        on_delete=on_delete_vignette
    )
