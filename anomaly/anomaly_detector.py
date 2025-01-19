from typing import Dict, List, Any
import logging
from smolagents import tool
from pinecone import Pinecone
from langchain_anthropic import ChatAnthropic
from config.base import config
from .prompts import generate_search_prompt, generate_anomaly_prompt

# Configure logging
logger = logging.getLogger(__name__)

def get_expense_namespace(transaction: Dict) -> str:
    """
    Get namespace according to transaction details.
    
    Args:
        transaction: Transaction dictionary containing details
    
    Returns:
        str: Namespace category from [Housing, Grocery, Fun, Investment, Miscellaneous]
    """
    try:
        # Initialize LLM
        llm = ChatAnthropic(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            timeout=config.llm.timeout,
            max_retries=config.llm.max_retries,
        )
        
        # Generate prompt
        namespace_prompt = f"""
        Transaction details:
        - Date: {transaction['date']}
        - Merchant: {transaction['merchant']}
        - Amount: ${abs(transaction['amount']):.2f}
        - Type: {transaction['type']}
        
        Analyze this transaction and get the most appropriate namespace category this transaction may belong to from [Housing , Grocery, Fun, Investment, Miscellaneous]
        Reply in only and only one word from the given namespace category
        """

        # Query LLM
        messages = [
            (
                "system",
                "Your name is ExpensAI. Your job is to help users manage their expenses by categorizing their credit card charges according to them. Keep your responses clear and concise."
            ),
            (
                "human",
                namespace_prompt
            )
        ]
        
        response = llm.invoke(messages)
        
        # Validate response
        if response.content not in ["Housing", "Grocery", "Fun", "Investment", "Miscellaneous"]:
            return "Miscellaneous"
        
        return response.content
        
    except Exception as e:
        logger.error(f"Error getting expense namespace: {e}")
        return "Miscellaneous"



@tool
def analyze_transaction(transaction: Dict) -> str:
    """
    Analyze a single transaction and return anomaly status.
    
    Args:
        transaction: Current transaction to analyze
    
    Returns:
        str: Analysis results (ANOMALY or NOT_ANOMALY)
    """
    try:
        # Initialize Pinecone
        pc = Pinecone(api_key=config.api.pinecone_api_key)
        index = pc.Index(config.pinecone.index_name)
        
        # Generate search embedding
        search_prompt = generate_search_prompt(transaction)
        embedding = pc.inference.embed(
            model="multilingual-e5-large",
            inputs=[search_prompt],
            parameters={"input_type": "query"}
        )

        # Get transaction namespace
        namespace = get_expense_namespace(transaction)
        logger.info(f"Transaction categorized as {namespace}")

        # Query similar transactions
        query_response = index.query(
            namespace=namespace,
            vector=embedding[0].values,
            top_k=3,
            include_values=False,
            include_metadata=True
        )

        # Extract context
        context = [match.metadata for match in query_response.matches]
        
        # Initialize LLM
        llm = ChatAnthropic(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            timeout=config.llm.timeout,
            max_retries=config.llm.max_retries,
        )
        
        # Generate anomaly detection prompt
        anomaly_prompt = generate_anomaly_prompt(transaction, context)

        # Query LLM
        messages = [
            (
                "system",
                "Your name is ExpensAI. Your job is to help users manage their expenses by categorizing their credit card charges according to them. Keep your responses clear and concise."
            ),
            (
                "human",
                anomaly_prompt
            )
        ]
        
        response = llm.invoke(messages)
        
        # Validate response
        if response.content not in ["ANOMALY", "NOT_ANOMALY"]:
            logger.warning(f"Invalid response from LLM: {response.content}")
            return "NOT_ANOMALY"
        
        logger.info(f"Transaction analyzed as: {response.content}")
        return response.content
    
    except Exception as e:
        logger.error(f"Error analyzing transaction: {e}")
        return "NOT_ANOMALY"

@tool
def get_human_feedback(transaction: Dict) -> str:
    """
    Get human feedback for anomalous transactions.
    
    Args:
        transaction: Transaction dictionary to get feedback on
    
    Returns:
        str: Human feedback on the transaction
    """
    try:
        return input(f"""The following transaction has been determined to be anomalous based on previous charges:
                     {transaction} 
                     Please provide feedback/explanation on the transaction for future reference.\n""")
    except Exception as e:
        logger.error(f"Error getting human feedback: {e}")
        return f"Error getting feedback: {str(e)}"