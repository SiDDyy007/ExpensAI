#!/usr/bin/env python3
"""
ExpensAI - Credit Card Statement Analysis and Expense Tracking System

This is the main entry point for ExpensAI. It orchestrates the complete workflow:
1. Statement Parsing
2. Transaction Analysis
3. Storage Management
4. Summary Generation
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import os

from smolagents import CodeAgent, LiteLLMModel, tool

# Import ExpensAI modules
from config.base import config
from parser_tools.statement_parser_tools import parse_amex_statement, parse_zolve_statement, parse_freedom_statement
from analysis.anomaly_detector import analyze_transaction, get_human_feedback
from storage.vector import upsert_transactions, store_monthly_summary, search_historical_summaries
from storage.sheets import update_expense_sheet, get_monthly_transactions

# Configure logging
logger = logging.getLogger(__name__)

class ExpenseAI:
    """Main ExpenseAI application class."""

    def __init__(self):
        """Initialize ExpenseAI with necessary components."""
        self.model = LiteLLMModel(
            model_id=config.llm.model,
            api_key=config.api.anthropic_api_key
        )
        
        # Initialize different agents for different tasks
        self.extraction_agent = CodeAgent(
            tools=[parse_amex_statement, parse_zolve_statement, parse_freedom_statement],
            model=self.model,
            add_base_tools=True
        )
        
        self.analysis_agent = CodeAgent(
            tools=[analyze_transaction, get_human_feedback],
            model=self.model,
            add_base_tools=True,
            additional_authorized_imports=["pandas"]
        )
        
        self.summary_agent = CodeAgent(
            tools=[
                get_monthly_transactions,
                search_historical_summaries,
                store_monthly_summary,
                self.get_user_input
            ],
            model=self.model,
            add_base_tools=True,
            additional_authorized_imports=["json", "pandas"]
        )
    
    @tool # Human-in-the-loop Feature
    def get_user_input(prompt: str) -> str:
        """
        Gets input from user after displaying a prompt.
        
        Args:
            prompt: Text to show to user as prompt
        
        Returns:
            User's input as string
        """
        try:
            return input(prompt + " ").strip()
        except Exception as e:
            return f"Error getting input: {str(e)}"
    
    def process_statements(self, statement_dir: str) -> List[Dict[str, Any]]:
        """
        Process credit card statements from the given directory.
        
        Args:
            statement_dir: Directory containing statement PDFs
            
        Returns:
            List of extracted transactions
        """
        try:
            statement_path = Path(statement_dir)
            if not statement_path.exists():
                raise FileNotFoundError(f"Statement directory not found: {statement_dir}")

            transactions = []
            for statement in statement_path.glob("*.pdf"):
                logger.info(f"Processing statement: {statement.name}")
                response = self.extraction_agent.run(
                    f"Extract my expenses from {statement} and return **only** a JSON object containing details of each charge, with no additional text or explanation."
                )

                if response:
                    transactions.extend(response)
                    logger.info(f"Extracted transactions from {statement.name}")
                else:
                    logger.warning(f"No transactions extracted from {statement.name}")

            return transactions[:5]

        except Exception as e:
            logger.error(f"Error processing statements: {e}")
            raise
    
    def analyze_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze transactions for anomalies and categorization.
        
        Args:
            transactions: List of transactions to analyze
            
        Returns:
            List of analyzed transactions with additional metadata
        """
        try:
            analyzed_transactions = []
            
            for transaction in transactions:
                # Define the transaction analysis prompt
                analysis_prompt = (
                    f"Can you analyze this transaction: {transaction}?\n\n"
                    "Based on the analysis, either ask the human to provide feedback or clarification "
                    "on the transaction for future use (only if needed).\n\n"
                    "Craft a concise description to include with the transaction JSON object for future reference.\n\n"
                    "Also include the category of the transaction from [Housing, Grocery, Fun, Investment, Miscellaneous].\n\n"
                    "The output must strictly be a Python dictionary object, not a string representation, "
                    "and follow this structure:\n"
                    "{\n"
                    '    "amount": <<amount>>,\n'
                    '    "merchant": <<merchant>>,\n'
                    '    "date": <<date>>,\n'
                    '    "type": <<type_of_transaction>>,\n'
                    '    "description": <<description>>,\n'
                    '    "category": <<transaction_category>>,\n'
                    '    "card": <<card>>,\n'
                    "}"
                )
                
                transaction_analysis = self.analysis_agent.run(analysis_prompt)
                if transaction_analysis:
                    analyzed_transactions.append(transaction_analysis)
                    logger.info(f"Analyzed transaction: {transaction['merchant']}")

            return analyzed_transactions

        except Exception as e:
            logger.error(f"Error analyzing transactions: {e}")
            raise
    
    def generate_summary(self, transactions: List[Dict[str, Any]]) -> None:
        """
        Generate and store monthly summary of transactions.
        
        Args:
            transactions: List of analyzed transactions
        """
        try:
            summary_prompt = f"""You are ExpensAI, a specialized AI assistant focused on credit card statement analysis and financial insights. 

            Here are your recent transaction analyses: {transactions}

            Please perform the following tasks in order:

            1. Generate a brief 2-3 line summary of the current month's transactions, highlighting key patterns or notable expenses.

            2. Ask the user: "Would you like me to close out this month's expense sheet and generate a detailed expense report?" (Wait for user response)

            If user agrees to generate the report:
            a. Use the get_monthly_transactions tool to get the overall month's transactions 
            b. Use the search_historical_summaries tool to fetch insights from previous months
            c. Generate a comprehensive expense report that includes:
                - Month-over-month spending trends
                - Category-wise breakdown
                - Notable changes in spending patterns
                - Actionable insights for better financial management
            d. Use the store_monthly_summary tool to save this month's summary for future reference

            3. Close the conversation with a friendly farewell that includes:
            - Acknowledgment of any actions taken
            - Professional closing

            Remember to:
            - Keep your summaries concise and focused on key insights
            - Use clear, professional language
            - Present financial data in an easy-to-understand manner
            - Maintain a helpful and supportive tone throughout"""

            self.summary_agent.run(summary_prompt)
            logger.info("Generated and stored monthly summary")

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            raise


    def run(self, statement_dir: str) -> None:
        """
        Run the complete ExpensAI workflow.
        
        Args:
            statement_dir: Directory containing statement PDFs
        """
        try:
            logger.info("Starting ExpenseAI workflow...")
            
            # Process statements
            transactions = self.process_statements(statement_dir)
            if not transactions:
                logger.warning("No transactions found in statements")
                return
            
            # Analyze transactions
            analyzed_transactions = self.analyze_transactions(transactions)
            if not analyzed_transactions:
                logger.warning("No transactions analyzed")
                return
            
            print("Analyzed trasactions ", analyzed_transactions)
            # Store transactions
            upsert_transactions(analyzed_transactions)
            update_expense_sheet(analyzed_transactions)
            
            # Generate summary
            self.generate_summary(analyzed_transactions)
            
            logger.info("ExpenseAI workflow completed successfully")
            
        except Exception as e:
            logger.error(f"Error in ExpenseAI workflow: {e}")
            raise


def main():
    """Main entry point for ExpenseAI."""
    try:
        # Setup logging
        setup_logging(log_file="expensai.log")
        
        # Initialize ExpenseAI
        expense_ai = ExpenseAI()
        
        # Get statement directory from environment or use default
        statement_dir = os.getenv("STATEMENT_DIR", "statements")
        
        # Run ExpenseAI
        expense_ai.run(statement_dir)
        
    except Exception as e:
        logger.error(f"ExpenseAI failed: {e}")
        raise

if __name__ == "__main__":
    main()