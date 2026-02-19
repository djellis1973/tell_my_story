import streamlit as st
import json
import base64
from datetime import datetime
import re
import os
import io
import tempfile
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from fpdf import FPDF
import hashlib
import time

# ============================================================================
# CELEBRATION BALLOONS FUNCTION
# ============================================================================
def show_celebration():
    """Show animated balloons when book is successfully generated"""
    # Store in session state that we've shown balloons
    st.session_state.balloons_shown = True
    
    balloons_html = """
    <style>
    @keyframes float {
        0% { transform: translateY(100vh) scale(0.5); opacity: 1; }
        100% { transform: translateY(-100vh) scale(1.2); opacity: 0; }
    }
    .balloon {
        position: fixed;
        bottom: -100px;
        width: 50px;
        height: 70px;
        background: radial-gradient(circle at 30% 30%, #fff, #ff6b6b);
        border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
        animation: float 8s ease-in forwards;
        z-index: 9999;
        pointer-events: none;
    }
    .balloon:nth-child(2) { left: 10%; background: radial-gradient(circle at 30% 30%, #fff, #ffd93d); animation-delay: 0.5s; }
    .balloon:nth-child(3) { left: 20%; background: radial-gradient(circle at 30% 30%, #fff, #6bff6b); animation-delay: 1s; }
    .balloon:nth-child(4) { left: 30%; background: radial-gradient(circle at 30% 30%, #fff, #6b6bff); animation-delay: 1.5s; }
    .balloon:nth-child(5) { left: 40%; background: radial-gradient(circle at 30% 30%, #fff, #ff6bff); animation-delay: 2s; }
    .balloon:nth-child(6) { left: 50%; background: radial-gradient(circle at 30% 30%, #fff, #6bffff); animation-delay: 2.5s; }
    .balloon:nth-child(7) { left: 60%; background: radial-gradient(circle at 30% 30%, #fff, #ffb06b); animation-delay: 3s; }
    .balloon:nth-child(8) { left: 70%; background: radial-gradient(circle at 30% 30%, #fff, #ff6b6b); animation-delay: 3.5s; }
    .balloon:nth-child(9) { left: 80%; background: radial-gradient(circle at 30% 30%, #fff, #ffd93d); animation-delay: 4s; }
    .balloon:nth-child(10) { left: 90%; background: radial-gradient(circle at 30% 30%, #fff, #6bff6b); animation-delay: 4.5s; }
    .balloon::after {
        content: '';
        position: absolute;
        bottom: -15px;
        left: 50%;
        transform: translateX(-50%);
        width: 2px;
        height: 30px;
        background: linear-gradient(to bottom, #888, #ccc);
    }
    .celebration-message {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px 50px;
        border-radius: 20px;
        font-size: 32px;
        font-weight: bold;
        z-index: 10000;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        animation: pop-in 0.5s ease-out;
        text-align: center;
    }
    @keyframes pop-in {
        0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
        80% { transform: translate(-50%, -50%) scale(1.1); }
        100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
    }
    </style>
    <div class="celebration-message">
        🎉 Congratulations! 🎉<br>
        <span style="font-size: 24px;">Your book has been published!</span>
    </div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    <div class="balloon"></div>
    """
    st.components.v1.html(balloons_html, height=0)
    
    # Also use Streamlit's balloons after a tiny delay
    time.sleep(0.5)
    st.balloons()

# ============================================================================
# CLEAN TEXT FUNCTION
# ============================================================================
def clean_text(text):
    """Convert HTML entities to regular characters"""
    if not text:
        return text
    
    # Convert &nbsp; to space
    text = text.replace('&nbsp;', ' ')
    
    # Also handle other common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

# ============================================================================
# PDF CLASS (FIXED - returns bytes directly)
# ============================================================================
class PDF(FPDF):
    def __init__(self, custom_cover=None):
        super().__init__()
        self.custom_cover = custom_cover
        
    def header(self):
        if self.page_no() > 1:
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, 'Tell My Story', 0, 0, 'L')
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')
            self.ln(15)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        year = datetime.now().strftime("%Y")
        self.cell(0, 10, f'Generated by Tell My Story - {year}', 0, 0, 'C')
    
    def safe_text(self, text):
        """Convert text to safe ASCII, replacing problematic characters"""
        if not text:
            return ""
        # Replace common special characters
        text = text.replace('•', '-')
        text = text.replace('…', '...')
        text = text.replace('“', '"')
        text = text.replace('”', '"')
        text = text.replace('‘', "'")
        text = text.replace('’', "'")
        text = text.replace('—', '-')
        text = text.replace('–', '-')
        # Encode to ASCII, ignoring errors
        return text.encode('ascii', 'ignore').decode('ascii')
    
    def add_cover_page(self, book_title, author_name, cover_type="simple", custom_cover=None):
        """Add cover page - either simple gradient or custom designed cover"""
        self.add_page()
        
        if cover_type == "custom" and custom_cover and custom_cover.get('cover_image') and os.path.exists(custom_cover['cover_image']):
            # Use the full cover image as-is, no text overlay
            try:
                self.image(custom_cover['cover_image'], x=0, y=0, w=210, h=297)
            except Exception as e:
                # Fallback to simple cover
                self.add_simple_cover(book_title, author_name)
        else:
            self.add_simple_cover(book_title, author_name)
    
    def add_simple_cover(self, book_title, author_name):
        """Simple gradient cover"""
        safe_title = self.safe_text(book_title)
        safe_author = self.safe_text(author_name)
        
        self.set_fill_color(102, 126, 234)
        self.rect(0, 0, 210, 297, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 30)
        self.cell(0, 40, '', 0, 1)
        self.cell(0, 20, safe_title, 0, 1, 'C')
        self.set_font('Arial', '', 16)
        self.cell(0, 10, f'by {safe_author}', 0, 1, 'C')
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%B %d, %Y")}', 0, 1, 'C')

# ============================================================================
# PDF GENERATION (FIXED - returns bytes, no double encoding)
# ============================================================================
def generate_pdf(book_title, author_name, stories, format_style, include_toc=True, include_dates=False, cover_type="simple", custom_cover=None):
    """Generate PDF with embedded images"""
    pdf = PDF(custom_cover)
    
    # Add cover page
    pdf.add_cover_page(book_title, author_name, cover_type, custom_cover)
    
    # Table of Contents
    if include_toc and stories:
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', 'B', 20)
        pdf.cell(0, 10, 'Table of Contents', 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font('Arial', '', 12)
        
        current_session = None
        for i, story in enumerate(stories, 1):
            session_id = story.get('session_id', '1')
            if session_id != current_session:
                session_title = pdf.safe_text(story.get('session_title', f'Session {session_id}'))
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 8, session_title, 0, 1)
                current_session = session_id
            question = pdf.safe_text(story.get('question', f'Story {i}'))
            pdf.set_font('Arial', '', 12)
            pdf.cell(10, 6, f'{i}.', 0, 0)
            pdf.cell(0, 6, question[:50] + "..." if len(question) > 50 else question, 0, 1)
        pdf.add_page()

    # Content
    if stories:
        current_session = None
        story_counter = 1
        for story in stories:
            session_id = story.get('session_id', '1')
            if session_id != current_session:
                session_title = pdf.safe_text(story.get('session_title', f'Session {session_id}'))
                pdf.set_font('Arial', 'B', 18)
                pdf.cell(0, 10, session_title, 0, 1, 'C')  # Centered session title
                pdf.ln(5)
                current_session = session_id
            
            question = pdf.safe_text(story.get('question', ''))
            answer_text = pdf.safe_text(story.get('answer_text', ''))
            images = story.get('images', [])
            
            if format_style == 'interview':
                pdf.set_font('Arial', 'B', 12)
                pdf.multi_cell(0, 6, f'Q: {question}')
                pdf.ln(2)
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 6, answer_text)
            else:  # biography format - just the answer
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 6, answer_text)
            
            # Embed images
            for img_data in images:
                b64 = img_data.get('base64')
                caption = pdf.safe_text(img_data.get('caption', ''))
                if b64:
                    try:
                        img_bytes = base64.b64decode(b64)
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                            tmp.write(img_bytes)
                            tmp_path = tmp.name
                        pdf.image(tmp_path, w=100)
                        os.unlink(tmp_path)
                        if caption:
                            pdf.set_font('Arial', 'I', 10)
                            pdf.cell(0, 6, f'Caption: {caption}', 0, 1, 'C')
                        pdf.ln(5)
                    except Exception as e:
                        print(f"Could not embed image: {e}")
            pdf.ln(5)
            story_counter += 1

    # Return the PDF as bytes directly (output() already returns bytes)
    return pdf.output(dest='S')

# ============================================================================
# DOCX GENERATION (FIXED - with centered tables)
# ============================================================================
def generate_docx(book_title, author_name, stories, format_style, include_toc=True, include_dates=False, cover_type="simple", custom_cover=None):
    """Generate DOCX with embedded images and centered content blocks"""
    doc = Document()
    
    # Set document margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)
    
    # Set normal style
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    
    # Title page - use full cover image if available
    if cover_type == "custom" and custom_cover and custom_cover.get('cover_image') and os.path.exists(custom_cover['cover_image']):
        # Add the full cover image - no text overlay
        try:
            doc.add_picture(custom_cover['cover_image'], width=Inches(6))
            last_paragraph = doc.paragraphs[-1]
            last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_page_break()
        except Exception as e:
            # Fallback to text title
            title = doc.add_heading(book_title, 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author = doc.add_paragraph(f'by {author_name}')
            author.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_page_break()
    else:
        # Simple text title
        title = doc.add_heading(book_title, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author = doc.add_paragraph(f'by {author_name}')
        author.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_para = doc.add_paragraph(f'Generated on {datetime.now().strftime("%B %d, %Y")}')
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_page_break()
    
    # TOC
    if include_toc and stories:
        toc = doc.add_heading('Table of Contents', 1)
        toc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        current_session = None
        for i, story in enumerate(stories, 1):
            session_id = story.get('session_id', '1')
            if session_id != current_session:
                session_title = story.get('session_title', f'Session {session_id}')
                p = doc.add_paragraph()
                p.add_run(session_title).bold = True
                p.paragraph_format.left_indent = Inches(0.25)
                current_session = session_id
            question = clean_text(story.get('question', f'Story {i}'))
            p = doc.add_paragraph(f'  {i}. {question[:50]}...' if len(question) > 50 else f'  {i}. {question}')
            p.paragraph_format.left_indent = Inches(0.5)
        doc.add_page_break()
    
    # Content with centered tables
    if stories:
        current_session = None
        story_counter = 1
        for story in stories:
            session_id = story.get('session_id', '1')
            
            # Add session header if new session - CENTERED
            if session_id != current_session:
                session_title = story.get('session_title', f'Session {session_id}')
                heading = doc.add_heading(session_title, 1)
                heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
                current_session = session_id
            
            question = clean_text(story.get('question', ''))
            answer_text = clean_text(story.get('answer_text', ''))
            images = story.get('images', [])
            
            # Create centered container table (6 inches wide)
            table = doc.add_table(rows=1, cols=1)
            table.autofit = False
            table.allow_autofit = False
            table.columns[0].width = Inches(6.0)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            
            # Get the cell
            cell = table.cell(0, 0)
            
            if format_style == 'interview' and question:
                # Question inside cell (left-aligned)
                q_para = cell.paragraphs[0]
                q_run = q_para.add_run(f'Q: {question}')
                q_run.bold = True
                q_run.italic = True
                q_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                q_para.paragraph_format.space_after = Pt(6)
                
                # Answer inside cell
                if answer_text:
                    a_para = cell.add_paragraph(answer_text)
                    a_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    a_para.paragraph_format.first_line_indent = Inches(0.25)
            else:
                # Just answer (biography style)
                if answer_text:
                    p = cell.paragraphs[0]
                    p.add_run(answer_text)
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p.paragraph_format.first_line_indent = Inches(0.25)
            
            # Embed images (outside table so they can be centered independently)
            for img_data in images:
                b64 = img_data.get('base64')
                caption = clean_text(img_data.get('caption', ''))
                if b64:
                    try:
                        img_bytes = base64.b64decode(b64)
                        img_stream = io.BytesIO(img_bytes)
                        doc.add_picture(img_stream, width=Inches(4))
                        last_paragraph = doc.paragraphs[-1]
                        last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        if caption:
                            cap = doc.add_paragraph(caption)
                            cap.style = 'Caption'
                            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    except Exception as e:
                        print(f"Could not embed image: {e}")
            
            # Add spacing between stories
            doc.add_paragraph()
            story_counter += 1
    
    # Save to bytes
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    return docx_bytes

# ============================================================================
# HTML GENERATION (FIXED - uses full cover image, no text overlay)
# ============================================================================
def generate_html(book_title, author_name, stories, format_style, include_toc=True, include_dates=False, cover_type="simple", custom_cover=None):
    """Generate beautiful HTML with embedded images"""
    
    cover_html = ""
    
    if cover_type == "custom" and custom_cover and custom_cover.get('cover_image') and os.path.exists(custom_cover['cover_image']):
        # Convert image to base64 for HTML embedding
        with open(custom_cover['cover_image'], 'rb') as f:
            img_data = f.read()
        img_b64 = base64.b64encode(img_data).decode()
        
        # Use the full cover image - no text overlay
        cover_html = f"""
        <div class="cover-page">
            <img src="data:image/jpeg;base64,{img_b64}" style="width:100%; max-width:800px; margin:0 auto; display:block;">
        </div>
        <hr>
        """
    else:
        # Simple text header
        cover_html = f"""
        <div class="book-header">
            <h1>{book_title}</h1>
            <div class="author">by {author_name}</div>
            <div class="date">Generated on {datetime.now().strftime("%B %d, %Y")}</div>
        </div>
        """
    
    # Build TOC
    toc_html = ""
    if include_toc and stories:
        toc_html = "<h2>Table of Contents</h2><ul class='toc'>"
        current_session = None
        for i, story in enumerate(stories, 1):
            session_id = story.get('session_id', '1')
            if session_id != current_session:
                session_title = story.get('session_title', f'Session {session_id}')
                toc_html += f"<li class='toc-session'>{session_title}</li>"
                current_session = session_id
            question = clean_text(story.get('question', f'Story {i}'))
            toc_html += f"<li class='toc-story'><a href='#story-{i}'>{i}. {question[:50]}...</a></li>"
        toc_html += "</ul><hr>"
    
    # Build content
    content_html = ""
    current_session = None
    for i, story in enumerate(stories, 1):
        session_id = story.get('session_id', '1')
        if session_id != current_session:
            session_title = story.get('session_title', f'Session {session_id}')
            content_html += f"<h1 class='session-title'>{session_title}</h1>"
            current_session = session_id
        
        question = clean_text(story.get('question', ''))
        answer_text = clean_text(story.get('answer_text', ''))
        images = story.get('images', [])
        
        # Add anchor for TOC
        content_html += f"<div class='story' id='story-{i}'>"
        
        if format_style == 'interview' and question:
            content_html += f"<h2 class='question'>Q: {question}</h2>"
        
        # Convert newlines to paragraphs
        paragraphs = answer_text.split('\n')
        for p in paragraphs:
            if p.strip():
                content_html += f"<p>{p}</p>"
        
        # Add images
        if images:
            content_html += "<div class='image-gallery'>"
            for img_data in images:
                b64 = img_data.get('base64')
                caption = clean_text(img_data.get('caption', ''))
                if b64:
                    content_html += f"""
                    <div class='image-item'>
                        <img src='data:image/jpeg;base64,{b64}' alt='{caption}'>
                        <div class='image-caption'>📝 {caption}</div>
                    </div>
                    """
            content_html += "</div>"
        
        content_html += "</div><hr>"
    
    # Complete HTML with styling
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{book_title}</title>
    <style>
        body {{
            font-family: 'Georgia', serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fafafa;
            color: #333;
            line-height: 1.6;
        }}
        .book-header {{
            text-align: center;
            padding: 60px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: -40px -20px 40px -20px;
            border-radius: 0 0 20px 20px;
        }}
        .cover-page {{
            margin: -40px -20px 40px -20px;
            text-align: center;
        }}
        h1 {{
            font-size: 48px;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .author {{
            font-size: 24px;
            margin-top: 10px;
            opacity: 0.9;
        }}
        .date {{
            font-size: 14px;
            margin-top: 20px;
            opacity: 0.8;
        }}
        .toc {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 30px 0;
        }}
        .toc ul {{
            list-style: none;
            padding: 0;
        }}
        .toc-session {{
            font-weight: bold;
            font-size: 18px;
            margin-top: 15px;
            color: #667eea;
        }}
        .toc-story {{
            margin-left: 20px;
        }}
        .toc-story a {{
            color: #333;
            text-decoration: none;
        }}
        .toc-story a:hover {{
            color: #667eea;
            text-decoration: underline;
        }}
        .session-title {{
            color: #764ba2;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-top: 40px;
            text-align: center;
        }}
        .story {{
            margin: 30px 0;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }}
        .question {{
            color: #667eea;
            font-style: italic;
        }}
        .image-gallery {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin: 20px 0;
            justify-content: center;
        }}
        .image-item {{
            flex: 1 1 300px;
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .image-item img {{
            max-width: 100%;
            height: auto;
            border-radius: 5px;
        }}
        .image-caption {{
            text-align: center;
            font-size: 14px;
            color: #666;
            margin-top: 10px;
            font-style: italic;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 40px 0;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 60px;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .book-header {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
        }}
    </style>
</head>
<body>
    {cover_html}
    
    {toc_html}
    
    <div class="content">
        {content_html}
    </div>
    
    <div class="footer">
        Generated by Tell My Story • {datetime.now().year}
    </div>
</body>
</html>"""
    return html

# ============================================================================
# MAIN PUBLISHER INTERFACE
# ============================================================================
def main():
    st.set_page_config(page_title="Biography Publisher", page_icon="📚", layout="wide")
    
    st.markdown("""
    <style>
        .main-header { text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       margin: -1rem -1rem 2rem -1rem; border-radius: 0 0 20px 20px; color: white; }
        .story-card { border-left: 4px solid #667eea; padding: 1rem; margin: 1rem 0; background: #f8f9fa; border-radius: 0 10px 10px 0; }
        .export-box { border: 2px solid #667eea; border-radius: 10px; padding: 2rem; margin: 2rem 0; background: white; }
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
    if 'cover_type' not in st.session_state:
        st.session_state.cover_type = "simple"
    if 'custom_cover_data' not in st.session_state:
        st.session_state.custom_cover_data = None
    if 'format_style' not in st.session_state:
        st.session_state.format_style = "interview"
    if 'include_toc' not in st.session_state:
        st.session_state.include_toc = True
    if 'balloons_shown' not in st.session_state:
        st.session_state.balloons_shown = False
    
    # Sidebar
    with st.sidebar:
        st.header("📂 Upload")
        uploaded_file = st.file_uploader("Upload JSON from Tell My Story", type=['json'])
        if uploaded_file:
            try:
                st.session_state.stories_data = json.load(uploaded_file)
                st.success("✅ Uploaded successfully!")
                user_profile = st.session_state.stories_data.get('user_profile', {})
                if user_profile:
                    first = user_profile.get('first_name', '')
                    last = user_profile.get('last_name', '')
                    if first and last:
                        st.session_state.author_name = f"{first} {last}"
                        st.session_state.book_title = f"The Story of {first} {last}"
                
                # Load custom cover if available
                if 'cover_design' in st.session_state.stories_data:
                    st.session_state.custom_cover_data = st.session_state.stories_data['cover_design']
            except Exception as e:
                st.error(f"Error loading file: {e}")
        
        st.divider()
        st.header("⚙️ Settings")
        st.session_state.book_title = st.text_input("Book Title", value=st.session_state.book_title)
        st.session_state.author_name = st.text_input("Author Name", value=st.session_state.author_name)
        
        st.session_state.format_style = st.radio(
            "Format Style",
            ["interview", "biography"],
            format_func=lambda x: {"interview": "📝 Show Questions & Answers", "biography": "📖 Just Answers (Biography Style)"}[x],
            index=0 if st.session_state.format_style == "interview" else 1
        )
        
        st.session_state.include_toc = st.checkbox("Include Table of Contents", value=st.session_state.include_toc)
        
        # Custom cover info
        if st.session_state.custom_cover_data:
            with st.expander("🎨 Custom Cover Preview"):
                if st.session_state.custom_cover_data.get('cover_image') and os.path.exists(st.session_state.custom_cover_data['cover_image']):
                    st.image(st.session_state.custom_cover_data['cover_image'], width=200)
                st.markdown(f"**Title:** {st.session_state.custom_cover_data.get('title', 'N/A')}")
                st.markdown(f"**Author:** {st.session_state.custom_cover_data.get('author', 'N/A')}")
    
    # Main content
    if st.session_state.stories_data:
        stories_data = st.session_state.stories_data
        stories = stories_data.get('stories', [])
        
        # Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Stories", len(stories))
        with col2:
            st.metric("Sessions", stories_data.get('summary', {}).get('total_sessions', 1))
        with col3:
            st.metric("Export Date", stories_data.get('export_date', 'Unknown')[:10])
        
        # Preview
        with st.expander("📖 Preview Stories", expanded=False):
            for i, story in enumerate(stories[:3]):
                st.markdown(f"**{'Q: ' + story.get('question', '') if st.session_state.format_style == 'interview' else story.get('session_title', 'Session')}**")
                st.markdown(f"*{story.get('answer_text', '')[:200]}...*")
                if story.get('images'):
                    st.caption(f"📸 {len(story['images'])} image(s) attached")
                st.divider()
            if len(stories) > 3:
                st.info(f"... and {len(stories) - 3} more stories")
        
        # Generate buttons
        st.subheader("🖨️ Generate Your Book")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Generate DOCX", type="primary", use_container_width=True):
                with st.spinner("Creating Word document with images..."):
                    docx_bytes = generate_docx(
                        st.session_state.book_title,
                        st.session_state.author_name,
                        stories,
                        st.session_state.format_style,
                        st.session_state.include_toc,
                        False,
                        "custom" if st.session_state.custom_cover_data else "simple",
                        st.session_state.custom_cover_data
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
                    # Show celebration AFTER download button appears
                    st.session_state.balloons_shown = False
                    time.sleep(0.5)
                    show_celebration()
        
        with col2:
            if st.button("📕 Generate PDF", type="primary", use_container_width=True):
                with st.spinner("Creating PDF with images..."):
                    pdf_bytes = generate_pdf(
                        st.session_state.book_title,
                        st.session_state.author_name,
                        stories,
                        st.session_state.format_style,
                        st.session_state.include_toc,
                        False,
                        "custom" if st.session_state.custom_cover_data else "simple",
                        st.session_state.custom_cover_data
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
                    # Show celebration AFTER download button appears
                    st.session_state.balloons_shown = False
                    time.sleep(0.5)
                    show_celebration()
        
        with col3:
            if st.button("🌐 Generate HTML", type="primary", use_container_width=True):
                with st.spinner("Creating HTML page..."):
                    html_content = generate_html(
                        st.session_state.book_title,
                        st.session_state.author_name,
                        stories,
                        st.session_state.format_style,
                        st.session_state.include_toc,
                        False,
                        "custom" if st.session_state.custom_cover_data else "simple",
                        st.session_state.custom_cover_data
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
                    # Show celebration AFTER download button appears
                    st.session_state.balloons_shown = False
                    time.sleep(0.5)
                    show_celebration()
        
        # Preview text
        if st.button("📄 Preview Text"):
            preview = f"{st.session_state.book_title}\nby {st.session_state.author_name}\n\n"
            for i, story in enumerate(stories[:5]):
                if st.session_state.format_style == 'interview':
                    preview += f"Q: {story.get('question', '')}\n"
                preview += f"{story.get('answer_text', '')[:200]}...\n\n"
            st.session_state.formatted_text = preview
        
        if st.session_state.formatted_text:
            with st.expander("📄 Text Preview", expanded=True):
                st.text_area("Preview", st.session_state.formatted_text, height=300)
    
    else:
        st.info("📚 Upload your stories JSON file using the sidebar to begin.")
        st.markdown("""
        ### Features:
        - 🎨 **Custom Cover Support** - Use your designed cover exactly as created
        - 📝 **Interview Format** - Shows questions and answers
        - 📖 **Biography Format** - Just the answers with session titles as chapter headings
        - 🖼️ **Embedded Images** - All your photos included
        - 🌐 **HTML Export** - Beautiful, printable web pages
        - 🎈 **Celebration Animation** - Balloons when your book is ready!
        """)

if __name__ == "__main__":
    main()
