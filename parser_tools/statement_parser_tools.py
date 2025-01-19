import pdfplumber
import re
from datetime import datetime
from smolagents import tool



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
    transactions = []
    
    # Two patterns to match different transaction types
    patterns = [
        # Regular charges pattern
        r'(\d{2}/\d{2}/\d{2})\s+(.+?)\s+\$(\d+\.\d{2})',
        # Payment pattern (includes * and negative amounts)
        r'(\d{2}/\d{2}/\d{2})\*\s+(.+?)\s+-\$(\d+\.\d{2})'
    ]
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            
            # Process each line to handle multiline transactions
            for line in text.split('\n'):
                transaction = None
                
                # Try both patterns
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        date_str, description, amount = match.groups()
                        
                        # Convert date to YYYY-MM-DD format
                        try:
                            date_obj = datetime.strptime(date_str, '%m/%d/%y')
                            formatted_date = date_obj.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                        
                        # For payments (second pattern), make amount negative
                        amount_float = float(amount)
                        if pattern == patterns[1]:  # Payment pattern
                            amount_float = -amount_float
                        
                        transaction = {
                            "date": formatted_date,
                            "merchant": description.strip(),
                            "amount": amount_float,
                            "type": "PAYMENT" if pattern == patterns[1] else "CHARGE",
                            "card" : 'AMEX'
                        }
                        break  # Exit pattern loop if we found a match
                
                if transaction:
                    transactions.append(transaction)
      
    return transactions

@tool
def parse_zolve_statement(pdf_path : str) -> dict:
    """
    This is a tool that extracts and returns a Expense JSON consisting of charges and information of each charge from a ZOLVE credit card bill statement.

    Args:
        pdf_path: The path to the ZOLVE credit card bill statement PDF file.
    """
    transactions = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Extract text from the page
                text = page.extract_text()
                
                # Split text into lines
                lines = text.split('\n')

                in_transactions = False
                
                # Process each line
                for line in lines:
                    # Skip empty lines and headers
                    if not line.strip() or 'Posted Date' in line or 'Sub Total' in line:
                        continue

                    if "Payments and Other Credits" in line:
                        in_transactions = True
                        negative_amount = True
                        continue

                    if "Purchases and Cash Advances" in line:
                        in_transactions = True
                        negative_amount = False
                        continue
                    
                    if in_transactions and not line.startswith("Sub Total:"):
                        # Try to parse the line as a transaction
                        try:
                            # Expected format: Posted Date Transaction Date Description Amount
                            parts = line.split()
                            
                            # Extract amount (last element)
                            amount_str = parts[-1].replace('$', '').replace(',', '')
                            amount = float(amount_str)
                            
                            # Extract dates (first two elements that match date format)
                            dates = []
                            for part in parts:
                                try:
                                    date = datetime.strptime(part, '%m/%d/%Y')
                                    dates.append(date.strftime('%Y-%m-%d'))
                                    if len(dates) == 2:
                                        break
                                except ValueError:
                                    continue
                            
                            if len(dates) == 2:
                                # Join remaining parts as description
                                description = ' '.join(parts[2:-1])
                                
                                transaction = {
                                    'posted_date': dates[0],
                                    'date': dates[1],
                                    'merchant': description,
                                    'amount': amount * (-1 if negative_amount else 1),
                                    'type' : "PAYMENT" if negative_amount else "CHARGE",
                                    'card' : "ZOLVE"
                                }
                                transactions.append(transaction)
                        except (ValueError, IndexError):
                            # Skip lines that don't match expected format
                            continue
    
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None
    
    return transactions

@tool
def parse_freedom_statement(pdf_path: str) -> dict:
    """
    This is a tool that extracts and returns a Expense JSON consisting of charges and information of each charge from a FREEDOM credit card bill statement.
    
    Args:
        pdf_path: The path to the FREEDOM credit card bill statement PDF file.
    """
    transactions = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            current_year = str(datetime.now().year) 
            for page in pdf.pages:
                text = page.extract_text()
                if 'Opening/Closing Date' in text:
                    match = re.search(r'Opening/Closing Date \d{2}/\d{2}/(\d{2})', text)
                    if match:
                        year = match.group(1)
                        # Convert 2-digit year to 4-digit year
                        current_year = '20' + year
                
                lines = text.split('\n')
                
                # Track current section
                in_transactions = False
                
                for line in lines:
                    # Skip empty lines
                    if not line.strip():
                        continue

                    # print(line, '\n')
                    
                    # Check for section headers
                    if "PAYMENTS AND OTHER CREDITS" in line or "PURCHASE" in line:
                        in_transactions = True
                        continue

                    if in_transactions:
                        try:
                            # Skip lines that don't start with a date
                            if not re.match(r'\d{2}/\d{2}', line):
                                continue
                                
                            # Split line into components
                            parts = line.split()
                            
                            # Extract date
                            date_str = parts[0] + '/' + current_year
                            transaction_date = datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
                            
                            # Extract amount (last element)
                            amount_str = parts[-1].replace('$', '').replace(',', '')
                            amount = float(amount_str)
                            
                            # Join remaining parts as description
                            description = ' '.join(parts[1:-1])
                            
                            transaction = {
                                'date': transaction_date,
                                'merchant': description,
                                'amount': amount,
                                'type': 'PAYMENT' if amount < 0 else 'PURCHASE',
                                'card' : 'FREEDOM'
                            }
                            
                            transactions.append(transaction)
                            
                        except (ValueError, IndexError) as e:
                            # Skip lines that don't match expected format
                            continue
    
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None
    
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