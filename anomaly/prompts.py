from typing import Dict, List

def generate_search_prompt(transaction: Dict) -> str:
    """
    Generate a prompt for vector similarity search.
    
    Args:
        transaction: Transaction dictionary containing date, merchant, amount, and type
    
    Returns:
        str: Formatted search prompt
    """
    return f"""
    Transaction details:
    - Date: {transaction['date']}
    - Merchant: {transaction['merchant']}
    - Amount: ${abs(transaction['amount']):.2f}
    - Type: {transaction['type']}
    
    Looking for similar transactions or patterns related to this merchant and amount.
    """

def generate_anomaly_prompt(transaction: Dict, context: List[Dict]) -> str:
    """
    Generate a prompt for anomaly detection using transaction and historical context.
    
    Args:
        transaction: Current transaction to analyze
        context: List of similar historical transactions
    
    Returns:
        str: Formatted anomaly detection prompt
    """
    context_str = f"Similar transactions:\n{context}" if context else "No similar transactions found."
    
    return f"""Based on the following transaction and historical context, respond with ONLY the word ANOMALY or NOT_ANOMALY.

            Transaction to analyze:
            - Date: {transaction['date']}
            - Merchant: {transaction['merchant']}
            - Amount: ${abs(transaction['amount']):.2f}
            - Type: {transaction['type']}

            Historical Context:
            {context_str}

            Consider these factors:
            1. Is the amount significantly different from similar transactions?
            2. Is this an unusual merchant for this type of amount?
            3. Is the transaction timing unusual?

            Respond with ONLY one word - ANOMALY or NOT_ANOMALY:"""