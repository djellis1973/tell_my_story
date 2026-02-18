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

def show_celebration():
    """Show a celebration animation when book is generated"""
    st.balloons()
    st.success("🎉 Your book has been generated successfully!")

def generate_docx(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_image=None):
    """Generate a Word document from stories"""
    doc = Document()
    
    # Set document styling
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    
    # Add title page
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(title)
    title_run.font.size = Pt(28)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0, 0, 0)
    
    # Add author
    author_para = doc.add_paragraph()
    author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    author_run = author_para.add_run(f"by {author}")
    author_run.font.size = Pt(16)
    author_run.font.italic = True
    
    # Add cover image if provided
    if cover_image:
        doc.add_page_break()
        try:
            image_stream = io.BytesIO(cover_image)
            doc.add_picture(image_stream, width=Inches(4))
            last_paragraph = doc.paragraphs[-1]
            last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception as e:
            st.warning(f"Could not add cover image: {e}")
    
    # Add publication info
    doc.add_page_break()
    copyright_para = doc.add_paragraph()
    copyright_para.add_run(f"© {datetime.now().year} {author}. All rights reserved.")
    
    # Table of Contents
    if include_toc:
        doc.add_page_break()
        toc_para = doc.add_paragraph()
        toc_run = toc_para.add_run("Table of Contents")
        toc_run.font.size = Pt(18)
        toc_run.font.bold = True
        
        sessions = {}
        for story in stories:
            session_title = story.get('session_title', 'Untitled Session')
            if session_title not in sessions:
                sessions[session_title] = []
            sessions[session_title].append(story)
        
        for session_title, session_stories in sessions.items():
            doc.add_paragraph(f"  {session_title}", style='List Bullet')
            for i, story in enumerate(session_stories[:3]):  # Show first 3 as examples
                doc.add_paragraph(f"    {story.get('question', 'Story')[:50]}...", style='List Bullet 2')
            if len(session_stories) > 3:
                doc.add_paragraph(f"    ... and {len(session_stories)-3} more stories", style='List Bullet 2')
    
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
            session_run.font.color.rgb = RGBColor(100, 100, 100)
        
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

def generate_html(title, author, stories, format_style="interview", include_toc=True, include_images=True, cover_html_path=None, cover_image=None):
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
            h3 {{
                font-size: 20px;
                margin-top: 30px;
                margin-bottom: 10px;
                color: #666;
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
            .answer {{
                margin-bottom: 30px;
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
            .toc {{
                background: #f9f9f9;
                padding: 20px;
                border-radius: 5px;
                margin: 30px 0;
            }}
            .toc h3 {{
                margin-top: 0;
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
            .cover-page {{
                text-align: center;
                margin-bottom: 50px;
                page-break-after: always;
            }}
            .cover-title {{
                font-size: 48px;
                font-weight: bold;
                margin: 50px 0 20px 0;
            }}
            .cover-author {{
                font-size: 24px;
                color: #666;
                margin-bottom: 40px;
            }}
            .copyright {{
                text-align: center;
                font-size: 12px;
                color: #999;
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            @media print {{
                body {{
                    padding: 0.5in;
                }}
                .toc {{
                    background: none;
                    border: 1px solid #ccc;
                }}
            }}
        </style>
    </head>
    <body>
    """)
    
    # Cover page
    html_parts.append('<div class="cover-page">')
    
    # Use custom cover HTML if provided
    if cover_html_path and os.path.exists(cover_html_path):
        try:
            with open(cover_html_path, 'r') as f:
                cover_content = f.read()
                # Extract just the cover part if it's a full HTML
                if '<body>' in cover_content:
                    cover_match = re.search(r'<body>(.*?)</body>', cover_content, re.DOTALL)
                    if cover_match:
                        cover_content = cover_match.group(1)
                html_parts.append(cover_content)
        except:
            # Fallback to simple cover
            html_parts.append(f'<h1 class="cover-title">{title}</h1>')
            html_parts.append(f'<p class="cover-author">by {author}</p>')
    elif cover_image:
        # Use uploaded image
        img_base64 = base64.b64encode(cover_image).decode()
        html_parts.append(f'<img src="data:image/jpeg;base64,{img_base64}" style="max-width:100%; max-height:400px; margin:20px auto;">')
        html_parts.append(f'<h1 class="cover-title">{title}</h1>')
        html_parts.append(f'<p class="cover-author">by {author}</p>')
    else:
        # Simple cover
        html_parts.append(f'<h1 class="cover-title">{title}</h1>')
        html_parts.append(f'<p class="cover-author">by {author}</p>')
    
    html_parts.append('</div>')
    
    # Copyright
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
            # Create anchor from session title
            anchor = session_title.lower().replace(' ', '-')
            html_parts.append(f'<li><a href="#{anchor}">{session_title}</a></li>')
        
        html_parts.append('</ul>')
        html_parts.append('</div>')
    
    # Add stories
    current_session = None
    for story in stories:
        session_title = story.get('session_title', 'Untitled Session')
        anchor = session_title.lower().replace(' ', '-')
        
        # Add session header if new session
        if session_title != current_session:
            current_session = session_title
            html_parts.append(f'<h2 id="{anchor}">{session_title}</h2>')
        
        if format_style == "interview":
            html_parts.append(f'<div class="question">{story.get("question", "")}</div>')
        
        # Format answer with paragraphs
        answer_text = story.get('answer_text', '')
        if answer_text:
            html_parts.append('<div class="answer">')
            paragraphs = answer_text.split('\n')
            for para in paragraphs:
                if para.strip():
                    html_parts.append(f'<p>{para.strip()}</p>')
            html_parts.append('</div>')
        
        # Add images
        if include_images and story.get('images'):
            for img in story.get('images', []):
                if img.get('base64'):
                    html_parts.append(f'<img src="data:image/jpeg;base64,{img["base64"]}" class="story-image">')
                    if img.get('caption'):
                        html_parts.append(f'<p class="image-caption">{img["caption"]}</p>')
        
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
