from pinecone import Pinecone
from smolagents import tool
from typing import List, Dict, Any, Optional
from dateutil.parser import parse
import logging
from config.base import config

# Configure logging
logger = logging.getLogger(__name__)

def get_pinecone_client() -> Pinecone:
    """Initialize and return Pinecone client."""
    try:
        return Pinecone(api_key=config.api.pinecone_api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone client: {e}")
        raise

def get_pinecone_index():
    """Get Pinecone index for expense data."""
    try:
        pc = get_pinecone_client()
        return pc.Index(config.pinecone.index_name)
    except Exception as e:
        logger.error(f"Failed to get Pinecone index: {e}")
        raise

def generate_transaction_text(transaction: Dict) -> str:
    """Generate text description for transaction embedding."""
    return f"Transaction: {transaction['merchant']} for amount ${transaction['amount']} on {transaction['date']}"

def get_transaction_embedding(pc: Pinecone, text: str) -> Dict:
    """Generate embedding for transaction text."""
    try:
        return pc.inference.embed(
            model="multilingual-e5-large",
            inputs=[text],
            parameters={"input_type": "passage", "truncate": "END"}
        )[0]
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise

def upsert_transactions(transactions: List[Dict]) -> None:
    """
    Upsert transactions to Pinecone index.
    
    Args:
        transactions: List of transaction dictionaries
    """
    try:
        pc = get_pinecone_client()
        index = get_pinecone_index()

        # Group transactions by category
        category_groups = {}
        for txn in transactions:
            category = txn.get('category', 'uncategorized')
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(txn)

        # Process each category
        for category, txns in category_groups.items():
            try:
                # Generate text descriptions
                texts = [generate_transaction_text(t) for t in txns]

                # Generate embeddings
                embeddings = [
                    get_transaction_embedding(pc, text)
                    for text in texts
                ]

                # Prepare records
                records = []
                for txn, embedding in zip(txns, embeddings):
                    unique_id = f"{txn['date']}_{txn['merchant'].replace(' ', '_')}"
                    records.append({
                        "id": unique_id,
                        "values": embedding['values'],
                        "metadata": txn
                    })

                # Upsert records
                index.upsert(vectors=records, namespace=category)
                logger.info(f"Uploaded {len(records)} transactions to namespace '{category}'")

            except Exception as e:
                logger.error(f"Error processing category {category}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error upserting transactions: {e}")
        raise

@tool
def search_historical_summaries(search_prompt: str) -> list:
    """
    Search previous months' summaries in Pinecone.
    
    Args:
        search_prompt: Search query string
        
    Returns:
        List of relevant historical summaries
    """
    try:
        pc = get_pinecone_client()
        index = get_pinecone_index()

        # Generate embedding for search prompt
        embedding = get_transaction_embedding(pc, search_prompt)

        # Query vectorDB
        results = index.query(
            namespace="summary",
            vector=embedding['values'],
            top_k=3,
            include_values=False,
            include_metadata=True
        )

        return [match.metadata for match in results.matches]

    except Exception as e:
        logger.error(f"Error searching summaries: {e}")
        return []

@tool
def store_monthly_summary(summary_text: str, month_date: str) -> str:
    """
    Store monthly expense summary in Pinecone.
    
    Args:
        summary_text: Monthly summary text
        month_date: Date string for the month
        
    Returns:
        Success or error message
    """
    try:
        pc = get_pinecone_client()
        index = get_pinecone_index()

        # Generate embedding
        embedding = get_transaction_embedding(pc, summary_text)

        # Create unique ID and prepare record
        date_obj = parse(month_date)
        unique_id = f"summary_{date_obj.strftime('%Y_%m')}"

        record = {
            "id": unique_id,
            "values": embedding['values'],
            "metadata": {
                "summary": summary_text,
                "month": date_obj.strftime("%B %Y"),
                "timestamp": date_obj.strftime("%Y-%m-%d")
            }
        }

        # Upsert to vectorDB
        index.upsert(
            vectors=[record],
            namespace="summary"
        )

        return f"Successfully stored summary for {date_obj.strftime('%B %Y')}"

    except Exception as e:
        error_msg = f"Error storing summary: {e}"
        logger.error(error_msg)
        return error_msg