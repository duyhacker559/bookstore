import sys
from PyPDF2 import PdfReader

def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python extract_pdf.py <pdf_path>', file=sys.stderr)
        sys.exit(1)
    pdf = sys.argv[1]
    print(extract_text(pdf))
