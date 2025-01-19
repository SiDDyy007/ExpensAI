import gspread
from google.oauth2.service_account import Credentials
from smolagents import tool
from typing import List, Dict, Optional
from dateutil.parser import parse
import logging
from config.base import config
import time
import random


# Configure logging
logger = logging.getLogger(__name__)

# Initialize Google Sheets client
def get_sheets_client():
    """Initialize and return Google Sheets client."""
    try:
        credentials = Credentials.from_service_account_file(
            config.sheets.service_account_file, 
            scopes=config.sheets.scopes
        )
        return gspread.authorize(credentials)
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets client: {e}")
        raise

def get_sheet_name(transaction_date: str) -> str:
    """
    Generate a sheet name based on the transaction date.

    Args:
        transaction_date: Transaction date string in any parsable format.

    Returns:
        str: Formatted sheet name in the form 'MONTH YYYY'_TEST.
    """
    date_obj = parse(transaction_date)
    sheet_name = date_obj.strftime("%B %y'").upper() + "_TEST"
    return sheet_name

def get_or_create_sheet(spreadsheet, sheet_name) -> gspread.Worksheet:
    """
    Get or create a sheet for the given sheet name in the spreadsheet.

    Args:
        spreadsheet: gspread spreadsheet object.
        sheet_name: Name of the sheet to retrieve or create.

    Returns:
        gspread.Worksheet: The existing or newly created worksheet.
    """
    try:
        try:
            # Attempt to fetch the existing sheet
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Create a new sheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="200", cols="10")
            headers = [
                "Date", "Transaction Details", "Expense", 
                "Method of Payment", "Type of Expense", "Notes",
                "", "Cards", "Total Expense"
            ]
            worksheet.insert_row(headers, index=1)
            logger.info(f"Created new sheet: {sheet_name}")

        return worksheet
    except Exception as e:
        logger.error(f"Error in get_or_create_sheet: {e}")
        raise

def update_cards_summary(spreadsheet: gspread.spreadsheet, sheet_name: str) -> None:
    """
    Update the cards summary section in the worksheet by aggregating expenses per payment method.

    Args:
        spreadsheet: gspread spreadsheet object.
        sheet_name: Name of the sheet to update the summary for.

    Raises:
        Exception: If any error occurs during updating.
    """
    try:
        worksheet = spreadsheet.worksheet(sheet_name)

        try:
            # Fetch all records from the worksheet
            records = worksheet.get_all_records()
        except Exception as e:
            logger.warning(f"Error fetching records: {e}")
            records = fix_and_fetch_headers(worksheet)

        # Fetch headers for column indexing
        headers = worksheet.row_values(1)

        # Calculate card expenses
        card_expenses = {}
        for record in records:
            card = record.get("Method of Payment")
            expense = record.get("Expense", 0)
            if card:
                card_expenses[card] = card_expenses.get(card, 0) + float(expense or 0)

        # Update worksheet with calculated card expenses
        cards_col_index = headers.index("Cards") + 1
        total_col_index = headers.index("Total Expense") + 1

        row = 2
        for card, total in card_expenses.items():
            worksheet.update_cell(row, cards_col_index, card)
            worksheet.update_cell(row, total_col_index, total)
            row += 1

        logger.info("Updated cards summary")
    except Exception as e:
        logger.error(f"Error updating cards summary: {e}")
        raise

def fix_and_fetch_headers(sheet: gspread.Worksheet) -> List[Dict]:
    """
    Fix duplicate headers in worksheet and return records.
    
    Args:
        sheet: Worksheet to fix headers
    
    Returns:
        List of records with fixed headers
    """
    headers = sheet.row_values(1)
    
    # Make headers unique
    seen = {}
    unique_headers = []
    for header in headers:
        if header in seen:
            seen[header] += 1
            unique_headers.append(f"{header}_{seen[header]}")
        else:
            seen[header] = 0
            unique_headers.append(header)
    
    # Update headers and return records
    sheet.update('1:1', [unique_headers])
    return sheet.get_all_records()

@tool
def update_expense_sheet(transactions: list) -> bool:
    """
    Update the expense sheet with new transactions and update card summaries.

    Args:
        transactions: List of transaction dictionaries containing transaction details.

    Returns:
        bool: True if all transactions are processed successfully, otherwise False.
    """ 
    try:
        total = len(transactions)
        passed = 0
        client = get_sheets_client()
        spreadsheet = client.open(config.sheets.spreadsheet_name)

        sheet_names_for_update = set()
        
        for transaction in transactions:
            try:
                def process_transaction():
                    sheet_name = get_sheet_name(transaction['date'])
                    sheet = get_or_create_sheet(spreadsheet, sheet_name)

                    # Prepare row data
                    row = [
                        transaction['date'],
                        transaction['merchant'],
                        transaction['amount'],
                        transaction['card'],
                        transaction['category'],
                        transaction.get('description', '')
                    ]

                    # Track sheet name for summary update
                    sheet_names_for_update.add(sheet_name)

                    # Add row to sheet
                    empty_row_index = len(sheet.get_all_values()) + 1
                    for index, value in enumerate(row, start=1):
                        sheet.update_cell(empty_row_index, index, value)

                    logger.info(f"Added transaction to sheet: {sheet.title}")

                # Retry transaction processing with exponential backoff
                exponential_backoff(process_transaction)
                passed += 1
            except Exception as e:
                logger.error(f"Error adding transaction: {e}")
                continue
        
        logger.info(f"{passed} out of {total} transactions updated successfully")

        # Update card summaries for relevant sheets
        for sheet_name in sheet_names_for_update:
            exponential_backoff(lambda: update_cards_summary(spreadsheet, sheet_name))

        return True
    except Exception as e:
        logger.error(f"Error in update_expense_sheet: {e}")
        return False

@tool
def get_monthly_transactions(date_str: str) -> list:
    """
    Get all transactions for a specific month.
    
    Args:
        date_str: Date string in any format
        
    Returns:
        List of transaction records
    """
    try:
        # Parse date and get sheet
        date_obj = parse(date_str)
        sheet_name = date_obj.strftime("%b %y'").upper()
        
        client = get_sheets_client()
        spreadsheet = client.open(config.sheets.spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Get records
        try:
            records = worksheet.get_all_records()
        except Exception as e:
            logger.warning(f"Error fetching records: {e}")
            records = fix_and_fetch_headers(worksheet)
            
        return records
        
    except Exception as e:
        logger.error(f"Error getting monthly transactions: {e}")
        return []
    
def exponential_backoff(func, max_retries=5, base_delay=1):
    """Exponential backoff algorithm for retrying a function."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Retrying after {delay:.2f} seconds due to error: {e}")
                time.sleep(delay)
            else:
                logger.error(f"Max retries reached. Error: {e}")
                raise