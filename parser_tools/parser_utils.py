"""Common utilities and types for statement parsers."""

from typing import TypedDict, List, Optional
from datetime import datetime
import re
import logging
from config.base import config

# Configure logging
logger = logging.getLogger(__name__)

class Transaction(TypedDict):
    """Type definition for a parsed transaction."""
    date: str  # YYYY-MM-DD format
    merchant: str
    amount: float
    type: str  # "CHARGE" or "PAYMENT"
    card: str  # Card type e.g., "AMEX", "ZOLVE", etc.

def format_date(date_str: str, input_format: str = "%m/%d/%y") -> str:
    """
    Convert date string to YYYY-MM-DD format.
    
    Args:
        date_str: Input date string
        input_format: Format of the input date string
        
    Returns:
        str: Date in YYYY-MM-DD format
    """
    try:
        date_obj = datetime.strptime(date_str, input_format)
        return date_obj.strftime("%Y-%m-%d")
    except ValueError as e:
        logger.warning(f"Error parsing date {date_str}: {e}")
        return date_str

def clean_amount(amount_str: str) -> float:
    """
    Clean and convert amount string to float.
    
    Args:
        amount_str: String representation of amount (e.g., "$123.45", "1,234.56")
        
    Returns:
        float: Cleaned amount value
    """
    try:
        # Remove currency symbols, commas and whitespace
        cleaned = re.sub(r'[^\d.-]', '', amount_str)
        return float(cleaned)
    except ValueError as e:
        logger.warning(f"Error parsing amount {amount_str}: {e}")
        return 0.0

def clean_merchant(merchant: str) -> str:
    """
    Clean merchant name string.
    
    Args:
        merchant: Raw merchant name string
        
    Returns:
        str: Cleaned merchant name
    """
    # Remove extra whitespace
    cleaned = ' '.join(merchant.split())
    # Remove common prefixes/suffixes if desired
    # cleaned = re.sub(r'^(THE|A)\s+', '', cleaned, flags=re.IGNORECASE)
    return cleaned