# pdf_processor.py
import pdfplumber

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF using pdfplumber
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the PDF
    """
    extracted_text = ""
    extracted_text_first_page = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            if i == 1:
                extracted_text_first_page = page.extract_text()
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\n"
    
    return extracted_text, extracted_text_first_page
