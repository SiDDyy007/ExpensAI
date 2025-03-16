# backend/database.py
import os
from supabase import create_client, Client
# from supabase.lib.client import SupabaseException

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env into the environment

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

def get_table_name_for_date(date):
    """
    Generate the appropriate table name for a given date
    """
    month = date.month
    year = date.year
    return f"transactions_{month:02d}_{year}"

async def store_transaction(user_id, transaction_data):
    """
    Store a transaction in the appropriate monthly partition
    """
    # Extract date from transaction data
    date_str = transaction_data.get('date')
    date_str = date_str.replace(",","").replace(" ", "").replace("*", "")  # Remove any spaces for consistent parsing
    # print("Transaction data received:", transaction_data)
    if isinstance(date_str, str):
        # Parse date string to datetime object
        try:
            date = datetime.strptime(date_str, '%m/%d/%y')
        except ValueError:
            try:
                date = datetime.strptime(date_str, '%m/%d/%Y')
            except ValueError:
                raise ValueError(f"Unsupported date format: {date_str}")
        except Exception as e:
            print(f"Error parsing date: {e} Skipping this boiiiiii")
            return None
    elif isinstance(date_str, datetime):
        date = date_str
    else:
        raise ValueError("Date is required")
    
    # Prepare transaction data
    transaction = {
        'user_id': user_id,
        'date': date.strftime('%Y-%m-%d'),
        'merchant': transaction_data.get('merchant'),
        'charge': float(transaction_data.get('amount', 0)),
        'card': transaction_data.get('card', 'UNKNOWN'),
        'category': transaction_data.get('category'),
        'note': transaction_data.get('note')
    }
    
    table_name = 'transactions'
    print("Inserting transaction into table:", table_name)
    # Insert transaction into the appropriate table
    try:
        result = supabase.table(f"{table_name}").insert(transaction).execute()
        print("result ", result)
        # if result.error:
        #     raise Exception(f"Error inserting transaction: {result.error}")
    except Exception as e:
        print("Unexpected error:", e)
    
    print("Transaction inserted successfully:", result.data)
    return result.data[0] if result.data else None

def create_partition_if_needed(month, year):
    """
    Call the database function to create a monthly partition if it doesn't exist
    """
    # Call the function that creates partitions
    print("Creating partition now for month:", month, "year:", year)
    # print("SUpbase - ", supabase)
    try: 
        data = supabase.rpc(
            'create_monthly_partition', 
            {'month': month, 'year': year}
        ).execute()
        print(data)
    except Exception as e:
        print(f"Unexpected error: {e}")

async def store_embedding(transaction_id, table_name, embedding, metadata=None):
    """
    Store a vector embedding for a transaction
    """
    # Prepare embedding data
    embedding_data = {
        'transaction_table': table_name,
        'transaction_id': transaction_id,
        'embedding': embedding,
        'metadata': metadata or {}
    }
    
    # Insert embedding
    try:
        result = supabase.table("transaction_embeddings").insert(embedding_data).execute()
        # print(result.data)
    except Exception as e:
        print(f"Unexpected embdeddings error: {e}")
    
    return result.data[0] if result.data else None

def find_similar_transactions(embedding, limit=5):
    """
    Find transactions with similar embeddings using vector similarity search
    Returns the metadata of the most similar transactions
    """
    try:
        result = supabase.rpc(
            'find_similar_transactions',
            {
                'query_embedding': embedding,
                'match_threshold': 0.8,
                'match_count': limit
            }
        ).execute()
        
        print(f"Found {len(result.data)} similar transactions")
        final_result = [result['metadata'] for result in result.data]  # Extract metadata from results
        return final_result
    except Exception as e:
        print(f"Error finding similar transactions: {e}")
        return []

async def get_monthly_summary(user_id, month, year):
    """
    Get the monthly summary for a user
    """
    try:
        update_monthly_summary(user_id, month, year)  # Ensure the summary is up-to-date
    except Exception as e:
        print(f"Error updating monthly summary: {e}")
    try:
        result = supabase.table("monthly_summaries") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("month", month) \
            .eq("year", year) \
            .execute()
        
        if result.data and len(result.data) > 0:
            print(f"Retrieved summary for user {user_id} in {month}/{year}")
            return result.data[0]
        else:
            print(f"No summary found for user {user_id}, month {month}, year {year}")
            
            # If no summary exists, we'll create a placeholder with zero values
            # This is optional but provides a better UX than showing nothing
            return {
                "user_id": user_id,
                "month": month,
                "year": year,
                "total_expenses": 0,
                "total_income": 0,
                "expenses_by_card": {},
                "expenses_by_category": {}
            }
            
    except Exception as e:
        print(f"Error getting monthly summary: {e}")
        return None

async def get_user_transactions(user_id, month, year, category=None, card=None):
    """
    Get transactions for a specific user in a given month/year with optional filters
    """
    # Query the transactions table directly with date filtering
    query = supabase.table("transactions") \
        .select("*") \
        .eq("user_id", user_id)
    
    # Filter by month and year using PostgreSQL EXTRACT function on the date column
    query = query \
        .filter("EXTRACT(MONTH FROM date::timestamp)", "eq", month) \
        .filter("EXTRACT(YEAR FROM date::timestamp)", "eq", year)
    
    # Add optional filters
    if category:
        query = query.eq("category", category)
    
    if card:
        query = query.eq("card", card)
    
    try:
        # Execute the query
        result = query.order("date", desc=True).execute()
        print(f"Retrieved {len(result.data)} transactions for user {user_id} in {month}/{year}")
    except Exception as e:
        print(f"Unexpected get transactions error: {e}")
        return []
        
    return result.data

async def update_transaction_category(transaction_id, table_name, category, note=None):
    """
    Update the category and optionally the note of a transaction
    """
    update_data = {'category': category}
    if note is not None:
        update_data['note'] = note
    try:
        result = supabase.table(f"{table_name}") \
            .update(update_data) \
            .eq("id", transaction_id) \
            .execute()
        print(result.data)
    # except SupabaseException as e:
    #     print(f"Supabase update error: {e}")
    except Exception as e:
        print(f"Unexpected update error: {e}")
    
    return result.data[0] if result.data else None

def update_monthly_summary(user_id, month, year ):
    """
    Manually triggers an update of the monthly summary for a specific user, month, and year.
    
    Args:
        user_id (str): UUID of the user
        month (int): Month number (1-12)
        year (int): Year (e.g., 2024)
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Call the stored procedure in Supabase
        result = supabase.rpc(
            'update_monthly_summary',
            {
                'user_uuid': user_id,
                'month_num': month,
                'year_num': year
            }
        ).execute()
        
        print(f"Successfully updated monthly summary for user {user_id}, month {month}, year {year}")
        
        # Fetch and return the updated summary
        summary_result = supabase.table("monthly_summaries") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("month", month) \
            .eq("year", year) \
            .execute()
            
        return {
            'success': True,
            'message': f"Monthly summary updated for {month}/{year}",
            'summary': summary_result.data[0] if summary_result.data else None
        }
        
    except Exception as e:
        print(f"Error updating monthly summary: {e}")
        return {
            'success': False,
            'message': f"Failed to update monthly summary: {str(e)}",
            'error': str(e)
        }