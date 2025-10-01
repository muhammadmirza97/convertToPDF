import os
from docx2pdf import convert as docx2pdf_convert
from PIL import Image
from fpdf import FPDF
import pdfkit

def convert_to_pdf(input_path):
    if not os.path.exists(input_path):
        print("File not found:", input_path)
        return

    filename, ext = os.path.splitext(input_path)
    ext = ext.lower()

    output_path = filename + ".pdf"

    try:
        if ext == ".docx":
            docx2pdf_convert(input_path, output_path)
            print("Converted DOCX to PDF:", output_path)

        elif ext in [".jpg", ".jpeg", ".png"]:
            image = Image.open(input_path).convert("RGB")
            image.save(output_path)
            print("Converted image to PDF:", output_path)

        elif ext == ".txt":
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            with open(input_path, 'r', encoding='utf-8') as f:
                for line in f:
                    pdf.cell(200, 10, txt=line.strip(), ln=True)
            pdf.output(output_path)
            print("Converted TXT to PDF:", output_path)

        elif ext == ".html":
            pdfkit.from_file(input_path, output_path)
            print("Converted HTML to PDF:", output_path)

        else:
            print(f"Unsupported file type: {ext}")

    except Exception as e:
        print("Error converting file:", e)

# Example usage:
# convert_to_pdf("example.docx")
