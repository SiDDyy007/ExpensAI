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
    # response = supabase.auth.get_user()
    # print("Current user response:", response)
    # if session_token and refresh_token:
    #     try:
    #         print("Setting session with token:", session_token, "and refresh token:", refresh_token)
    #         supabase.auth.set_session(session_token, refresh_token)
    #     except Exception as e:
    #         print(f"Error setting session: {e}")
    #         raise ValueError("Invalid token provided")
    # else:
    #     raise ValueError("Token is required to set session")
    
    # response = supabase.auth.get_user()
    # print("Current user 2nd response:", response)


    # Extract date from transaction data
    date_str = transaction_data.get('date')
    date_str = date_str.replace(",","").replace(" ", "").replace("*", "")  # Remove any spaces for consistent parsing
    print("Transaction data received:", transaction_data)
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
    
    # print("Getting table name for date:", date)
    # Format table name
    table_name = get_table_name_for_date(date)

    print("Table name for date:", table_name)

    
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
    
    # Create partition if it doesn't exist
    # create_partition_if_needed(date.month, date.year)
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
    # except SupabaseException as e:
    #     print(f"Supabase embeddings error: {e}")
    except Exception as e:
        print(f"Unexpected embdeddings error: {e}")
    
    return result.data[0] if result.data else None

async def find_similar_transactions(embedding, limit=5):
    """
    Find transactions with similar embeddings using vector similarity search
    """
    # Use the vector similarity search capability of Supabase
    try:
        query = supabase.rpc(
            'match_transaction_embeddings',
            {
                'query_embedding': embedding,
                'match_threshold': 0.8,  # Adjust based on your needs
                'match_count': limit
            }
        )
        result = query.execute()
        print(result.data)
    # except SupabaseException as e:
    #     print(f"Supabase similar error: {e}")
    except Exception as e:
        print(f"Unexpected similar error: {e}")
    return result.data

async def get_monthly_summary(user_id, month, year):
    """
    Get the monthly summary for a user
    """
    try:
        result = supabase.table("monthly_summaries") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("month", month) \
            .eq("year", year) \
            .execute()
        print(result.data)
    # except SupabaseException as e:
    #     print(f"Supabase summary error: {e}")
    except Exception as e:
        print(f"Unexpected summary error: {e}")
    
    return result.data[0] if result.data else None

async def get_user_transactions(user_id, month, year, category=None, card=None):
    """
    Get transactions for a specific user in a given month/year with optional filters
    """
    table_name = f"transactions_{month:02d}_{year}"
    
    # Start building the query
    query = supabase.table(f"{table_name}") \
        .select("*") \
        .eq("user_id", user_id)
    
    # Add optional filters
    if category:
        query = query.eq("category", category)
    
    if card:
        query = query.eq("card", card)
    
    try:
        # Execute the query
        result = query.order("date", desc=True).execute()
        print(result.data)
    # except SupabaseException as e:
    #     print(f"Supabase get trans error: {e}")
    except Exception as e:
        print(f"Unexpected get trans error: {e}")
        
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