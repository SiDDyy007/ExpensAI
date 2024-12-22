from PyPDF2 import PdfReader
import re
import json
from dotenv import load_dotenv
import os


load_dotenv()
password = os.getenv("PASSWORD")

# if reader.is_encrypted:
#     reader.decrypt(password)
# print("Number of pages:", len(reader.pages))

def getAMEX(reader):
    charges = ""

    capture = False

    for page_number in range(len(reader.pages)): 
        page = reader.pages[page_number]
        page_text = page.extract_text()
        
        if "Card Ending 6-21001" in page_text:
            capture = True
        
        if capture:
            charges += page_text
        
        if "Total Fees for this Period" in page_text:
            capture = False
            break
    return charges

def getZolve(reader):
    charges = ""

    capture = False

    for page_number in range(len(reader.pages)): 
        page = reader.pages[page_number]
        page_text = page.extract_text()
        # print(page_text)
        
        if "payments and other credits" in page_text.lower():
            capture = True
        
        if capture:
            charges += page_text
        
        if "fees and interest charged" in page_text.lower():
            capture = False
            break
    return charges

def extract_charges(reader, card_type):
    if card_type == "AMEX":
        charges = getAMEX(reader)
        pattern = r'(\d{2}/\d{2}/\d{2})(.*?)(\$\d+\.\d{2})'
    elif card_type == "ZOLVE":
        charges = getZolve(reader)
        pattern = r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(\$\d+\.\d{2})'
    else:
        raise ValueError("Unsupported card type")
    # print(charges)
    matches = re.findall(pattern, charges, re.DOTALL)
    # print(matches)
    charges_list = []
    for match in matches:
        if card_type == "AMEX":
            charge = {
                "date": match[0].strip(),
                "description": match[1].strip(),
                "amount": match[2].strip()
            }
        elif card_type == "ZOLVE":
            charge = {
                "posted_date": match[0].strip(),
                "transaction_date": match[1].strip(),
                "description": match[2].strip(),
                "amount": match[3].strip()
            }
        charges_list.append(charge)

    # charges_json = json.dumps(charges_list, indent=4)
    return charges_list

def getExpenseJSON(reader = None, card_type = 'ZOLVE'):
    reader = PdfReader('statements/ZOLVE.pdf')
    # reader = PdfReader('AMEX.pdf')
    if reader.is_encrypted:
        reader.decrypt(password)

    if card_type == "AMEX":
        charges_json = extract_charges(reader, card_type="AMEX")
    elif card_type == "ZOLVE":
        charges_json = extract_charges(reader, card_type="ZOLVE")
    else:
        raise ValueError("Unsupported card type")
    return charges_json

# charges_json = extract_charges(reader, card_type="ZOLVE")
# print(charges_json)
