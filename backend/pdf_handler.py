import pdfplumber
import tempfile
import os
from fastapi import UploadFile
from transformers import BertTokenizerFast, BertForTokenClassification
import torch
from database import store_transaction, store_embedding
from sentence_transformers import SentenceTransformer
from smolagents import CodeAgent, LiteLLMModel, tool
import numpy as np
import time
import requests

# Load BERT model for NER
model_path = os.environ.get("PRETRAINED_MODEL_PATH")
# Load tokenizer
tokenizer = BertTokenizerFast.from_pretrained(model_path)
# Load model (automatically detects .safetensors)
model = BertForTokenClassification.from_pretrained(model_path)

agent_model = LiteLLMModel(
            model_id=os.environ.get("ANTHROPIC_MODEL"),  # Ensure this is set in your environment
            api_key=os.environ.get("ANTHROPIC_API_KEY"),  # Ensure this is set in your environment
        )

# Load sentence transformer for embeddings
embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")

def extract_transactions(text_list : list, tokenizer=tokenizer, model=model):
    """
    Extract transactions from text using the BERT NER model
    """
    transactions = []
    for text in text_list:
        # Process each chunk with BERT & Group entities into potential transactions
        transaction = process_entities_into_transaction(model=model, tokenizer=tokenizer, text=text)
        # Debugging: print the transaction for inspection
        print("--t--")
        if transaction:
            transactions.extend(transaction)
    
    return transactions

def process_entities_into_transaction(model, tokenizer, text):
    """
    Convert NER entities into transaction dictionaries
    Extract transactions from the given text
    """
    # device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    device = 'mps'
    model.eval()
    model.to(device)

    transactions = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    for line in lines:
        # Tokenize
        inputs = tokenizer(
            line,
            return_tensors='pt',
            padding=True,
            truncation=True,
            max_length=128,
            return_offsets_mapping=True
        )

        # Extract offsets before moving inputs to device
        offsets = inputs.pop('offset_mapping').squeeze().tolist()

        # Move inputs to device
        input_ids = inputs['input_ids'].to(device)
        attention_mask = inputs['attention_mask'].to(device)

        # Get predictions
        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            predictions = torch.argmax(outputs.logits, dim=2).squeeze().tolist()

        # Extract entities
        date = ""
        merchant = ""
        amount = ""

        current_entity = None
        current_text = ""

        tokens = tokenizer.convert_ids_to_tokens(input_ids.squeeze().tolist())

        for i, (token, pred, offset) in enumerate(zip(tokens, predictions, offsets)):
            # Skip special tokens
            if offset == [0, 0]:
                continue

            # Get label
            label = model.config.id2label.get(pred, 'O')

            # Handle entity transitions
            if label.startswith('B-'):
                # Save previous entity
                if current_entity == 'DATE' and current_text:
                    date = current_text.replace('##', '')
                elif current_entity == 'MERCHANT' and current_text:
                    merchant = current_text.replace('##', '')
                elif current_entity == 'AMOUNT' and current_text:
                    amount = current_text.replace('##', '')

                # Start new entity
                current_entity = label[2:]
                current_text = token.replace('##', '')

            elif label.startswith('I-') and current_entity == label[2:]:
                # Continue current entity
                if token.startswith('##'):
                    current_text += token[2:]
                else:
                    current_text += " " + token

            else:  # O or different entity
                # Save previous entity
                if current_entity == 'DATE' and current_text:
                    date = current_text.replace('##', '')
                elif current_entity == 'MERCHANT' and current_text:
                    merchant = current_text.replace('##', '')
                elif current_entity == 'AMOUNT' and current_text:
                    amount = current_text.replace('##', '')

                # Reset
                current_entity = None
                current_text = ""

        # Save final entity
        if current_entity == 'DATE' and current_text:
            date = current_text.replace('##', '')
        elif current_entity == 'MERCHANT' and current_text:
            merchant = current_text.replace('##', '')
        elif current_entity == 'AMOUNT' and current_text:
            amount = current_text.replace('##', '')

        # Clean up entities
        date = date.strip()
        merchant = merchant.strip()
        amount = amount.strip()

        # Add transaction if we have at least date and one other field
        if date and (merchant or amount):
            transactions.append({
                'Date': date,
                'Merchant': merchant,
                'Charge': amount
            })

    return transactions

@tool
def get_historical_context(note_to_search : str) -> dict:
    """
    This is a tool that gets historical context for a transaction based on previous transactions.
    Args:
        note_to_search: A small paraphrase which will help to search for the historical context
    Returns:
        dict: A dictionary containing historical context for the transaction
    """
    # Use the vector similarity search capability of Supabase
    from database import find_similar_transactions
    try:
        note_embedding = create_embedding(note_to_search)
    except Exception as e:
        print(f"Error creating embedding for note: {e}")
        return "Error creating embedding for note"

    # Find similar transactions based on the note embedding
    result = find_similar_transactions(note_embedding.tolist(), limit=5)
    if not result:
        print("No similar transactions found")
        return "No similar transactions found"
    return result

@tool
def get_human_feedback(merchant: str, charge: float) -> str:
    """
    Get human feedback for anomalous transactions that cannot be categorized automatically.
    Args:
        merchant: The name of the merchant for the transaction.
        charge: The transaction amount.
    Returns:
        str: Human feedback on the transaction.
    """
    try:
            # Define API endpoints (adjust based on your deployment)
            api_base_url = "http://localhost:3000/api/transactions"
            request_endpoint = f"{api_base_url}/request-feedback"
            result_endpoint = f"{api_base_url}/get-feedback-result"
            
            # Request feedback from frontend
            response = requests.post(
                request_endpoint,
                json={"merchant": merchant, "charge": charge}
            )
            
            if not response.ok:
                print(f"Error requesting feedback: {response.status_code} {response.text}")
                return "Could not get feedback. Please use your best judgement for now"
            
            request_data = response.json()
            request_id = request_data.get("requestId")
            
            if not request_id:
                print( "Error: Missing request ID in response")
                return "Could not get feedback. Please use your best judgement for now"
            
            # Wait for user feedback with timeout (default 5 minutes)
            max_attempts = 60  # 5 minutes with 5-second intervals
            for attempt in range(max_attempts):
                # Check if feedback is available
                result_response = requests.get(f"{result_endpoint}?requestId={request_id}")
                
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    if result_data.get("success"):
                        return result_data.get("feedback", "")
                
                # Wait before checking again
                time.sleep(5)
            print("Feedback request timed out after 5 minutes")
            return "Could not get feedback. Please use your best judgement for now"
            # return "Feedback request timed out after 5 minutes"
            
    except Exception as e:
        print( f"Error getting feedback: {str(e)}")
        return "Could not get feedback. Please use your best judgement for now"
    
from datetime import datetime

def complete_date(date_str, assumed_year=None):
    """Converts 'MM / DD' to 'YYYY-MM-DD' with assumed or current year."""
    try:
        assumed_year = assumed_year or datetime.now().year
        month, day = map(int, date_str.replace(" ", "").split("/"))
        return f"{assumed_year:04d}-{month:02d}-{day:02d}"
    except Exception as e:
        print(f"Error completing date: {e}")
        return None

def parse_freedom_transaction(transaction) -> bool:
    # Set card issuer here and modification of transaction
    if not transaction.get('Charge') or not transaction.get('Date') or not transaction.get('Merchant') or '$' in transaction.get('Charge'):
        return False
    transaction['Date'] = complete_date(transaction['Date'])
    if not transaction['Date']:
        return False
    transaction['Card'] = 'FREEDOM'
    return transaction

def parse_amex_transaction(transaction) -> bool:
    # Set card issuer here and modification of transaction
    if not transaction.get('Charge') or not transaction.get('Date') or not transaction.get('Merchant') or '$' not in transaction.get('Charge'):
        return False
    transaction['Card'] = 'AMEX'
    transaction['Date'] = parse_date(transaction['Date'])
    if not transaction['Date']:
        return False
    return transaction

def parse_date(date_str):
    """
    Parse date string to 'YYYY-MM-DD' format
    """
    date_str = date_str.replace(",","").replace(" ", "").replace("*", "")  # Remove any spaces for consistent parsing
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
        print("Date is required")
        return None
    return date

card_issuers = {    'AMEX': parse_amex_transaction,
                    'FREEDOM': parse_freedom_transaction,
                    'ZOLVE': 'ZOLVE' # TODO: Implement ZOLVE transaction parsing
                }

def get_category_and_note(transaction):
    """
    Get category and note for a transaction
    """
    analysis_agent = CodeAgent(
        tools=[get_historical_context, get_human_feedback],
        model=agent_model,
        # add_base_tools=True,
        additional_authorized_imports=["pandas", "datetime", "numpy"] 
    )


    try:
        analysis_prompt = f"""You are a financial analyst assisting in transaction categorization and pattern recognition.  

        Context:  
        Analyze the given transaction based on your understanding and reasoning to categorize it.  
        Refer to previous user transactions using the `get_historical_context` tool if relevant.  
        Use your knowledge to craft a short note describing the charge type.  

        Clarification:  
        Only ask the user for feedback **if necessary**—specifically, when:  
        - No relevant historical data is found.  
        - The charge description is unclear.  
        - The charge amount is unusual.  

        Otherwise, categorize the transaction using logical inference.  

        Output Format:  
        Return a Python dictionary in this exact structure:  

        {{  
            "category": <<One of ['Housing', 'Grocery', 'Fun', 'Investment', 'Utilities', 'Payments', 'Miscellaneous']>>,  
            "note": <<Concise explanation of the transaction for future reference>>  
        }}  

        Transaction: {transaction}"""
            
        transaction_analysis = analysis_agent.run(analysis_prompt)

        return transaction_analysis

    except Exception as e:
        print(f"Error during transaction analysis: {e}")
        raise Exception(f"Error during transaction analysis: {e}")


async def process_pdf_and_store(file: UploadFile, user_id: str):
    """
    Process a PDF file, extract transactions, and store them in the database
    """
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        # Write the uploaded file content to the temporary file
        contents = await file.read()
        temp_file.write(contents)
        temp_file_path = temp_file.name

    # Extract text from PDF
    with pdfplumber.open(temp_file_path) as pdf:
        for page in pdf.pages:
            first_page_text = page.extract_text()
            break  # Only need the first page for card issuer detection
    
    try:
        extraction_agent = CodeAgent(
            model=agent_model,
            tools=[],
            add_base_tools=False
        )

        extractor_text =f"""You are an information extractor specialized in identifying financial institutions.  

                        Context:  
                        Analyze the first page of the statement and determine the card issuer. The issuer must be one of the following: ['AMEX', 'FREEDOM', 'ZOLVE'].  

                        First Page Text:  
                        {first_page_text}

                        Output Format:  
                        Return only the card issuer name from the given list—nothing else."""

        card_issuer_response = extraction_agent.run(extractor_text)
    except Exception as e:
        print(f"Error during card issuer detection: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    
    postprocessing_function = card_issuers.get(card_issuer_response.strip(), None)
    if not postprocessing_function:
        return {
            'success': False,
            'error': "Card issuer not recognized or unsupported"
        }
    print("Card issuer detection response:", card_issuer_response)

    try:
        # Extract text from PDF
        text_list = []
        with pdfplumber.open(temp_file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_list.append(page_text)
        
        # Extract transactions from text
        transactions = extract_transactions(text_list)
        print("Length of transactions:", len(transactions))
        
        # Store each transaction
        stored_transactions = []
        for extracted_transaction in transactions:
            try:
                transaction = postprocessing_function(extracted_transaction)
                # Format transaction for database
                if not transaction:
                    # Skip incomplete transactions
                    print(f"Skipping incomplete transaction: {extracted_transaction}")
                    continue
                
                db_transaction = {
                    'date': transaction.get('Date'),
                    'merchant': transaction.get('Merchant'),
                    'amount': parse_amount(transaction.get('Charge', '0')),
                    'card': transaction.get('Card', 'UNKNOWN'),
                    # Category and note will be filled later by LLM
                }
                if db_transaction['amount'] == 0:
                    print(f"Skipping transaction with zero amount: {db_transaction}")
                    continue
                
                print(f"Processing transaction: {db_transaction}")
                analysis = get_category_and_note(db_transaction)
                print("Analysis result:", analysis)
                if analysis and 'category' in analysis and 'note' in analysis:
                    db_transaction['category'] = analysis['category']
                    db_transaction['note'] = analysis['note']

            
                # Store in database
                result = await store_transaction(user_id, db_transaction)
                if result:
                    stored_transactions.append(result)
                    
                    # Generate note for the transaction (will be updated later by LLM)
                    if not db_transaction.get('note'):
                        note = f"{transaction.get('Merchant')} {transaction.get('Charge')}"
                    else:
                        note = db_transaction['note']
                    
                    # Create and store embedding
                    print(f"Creating embedding for note: {note}")
                    embedding = create_embedding(note)
                    table_name = f'{db_transaction['category']}_transactions' 
                    print("Storing embedding now ...")
                    await store_embedding(result['id'], table_name, embedding.tolist(), {
                        'merchant': db_transaction.get('merchant'),
                        'amount': db_transaction.get('amount'),
                        'category': db_transaction.get('category'),
                        'note': db_transaction.get('note')
                    })
            except Exception as e:
                print(f"Error processing transaction {transaction}: {e}")
                continue
        
        return {
            'success': True,
            'transactions_count': len(stored_transactions),
            'transactions': stored_transactions
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

def parse_amount(amount_str):
    """
    Parse amount string to float
    """
    # Remove $ and commas, then convert to float
    cleaned = amount_str.replace(" ","").replace('$', '').replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def create_embedding(text):
    """
    Create vector embedding from text
    """
    try:
        # Use sentence transformer to create embedding
        embedding = embedding_model.encode([text])
        print(f"Embedding created for text: {text}")
    except Exception as e:
        print(f"Error creating embedding: {e}")
    return embedding[0]