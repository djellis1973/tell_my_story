# biography_publisher.py
import streamlit as st
from datetime import datetime
import io
import base64
import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ============================================================================
# PUBLISHER INTEGRATION WITH MAIN APP
# ============================================================================

def integrate_with_main_app():
    """Check if running within main app and get session data"""
    try:
        # Check if we're in the main app context
        if 'st' in globals() and hasattr(st, 'session_state'):
            # Try to get sessions from main app
            if 'current_question_bank' in st.session_state:
                return st.session_state.current_question_bank
            elif 'SESSIONS' in st.session_state:
                return st.session_state.SESSIONS
    except:
        pass
    return None

# Get sessions from main app if available
MAIN_APP_SESSIONS = integrate_with_main_app()

# ============================================================================
# HELPER FUNCTIONS FOR PUBLISHER
# ============================================================================

def prepare_stories_for_publishing(responses_data, sessions_data=None):
    """Convert response data to format needed for publishing"""
    stories = []
    
    if sessions_data is None:
        sessions_data = MAIN_APP_SESSIONS or []
    
    for session in sessions_data:
        session_id = session["id"]
        session_data = responses_data.get(str(session_id), {})
        session_data = responses_data.get(session_id, session_data)
        
        for question_text, answer_data in session_data.get("questions", {}).items():
            # Get images if available
            images = []
            if answer_data.get("images"):
                for img_ref in answer_data.get("images", []):
                    img_id = img_ref.get("id")
                    # Try to get image from main app's image handler
                    b64 = None
                    if st.session_state.get('image_handler'):
                        b64 = st.session_state.image_handler.get_image_base64(img_id)
                    
                    images.append({
                        "id": img_id,
                        "base64": b64,
                        "caption": img_ref.get("caption", "")
                    })
            
            stories.append({
                "question": question_text,
                "answer_text": re.sub(r'<[^>]+>', '', answer_data.get("answer", "")),
                "timestamp": answer_data.get("timestamp", ""),
                "session_id": session_id,
                "session_title": session["title"],
                "has_images": answer_data.get("has_images", False),
                "image_count": answer_data.get("image_count", 0),
                "images": images
            })
    
    return stories

# ============================================================================
# MODIFIED PUBLISHER FUNCTIONS WITH PROPER ERROR HANDLING
# ============================================================================

def show_publisher_interface():
    """Display the publisher interface within the main app"""
    
    st.markdown("## 📚 Publish Your Book")
    st.markdown("---")
    
    # Get data from main app
    if not st.session_state.get('logged_in'):
        st.warning("Please log in to publish your book.")
        return
    
    # Prepare stories
    stories = prepare_stories_for_publishing(
        st.session_state.responses,
        st.session_state.get('current_question_bank', [])
    )
    
    if not stories:
        st.info("No stories yet! Start writing to publish your book.")
        return
    
    # Get user profile info
    profile = st.session_state.user_account.get('profile', {})
    first_name = profile.get('first_name', 'My')
    last_name = profile.get('last_name', '')
    
    # Publishing options
    col1, col2 = st.columns(2)
    
    with col1:
        # Book details
        book_title = st.text_input(
            "Book Title",
            value=f"{first_name}'s Life Story",
            key="publisher_book_title"
        )
        
        author_name = st.text_input(
            "Author Name",
            value=f"{first_name} {last_name}".strip() or "Author Name",
            key="publisher_author_name"
        )
        
        format_style = st.selectbox(
            "Format Style",
            ["interview", "biography", "memoir"],
            format_func=lambda x: {
                "interview": "📝 Interview Q&A",
                "biography": "📖 Continuous Biography",
                "memoir": "📚 Chapter-based Memoir"
            }[x],
            key="publisher_format"
        )
    
    with col2:
        # Cover options
        st.markdown("### Cover Design")
        cover_choice = st.radio(
            "Cover Type",
            ["simple", "uploaded"],
            format_func=lambda x: "🎨 Simple Gradient Cover" if x == "simple" else "📸 Upload Your Own Cover",
            key="publisher_cover_type"
        )
        
        cover_image = None
        if cover_choice == "uploaded":
            uploaded_cover = st.file_uploader(
                "Upload Cover Image",
                type=['jpg', 'jpeg', 'png'],
                key="publisher_cover_upload"
            )
            if uploaded_cover:
                cover_image = uploaded_cover.getvalue()
                st.image(cover_image, caption="Cover Preview", width=200)
        
        # Additional options
        include_toc = st.checkbox("Include Table of Contents", value=True, key="publisher_toc")
        include_images = st.checkbox("Include Images", value=True, key="publisher_images")
    
    st.markdown("---")
    
    # Generate buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Generate DOCX", type="primary", use_container_width=True):
            with st.spinner("Creating Word document..."):
                try:
                    docx_bytes = generate_docx(
                        book_title,
                        author_name,
                        stories,
                        format_style,
                        include_toc,
                        include_images,
                        cover_image,
                        cover_choice
                    )
                    
                    filename = f"{book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.docx"
                    
                    st.download_button(
                        label="📥 Download DOCX",
                        data=docx_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key="docx_download_publisher"
                    )
                    
                    show_celebration()
                except Exception as e:
                    st.error(f"Error generating DOCX: {str(e)}")
    
    with col2:
        if st.button("🌐 Generate HTML", type="primary", use_container_width=True):
            with st.spinner("Creating HTML page..."):
                try:
                    html_content = generate_html(
                        book_title,
                        author_name,
                        stories,
                        format_style,
                        include_toc,
                        include_images,
                        None,  # cover_html_path
                        cover_image,
                        cover_choice
                    )
                    
                    filename = f"{book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html"
                    
                    st.download_button(
                        label="📥 Download HTML",
                        data=html_content,
                        file_name=filename,
                        mime="text/html",
                        use_container_width=True,
                        key="html_download_publisher"
                    )
                    
                    show_celebration()
                except Exception as e:
                    st.error(f"Error generating HTML: {str(e)}")
    
    with col3:
        if st.button("📦 Generate ZIP", type="primary", use_container_width=True):
            with st.spinner("Creating ZIP package..."):
                try:
                    import zipfile
                    import io
                    
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        # Generate HTML
                        html_content = generate_html(
                            book_title,
                            author_name,
                            stories,
                            format_style,
                            include_toc,
                            include_images,
                            None,
                            cover_image,
                            cover_choice
                        )
                        
                        zip_file.writestr(f"{book_title.replace(' ', '_')}.html", html_content)
                        
                        # Add images to zip
                        for story in stories:
                            for img in story.get('images', []):
                                if img.get('base64'):
                                    img_data = base64.b64decode(img['base64'])
                                    img_filename = f"images/{img['id']}.jpg"
                                    zip_file.writestr(img_filename, img_data)
                    
                    filename = f"{book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.zip"
                    
                    st.download_button(
                        label="📥 Download ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=filename,
                        mime="application/zip",
                        use_container_width=True,
                        key="zip_download_publisher"
                    )
                    
                    show_celebration()
                except Exception as e:
                    st.error(f"Error generating ZIP: {str(e)}")
    
    # Statistics
    st.markdown("---")
    st.markdown("### 📊 Book Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Stories", len(stories))
    
    with col2:
        total_words = sum(len(story['answer_text'].split()) for story in stories)
        st.metric("Total Words", f"{total_words:,}")
    
    with col3:
        sessions_count = len(set(story['session_id'] for story in stories))
        st.metric("Sessions", sessions_count)
    
    with col4:
        images_count = sum(story.get('image_count', 0) for story in stories)
        st.metric("Images", images_count)

# ============================================================================
# ADD THIS TO YOUR MAIN biographer.py FILE
# Add this function to integrate the publisher
# ============================================================================

def add_publisher_to_sidebar():
    """Add publisher button to main app sidebar"""
    
    st.sidebar.divider()
    st.sidebar.header("📚 Publishing")
    
    if st.sidebar.button("🎨 Publish Your Book", type="primary", use_container_width=True):
        st.session_state.show_publisher = True
        st.rerun()
    
    # Add stats
    if st.session_state.logged_in:
        total_stories = sum(
            len(st.session_state.responses.get(s["id"], {}).get("questions", {}))
            for s in st.session_state.get('current_question_bank', [])
        )
        
        if total_stories > 0:
            st.sidebar.info(f"📝 {total_stories} stories ready to publish")

def show_celebration():
    """Show a celebration animation when book is generated"""
    st.balloons()
    st.success("🎉 Your book has been generated successfully!")

def generate_docx(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_image=None, cover_choice="simple"):
    """Generate a Word document from stories"""
    doc = Document()
    
    # Set document styling
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    
    # COVER PAGE - Based on user choice
    if cover_choice == "uploaded" and cover_image:
        # Add uploaded image as cover
        try:
            image_stream = io.BytesIO(cover_image)
            doc.add_picture(image_stream, width=Inches(5))
            last_paragraph = doc.paragraphs[-1]
            last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add title and author below image
            doc.add_paragraph()
            title_para = doc.add_paragraph()
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_run = title_para.add_run(title)
            title_run.font.size = Pt(28)
            title_run.font.bold = True
            
            author_para = doc.add_paragraph()
            author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author_run = author_para.add_run(f"by {author}")
            author_run.font.size = Pt(16)
            author_run.font.italic = True
        except Exception as e:
            # Fallback to simple title
            title_para = doc.add_paragraph()
            title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title_run = title_para.add_run(title)
            title_run.font.size = Pt(28)
            title_run.font.bold = True
            
            author_para = doc.add_paragraph()
            author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author_run = author_para.add_run(f"by {author}")
            author_run.font.size = Pt(16)
            author_run.font.italic = True
    else:
        # Simple title cover
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run(title)
        title_run.font.size = Pt(28)
        title_run.font.bold = True
        
        author_para = doc.add_paragraph()
        author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author_run = author_para.add_run(f"by {author}")
        author_run.font.size = Pt(16)
        author_run.font.italic = True
    
    # Add publication info
    doc.add_page_break()
    copyright_para = doc.add_paragraph()
    copyright_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    copyright_para.add_run(f"© {datetime.now().year} {author}. All rights reserved.")
    
    # Table of Contents
    if include_toc:
        doc.add_page_break()
        toc_para = doc.add_paragraph()
        toc_run = toc_para.add_run("Table of Contents")
        toc_run.font.size = Pt(18)
        toc_run.font.bold = True
        
        # Group by session for TOC
        sessions = {}
        for story in stories:
            session_title = story.get('session_title', 'Untitled Session')
            if session_title not in sessions:
                sessions[session_title] = []
            sessions[session_title].append(story)
        
        for session_title in sessions.keys():
            doc.add_paragraph(f"  {session_title}", style='List Bullet')
    
    # Add stories
    doc.add_page_break()
    
    current_session = None
    for story in stories:
        session_title = story.get('session_title', 'Untitled Session')
        
        # Add session header if new session
        if session_title != current_session:
            current_session = session_title
            session_para = doc.add_paragraph()
            session_run = session_para.add_run(session_title)
            session_run.font.size = Pt(16)
            session_run.font.bold = True
        
        if format_style == "interview":
            # Add question
            q_para = doc.add_paragraph()
            q_run = q_para.add_run(story.get('question', ''))
            q_run.font.bold = True
            q_run.font.italic = True
        
        # Add answer
        answer_text = story.get('answer_text', '')
        if answer_text:
            # Split into paragraphs
            paragraphs = answer_text.split('\n')
            for para in paragraphs:
                if para.strip():
                    doc.add_paragraph(para.strip())
        
        # Add images if any
        if include_images and story.get('images'):
            for img in story.get('images', []):
                if img.get('base64'):
                    try:
                        img_data = base64.b64decode(img['base64'])
                        img_stream = io.BytesIO(img_data)
                        doc.add_picture(img_stream, width=Inches(4))
                        last_paragraph = doc.paragraphs[-1]
                        last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        
                        # Add caption
                        if img.get('caption'):
                            caption_para = doc.add_paragraph()
                            caption_run = caption_para.add_run(img['caption'])
                            caption_run.font.size = Pt(10)
                            caption_run.font.italic = True
                            caption_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    except:
                        pass
        
        # Add spacing between stories
        doc.add_paragraph()
    
    # Save to bytes
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    
    return docx_bytes.getvalue()

def generate_html(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_html_path=None, cover_image=None, cover_choice="simple"):
    """Generate an HTML document from stories"""
    
    # Start building HTML
    html_parts = []
    
    # HTML header with styling
    html_parts.append(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: 'Georgia', serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px 20px;
                background: #fff;
            }}
            h1 {{
                font-size: 42px;
                text-align: center;
                margin-bottom: 10px;
                color: #000;
            }}
            h2 {{
                font-size: 28px;
                margin-top: 40px;
                margin-bottom: 20px;
                color: #444;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
            }}
            .author {{
                text-align: center;
                font-size: 18px;
                color: #666;
                margin-bottom: 40px;
                font-style: italic;
            }}
            .question {{
                font-weight: bold;
                font-size: 18px;
                margin-top: 30px;
                margin-bottom: 10px;
                color: #2c3e50;
                border-left: 4px solid #3498db;
                padding-left: 15px;
            }}
            .story-image {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 20px auto;
                border-radius: 5px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .image-caption {{
                text-align: center;
                font-size: 14px;
                color: #666;
                margin-top: -10px;
                margin-bottom: 20px;
                font-style: italic;
            }}
            .cover-page {{
                text-align: center;
                margin-bottom: 50px;
                page-break-after: always;
                min-height: 80vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            .cover-image {{
                max-width: 100%;
                max-height: 70vh;
                object-fit: contain;
                margin: 20px auto;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            .simple-cover {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 60px 20px;
                border-radius: 10px;
                color: white;
                margin: 20px;
            }}
            .simple-cover h1 {{
                color: white;
            }}
            .simple-cover .author {{
                color: rgba(255,255,255,0.9);
            }}
            .copyright {{
                text-align: center;
                font-size: 12px;
                color: #999;
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            .toc {{
                background: #f9f9f9;
                padding: 20px;
                border-radius: 5px;
                margin: 30px 0;
            }}
            .toc ul {{
                list-style-type: none;
                padding-left: 0;
            }}
            .toc li {{
                margin-bottom: 10px;
            }}
            .toc a {{
                color: #3498db;
                text-decoration: none;
            }}
            .toc a:hover {{
                text-decoration: underline;
            }}
            @media print {{
                body {{
                    padding: 0.5in;
                }}
                .cover-page {{
                    page-break-after: always;
                    min-height: auto;
                }}
            }}
        </style>
    </head>
    <body>
    """)
    
    # COVER PAGE - Based on user choice
    html_parts.append('<div class="cover-page">')
    
    if cover_choice == "uploaded" and cover_image:
        # Use uploaded image
        try:
            img_base64 = base64.b64encode(cover_image).decode()
            html_parts.append(f'''
            <div>
                <img src="data:image/jpeg;base64,{img_base64}" class="cover-image">
                <h1>{title}</h1>
                <p class="author">by {author}</p>
            </div>
            ''')
        except Exception:
            # Fallback to simple cover
            html_parts.append(f'''
            <div class="simple-cover">
                <h1>{title}</h1>
                <p class="author">by {author}</p>
            </div>
            ''')
    else:
        # Simple gradient cover
        html_parts.append(f'''
        <div class="simple-cover">
            <h1>{title}</h1>
            <p class="author">by {author}</p>
        </div>
        ''')
    
    html_parts.append('</div>')  # Close cover-page
    
    # Copyright page
    html_parts.append(f'<p class="copyright">© {datetime.now().year} {author}. All rights reserved.</p>')
    
    # Table of Contents
    if include_toc:
        html_parts.append('<div class="toc">')
        html_parts.append('<h3>Table of Contents</h3>')
        html_parts.append('<ul>')
        
        # Group by session
        sessions = {}
        for story in stories:
            session_title = story.get('session_title', 'Untitled Session')
            if session_title not in sessions:
                sessions[session_title] = []
            sessions[session_title].append(story)
        
        for session_title in sessions.keys():
            anchor = session_title.lower().replace(' ', '-').replace('?', '').replace('!', '').replace(',', '')
            html_parts.append(f'<li><a href="#{anchor}">{session_title}</a></li>')
        
        html_parts.append('</ul>')
        html_parts.append('</div>')
    
    # Add stories
    current_session = None
    for story in stories:
        session_title = story.get('session_title', 'Untitled Session')
        anchor = session_title.lower().replace(' ', '-').replace('?', '').replace('!', '').replace(',', '')
        
        # Add session header if new session
        if session_title != current_session:
            current_session = session_title
            html_parts.append(f'<h2 id="{anchor}">{session_title}</h2>')
        
        if format_style == "interview":
            html_parts.append(f'<div class="question">{story.get("question", "")}</div>')
        
        # Format answer with paragraphs
        answer_text = story.get('answer_text', '')
        if answer_text:
            html_parts.append('<div>')
            paragraphs = answer_text.split('\n')
            for para in paragraphs:
                if para.strip():
                    escaped_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    html_parts.append(f'<p>{escaped_para}</p>')
            html_parts.append('</div>')
        
        # Add images
        if include_images and story.get('images'):
            for img in story.get('images', []):
                if img.get('base64'):
                    html_parts.append(f'<img src="data:image/jpeg;base64,{img["base64"]}" class="story-image">')
                    if img.get('caption'):
                        caption = img['caption'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_parts.append(f'<p class="image-caption">{caption}</p>')
        
        # Add separator
        html_parts.append('<hr style="margin: 30px 0; border: none; border-top: 1px dashed #ccc;">')
    
    # Close HTML
    html_parts.append("""
    </body>
    </html>
    """)
    
    # Join all parts
    html_content = '\n'.join(html_parts)
    
    return html_content

