def display_vignette_creator(self, on_publish=None, edit_vignette=None):
    """Display vignette creation/editing interface - COMPLETELY REMOVED TAGS"""
    if edit_vignette:
        st.subheader("✏️ Edit Vignette")
    else:
        st.subheader("✍️ Create New Vignette")
    
    # Pre-populate form if editing
    initial_title = edit_vignette.get("title", "") if edit_vignette else ""
    initial_content = edit_vignette.get("content", "") if edit_vignette else ""
    initial_theme = edit_vignette.get("theme", "") if edit_vignette else ""
    
    with st.form(key=f"vignette_form_{uuid.uuid4()}"):  # UNIQUE KEY to avoid duplicates
        # Theme selection
        theme_options = self.standard_themes + ["Custom Theme"]
        
        theme_index = 0
        if initial_theme in self.standard_themes:
            theme_index = self.standard_themes.index(initial_theme)
        elif initial_theme:
            theme_index = len(self.standard_themes)
        
        selected_theme = st.selectbox("Theme", theme_options, index=theme_index, key=f"theme_select_{uuid.uuid4()}")
        
        if selected_theme == "Custom Theme":
            custom_theme = st.text_input("Custom Theme", 
                                       value=initial_theme if initial_theme and initial_theme not in self.standard_themes else "",
                                       key=f"custom_theme_{uuid.uuid4()}")
            theme = custom_theme if custom_theme.strip() else "Personal Story"
        else:
            theme = selected_theme
        
        # Title
        title = st.text_input("Title", value=initial_title, key=f"title_input_{uuid.uuid4()}")
        
        # Content
        content = st.text_area("Story", value=initial_content, height=300, key=f"content_area_{uuid.uuid4()}")
        
        # Word count
        if content:
            st.caption(f"Words: {len(content.split())}")
        
        # NO TAGS FIELD - COMPLETELY REMOVED
        
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
                title_to_use = title if title.strip() else f"Draft"
                vignette = self.create_vignette(title_to_use, content, theme, is_draft=True)
                st.success("💾 Draft saved!")
                st.rerun()
                return True
        
        return False
