import streamlit as st
from datetime import datetime
import io
import base64
import re
import html
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from fpdf import FPDF
import ebooklib
from ebooklib import epub

def clean_text(text):
    if not text: return text
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def generate_docx(title, author, stories, format_style):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Cover
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(title).font.size = Pt(42)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"by {author}").font.size = Pt(24)
    doc.add_page_break()
    
    # Stories
    for story in stories:
        if format_style == "interview" and story.get('question'):
            p = doc.add_paragraph()
            p.add_run(clean_text(story['question'])).bold = True
        if story.get('answer_text'):
            for para in clean_text(story['answer_text']).split('\n'):
                if para.strip():
                    doc.add_paragraph(para.strip())
        doc.add_paragraph()
    
    bytes_io = io.BytesIO()
    doc.save(bytes_io)
    bytes_io.seek(0)
    return bytes_io.getvalue()

def generate_html(title, author, stories, format_style):
    html_content = f"<h1>{title}</h1><p><i>by {author}</i></p>"
    for story in stories:
        if format_style == "interview" and story.get('question'):
            html_content += f"<p><b>{story['question']}</b></p>"
        if story.get('answer_text'):
            html_content += f"<p>{story['answer_text'].replace(chr(10), '<br>')}</p>"
        html_content += "<hr>"
    return html_content

def generate_epub(title, author, stories, format_style):
    book = epub.EpubBook()
    book.set_identifier('id123')
    book.set_title(title)
    book.set_language('en')
    book.add_author(author)
    
    content = f"<h1>{title}</h1><h3>by {author}</h3>"
    for story in stories:
        if format_style == "interview" and story.get('question'):
            content += f"<p><b>{story['question']}</b></p>"
        if story.get('answer_text'):
            content += f"<p>{story['answer_text'].replace(chr(10), '<br>')}</p>"
        content += "<hr>"
    
    chap = epub.EpubHtml(title='Content', file_name='content.xhtml')
    chap.content = content
    book.add_item(chap)
    book.spine = ['nav', chap]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    bytes_io = io.BytesIO()
    epub.write_epub(bytes_io, book)
    bytes_io.seek(0)
    return bytes_io.getvalue()

class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf(title, author, stories, format_style):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Times', 'B', 24)
    pdf.cell(0, 50, title, 0, 1, 'C')
    pdf.set_font('Times', 'I', 16)
    pdf.cell(0, 10, f'by {author}', 0, 1, 'C')
    pdf.add_page()
    
    pdf.set_font('Times', '', 12)
    for story in stories:
        if format_style == "interview" and story.get('question'):
            pdf.set_font('Times', 'B', 12)
            pdf.multi_cell(0, 6, story['question'])
            pdf.ln(3)
        if story.get('answer_text'):
            pdf.set_font('Times', '', 12)
            pdf.multi_cell(0, 6, story['answer_text'])
        pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin-1')

def generate_rtf(title, author, stories, format_style):
    rtf = "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Times New Roman;}}\\f0\\fs24\n"
    rtf += f"\\pard\\qc \\b\\fs48 {title}\\b0\\par\n"
    rtf += f"\\pard\\qc \\i\\fs36 by {author}\\i0\\par\n\n"
    
    for story in stories:
        if format_style == "interview" and story.get('question'):
            rtf += f"\\pard\\li720 \\b {story['question']}\\b0\\par\n"
        if story.get('answer_text'):
            for para in story['answer_text'].split('\n'):
                if para.strip():
                    rtf += f"\\pard\\fi720 {para}\\par\n"
        rtf += "\\par\n"
    
    rtf += "}"
    return rtf.encode('utf-8')

def main():
    st.set_page_config(page_title="Book Publisher", layout="wide")
    st.title("📚 Book Publisher")
    
    with st.sidebar:
        title = st.text_input("Book Title", "My Book")
        author = st.text_input("Author", "Anonymous")
        format_style = st.selectbox("Format", ["interview", "narrative"])
        
        st.subheader("Export Formats")
        export_docx = st.checkbox("DOCX", True)
        export_html = st.checkbox("HTML", True)
        export_epub = st.checkbox("EPUB", True)
        export_pdf = st.checkbox("PDF", True)
        export_rtf = st.checkbox("RTF", True)
    
    # Stories
    if 'stories' not in st.session_state:
        st.session_state.stories = []
    
    st.header("Stories")
    if st.button("➕ Add Story"):
        st.session_state.stories.append({"question": "", "answer_text": ""})
    
    for i, story in enumerate(st.session_state.stories):
        with st.expander(f"Story {i+1}"):
            story['question'] = st.text_input(f"Question", story['question'], key=f"q_{i}")
            story['answer_text'] = st.text_area(f"Answer", story['answer_text'], key=f"a_{i}")
            if st.button(f"Delete", key=f"d_{i}"):
                st.session_state.stories.pop(i)
                st.rerun()
    
    if st.button("📖 GENERATE BOOK", type="primary"):
        if not st.session_state.stories:
            st.error("Add stories first")
            return
        
        with st.spinner("Generating..."):
            files = {}
            
            if export_docx:
                files['docx'] = generate_docx(title, author, st.session_state.stories, format_style)
            if export_html:
                files['html'] = generate_html(title, author, st.session_state.stories, format_style).encode('utf-8')
            if export_epub:
                files['epub'] = generate_epub(title, author, st.session_state.stories, format_style)
            if export_pdf:
                files['pdf'] = generate_pdf(title, author, st.session_state.stories, format_style)
            if export_rtf:
                files['rtf'] = generate_rtf(title, author, st.session_state.stories, format_style)
            
            st.balloons()
            st.subheader("Download")
            
            # SHOW ALL BUTTONS
            for fmt, data in files.items():
                mime = {
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'html': 'text/html',
                    'epub': 'application/epub+zip',
                    'pdf': 'application/pdf',
                    'rtf': 'application/rtf'
                }.get(fmt, 'application/octet-stream')
                
                st.download_button(
                    label=f"Download {fmt.upper()}",
                    data=data,
                    file_name=f"{title}.{fmt}",
                    mime=mime,
                    use_container_width=True
                )

if __name__ == "__main__":
    main()
