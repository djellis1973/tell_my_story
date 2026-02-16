# biography_publisher.py – DOCX, HTML & ZIP with embedded images and cover designer
import streamlit as st
import json
import base64
from datetime import datetime
import re
import os
import io
import zipfile
import time
from PIL import Image
from docx import Document
from docx.shared import Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

st.set_page_config(page_title="Biography Publisher", page_icon="📚", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main-header { text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   margin: -1rem -1rem 2rem -1rem; border-radius: 0 0 20px 20px; color: white; }
    .story-card { border-left: 4px solid #667eea; padding: 1rem; margin: 1rem 0; background: #f8f9fa; border-radius: 0 10px 10px 0; }
    .export-box { border: 2px solid #667eea; border-radius: 10px; padding: 2rem; margin: 2rem 0; background: white; }
    .cover-preview { padding: 40px 20px; text-align: center; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                     margin: 20px 0; min-height: 300px; display: flex; flex-direction: column; justify-content: center;
                     border: 1px solid #ddd; }
    .cover-preview h1 { margin-bottom: 10px; font-size: 28px; }
    .cover-preview p { font-size: 16px; opacity: 0.9; }
    .cover-preview img { max-width: 80%; max-height: 200px; object-fit: contain; margin-bottom: 15px; border-radius: 4px; }
    .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: white; z-index: 1000; 
                     overflow-y: auto; padding: 2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📚 Biography Publisher</h1><p>Transform your stories into a beautifully formatted biography with images</p></div>', unsafe_allow_html=True)

# Initialize session state
if 'stories_data' not in st.session_state:
    st.session_state.stories_data = None
if 'formatted_text' not in st.session_state:
    st.session_state.formatted_text = ""
if 'book_title' not in st.session_state:
    st.session_state.book_title = ""
if 'author_name' not in st.session_state:
    st.session_state.author_name = ""
if 'selected_format' not in st.session_state:
    st.session_state.selected_format = "interview"
if 'include_toc' not in st.session_state:
    st.session_state.include_toc = True
if 'include_dates' not in st.session_state:
    st.session_state.include_dates = False
if 'show_cover_designer' not in st.session_state:
    st.session_state.show_cover_designer = False
if 'cover_design' not in st.session_state:
    st.session_state.cover_design = None
if 'cover_image' not in st.session_state:
    st.session_state.cover_image = None

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Publication Settings")
    st.subheader("Book Details")
    st.session_state.book_title = st.text_input("Book Title", value=st.session_state.book_title)
    st.session_state.author_name = st.text_input("Author Name", value=st.session_state.author_name)
    st.subheader("Format Options")
    st.session_state.selected_format = st.radio(
        "Format Style",
        ["interview", "biography", "memoir"],
        format_func=lambda x: {"interview": "📝 Interview Q&A", "biography": "📖 Continuous Biography", "memoir": "📚 Chapter-based Memoir"}[x]
    )
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.include_toc = st.checkbox("Table of Contents", value=True)
    with col2:
        st.session_state.include_dates = st.checkbox("Include Dates", value=False)
    st.divider()
    st.subheader("📂 Upload Stories")
    uploaded_file = st.file_uploader("Upload JSON from Tell My Story", type=['json'])
    if uploaded_file:
        try:
            st.session_state.stories_data = json.load(uploaded_file)
            st.success("✅ Uploaded successfully!")
            # Auto-fill title/author from profile
            user_profile = st.session_state.stories_data.get('user_profile', {})
            if user_profile:
                first = user_profile.get('first_name', '')
                last = user_profile.get('last_name', '')
                if first and last:
                    st.session_state.author_name = f"{first} {last}"
                    st.session_state.book_title = f"The Story of {first} {last}"
        except Exception as e:
            st.error(f"Error loading file: {e}")

# ============================================================================
# COVER DESIGNER MODAL - FIXED with image preview
# ============================================================================
def show_cover_designer():
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    st.title("🎨 Cover Designer")
    
    if st.button("← Back", key="cover_back"):
        st.session_state.show_cover_designer = False
        st.rerun()
    
    st.markdown("### Design your book cover")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Cover Options**")
        cover_type = st.selectbox("Cover Style", ["Simple", "Elegant", "Modern", "Classic", "Vintage"])
        title_font = st.selectbox("Title Font", ["Georgia", "Arial", "Times New Roman", "Helvetica", "Calibri"])
        title_color = st.color_picker("Title Color", "#000000")
        background_color = st.color_picker("Background Color", "#FFFFFF")
        
        uploaded_cover = st.file_uploader("Upload Cover Image (optional)", type=['jpg', 'jpeg', 'png'], key="publisher_cover_upload")
        if uploaded_cover:
            st.image(uploaded_cover, caption="Your cover image", width=300)
            # Store in session state for preview
            bytes_data = uploaded_cover.getvalue()
            st.session_state.cover_image = base64.b64encode(bytes_data).decode()
    
    with col2:
        st.markdown("**Preview**")
        first_name = "Author"
        if st.session_state.stories_data:
            profile = st.session_state.stories_data.get('user_profile', {})
            first_name = profile.get('first_name', 'Author')
        preview_title = st.text_input("Preview Title", value=f"{first_name}'s Story", key="publisher_preview_title")
        
        # Build preview HTML with image if uploaded
        preview_html = f'<div class="cover-preview" style="background-color:{background_color};">'
        
        # FIX: Add image to preview if uploaded
        if st.session_state.cover_image:
            preview_html += f'<img src="data:image/jpeg;base64,{st.session_state.cover_image}" alt="Cover Image">'
        
        preview_html += f'''
            <h1 style="font-family:{title_font}; color:{title_color};">{preview_title}</h1>
            <p>by {first_name}</p>
        </div>
        '''
        st.markdown(preview_html, unsafe_allow_html=True)
    
    if st.button("💾 Save Cover Design", type="primary", width='stretch'):
        # Save cover design to session state
        st.session_state.cover_design = {
            "cover_type": cover_type,
            "title_font": title_font,
            "title_color": title_color,
            "background_color": background_color,
            "title": preview_title
        }
        
        if uploaded_cover:
            # Save image data
            bytes_data = uploaded_cover.getvalue()
            st.session_state.cover_image = base64.b64encode(bytes_data).decode()
            st.session_state.cover_design['cover_image'] = st.session_state.cover_image
        
        st.success("Cover design saved!")
        time.sleep(1)
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================================
# DOCX GENERATION WITH COVER
# ============================================================================
def generate_docx(book_title, author_name, stories, format_style, include_toc, include_dates):
    doc = Document()
    
    # Add cover if exists
    if st.session_state.cover_design:
        cover = st.session_state.cover_design
        
        # Add background color (approximated with a table)
        table = doc.add_table(rows=1, cols=1)
        table.autofit = False
        table.allow_autofit = False
        cell = table.cell(0, 0)
        cell.width = Inches(6)
        # Set cell shading
        shading_elm = OxmlElement('w:shd')
        shading_elm.set(qn('w:fill'), cover.get('background_color', '#667eea').lstrip('#'))
        cell._tc.get_or_add_tcPr().append(shading_elm)
        
        # Add cover image
        if cover.get('cover_image'):
            try:
                img_bytes = base64.b64decode(cover['cover_image'])
                img_stream = io.BytesIO(img_bytes)
                doc.add_picture(img_stream, width=Inches(4))
                last_paragraph = doc.paragraphs[-1]
                last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            except:
                pass
        
        # Add title with cover font
        title = doc.add_heading(cover.get('title', book_title), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Set font color
        color_hex = cover.get('title_color', '#000000').lstrip('#')
        for run in title.runs:
            run.font.name = cover.get('title_font', 'Arial')
            run.font.color.rgb = RGBColor(
                int(color_hex[0:2], 16),
                int(color_hex[2:4], 16),
                int(color_hex[4:6], 16)
            )
    else:
        # Default title page
        title = doc.add_heading(book_title, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    author = doc.add_paragraph(f'by {author_name}')
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para = doc.add_paragraph(f'Generated on {datetime.now().strftime("%B %d, %Y")}')
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()
    
    # TOC
    if include_toc:
        doc.add_heading('Table of Contents', 1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        if isinstance(stories, list):
            current_session = None
            for i, story in enumerate(stories, 1):
                session_id = story.get('session_id', '1')
                if session_id != current_session:
                    session_title = story.get('session_title', f'Session {session_id}')
                    doc.add_heading(session_title, 2)
                    current_session = session_id
                question = story.get('question', f'Story {i}')
                p = doc.add_paragraph(f'{i}. {question}')
                p.style = 'List Bullet'
        doc.add_page_break()
    
    # Content
    if isinstance(stories, list):
        current_session = None
        story_counter = 1
        for story in stories:
            session_id = story.get('session_id', '1')
            if session_id != current_session:
                session_title = story.get('session_title', f'Session {session_id}')
                doc.add_heading(session_title, 1)
                current_session = session_id
            question = story.get('question', '')
            answer_text = story.get('answer_text', '')
            images = story.get('images', [])
            
            if format_style == 'interview':
                doc.add_heading(f'Q: {question}', 3)
                doc.add_paragraph(answer_text)
            elif format_style == 'biography':
                doc.add_paragraph(answer_text)
            else:
                doc.add_heading(f'Chapter {story_counter}: {question}', 2)
                doc.add_paragraph(answer_text)
            
            # Embed images
            for img_data in images:
                b64 = img_data.get('base64')
                caption = img_data.get('caption', '')
                if b64:
                    try:
                        img_bytes = base64.b64decode(b64)
                        img_stream = io.BytesIO(img_bytes)
                        doc.add_picture(img_stream, width=Inches(4))
                        if caption:
                            cap = doc.add_paragraph(caption)
                            cap.style = 'Caption'
                    except:
                        pass
            doc.add_paragraph()
            story_counter += 1
    
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    return docx_bytes

# ============================================================================
# HTML GENERATION WITH COVER
# ============================================================================
def generate_html(book_title, author_name, stories):
    # Add cover if exists
    cover_html = ""
    if st.session_state.cover_design:
        cover = st.session_state.cover_design
        cover_html = f'''
        <div class="book-cover" style="background-color: {cover.get("background_color", "#667eea")}; text-align: center; padding: 60px 20px; border-radius: 8px; margin-bottom: 30px;">
        '''
        if cover.get('cover_image'):
            cover_html += f'<img src="data:image/jpeg;base64,{cover["cover_image"]}" alt="Book Cover" style="max-width: 80%; max-height: 300px; object-fit: contain; margin-bottom: 20px;">'
        cover_html += f'''
            <h1 style="font-family: {cover.get("title_font", "Arial")}; color: {cover.get("title_color", "#000000")};">{cover.get("title", book_title)}</h1>
            <p>by {author_name}</p>
        </div>
        '''
    else:
        cover_html = f'''
        <div class="book-cover" style="background-color: #667eea; color: white; text-align: center; padding: 60px 20px; border-radius: 8px; margin-bottom: 30px;">
            <h1>{book_title}</h1>
            <p>by {author_name}</p>
        </div>
        '''
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{book_title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .book-cover {{ margin-bottom: 30px; }}
        .story {{ margin-bottom: 30px; }}
        .question {{ font-weight: bold; font-size: 1.2em; margin-bottom: 10px; }}
        .answer {{ line-height: 1.6; }}
        .image-gallery {{ display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; }}
        .image-item {{ max-width: 300px; }}
        .image-item img {{ max-width: 100%; border-radius: 4px; }}
        .caption {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
        hr {{ margin: 40px 0; border: 0; border-top: 1px solid #eee; }}
        .footer {{ text-align: center; color: #999; font-size: 0.9em; margin-top: 50px; }}
    </style>
</head>
<body>
    {cover_html}
"""
    
    for i, story in enumerate(stories):
        html += f"""
    <div class="story">
        <div class="question">{story['question']}</div>
        <div class="answer">{story['answer_text']}</div>
"""
        if story.get('images'):
            html += '        <div class="image-gallery">\n'
            for img in story.get('images', []):
                if img.get('base64'):
                    html += f'            <div class="image-item">\n'
                    html += f'                <img src="data:image/jpeg;base64,{img["base64"]}" alt="{img.get("caption", "")}">\n'
                    if img.get('caption'):
                        html += f'                <div class="caption">📝 {img["caption"]}</div>\n'
                    html += f'            </div>\n'
            html += '        </div>\n'
        
        html += f"""
    </div>
    <hr>
"""
    
    html += f"""
    <div class="footer">
        Generated by Tell My Story • {datetime.now().strftime("%B %d, %Y")}
    </div>
</body>
</html>"""
    return html

# ============================================================================
# ZIP GENERATION WITH COVER
# ============================================================================
def generate_zip(book_title, author_name, stories):
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add cover if exists
        cover_html = ""
        if st.session_state.cover_design:
            cover = st.session_state.cover_design
            if cover.get('cover_image'):
                img_bytes = base64.b64decode(cover['cover_image'])
                zip_file.writestr("cover.jpg", img_bytes)
                cover_img_tag = '<img src="cover.jpg" alt="Book Cover" style="max-width: 80%; max-height: 300px; object-fit: contain; margin-bottom: 20px;">'
            else:
                cover_img_tag = ""
            
            cover_html = f'''
            <div class="book-cover" style="background-color: {cover.get("background_color", "#667eea")}; text-align: center; padding: 60px 20px; border-radius: 8px; margin-bottom: 30px;">
                {cover_img_tag}
                <h1 style="font-family: {cover.get("title_font", "Arial")}; color: {cover.get("title_color", "#000000")};">{cover.get("title", book_title)}</h1>
                <p>by {author_name}</p>
            </div>
            '''
        else:
            cover_html = f'''
            <div class="book-cover" style="background-color: #667eea; color: white; text-align: center; padding: 60px 20px; border-radius: 8px; margin-bottom: 30px;">
                <h1>{book_title}</h1>
                <p>by {author_name}</p>
            </div>
            '''
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{book_title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .book-cover {{ margin-bottom: 30px; }}
        .story {{ margin-bottom: 30px; }}
        .question {{ font-weight: bold; font-size: 1.2em; margin-bottom: 10px; }}
        .answer {{ line-height: 1.6; }}
        .image-gallery {{ display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; }}
        .image-item {{ max-width: 300px; }}
        .image-item img {{ max-width: 100%; border-radius: 4px; }}
        .caption {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
        hr {{ margin: 40px 0; border: 0; border-top: 1px solid #eee; }}
        .footer {{ text-align: center; color: #999; font-size: 0.9em; margin-top: 50px; }}
    </style>
</head>
<body>
    {cover_html}
"""
        
        image_counter = 0
        for i, story in enumerate(stories):
            html += f"""
    <div class="story">
        <div class="question">{story['question']}</div>
        <div>{story['answer_text']}</div>
"""
            for j, img in enumerate(story.get('images', [])):
                if img.get('base64'):
                    img_data = base64.b64decode(img['base64'])
                    img_filename = f"images/image_{i}_{j}.jpg"
                    zip_file.writestr(img_filename, img_data)
                    
                    html += f'        <img src="{img_filename}" alt="{img.get("caption", "")}" style="max-width: 100%; margin: 10px 0;">\n'
                    if img.get('caption'):
                        html += f'        <div class="caption">📝 {img["caption"]}</div>\n'
                    image_counter += 1
            
            html += f"""
    </div>
    <hr>
"""
        
        html += f"""
    <div class="footer">
        Generated by Tell My Story • {datetime.now().strftime("%B %d, %Y")}<br>
        Contains {image_counter} images
    </div>
</body>
</html>"""
        
        zip_file.writestr(f"{book_title.replace(' ', '_')}.html", html)
        
        # Add a simple README
        readme = f"""Book Package: {book_title}
Author: {author_name}
Generated: {datetime.now().strftime("%B %d, %Y")}

This package contains:
- {book_title.replace(' ', '_')}.html - The complete book
- cover.jpg - Cover image (if provided)
- images/ - Folder containing all story images

Total stories: {len(stories)}
Total images: {image_counter}
"""
        zip_file.writestr("README.txt", readme)
    
    return zip_file.getvalue()

# ============================================================================
# MAIN INTERFACE
# ============================================================================
if st.session_state.stories_data:
    stories_data = st.session_state.stories_data
    stories = stories_data.get('stories', [])
    user_profile = stories_data.get('user_profile', {})

    # Cover Designer button at the top
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🎨 Cover Designer", use_container_width=True):
            st.session_state.show_cover_designer = True
            st.rerun()

    # Show cover preview if exists
    if st.session_state.cover_design:
        with st.expander("🎨 Current Cover Design", expanded=False):
            cover = st.session_state.cover_design
            preview_html = f'<div class="cover-preview" style="background-color:{cover.get("background_color", "#FFFFFF")};">'
            if cover.get('cover_image'):
                preview_html += f'<img src="data:image/jpeg;base64,{cover["cover_image"]}" alt="Cover Image">'
            preview_html += f'''
                <h1 style="font-family:{cover.get("title_font", "Arial")}; color:{cover.get("title_color", "#000000")};">{cover.get("title", "My Story")}</h1>
                <p>by {st.session_state.author_name}</p>
            </div>
            '''
            st.markdown(preview_html, unsafe_allow_html=True)

    # Display summary
    st.subheader("📊 Data Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Stories", stories_data.get('summary', {}).get('total_stories', len(stories)))
    with col2:
        st.metric("Sessions", stories_data.get('summary', {}).get('total_sessions', 1))
    with col3:
        st.metric("Export Date", stories_data.get('export_date', 'Unknown')[:10])

    # Preview
    with st.expander("📖 Preview Stories", expanded=False):
        for i, story in enumerate(stories[:3]):  # Show first 3
            st.markdown(f"**Q: {story.get('question', '')}**")
            st.markdown(f"*{story.get('answer_text', '')[:200]}...*")
            if story.get('images'):
                st.caption(f"📸 {len(story['images'])} image(s) attached")
            st.divider()
        if len(stories) > 3:
            st.info(f"... and {len(stories) - 3} more stories")

    # Formatting controls
    st.subheader("🖨️ Generate Biography")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Generate DOCX", type="primary", use_container_width=True):
            with st.spinner("Creating Word document with images..."):
                docx_bytes = generate_docx(
                    st.session_state.book_title,
                    st.session_state.author_name,
                    stories,
                    st.session_state.selected_format,
                    st.session_state.include_toc,
                    st.session_state.include_dates
                )
                filename = f"{st.session_state.book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.docx"
                st.download_button(
                    "📥 Download DOCX", 
                    data=docx_bytes, 
                    file_name=filename, 
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                    use_container_width=True,
                    key="docx_download"
                )
    
    with col2:
        if st.button("🌐 Generate HTML", type="primary", use_container_width=True):
            with st.spinner("Creating HTML page..."):
                html_content = generate_html(
                    st.session_state.book_title,
                    st.session_state.author_name,
                    stories
                )
                filename = f"{st.session_state.book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html"
                st.download_button(
                    "📥 Download HTML", 
                    data=html_content, 
                    file_name=filename, 
                    mime="text/html", 
                    use_container_width=True,
                    key="html_download"
                )
    
    with col3:
        if st.button("📦 Generate ZIP", type="primary", use_container_width=True):
            with st.spinner("Creating ZIP package with all images..."):
                zip_data = generate_zip(
                    st.session_state.book_title,
                    st.session_state.author_name,
                    stories
                )
                filename = f"{st.session_state.book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.zip"
                st.download_button(
                    "📥 Download ZIP", 
                    data=zip_data, 
                    file_name=filename, 
                    mime="application/zip", 
                    use_container_width=True,
                    key="zip_download"
                )
    
    # Preview text
    if st.button("📄 Preview Text", use_container_width=True):
        preview = f"{st.session_state.book_title}\nby {st.session_state.author_name}\n\n"
        for i, story in enumerate(stories[:5]):
            preview += f"Story {i+1}: {story.get('question', '')}\n"
            preview += f"{story.get('answer_text', '')[:200]}...\n\n"
        st.session_state.formatted_text = preview
    
    # Show preview if available
    if st.session_state.formatted_text:
        with st.expander("📄 Text Preview", expanded=True):
            st.text_area("Preview", st.session_state.formatted_text, height=300)

else:
    st.info("📚 Upload your stories JSON file using the sidebar to begin.")
    st.markdown("""
    ### How to use:
    1. Export your data from the **Tell My Story** app
    2. Upload the JSON file using the sidebar
    3. Click **🎨 Cover Designer** to design your cover
    4. Customize your book settings
    5. Generate DOCX, HTML, or ZIP with embedded images
    """)

# ============================================================================
# MODAL HANDLING
# ============================================================================
if st.session_state.show_cover_designer:
    show_cover_designer()
    st.stop()

st.markdown("---")
st.caption(f"Biography Publisher • {datetime.now().year}")
