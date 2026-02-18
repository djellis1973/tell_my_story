# biography_publisher.py – PDF & DOCX with embedded images and optional cover designer
import streamlit as st
import json
import base64
from datetime import datetime
import re
from openai import OpenAI
import os
import io
import time
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fpdf import FPDF
from PIL import Image
import hashlib

st.set_page_config(page_title="Biography Publisher", page_icon="📚", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main-header { text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   margin: -1rem -1rem 2rem -1rem; border-radius: 0 0 20px 20px; color: white; }
    .story-card { border-left: 4px solid #667eea; padding: 1rem; margin: 1rem 0; background: #f8f9fa; border-radius: 0 10px 10px 0; }
    .export-box { border: 2px solid #667eea; border-radius: 10px; padding: 2rem; margin: 2rem 0; background: white; }
    .cover-preview { border: 2px solid #ddd; border-radius: 10px; padding: 20px; margin: 20px 0; background: white; }
    .simple-cover { width: 100%; aspect-ratio: 600/900; border: 2px solid #ddd; border-radius: 10px; 
                    display: flex; flex-direction: column; justify-content: space-between; padding: 30px 20px; 
                    box-sizing: border-box; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 0 auto; max-width: 450px; }
    .custom-cover { width: 100%; aspect-ratio: 600/900; border: 2px solid #ddd; border-radius: 10px; 
                    overflow: hidden; position: relative; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 0 auto; max-width: 450px; }
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
if 'cover_color' not in st.session_state:
    st.session_state.cover_color = "#2c3e50"
if 'selected_format' not in st.session_state:
    st.session_state.selected_format = "interview"
if 'include_toc' not in st.session_state:
    st.session_state.include_toc = True
if 'include_dates' not in st.session_state:
    st.session_state.include_dates = False

# Cover designer state
if 'use_custom_cover' not in st.session_state:
    st.session_state.use_custom_cover = False
if 'cover_design' not in st.session_state:
    st.session_state.cover_design = {
        "title": "",
        "subtitle": "",
        "author": "",
        "cover_type": "Simple",
        "title_font": "Georgia",
        "title_color": "#000000",
        "background_color": "#FFFFFF",
        "cover_image": None
    }
if 'cover_image_path' not in st.session_state:
    st.session_state.cover_image_path = None

# ============================================================================
# COVER DESIGNER FUNCTIONS
# ============================================================================
def save_cover_image(uploaded_file, title, author, subtitle):
    """Save uploaded cover image and return path"""
    if uploaded_file:
        # Create directory if it doesn't exist
        os.makedirs("temp_covers", exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c.isspace()).replace(" ", "_")[:30]
        filename = f"temp_covers/cover_{safe_title}_{timestamp}.jpg"
        
        # Save the file
        with open(filename, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        return filename
    return None

def create_simple_cover_html(title, author, subtitle, background_color, title_color, title_font):
    """Generate HTML for simple cover preview"""
    subtitle_html = f'<h2 style="font-family:{title_font}; color:{title_color}; font-size:24px; margin:5px 0 0 0;">{subtitle}</h2>' if subtitle else ''
    
    return f'''
    <div style="width:100%; max-width:450px; margin:0 auto;">
        <div class="simple-cover" style="background-color:{background_color};">
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
        <div class="custom-cover">
            <img src="data:image/jpeg;base64,{img_base64}" style="width:100%; height:100%; object-fit:cover;">
            <div style="position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.3); display:flex; flex-direction:column; justify-content:space-between; padding:30px 20px; box-sizing:border-box;">
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

def render_cover_designer():
    """Display the cover designer interface"""
    st.markdown("## 🎨 Cover Designer")
    st.markdown("Design your book cover - Portrait format (6\" x 9\")")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Cover Options**")
        
        # Editable fields
        title = st.text_input("Book Title", value=st.session_state.cover_design.get('title', st.session_state.book_title))
        subtitle = st.text_input("Subtitle (optional)", value=st.session_state.cover_design.get('subtitle', ''), 
                                placeholder="A brief subtitle or tagline")
        author = st.text_input("Author Name", value=st.session_state.cover_design.get('author', st.session_state.author_name))
        
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
        
        # Update session state with current values
        st.session_state.cover_design.update({
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "cover_type": cover_type,
            "title_font": title_font,
            "title_color": title_color,
            "background_color": background_color
        })
        
        if uploaded_cover:
            st.session_state.cover_image_path = save_cover_image(uploaded_cover, title, author, subtitle)
    
    with col2:
        st.markdown("**Preview (6\" x 9\" portrait)**")
        
        # Generate preview
        if st.session_state.cover_image_path:
            preview_html = create_custom_cover_html(
                st.session_state.cover_design['title'],
                st.session_state.cover_design['author'],
                st.session_state.cover_design['subtitle'],
                st.session_state.cover_image_path,
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
            st.rerun()

# ============================================================================
# PDF GENERATION FUNCTION (with cover and images)
# ============================================================================
class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, st.session_state.book_title, 0, 0, 'L')
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')
            self.ln(15)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Generated by Tell My Story • {datetime.now().strftime("%Y")}', 0, 0, 'C')

def generate_pdf_with_cover(book_title, author_name, stories, format_style, include_toc, include_dates, 
                           use_custom_cover=False, cover_design=None, cover_image_path=None):
    """Generate PDF with optional custom cover"""
    pdf = PDF()
    
    # Add cover page
    pdf.add_page()
    
    if use_custom_cover and cover_image_path and os.path.exists(cover_image_path):
        # Use custom cover with image
        pdf.image(cover_image_path, x=0, y=0, w=210, h=297)
        
        # Add text overlay
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 30)
        
        # Calculate positions for centered text
        title = cover_design.get('title', book_title)
        author = cover_design.get('author', author_name)
        subtitle = cover_design.get('subtitle', '')
        
        # Title
        pdf.set_xy(0, 80)
        pdf.cell(210, 20, title, 0, 1, 'C')
        
        # Subtitle if exists
        if subtitle:
            pdf.set_font('Arial', '', 16)
            pdf.cell(210, 15, subtitle, 0, 1, 'C')
        
        # Author
        pdf.set_font('Arial', '', 16)
        pdf.set_xy(0, 200)
        pdf.cell(210, 15, f'by {author}', 0, 1, 'C')
        
        # Generation date
        pdf.set_font('Arial', 'I', 10)
        pdf.set_xy(0, 250)
        pdf.cell(210, 10, f'Generated on {datetime.now().strftime("%B %d, %Y")}', 0, 1, 'C')
    else:
        # Use simple cover with color
        pdf.set_fill_color(102, 126, 234)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 30)
        pdf.cell(0, 40, '', 0, 1)
        pdf.cell(0, 20, book_title, 0, 1, 'C')
        pdf.set_font('Arial', '', 16)
        pdf.cell(0, 10, f'by {author_name}', 0, 1, 'C')
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Generated on {datetime.now().strftime("%B %d, %Y")}', 0, 1, 'C')
    
    # Table of Contents
    pdf.add_page()
    if include_toc:
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', 'B', 20)
        pdf.cell(0, 10, 'Table of Contents', 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font('Arial', '', 12)
        
        if isinstance(stories, list):
            current_session = None
            for i, story in enumerate(stories, 1):
                session_id = story.get('session_id', '1')
                if session_id != current_session:
                    session_title = story.get('session_title', f'Session {session_id}')
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 8, session_title, 0, 1)
                    current_session = session_id
                question = story.get('question', f'Story {i}')
                pdf.set_font('Arial', '', 12)
                pdf.cell(10, 6, f'{i}.', 0, 0)
                pdf.cell(0, 6, question[:50] + "..." if len(question) > 50 else question, 0, 1)
    
    # Content
    if isinstance(stories, list):
        current_session = None
        story_counter = 1
        for story in stories:
            session_id = story.get('session_id', '1')
            if session_id != current_session:
                session_title = story.get('session_title', f'Session {session_id}')
                pdf.add_page()
                pdf.set_font('Arial', 'B', 18)
                pdf.cell(0, 10, session_title, 0, 1, 'L')
                pdf.ln(5)
                current_session = session_id
            
            question = story.get('question', '')
            answer_text = story.get('answer_text', '')
            images = story.get('images', [])
            
            if format_style == 'interview':
                pdf.set_font('Arial', 'B', 12)
                pdf.multi_cell(0, 6, f'Q: {question}')
                pdf.ln(2)
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 6, answer_text)
            elif format_style == 'biography':
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 6, answer_text)
            else:  # memoir
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 8, f'Chapter {story_counter}: {question}', 0, 1)
                pdf.ln(4)
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 6, answer_text)
            
            # Embed images
            for img_data in images:
                b64 = img_data.get('base64')
                caption = img_data.get('caption', '')
                if b64:
                    try:
                        img_bytes = base64.b64decode(b64)
                        img_path = f'/tmp/img_{img_data["id"]}_{hashlib.md5(img_bytes).hexdigest()[:8]}.jpg'
                        with open(img_path, 'wb') as f:
                            f.write(img_bytes)
                        pdf.image(img_path, w=100)
                        os.remove(img_path)
                        if caption:
                            pdf.set_font('Arial', 'I', 10)
                            pdf.cell(0, 6, f'📝 {caption}', 0, 1, 'C')
                        pdf.ln(5)
                    except:
                        pass
            pdf.ln(5)
            story_counter += 1

    return pdf.output(dest='S').encode('latin1')

# ============================================================================
# DOCX GENERATION WITH IMAGES AND COVER
# ============================================================================
def generate_docx_with_cover(book_title, author_name, stories, format_style, include_toc, include_dates,
                            use_custom_cover=False, cover_design=None, cover_image_path=None):
    """Generate DOCX with optional custom cover"""
    doc = Document()
    
    # Title page
    if use_custom_cover and cover_image_path and os.path.exists(cover_image_path):
        # Add cover image
        doc.add_picture(cover_image_path, width=Inches(6))
        doc.add_paragraph()
    
    # Title
    title = doc.add_heading(book_title, 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Subtitle if exists
    if use_custom_cover and cover_design and cover_design.get('subtitle'):
        subtitle = doc.add_paragraph(cover_design['subtitle'])
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.style = 'Subtitle'
    
    # Author
    author = doc.add_paragraph(f'by {author_name}')
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Date
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
# SIDEBAR SETTINGS
# ============================================================================
with st.sidebar:
    st.header("⚙️ Publication Settings")
    
    st.subheader("Book Details")
    st.session_state.book_title = st.text_input("Book Title", value=st.session_state.book_title)
    st.session_state.author_name = st.text_input("Author Name", value=st.session_state.author_name)
    
    st.subheader("Cover Options")
    
    # Cover type selector
    cover_option = st.radio(
        "Cover Type",
        ["Simple Default Cover", "Custom Designed Cover"],
        key="cover_option_radio"
    )
    
    st.session_state.use_custom_cover = (cover_option == "Custom Designed Cover")
    
    # If custom cover is selected, show cover designer button
    if st.session_state.use_custom_cover:
        if st.button("🎨 Open Cover Designer", type="primary", use_container_width=True):
            st.session_state.show_cover_designer = not st.session_state.get('show_cover_designer', False)
        
        # Simple color picker for simple cover
    else:
        st.session_state.cover_color = st.color_picker("Cover Color", value=st.session_state.cover_color)
    
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
                    
                    # Update cover design with default values
                    st.session_state.cover_design['title'] = st.session_state.book_title
                    st.session_state.cover_design['author'] = st.session_state.author_name
        except Exception as e:
            st.error(f"Error loading file: {e}")

# ============================================================================
# MAIN INTERFACE
# ============================================================================

# Show cover designer if enabled
if st.session_state.get('show_cover_designer', False):
    render_cover_designer()
    st.divider()

# Main content
if st.session_state.stories_data:
    stories_data = st.session_state.stories_data
    stories = stories_data.get('stories', [])
    user_profile = stories_data.get('user_profile', {})

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
        for i, story in enumerate(stories[:3]):
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
                docx_bytes = generate_docx_with_cover(
                    st.session_state.book_title,
                    st.session_state.author_name,
                    stories,
                    st.session_state.selected_format,
                    st.session_state.include_toc,
                    st.session_state.include_dates,
                    st.session_state.use_custom_cover,
                    st.session_state.cover_design if st.session_state.use_custom_cover else None,
                    st.session_state.cover_image_path if st.session_state.use_custom_cover else None
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
        if st.button("📕 Generate PDF", type="primary", use_container_width=True):
            with st.spinner("Creating PDF with images..."):
                pdf_bytes = generate_pdf_with_cover(
                    st.session_state.book_title,
                    st.session_state.author_name,
                    stories,
                    st.session_state.selected_format,
                    st.session_state.include_toc,
                    st.session_state.include_dates,
                    st.session_state.use_custom_cover,
                    st.session_state.cover_design if st.session_state.use_custom_cover else None,
                    st.session_state.cover_image_path if st.session_state.use_custom_cover else None
                )
                filename = f"{st.session_state.book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.download_button(
                    "📥 Download PDF", 
                    data=pdf_bytes, 
                    file_name=filename, 
                    mime="application/pdf", 
                    use_container_width=True,
                    key="pdf_download"
                )
    
    with col3:
        if st.button("📄 Preview Text", use_container_width=True):
            # Simple text preview
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
    3. Choose between **Simple Default Cover** or **Custom Designed Cover**
    4. If choosing custom cover, open the Cover Designer and create your design
    5. Customize your book settings
    6. Generate PDF or DOCX with embedded images
    """)

st.markdown("---")
st.caption(f"Biography Publisher • {datetime.now().year}")

