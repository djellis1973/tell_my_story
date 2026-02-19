from datetime import datetime
import io
import base64
import os
import re
import html
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import subprocess
import tempfile
import platform

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
    # This function will be called from the main app, so we need to import streamlit here
    import streamlit as st
    st.balloons()
    st.success("🎉 Your book has been generated successfully!")

def generate_docx(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_image=None, cover_choice="simple"):
    """Generate a Word document from stories with proper centering"""
    
    doc = Document()
    
    # Set document margins
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
    
    # COVER PAGE - Based on user choice
    if cover_choice == "uploaded" and cover_image:
        try:
            image_stream = io.BytesIO(cover_image)
            
            # Add the cover image centered
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run()
            r.add_picture(image_stream, width=Inches(5))
            
            # Add title below image (centered)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(title)
            run.font.size = Pt(42)
            run.font.bold = True
            
            # Add author below title (centered)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(f"by {author}")
            run.font.size = Pt(24)
            run.font.italic = True
            
        except Exception as e:
            # Fallback to simple text cover (centered)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(title)
            run.font.size = Pt(42)
            run.font.bold = True
            
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(f"by {author}")
            run.font.size = Pt(24)
            run.font.italic = True
    else:
        # Simple text cover (centered)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(title)
        run.font.size = Pt(42)
        run.font.bold = True
        
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"by {author}")
        run.font.size = Pt(24)
        run.font.italic = True
    
    doc.add_page_break()
    
    # Add publication info (centered)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"© {datetime.now().year} {author}. All rights reserved.")
    doc.add_page_break()
    
    # Table of Contents
    if include_toc:
        # TOC title (centered)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("Table of Contents")
        run.font.size = Pt(18)
        run.font.bold = True
        p.paragraph_format.space_after = Pt(12)
        
        # Group by session for TOC
        sessions = {}
        for story in stories:
            session_title = story.get('session_title', 'Untitled Session')
            if session_title not in sessions:
                sessions[session_title] = []
            sessions[session_title].append(story)
        
        # Add TOC entries (left-aligned with indent)
        for session_title in sessions.keys():
            p = doc.add_paragraph(f"  {session_title}", style='List Bullet')
            p.paragraph_format.left_indent = Inches(0.5)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        doc.add_page_break()
    
    # Add stories
    current_session = None
    for story in stories:
        session_title = story.get('session_title', 'Untitled Session')
        
        # Add session header if new session (centered)
        if session_title != current_session:
            current_session = session_title
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(session_title)
            run.font.size = Pt(16)
            run.font.bold = True
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
        
        if format_style == "interview":
            # Add question (left-aligned, bold, italic)
            question_text = story.get('question', '')
            clean_question = clean_text(question_text)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(clean_question)
            run.font.bold = True
            run.font.italic = True
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(3)
        
        # Add answer (left-aligned with first line indent)
        answer_text = story.get('answer_text', '')
        if answer_text:
            clean_answer = clean_text(answer_text)
            
            # Split into paragraphs and add
            paragraphs = clean_answer.split('\n')
            for para in paragraphs:
                if para.strip():
                    p = doc.add_paragraph(para.strip())
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p.paragraph_format.first_line_indent = Inches(0.25)
                    p.paragraph_format.space_after = Pt(6)
        
        # Add images if any
        if include_images and story.get('images'):
            for img in story.get('images', []):
                if img.get('base64'):
                    try:
                        img_data = base64.b64decode(img['base64'])
                        img_stream = io.BytesIO(img_data)
                        
                        # Add image centered
                        p = doc.add_paragraph()
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        run = p.add_run()
                        run.add_picture(img_stream, width=Inches(4))
                        
                        # Add caption centered under image
                        if img.get('caption'):
                            clean_caption = clean_text(img['caption'])
                            p = doc.add_paragraph(clean_caption)
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            p.runs[0].font.size = Pt(10)
                            p.runs[0].font.italic = True
                            p.paragraph_format.space_before = Pt(3)
                            p.paragraph_format.space_after = Pt(6)
                    except Exception as e:
                        print(f"Error adding image: {e}")
                        continue
        
        # Add spacing between stories
        doc.add_paragraph()
    
    # Save to bytes
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    
    return docx_bytes.getvalue()

def generate_html(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_image=None, cover_choice="simple"):
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
                text-align: center;
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
                text-align: left;
            }}
            .answer {{
                text-align: left;
                margin-bottom: 20px;
            }}
            .answer p {{
                text-indent: 0.25in;
                margin-bottom: 6px;
                text-align: left;
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
                text-align: center;
            }}
            .simple-cover h1 {{
                color: white;
                text-align: center;
            }}
            .simple-cover .author {{
                color: rgba(255,255,255,0.9);
                text-align: center;
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
                text-align: left;
            }}
            .toc h3 {{
                text-align: center;
            }}
            .toc ul {{
                list-style-type: none;
                padding-left: 0;
            }}
            .toc li {{
                margin-bottom: 10px;
                text-align: left;
            }}
            .toc a {{
                color: #3498db;
                text-decoration: none;
            }}
            .toc a:hover {{
                text-decoration: underline;
            }}
            hr {{
                margin: 30px 0;
                border: none;
                border-top: 1px dashed #ccc;
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
                <h1>{html.escape(title)}</h1>
                <p class="author">by {html.escape(author)}</p>
            </div>
            ''')
        except Exception:
            html_parts.append(f'''
            <div class="simple-cover">
                <h1>{html.escape(title)}</h1>
                <p class="author">by {html.escape(author)}</p>
            </div>
            ''')
    else:
        html_parts.append(f'''
        <div class="simple-cover">
            <h1>{html.escape(title)}</h1>
            <p class="author">by {html.escape(author)}</p>
        </div>
        ''')
    
    html_parts.append('</div>')
    
    # Copyright page
    html_parts.append(f'<p class="copyright">© {datetime.now().year} {html.escape(author)}. All rights reserved.</p>')
    
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
            html_parts.append(f'<li><a href="#{anchor}">{html.escape(session_title)}</a></li>')
        
        html_parts.append('</ul>')
        html_parts.append('</div>')
    
    # Add stories
    current_session = None
    for story in stories:
        session_title = story.get('session_title', 'Untitled Session')
        anchor = session_title.lower().replace(' ', '-').replace('?', '').replace('!', '').replace(',', '')
        
        if session_title != current_session:
            current_session = session_title
            html_parts.append(f'<h2 id="{anchor}">{html.escape(session_title)}</h2>')
        
        if format_style == "interview":
            # Clean question text
            question_text = story.get('question', '')
            clean_question = clean_text(question_text)
            html_parts.append(f'<div class="question">{html.escape(clean_question)}</div>')
        
        # Format answer
        answer_text = story.get('answer_text', '')
        if answer_text:
            clean_answer = clean_text(answer_text)
            
            html_parts.append('<div class="answer">')
            paragraphs = clean_answer.split('\n')
            for para in paragraphs:
                if para.strip():
                    escaped_para = html.escape(para.strip())
                    html_parts.append(f'<p>{escaped_para}</p>')
            html_parts.append('</div>')
        
        # Add images
        if include_images and story.get('images'):
            for img in story.get('images', []):
                if img.get('base64'):
                    html_parts.append(f'<img src="data:image/jpeg;base64,{img["base64"]}" class="story-image">')
                    if img.get('caption'):
                        clean_caption = clean_text(img['caption'])
                        caption = html.escape(clean_caption)
                        html_parts.append(f'<p class="image-caption">{caption}</p>')
        
        html_parts.append('<hr>')
    
    html_parts.append("""
    </body>
    </html>
    """)
    
    return '\n'.join(html_parts)

def generate_epub(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_image=None, cover_choice="simple"):
    """Generate an EPUB file (requires Pandoc)"""
    
    # First generate HTML
    html_content = generate_html(title, author, stories, format_style, include_toc, include_images, cover_image, cover_choice)
    
    # Try to convert HTML to EPUB using pandoc
    try:
        # Check if pandoc is available
        result = subprocess.run(['pandoc', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            return None, "Pandoc not found. Please install pandoc to generate EPUB files."
        
        # Create temp files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            html_path = f.name
        
        epub_path = tempfile.NamedTemporaryFile(suffix='.epub', delete=False).name
        
        # Convert HTML to EPUB
        cmd = [
            'pandoc',
            html_path,
            '-o', epub_path,
            '--metadata', f'title={title}',
            '--metadata', f'author={author}',
            '--toc' if include_toc else ''
        ]
        
        # Remove empty arguments
        cmd = [arg for arg in cmd if arg]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            with open(epub_path, 'rb') as f:
                epub_bytes = f.read()
            
            # Clean up temp files
            os.unlink(html_path)
            os.unlink(epub_path)
            
            return epub_bytes, None
        else:
            return None, f"Pandoc error: {result.stderr}"
            
    except FileNotFoundError:
        return None, "Pandoc not found. Please install pandoc to generate EPUB files."
    except Exception as e:
        return None, str(e)

def generate_rtf(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_image=None, cover_choice="simple"):
    """Generate an RTF file using a simple RTF template"""
    
    # First generate HTML
    html_content = generate_html(title, author, stories, format_style, include_toc, include_images, cover_image, cover_choice)
    
    # Try to convert HTML to RTF using pandoc
    try:
        result = subprocess.run(['pandoc', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            return generate_rtf_fallback(title, author, stories, format_style, include_toc)
        
        # Create temp files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            html_path = f.name
        
        rtf_path = tempfile.NamedTemporaryFile(suffix='.rtf', delete=False).name
        
        # Convert HTML to RTF
        cmd = ['pandoc', html_path, '-o', rtf_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            with open(rtf_path, 'rb') as f:
                rtf_bytes = f.read()
            
            # Clean up temp files
            os.unlink(html_path)
            os.unlink(rtf_path)
            
            return rtf_bytes
        else:
            return generate_rtf_fallback(title, author, stories, format_style, include_toc)
            
    except FileNotFoundError:
        return generate_rtf_fallback(title, author, stories, format_style, include_toc)

def generate_rtf_fallback(title, author, stories, format_style="interview", include_toc=True):
    """Generate a simple RTF file without pandoc"""
    
    rtf_header = r"""{\rtf1\ansi\deff0{\fonttbl{\f0 Times New Roman;}{\f1 Arial;}}
\paperw12240\paperh15840\margl1440\margr1440\margt1440\margb1440
"""
    
    rtf_content = []
    rtf_content.append(rtf_header)
    
    # Title
    rtf_content.append(r"\pard\qc\fs72\b " + title + r"\par\par")
    
    # Author
    rtf_content.append(r"\pard\qc\fs48\i by " + author + r"\par\par")
    
    # Copyright
    rtf_content.append(r"\pard\qc\fs24\i Copyright " + str(datetime.now().year) + r" " + author + r". All rights reserved.\par\par")
    
    # Stories
    current_session = None
    for story in stories:
        session_title = story.get('session_title', 'Untitled Session')
        
        if session_title != current_session:
            current_session = session_title
            rtf_content.append(r"\pard\qc\fs40\b " + session_title + r"\par\par")
        
        if format_style == "interview":
            question = clean_text(story.get('question', ''))
            rtf_content.append(r"\pard\ql\fs28\b\i " + question + r"\par")
        
        answer = clean_text(story.get('answer_text', ''))
        paragraphs = answer.split('\n')
        for para in paragraphs:
            if para.strip():
                rtf_content.append(r"\pard\ql\fs24\fi360 " + para.strip() + r"\par")
        
        rtf_content.append(r"\par")
    
    rtf_content.append("}")
    
    return '\n'.join(rtf_content).encode('utf-8')

def generate_pdf(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_image=None, cover_choice="simple"):
    """Generate a PDF file using weasyprint or pandoc"""
    
    # First generate HTML
    html_content = generate_html(title, author, stories, format_style, include_toc, include_images, cover_image, cover_choice)
    
    # Try weasyprint first
    try:
        from weasyprint import HTML
        
        pdf_bytes = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_bytes)
        pdf_bytes.seek(0)
        return pdf_bytes.getvalue(), None
        
    except ImportError:
        # Try pandoc as fallback
        try:
            result = subprocess.run(['pandoc', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                # Create temp files
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    html_path = f.name
                
                pdf_path = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
                
                # Convert HTML to PDF
                cmd = ['pandoc', html_path, '-o', pdf_path]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    
                    # Clean up
                    os.unlink(html_path)
                    os.unlink(pdf_path)
                    
                    return pdf_bytes, None
                else:
                    return None, f"Pandoc error: {result.stderr}"
            else:
                return None, "Please install weasyprint (pip install weasyprint) or pandoc to generate PDF files."
                
        except FileNotFoundError:
            return None, "Please install weasyprint (pip install weasyprint) or pandoc to generate PDF files."
