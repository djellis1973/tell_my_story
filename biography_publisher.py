# biography_publisher.py – COMPLETE VERSION (NO SIDEBAR)
import streamlit as st
import json
import base64
from datetime import datetime
import os
import io
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import time

# ============================================================================
# CELEBRATION BALLOONS
# ============================================================================
def show_celebration():
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
    <div class="celebration-message">🎉 Congratulations! 🎉<br><span style="font-size: 24px;">Your book has been published!</span></div>
    <div class="balloon"></div><div class="balloon"></div><div class="balloon"></div><div class="balloon"></div><div class="balloon"></div>
    <div class="balloon"></div><div class="balloon"></div><div class="balloon"></div><div class="balloon"></div><div class="balloon"></div>
    """
    st.components.v1.html(balloons_html, height=0)
    time.sleep(0.5)
    st.balloons()

# ============================================================================
# DOCX GENERATION
# ============================================================================
def generate_docx(book_title, author_name, stories, format_style, include_toc=True, include_dates=False, cover_image=None):
    doc = Document()
    
    # COVER: Use uploaded image OR simple text
    if cover_image is not None:
        try:
            img_stream = io.BytesIO(cover_image)
            doc.add_picture(img_stream, width=Inches(6))
            doc.add_page_break()
        except:
            title = doc.add_heading(book_title, 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author = doc.add_paragraph(f'by {author_name}')
            author.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_page_break()
    else:
        title = doc.add_heading(book_title, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author = doc.add_paragraph(f'by {author_name}')
        author.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_page_break()
    
    # TOC
    if include_toc and stories:
        doc.add_heading('Table of Contents', 1).alignment = WD_ALIGN_PARAGRAPH.CENTER
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
    if stories:
        current_session = None
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
            else:
                doc.add_paragraph(answer_text)
            
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
# HTML GENERATION
# ============================================================================
def generate_html(book_title, author_name, stories, format_style, include_toc=True, include_dates=False, cover_image=None):
    
    # COVER: Use uploaded image OR simple gradient
    if cover_image is not None:
        img_b64 = base64.b64encode(cover_image).decode()
        cover_html = f'''
        <div style="text-align:center; margin:0 auto 40px auto;">
            <img src="data:image/jpeg;base64,{img_b64}" style="width:100%; max-width:600px; box-shadow:0 10px 20px rgba(0,0,0,0.3);">
        </div>
        <hr>
        '''
    else:
        cover_html = f'''
        <div class="book-header">
            <h1>{book_title}</h1>
            <div class="author">by {author_name}</div>
        </div>
        '''
    
    # TOC
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
            question = story.get('question', f'Story {i}')
            toc_html += f"<li class='toc-story'><a href='#story-{i}'>{i}. {question}</a></li>"
        toc_html += "</ul><hr>"
    
    # Content
    content_html = ""
    current_session = None
    for i, story in enumerate(stories, 1):
        session_id = story.get('session_id', '1')
        if session_id != current_session:
            session_title = story.get('session_title', f'Session {session_id}')
            content_html += f"<h1 class='session-title'>{session_title}</h1>"
            current_session = session_id
        
        question = story.get('question', '')
        answer_text = story.get('answer_text', '')
        images = story.get('images', [])
        
        content_html += f"<div class='story' id='story-{i}'>"
        if format_style == 'interview':
            content_html += f"<h2 class='question'>Q: {question}</h2>"
        
        for p in answer_text.split('\n'):
            if p.strip():
                content_html += f"<p>{p}</p>"
        
        if images:
            content_html += "<div class='image-gallery'>"
            for img_data in images:
                b64 = img_data.get('base64')
                caption = img_data.get('caption', '')
                if b64:
                    content_html += f"""
                    <div class='image-item'>
                        <img src='data:image/jpeg;base64,{b64}'>
                        <div class='image-caption'>📝 {caption}</div>
                    </div>
                    """
            content_html += "</div>"
        content_html += "</div><hr>"
    
    # Final HTML
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{book_title}</title>
<style>
    body {{ font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; background: #fafafa; }}
    .book-header {{ text-align: center; padding: 60px 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; margin: -40px -20px 40px -20px; }}
    .session-title {{ color: #764ba2; border-bottom: 2px solid #667eea; }}
    .question {{ color: #667eea; font-style: italic; }}
    .image-gallery {{ display: flex; flex-wrap: wrap; gap: 20px; }}
    .image-item {{ flex: 1 1 300px; background: white; padding: 15px; border-radius: 10px; }}
    .image-item img {{ max-width: 100%; }}
    .toc {{ background: white; padding: 30px; border-radius: 10px; }}
    .toc-session {{ font-weight: bold; color: #667eea; }}
    hr {{ margin: 40px 0; }}
</style>
</head>
<body>
    {cover_html}
    {toc_html}
    <div class="content">{content_html}</div>
    <div class="footer" style="text-align:center; color:#999;">Generated by Tell My Story • {datetime.now().year}</div>
</body>
</html>"""
    return html

# ============================================================================
# MAIN - NO SIDEBAR, EVERYTHING IN MAIN SCREEN
# ============================================================================
def main():
    st.set_page_config(page_title="Biography Publisher", page_icon="📚", layout="wide")
    
    st.markdown("""
    <div style="text-align:center; padding:2rem; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; margin:-1rem -1rem 2rem -1rem;">
        <h1>📚 Biography Publisher</h1>
        <p>Upload a JPG - it becomes your cover</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'stories_data' not in st.session_state:
        st.session_state.stories_data = None
    if 'book_title' not in st.session_state:
        st.session_state.book_title = ""
    if 'author_name' not in st.session_state:
        st.session_state.author_name = ""
    if 'format_style' not in st.session_state:
        st.session_state.format_style = "interview"
    if 'include_toc' not in st.session_state:
        st.session_state.include_toc = True
    if 'uploaded_cover' not in st.session_state:
        st.session_state.uploaded_cover = None
    
    # ============================================================
    # STEP 1: UPLOAD STORIES (MAIN SCREEN)
    # ============================================================
    st.markdown("### 📂 Step 1: Upload Your Stories")
    uploaded_file = st.file_uploader("Upload JSON from Tell My Story", type=['json'])
    if uploaded_file:
        try:
            st.session_state.stories_data = json.load(uploaded_file)
            st.success("✅ Stories loaded successfully!")
            user_profile = st.session_state.stories_data.get('user_profile', {})
            if user_profile:
                first = user_profile.get('first_name', '')
                last = user_profile.get('last_name', '')
                if first or last:
                    st.session_state.author_name = f"{first} {last}".strip()
                    st.session_state.book_title = f"The Story of {first} {last}".strip()
        except Exception as e:
            st.error(f"Error loading file: {e}")
    
    st.markdown("---")
    
    # ============================================================
    # STEP 2: UPLOAD COVER IMAGE (MAIN SCREEN - NO SIDEBAR)
    # ============================================================
    st.markdown("### 🖼️ Step 2: Upload Cover Image (Optional)")
    st.markdown("Upload any JPG or PNG - it will become your book cover")
    
    uploaded_cover = st.file_uploader("Choose an image file", type=['jpg', 'jpeg', 'png'], key="cover_upload_main")
    if uploaded_cover:
        st.session_state.uploaded_cover = uploaded_cover.getvalue()
        st.image(uploaded_cover, width=300, caption="Your cover image")
        st.success("✅ Cover image ready to use")
    
    st.markdown("---")
    
    # ============================================================
    # STEP 3: BOOK SETTINGS (MAIN SCREEN)
    # ============================================================
    st.markdown("### ⚙️ Step 3: Book Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.book_title = st.text_input("Book Title", value=st.session_state.book_title)
    with col2:
        st.session_state.author_name = st.text_input("Author Name", value=st.session_state.author_name)
    
    st.session_state.format_style = st.radio(
        "Format Style",
        ["interview", "biography"],
        format_func=lambda x: "📝 Show Questions & Answers" if x == "interview" else "📖 Just Answers (Biography Style)",
        horizontal=True
    )
    
    st.session_state.include_toc = st.checkbox("Include Table of Contents", value=st.session_state.include_toc)
    
    st.markdown("---")
    
    # ============================================================
    # STEP 4: GENERATE BOOK (MAIN SCREEN)
    # ============================================================
    if st.session_state.stories_data:
        stories_data = st.session_state.stories_data
        stories = stories_data.get('stories', [])
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Stories", len(stories))
        with col2:
            sessions = len(set(s.get('session_id') for s in stories))
            st.metric("Sessions", sessions)
        with col3:
            total_images = sum(len(s.get('images', [])) for s in stories)
            st.metric("Images in Stories", total_images)
        
        # Preview
        with st.expander("📖 Preview Stories", expanded=False):
            for i, story in enumerate(stories[:3]):
                st.markdown(f"**{story.get('session_title', 'Session')}**")
                if st.session_state.format_style == 'interview':
                    st.markdown(f"*Q: {story.get('question', '')}*")
                st.markdown(f"{story.get('answer_text', '')[:200]}...")
                if story.get('images'):
                    st.caption(f"📸 {len(story['images'])} image(s)")
                st.divider()
        
        # Generate buttons
        st.markdown("### 📤 Step 4: Generate Your Book")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Generate DOCX", type="primary", use_container_width=True):
                with st.spinner("Creating Word document..."):
                    docx_bytes = generate_docx(
                        st.session_state.book_title,
                        st.session_state.author_name,
                        stories,
                        st.session_state.format_style,
                        st.session_state.include_toc,
                        False,
                        st.session_state.uploaded_cover
                    )
                    filename = f"{st.session_state.book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.docx"
                    st.download_button(
                        "📥 Download DOCX", 
                        data=docx_bytes, 
                        file_name=filename, 
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="docx_download"
                    )
                    show_celebration()
        
        with col2:
            if st.button("🌐 Generate HTML", type="primary", use_container_width=True):
                with st.spinner("Creating HTML page..."):
                    html_content = generate_html(
                        st.session_state.book_title,
                        st.session_state.author_name,
                        stories,
                        st.session_state.format_style,
                        st.session_state.include_toc,
                        False,
                        st.session_state.uploaded_cover
                    )
                    filename = f"{st.session_state.book_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html"
                    st.download_button(
                        "📥 Download HTML", 
                        data=html_content, 
                        file_name=filename, 
                        mime="text/html",
                        key="html_download"
                    )
                    show_celebration()
    else:
        st.info("👆 Start by uploading your stories JSON file above")

if __name__ == "__main__":
    main()
