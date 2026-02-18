# biography_publisher.py – PDF & DOCX with embedded images and optional cover designer
import streamlit as st
import json
import base64
from datetime import datetime
import re
import os
import io
import time
import hashlib
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fpdf import FPDF
from PIL import Image
import zipfile

# ============================================================================
# COVER DESIGNER STATE (shared via session state)
# ============================================================================
print("Initializing cover designer state...")  # DEBUG
if 'cover_design' not in st.session_state:
    st.session_state.cover_design = {
        "title": "",
        "subtitle": "",
        "author": "",
        "cover_type": "Simple",
        "title_font": "Georgia",
        "title_color": "#000000",
        "background_color": "#FFFFFF",
        "cover_image": None,
        "cover_image_path": None
    }
    print("Cover design initialized")  # DEBUG

if 'show_cover_designer' not in st.session_state:
    st.session_state.show_cover_designer = False
    print("Show cover designer initialized")  # DEBUG
# ============================================================================
# COVER DESIGNER FUNCTIONS
# ============================================================================
def save_cover_image(uploaded_file, title):
    """Save uploaded cover image and return path"""
    if uploaded_file:
        os.makedirs("temp_covers", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c.isspace()).replace(" ", "_")[:30]
        filename = f"temp_covers/cover_{safe_title}_{timestamp}.jpg"
        with open(filename, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        return filename
    return None

def create_simple_cover_html(title, author, subtitle, background_color, title_color, title_font):
    """Generate HTML for simple cover preview"""
    subtitle_html = f'<h2 style="font-family:{title_font}; color:{title_color}; font-size:24px; margin:5px 0 0 0;">{subtitle}</h2>' if subtitle else ''
    
    return f'''
    <div style="width:100%; max-width:450px; margin:0 auto;">
        <div style="
            width:100%;
            aspect-ratio:600/900;
            background-color:{background_color};
            border:2px solid #ddd;
            border-radius:10px;
            display:flex;
            flex-direction:column;
            justify-content:space-between;
            padding:30px 20px;
            box-sizing:border-box;
            box-shadow:0 4px 8px rgba(0,0,0,0.1);
        ">
            <div style="text-align:center;">
                <h1 style="font-family:{title_font}; color:{title_color}; font-size:48px; margin:0;">{title}</h1>
                {subtitle_html}
            </div>
            <div style="text-align:center;">
                <p style="font-family:{title_font}; color:{title_color}; font-size:24px; margin:0;">by {author}</p>
            </div>
        </div>
    </div>
    '''

def create_custom_cover_html(title, author, subtitle, image_path, title_font):
    """Generate HTML for custom cover preview with image"""
    if not image_path or not os.path.exists(image_path):
        return create_simple_cover_html(title, author, subtitle, "#FFFFFF", "#000000", title_font)
    
    with open(image_path, 'rb') as f:
        img_bytes = f.read()
    img_base64 = base64.b64encode(img_bytes).decode()
    
    subtitle_html = f'<h2 style="font-family:{title_font}; color:white; font-size:24px; margin:5px 0 0 0; text-shadow:2px 2px 4px black;">{subtitle}</h2>' if subtitle else ''
    
    return f'''
    <div style="width:100%; max-width:450px; margin:0 auto;">
        <div style="
            width:100%;
            aspect-ratio:600/900;
            background-image:url('data:image/jpeg;base64,{img_base64}');
            background-size:cover;
            background-position:center;
            border:2px solid #ddd;
            border-radius:10px;
            overflow:hidden;
            position:relative;
            box-shadow:0 4px 8px rgba(0,0,0,0.1);
        ">
            <div style="
                position:absolute;
                top:0;
                left:0;
                width:100%;
                height:100%;
                background:rgba(0,0,0,0.3);
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                padding:30px 20px;
                box-sizing:border-box;
            ">
                <div style="text-align:center;">
                    <h1 style="font-family:{title_font}; color:white; font-size:48px; margin:0; text-shadow:2px 2px 4px black;">{title}</h1>
                    {subtitle_html}
                </div>
                <div style="text-align:center;">
                    <p style="font-family:{title_font}; color:white; font-size:24px; margin:0; text-shadow:1px 1px 2px black;">by {author}</p>
                </div>
            </div>
        </div>
    </div>
    '''

def show_cover_designer():
    """Display the cover designer interface (can be called from main app)"""
    
    # Initialize session state INSIDE the function
    if 'cover_design' not in st.session_state:
        st.session_state.cover_design = {
            "title": "",
            "subtitle": "",
            "author": "",
            "cover_type": "Simple",
            "title_font": "Georgia",
            "title_color": "#000000",
            "background_color": "#FFFFFF",
            "cover_image": None,
            "cover_image_path": None
        }
    
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    st.title("🎨 Cover Designer")
    
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("✕", key="close_cover_designer"):
            st.session_state.show_cover_designer = False
            st.rerun()
    
    st.markdown("### Design your book cover - Portrait format (6\" x 9\")")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Cover Options**")
        
        # Get user profile from main app if available
        default_title = "My Story"
        default_author = "Author Name"
        if 'user_account' in st.session_state and st.session_state.user_account:
            profile = st.session_state.user_account.get('profile', {})
            first = profile.get('first_name', '')
            last = profile.get('last_name', '')
            if first:
                default_title = f"{first}'s Story"
                default_author = f"{first} {last}".strip() if last else first
        
        title = st.text_input("Book Title", value=st.session_state.cover_design.get('title', default_title))
        subtitle = st.text_input("Subtitle (optional)", value=st.session_state.cover_design.get('subtitle', ''), 
                                placeholder="A brief subtitle or tagline")
        author = st.text_input("Author Name", value=st.session_state.cover_design.get('author', default_author))
        
        cover_type = st.selectbox("Cover Style", ["Simple", "Elegant", "Modern", "Classic", "Vintage"], 
                                 index=["Simple", "Elegant", "Modern", "Classic", "Vintage"].index(
                                     st.session_state.cover_design.get('cover_type', 'Simple')))
        
        title_font = st.selectbox("Title Font", ["Georgia", "Arial", "Times New Roman", "Helvetica", "Calibri"],
                                 index=["Georgia", "Arial", "Times New Roman", "Helvetica", "Calibri"].index(
                                     st.session_state.cover_design.get('title_font', 'Georgia')))
        
        title_color = st.color_picker("Title Color", value=st.session_state.cover_design.get('title_color', '#000000'))
        background_color = st.color_picker("Background Color", value=st.session_state.cover_design.get('background_color', '#FFFFFF'))
        
        st.markdown("**Cover Image (optional):**")
        uploaded_cover = st.file_uploader("Upload Cover Image", type=['jpg', 'jpeg', 'png'], key="cover_uploader")
        
        if uploaded_cover:
            st.image(uploaded_cover, caption="Preview", width=250)
            cover_image_path = save_cover_image(uploaded_cover, title)
        else:
            cover_image_path = st.session_state.cover_design.get('cover_image_path')
        
        # Update session state
        st.session_state.cover_design.update({
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "cover_type": cover_type,
            "title_font": title_font,
            "title_color": title_color,
            "background_color": background_color,
            "cover_image_path": cover_image_path
        })
    
    with col2:
        st.markdown("**Preview (6\" x 9\" portrait)**")
        
        # Generate preview
        if st.session_state.cover_design.get('cover_image_path'):
            preview_html = create_custom_cover_html(
                st.session_state.cover_design['title'],
                st.session_state.cover_design['author'],
                st.session_state.cover_design['subtitle'],
                st.session_state.cover_design['cover_image_path'],
                st.session_state.cover_design['title_font']
            )
        else:
            preview_html = create_simple_cover_html(
                st.session_state.cover_design['title'],
                st.session_state.cover_design['author'],
                st.session_state.cover_design['subtitle'],
                st.session_state.cover_design['background_color'],
                st.session_state.cover_design['title_color'],
                st.session_state.cover_design['title_font']
            )
        
        from streamlit.components.v1 import html
        html(preview_html, height=700)
        st.caption("6\" wide × 9\" tall (portrait format)")
    
    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("💾 Save Cover Design", type="primary", use_container_width=True):
            st.success("Cover design saved!")
            time.sleep(1)
            st.session_state.show_cover_designer = False
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.show_cover_designer:
        st.stop()

# ============================================================================
# COVER SELECTION DIALOG
# ============================================================================
def cover_selection_dialog(export_format):
    """Show dialog to choose cover type before export"""
    st.markdown('<div class="modal-overlay">', unsafe_allow_html=True)
    st.title("📚 Choose Cover")
    
    st.markdown(f"### Exporting as {export_format.upper()}")
    st.markdown("What cover would you like to use?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Simple Default Cover")
        st.color_picker("Cover Color", value="#2c3e50", key="simple_cover_color")
        if st.button("Use Simple Cover", key=f"use_simple_{export_format}", type="primary", use_container_width=True):
            return {
                "type": "simple",
                "color": st.session_state.simple_cover_color
            }
    
    with col2:
        st.markdown("### Custom Designed Cover")
        if st.session_state.cover_design.get('title'):
            st.markdown(f"**Title:** {st.session_state.cover_design['title']}")
            st.markdown(f"**Author:** {st.session_state.cover_design['author']}")
            if st.session_state.cover_design.get('cover_image_path'):
                st.markdown("✅ Has custom image")
        else:
            st.markdown("*No cover designed yet*")
            st.markdown("Go to Cover Designer first")
        
        if st.button("Use Custom Cover", key=f"use_custom_{export_format}", type="primary", use_container_width=True):
            return {
                "type": "custom",
                "design": st.session_state.cover_design
            }
    
    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("Cancel", key=f"cancel_{export_format}"):
            return None
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
    return None

# ============================================================================
# PDF GENERATION (with cover)
# ============================================================================
class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, 'My Story', 0, 0, 'L')
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')
            self.ln(15)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Generated by Tell My Story • {datetime.now().strftime("%Y")}', 0, 0, 'C')

def generate_pdf_with_cover(book_title, author_name, stories, cover_choice):
    """Generate PDF with selected cover"""
    pdf = PDF()
    
    # Add cover page
    pdf.add_page()
    
    if cover_choice["type"] == "custom" and cover_choice["design"].get('cover_image_path'):
        # Use custom cover with image
        image_path = cover_choice["design"]['cover_image_path']
        if os.path.exists(image_path):
            pdf.image(image_path, x=0, y=0, w=210, h=297)
            
            # Add text overlay
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 30)
            
            title = cover_choice["design"].get('title', book_title)
            author = cover_choice["design"].get('author', author_name)
            subtitle = cover_choice["design"].get('subtitle', '')
            
            pdf.set_xy(0, 80)
            pdf.cell(210, 20, title, 0, 1, 'C')
            
            if subtitle:
                pdf.set_font('Arial', '', 16)
                pdf.cell(210, 15, subtitle, 0, 1, 'C')
            
            pdf.set_font('Arial', '', 16)
            pdf.set_xy(0, 200)
            pdf.cell(210, 15, f'by {author}', 0, 1, 'C')
    else:
        # Use simple cover
        color = cover_choice.get("color", "#2c3e50")
        # Convert hex to RGB
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        
        pdf.set_fill_color(rgb[0], rgb[1], rgb[2])
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 30)
        pdf.cell(0, 40, '', 0, 1)
        pdf.cell(0, 20, book_title, 0, 1, 'C')
        pdf.set_font('Arial', '', 16)
        pdf.cell(0, 10, f'by {author_name}', 0, 1, 'C')
    
    # Add content pages
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 11)
    
    for story in stories:
        question = story.get('question', '')
        answer = story.get('answer_text', '')
        
        pdf.set_font('Arial', 'B', 12)
        pdf.multi_cell(0, 6, question)
        pdf.ln(2)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 6, answer)
        pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin1', 'ignore')

# ============================================================================
# DOCX GENERATION (with cover)
# ============================================================================
def generate_docx_with_cover(book_title, author_name, stories, cover_choice):
    """Generate DOCX with selected cover"""
    doc = Document()
    
    # Add cover
    if cover_choice["type"] == "custom" and cover_choice["design"].get('cover_image_path'):
        image_path = cover_choice["design"]['cover_image_path']
        if os.path.exists(image_path):
            doc.add_picture(image_path, width=Inches(6))
            doc.add_paragraph()
    
    # Title
    title = doc.add_heading(book_title, 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Subtitle if exists
    if cover_choice["type"] == "custom" and cover_choice["design"].get('subtitle'):
        subtitle = doc.add_paragraph(cover_choice["design"]['subtitle'])
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.style = 'Subtitle'
    
    # Author
    author = doc.add_paragraph(f'by {author_name}')
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_page_break()
    
    # Content
    for story in stories:
        question = story.get('question', '')
        answer = story.get('answer_text', '')
        images = story.get('images', [])
        
        doc.add_heading(question, 3)
        doc.add_paragraph(answer)
        
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
    
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    return docx_bytes

# ============================================================================
# HTML GENERATION (with cover)
# ============================================================================
def generate_html_with_cover(book_title, author_name, stories, cover_choice):
    """Generate HTML with selected cover"""
    
    # Create cover HTML
    if cover_choice["type"] == "custom" and cover_choice["design"].get('cover_image_path'):
        image_path = cover_choice["design"]['cover_image_path']
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode()
        
        cover_html = f'''
        <div class="cover-page">
            <img src="data:image/jpeg;base64,{img_base64}" class="cover-image">
            <div class="cover-overlay">
                <h1 class="cover-title">{cover_choice["design"].get('title', book_title)}</h1>
                {f'<h2 class="cover-subtitle">{cover_choice["design"]["subtitle"]}</h2>' if cover_choice["design"].get('subtitle') else ''}
                <p class="cover-author">by {cover_choice["design"].get('author', author_name)}</p>
            </div>
        </div>
        '''
    else:
        color = cover_choice.get("color", "#2c3e50")
        cover_html = f'''
        <div class="cover-page" style="background-color:{color};">
            <div class="cover-content">
                <h1 class="cover-title">{book_title}</h1>
                <p class="cover-author">by {author_name}</p>
            </div>
        </div>
        '''
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{book_title}</title>
    <style>
        body {{ font-family: Georgia, serif; margin: 0; padding: 20px; }}
        .cover-page {{ width: 100%; min-height: 100vh; position: relative; margin-bottom: 30px; }}
        .cover-image {{ width: 100%; height: auto; }}
        .cover-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                         background: rgba(0,0,0,0.3); display: flex; flex-direction: column; 
                         justify-content: center; align-items: center; color: white; }}
        .cover-title {{ font-size: 48px; margin: 0; text-shadow: 2px 2px 4px black; }}
        .cover-subtitle {{ font-size: 24px; margin: 10px 0; text-shadow: 1px 1px 2px black; }}
        .cover-author {{ font-size: 24px; text-shadow: 1px 1px 2px black; }}
        .cover-content {{ text-align: center; color: white; padding: 40px; }}
        .story {{ margin: 30px 0; padding: 20px; border-left: 4px solid #667eea; }}
        .question {{ font-weight: bold; font-size: 18px; margin-bottom: 10px; }}
        .answer {{ line-height: 1.6; }}
        .image-gallery {{ margin: 20px 0; }}
        .image-item {{ margin: 10px 0; }}
        .image-item img {{ max-width: 100%; border-radius: 5px; }}
        .caption {{ font-style: italic; color: #666; margin-top: 5px; }}
    </style>
</head>
<body>
    {cover_html}
"""
    
    for story in stories:
        question = story.get('question', '')
        answer = story.get('answer_text', '')
        
        html += f"""
    <div class="story">
        <div class="question">{question}</div>
        <div class="answer">{answer}</div>
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
# ZIP GENERATION (with cover)
# ============================================================================
def generate_zip_with_cover(book_title, author_name, stories, cover_choice):
    """Generate ZIP with HTML and separate images"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        
        # Create cover HTML
        if cover_choice["type"] == "custom" and cover_choice["design"].get('cover_image_path'):
            image_path = cover_choice["design"]['cover_image_path']
            with open(image_path, 'rb') as f:
                img_bytes = f.read()
            zip_file.writestr("cover.jpg", img_bytes)
            
            cover_html = f'''
            <div class="cover-page">
                <img src="cover.jpg" class="cover-image">
                <div class="cover-overlay">
                    <h1 class="cover-title">{cover_choice["design"].get('title', book_title)}</h1>
                    {f'<h2 class="cover-subtitle">{cover_choice["design"]["subtitle"]}</h2>' if cover_choice["design"].get('subtitle') else ''}
                    <p class="cover-author">by {cover_choice["design"].get('author', author_name)}</p>
                </div>
            </div>
            '''
        else:
            color = cover_choice.get("color", "#2c3e50")
            cover_html = f'''
            <div class="cover-page" style="background-color:{color};">
                <div class="cover-content">
                    <h1 class="cover-title">{book_title}</h1>
                    <p class="cover-author">by {author_name}</p>
                </div>
            </div>
            '''
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{book_title}</title>
    <style>
        body {{ font-family: Georgia, serif; margin: 0; padding: 20px; }}
        .cover-page {{ width: 100%; min-height: 100vh; position: relative; margin-bottom: 30px; }}
        .cover-image {{ width: 100%; height: auto; }}
        .cover-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                         background: rgba(0,0,0,0.3); display: flex; flex-direction: column; 
                         justify-content: center; align-items: center; color: white; }}
        .cover-title {{ font-size: 48px; margin: 0; text-shadow: 2px 2px 4px black; }}
        .cover-subtitle {{ font-size: 24px; margin: 10px 0; text-shadow: 1px 1px 2px black; }}
        .cover-author {{ font-size: 24px; text-shadow: 1px 1px 2px black; }}
        .cover-content {{ text-align: center; color: white; padding: 40px; }}
        .story {{ margin: 30px 0; padding: 20px; border-left: 4px solid #667eea; }}
        .question {{ font-weight: bold; font-size: 18px; margin-bottom: 10px; }}
        .answer {{ line-height: 1.6; }}
        img {{ max-width: 100%; border-radius: 5px; }}
        .caption {{ font-style: italic; color: #666; margin-top: 5px; }}
    </style>
</head>
<body>
    {cover_html}
"""
        
        image_counter = 0
        for i, story in enumerate(stories):
            question = story.get('question', '')
            answer = story.get('answer_text', '')
            
            html += f"""
    <div class="story">
        <div class="question">{question}</div>
        <div>{answer}</div>
"""
            
            for j, img in enumerate(story.get('images', [])):
                if img.get('base64'):
                    img_data = base64.b64decode(img['base64'])
                    img_filename = f"images/image_{i}_{j}.jpg"
                    zip_file.writestr(img_filename, img_data)
                    
                    html += f'        <img src="{img_filename}" alt="{img.get("caption", "")}">\n'
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
    
    return zip_buffer.getvalue()
