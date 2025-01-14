import pdfplumber
import json
import re
from datetime import datetime
from smolagents import tool



@tool
def parse_amex_statement(pdf_path : str) -> dict:
    """
    This is a tool that returns a JSON consisting of charges and information of each charge from a AMEX credit card bill statement.

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
                            "type": "PAYMENT" if pattern == patterns[1] else "CHARGE"
                        }
                        break  # Exit pattern loop if we found a match
                
                if transaction:
                    transactions.append(transaction)
    
    # # Save to file if output path provided
    # if output_path:
    #     with open(output_path, 'w') as f:
    #         json.dump({"transactions": transactions}, f, indent=2)
    
    return transactions

# Example usage
# if __name__ == "__main__":
#     transactions = parse_amex_statement("statements/AMEX.pdf", "transactions.json")
#     print(f"Found {len(transactions)} transactions")