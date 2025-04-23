from fpdf import FPDF
import os

def generate_pdf(messages: list) -> bytes:
    if not messages:
        raise ValueError("No messages to export.")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Use full path for the font
    font_path = os.path.join("assets", "fonts", "DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    for msg in messages:
        role = msg["role"].capitalize()
        content = msg["content"]
        pdf.multi_cell(0, 10, f"{role}: {content}\n")

    return pdf.output(dest="S").encode("latin1")

def generate_txt(messages: list) -> str:
    """Generate a plain text export of chat messages."""
    if not messages:
        raise ValueError("No messages to export.")

    txt = ""
    for msg in messages:
        txt += f"{msg['role'].capitalize()}: {msg['content']}\n\n"

    return txt
