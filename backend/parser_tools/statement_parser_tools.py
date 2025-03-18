import pdfplumber
import re
from datetime import datetime
from smolagents import tool
from bert_model import process_text_with_bert, extract_transactions, load_model



tokenizer, model = load_model()

@tool
def parse_amex_statement(pdf_path : str) -> dict:
    """
    This is a tool that extracts and returns a Expense JSON consisting of charges and information of each charge from a AMEX credit card bill statement.

    Args:
        pdf_path: The path to the AMEX credit card bill statement PDF file.

    Handles formats:
    - Regular charges: 09/22/24 PAYPAL *STARBUCKS 8007827282 WA $25.00
    - Payments: 10/14/24* MOBILE PAYMENT - THANK YOU -$620.00
    """
    sample_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                sample_text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error opening: {e}")
    
    transactions = extract_transactions(tokenizer, model, sample_text)

    postprocessed_transactions = []
    for t in transactions:
        if t['Date'] and t['Merchant'] and (t['Charge'] and '$' in t['Charge']):
            print(f"Date: {t['Date']}, Merchant: {t['Merchant']}, Charge: {t['Charge']}")
            postprocessed_transactions.append({
                'date': t['Date'],
                'merchant': t['Merchant'],
                'amount': float(t['Charge'].replace('$', '')),
                'type': 'PAYMENT' if '-' in t['Charge'] else 'CHARGE',
                'card': 'AMEX'
            })

    # Add postprocessed_transactions to the Supabase database
    return transactions

@tool
def parse_zolve_statement(pdf_path : str) -> dict:
    """
    This is a tool that extracts and returns a Expense JSON consisting of charges and information of each charge from a ZOLVE credit card bill statement.

    Args:
        pdf_path: The path to the ZOLVE credit card bill statement PDF file.
    """
    sample_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                sample_text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error opening: {e}")
    
    transactions = extract_transactions(tokenizer, model, sample_text)

    postprocessed_transactions = []
    for t in transactions:
        if t['Date'] and t['Merchant'] and (t['Charge'] and '$' in t['Charge']):
            print(f"Date: {t['Date']}, Merchant: {t['Merchant']}, Charge: {t['Charge']}")
            postprocessed_transactions.append({
                'date': t['Date'],
                'merchant': t['Merchant'],
                'amount': float(t['Charge'].replace('$', '')),
                'type': 'PAYMENT' if '-' in t['Charge'] else 'CHARGE',
                'card': 'ZOLVE'
            })

    # Add postprocessed_transactions to the Supabase database
    return transactions

@tool
def parse_freedom_statement(pdf_path: str) -> dict:
    """
    This is a tool that extracts and returns a Expense JSON consisting of charges and information of each charge from a FREEDOM credit card bill statement.
    
    Args:
        pdf_path: The path to the FREEDOM credit card bill statement PDF file.
    """
 
    sample_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                sample_text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error opening: {e}")
    
    transactions = extract_transactions(tokenizer, model, sample_text)

    postprocessed_transactions = []
    for t in transactions:
        if t['Date'] and t['Merchant'] and (t['Charge'] and '$' not in t['Charge']):
            print(f"Date: {t['Date']}, Merchant: {t['Merchant']}, Charge: {t['Charge']}")
            postprocessed_transactions.append({
                'date': t['Date'],
                'merchant': t['Merchant'],
                'amount': float(t['Charge'].replace('$', '')),
                'type': 'PAYMENT' if '-' in t['Charge'] else 'CHARGE',
                'card': 'FREEDOM'
            })

    # Add postprocessed_transactions to the Supabase database
    return transactions


def parse_checking_statement(pdf_path):
    """
    Parse checking account statement PDF and extract transactions.
    Returns a dictionary containing transactions and account summary.
    """
    transactions = []
    account_summary = {
        'beginning_balance': None,
        'ending_balance': None
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                lines = text.split('\n')
                
                in_transaction_section = False
                
                for line in lines:
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Check for transaction detail header
                    if "TRANSACTION DETAIL" in line:
                        in_transaction_section = True
                        continue
                    
                    if in_transaction_section:
                        try:
                            # Handle Beginning Balance
                            if "Beginning Balance" in line:
                                balance_str = line.split('$')[-1].replace(',', '')
                                account_summary['beginning_balance'] = float(balance_str)
                                continue
                            
                            # Handle Ending Balance
                            if "Ending Balance" in line:
                                balance_str = line.split('$')[-1].replace(',', '')
                                account_summary['ending_balance'] = float(balance_str)
                                continue
                            
                            # Skip header line
                            if "DATE" in line and "DESCRIPTION" in line:
                                continue
                                
                            # Parse regular transaction lines
                            # Split on multiple spaces to handle varying formats
                            print(line, '\n')
                            parts = re.split(r'\s{2,}', line.strip())
                            print(parts)
                            
                            # Check if this line looks like a transaction
                            if not re.match(r'\d{1,2}/\d{1,2}', parts[0]):
                                print("We are conintuning ... :)()")
                                continue
                                
                            # Extract date
                            date = datetime.strptime(parts[0], '%m/%d').strftime('2024-%m-%d')
                            
                            # Extract amount and balance
                            # Look for dollar amounts with negative signs and decimal points
                            amounts = re.findall(r'-?\$?[\d,]+\.\d{2}', line)
                            if len(amounts) >= 2:  # We need at least amount and balance
                                amount_str = amounts[-2].replace('$', '').replace(',', '')
                                balance_str = amounts[-1].replace('$', '').replace(',', '')
                                amount = float(amount_str)
                                balance = float(balance_str)
                                
                                # Extract description (everything between date and amount)
                                description = ' '.join(parts[1:-2]).strip()
                                
                                transaction = {
                                    'date': date,
                                    'description': description,
                                    'amount': amount,
                                    'balance': balance,
                                }
                                
                                transactions.append(transaction)
                            
                        except (ValueError, IndexError) as e:
                            # Skip lines that don't match expected format
                            continue
    
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None
    
    return {
        'transactions': transactions,
        'account_summary': account_summary
    }