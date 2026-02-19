import streamlit as st
from datetime import datetime
import io
import base64
import os
import re
import html  # Add this import
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def clean_text(text):
    """Convert HTML entities to regular characters"""
    if not text:
        return text
    
    # Convert &nbsp; to space (this is the main fix)
    text = text.replace('&nbsp;', ' ')
    
    # Also handle other common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Remove HTML tags but keep paragraph structure
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()

def show_celebration():
    """Show a celebration animation when book is generated"""
    st.balloons()
    st.success("🎉 Your book has been generated successfully!")

def generate_docx(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_image=None, cover_choice="simple"):
    """Generate a Word document from stories"""
    
    doc = Document()
    
    # Set document margins (1 inch margins = 14400 twips)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Set document styling
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT  # Text inside is left-aligned
    style.paragraph_format.first_line_indent = Inches(0.25)  # Add paragraph indents
    
    # COVER PAGE - Based on user choice
    if cover_choice == "uploaded" and cover_image:
        try:
            image_stream = io.BytesIO(cover_image)
            
            # Add the cover image centered
            doc.add_picture(image_stream, width=Inches(5))
            last_paragraph = doc.paragraphs[-1]
            last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add a page break after the cover image only
            doc.add_page_break()
            
        except Exception as e:
            # Fallback to simple text cover
            cover_para = doc.add_paragraph()
            cover_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cover_run = cover_para.add_run(title)
            cover_run.font.size = Pt(42)
            cover_run.font.bold = True
            
            author_para = doc.add_paragraph()
            author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author_run = author_para.add_run(f"by {author}")
            author_run.font.size = Pt(24)
            author_run.font.italic = True
            
            doc.add_page_break()
    else:
        # Simple text cover only
        cover_para = doc.add_paragraph()
        cover_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cover_run = cover_para.add_run(title)
        cover_run.font.size = Pt(42)
        cover_run.font.bold = True
        
        author_para = doc.add_paragraph()
        author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author_run = author_para.add_run(f"by {author}")
        author_run.font.size = Pt(24)
        author_run.font.italic = True
        
        doc.add_page_break()
    
    # Add publication info (on its own page after cover)
    copyright_para = doc.add_paragraph()
    copyright_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    copyright_para.add_run(f"© {datetime.now().year} {author}. All rights reserved.")
    
    # Add a blank line after copyright
    doc.add_paragraph()
    
    # Table of Contents
    if include_toc:
        doc.add_page_break()
        toc_para = doc.add_paragraph()
        toc_run = toc_para.add_run("Table of Contents")
        toc_run.font.size = Pt(18)
        toc_run.font.bold = True
        toc_para.alignment = WD_ALIGN_PARAGRAPH.CENTER  # Center the TOC title
        toc_para.paragraph_format.space_after = Pt(12)
        
        # Group by session for TOC
        sessions = {}
        for story in stories:
            session_title = story.get('session_title', 'Untitled Session')
            if session_title not in sessions:
                sessions[session_title] = []
            sessions[session_title].append(story)
        
        for session_title in sessions.keys():
            p = doc.add_paragraph(f"  {session_title}", style='List Bullet')
            p.paragraph_format.left_indent = Inches(0.5)  # Indent the TOC entries
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT  # Keep TOC text left-aligned
    
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
            session_para.alignment = WD_ALIGN_PARAGRAPH.CENTER  # Center the session title
            session_para.paragraph_format.space_before = Pt(12)
            session_para.paragraph_format.space_after = Pt(6)
        
        if format_style == "interview":
            # Add question
            question_text = story.get('question', '')
            clean_question = clean_text(question_text)
            q_para = doc.add_paragraph()
            q_run = q_para.add_run(clean_question)
            q_run.font.bold = True
            q_run.font.italic = True
            q_para.alignment = WD_ALIGN_PARAGRAPH.LEFT  # Questions left-aligned
            q_para.paragraph_format.space_before = Pt(6)
            q_para.paragraph_format.space_after = Pt(3)
        
        # Add answer - CLEAN IT HERE
        answer_text = story.get('answer_text', '')
        if answer_text:
            # Clean the text before adding to document
            clean_answer = clean_text(answer_text)
            
            # Split into paragraphs and add
            paragraphs = clean_answer.split('\n')
            for para in paragraphs:
                if para.strip():
                    p = doc.add_paragraph(para.strip())
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT  # Text inside left-aligned
                    p.paragraph_format.first_line_indent = Inches(0.25)  # Indent first line
                    p.paragraph_format.space_after = Pt(6)
        
        # Add images if any
        if include_images and story.get('images'):
            for img in story.get('images', []):
                if img.get('base64'):
                    try:
                        img_data = base64.b64decode(img['base64'])
                        img_stream = io.BytesIO(img_data)
                        
                        # Add image centered (the image block is centered)
                        doc.add_picture(img_stream, width=Inches(4))
                        last_paragraph = doc.paragraphs[-1]
                        last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        
                        # Add caption
                        if img.get('caption'):
                            caption_para = doc.add_paragraph()
                            clean_caption = clean_text(img['caption'])
                            caption_run = caption_para.add_run(clean_caption)
                            caption_run.font.size = Pt(10)
                            caption_run.font.italic = True
                            caption_para.alignment = WD_ALIGN_PARAGRAPH.CENTER  # Caption centered under image
                            caption_para.paragraph_format.space_before = Pt(3)
                            caption_para.paragraph_format.space_after = Pt(6)
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
            html_parts.append(f'''
            <div class="simple-cover">
                <h1>{title}</h1>
                <p class="author">by {author}</p>
            </div>
            ''')
    else:
        html_parts.append(f'''
        <div class="simple-cover">
            <h1>{title}</h1>
            <p class="author">by {author}</p>
        </div>
        ''')
    
    html_parts.append('</div>')
    
    # Copyright page
    html_parts.append(f'<p class="copyright">© {datetime.now().year} {author}. All rights reserved.</p>')
    
    # Table of Contents
    if include_toc:
        html_parts.append('<div class="toc">')
        html_parts.append('<h3>Table of Contents</h3>')
        html_parts.append('<ul>')
        
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
        
        if session_title != current_session:
            current_session = session_title
            html_parts.append(f'<h2 id="{anchor}">{session_title}</h2>')
        
        if format_style == "interview":
            # Clean question text
            question_text = story.get('question', '')
            clean_question = clean_text(question_text)
            html_parts.append(f'<div class="question">{clean_question}</div>')
        
        # Format answer - CLEAN IT HERE
        answer_text = story.get('answer_text', '')
        if answer_text:
            clean_answer = clean_text(answer_text)
            
            html_parts.append('<div>')
            paragraphs = clean_answer.split('\n')
            for para in paragraphs:
                if para.strip():
                    # Escape HTML special characters
                    escaped_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    html_parts.append(f'<p>{escaped_para}</p>')
            html_parts.append('</div>')
        
        # Add images
        if include_images and story.get('images'):
            for img in story.get('images', []):
                if img.get('base64'):
                    html_parts.append(f'<img src="data:image/jpeg;base64,{img["base64"]}" class="story-image">')
                    if img.get('caption'):
                        # Clean caption text
                        clean_caption = clean_text(img['caption'])
                        caption = clean_caption.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_parts.append(f'<p class="image-caption">{caption}</p>')
        
        html_parts.append('<hr style="margin: 30px 0; border: none; border-top: 1px dashed #ccc;">')
    
    html_parts.append("""
    </body>
    </html>
    """)
    
    return '\n'.join(html_parts)
