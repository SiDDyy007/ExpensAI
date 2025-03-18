import os
import json
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

def calculate_monthly_summaries(
    month=None, 
    year=None, 
    user_id=None, 
    specific_months=None, 
    recalculate_all=False
):
    """
    Calculate monthly summaries for expenses by card and category.
    
    Parameters:
    - month: Integer representing the month (1-12). If None, uses current month.
    - year: Integer representing the year. If None, uses current year.
    - user_id: UUID of the user to calculate summaries for. If None, calculates for all users.
    - specific_months: List of (month, year) tuples to calculate for. Overrides month and year parameters.
    - recalculate_all: Boolean to recalculate for all months in the database.
    
    Returns:
    - Dict with summary of operations performed
    """
    # Initialize Supabase client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase = create_client(url, key)
    
    results = []
    
    # Determine which months to process
    months_to_process = []
    
    if recalculate_all:
        # Get all distinct month/year combinations from transactions table
        response = supabase.table('transactions').select('date').execute()
        if len(response.data) > 0:
            # Extract unique month/year combinations
            unique_dates = set()
            for item in response.data:
                date = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
                unique_dates.add((date.month, date.year))
            months_to_process = list(unique_dates)
    elif specific_months:
        months_to_process = specific_months
    else:
        # Use provided month/year or default to current
        current_date = datetime.now()
        month = month or current_date.month
        year = year or current_date.year
        months_to_process = [(month, year)]
    
    # Process each month
    for month, year in months_to_process:
        # Call the Supabase function
        response = supabase.rpc(
            'calculate_all_monthly_summaries',
            {
                'p_month': month,
                'p_year': year,
                'p_user_id': user_id
            }
        ).execute()
        
        if hasattr(response, 'error') and response.error:
            results.append({
                'month': month,
                'year': year,
                'user_id': user_id,
                'error': response.error
            })
        else:
            results.append(response.data)
    
    return {
        'success': True,
        'summary': f"Processed {len(results)} month(s)",
        'details': results
    }

# Example usage
if __name__ == "__main__":
    # Example 1: Calculate for current month
    result = calculate_monthly_summaries(year=2024, month=4, user_id='990042f4-754c-4115-a838-2f73539a161f')
    print(json.dumps(result, indent=2))
    
    # Example 2: Calculate for a specific month
    # result = calculate_monthly_summaries(month=3, year=2024)
    
    # Example 3: Calculate for a specific user
    # result = calculate_monthly_summaries(user_id="some-user-uuid")
    
    # Example 4: Calculate for specific months
    # result = calculate_monthly_summaries(specific_months=[(1, 2024), (2, 2024)])
    
    # Example 5: Recalculate all months
    # result = calculate_monthly_summaries(recalculate_all=True)