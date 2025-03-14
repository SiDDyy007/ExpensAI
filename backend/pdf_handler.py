# backend/pdf_handler.py
import pdfplumber
import tempfile
import os
from fastapi import UploadFile
# from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from transformers import BertTokenizerFast, BertForTokenClassification
import torch
from database import store_transaction, store_embedding
from sentence_transformers import SentenceTransformer
from smolagents import CodeAgent, LiteLLMModel, tool, ToolCallingAgent
# from parser_tools.statement_parser_tools import parse_amex_statement
import numpy as np

# Load BERT model for NER
model_path = 'transaction_extraction_model/'
# Load tokenizer
tokenizer = BertTokenizerFast.from_pretrained(model_path)
# Load model (automatically detects .safetensors)
model = BertForTokenClassification.from_pretrained(model_path)

agent_model = LiteLLMModel(
            model_id='claude-3-5-haiku-20241022',
            api_key=os.environ.get("ANTHROPIC_API_KEY"),  # Ensure this is set in your environment
        )

# tokenizer = AutoTokenizer.from_pretrained("dbmdz/bert-large-cased-finetuned-conll03-english")
# model = AutoModelForTokenClassification.from_pretrained("dbmdz/bert-large-cased-finetuned-conll03-english")
# ner = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

# Load sentence transformer for embeddings
embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")

def extract_transactions(text_list : list, tokenizer=tokenizer, model=model):
    """
    Extract transactions from text using the BERT NER model
    """
    # Split text into manageable chunks for BERT (512 token limit)
    # chunks = split_text_into_chunks(text, max_length=450)
    
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
    context = []
    """
    Find transactions with similar embeddings using vector similarity search
    """
    # Use the vector similarity search capability of Supabase
    from database import find_similar_transactions
    note_embedding = create_embedding(note_to_search)
    result = find_similar_transactions(note_embedding.tolist(), limit=5)
    if not result:
        return "No similar transactions found"
    return result

@tool
def get_human_feedback(transaction : dict) -> str:
    """
    Get human feedback for anomalous transactions which you can not categorize on your own or based upon historical context.
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
        return f"Error getting feedback: {str(e)}"


def parse_amex_transaction(transaction) -> bool:
    # Set card issuer here and modification of transaction
    if not transaction.get('Charge') or not transaction.get('Date') or not transaction.get('Merchant') or '$' not in transaction.get('Charge'):
        return True
    return False

def get_category_and_note(transaction):
    """
    Get category and note for a transaction
    """
    analysis_agent = CodeAgent(
        tools=[get_historical_context, get_human_feedback],
        model=agent_model,
        add_base_tools=True,
        additional_authorized_imports=["pandas"]
    )


    try:
        analysis_prompt = (
            f"Can you analyze this transaction: {transaction}?\n\n"
            "For the analysis you can also refer to previous transactions of the user.\n " 
            "For that you can use get_historical_context tool where you can craft an short note argument of the charge type based upon your understanding\n\n"
            "Based on the analysis, either ask the human to provide feedback or clarification "
            "on the transaction for future use (only if needed).\n\n"
            "Craft a concise short note description to include with the JSON object for future reference.\n\n"
            "Also include the category of the transaction from [Housing, Grocery, Fun, Investment, Miscellaneous].\n\n"
            "The output must strictly be a Python dictionary object, not a string representation, "
            "and follow this structure:\n"
            "{\n"
            '    "category": <<transaction_category>>,\n'
            '    "note": <<note>>,\n'
            "}"
        )
            
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
    # text_list = []
    with pdfplumber.open(temp_file_path) as pdf:
        for page in pdf.pages:
            first_page_text = page.extract_text()
            break  # Only need the first page for card issuer detection
    
    try:
        extraction_agent = CodeAgent(
            model=agent_model,
            tools=[],
            add_base_tools=True
        )

        response = extraction_agent.run(
                    f"""Based upon the first page of the statement, determine the card issuer and output its name\n
                    First page text \n : {first_page_text} \n
                    The card issuer names must be from ['AMEX', 'FREEDOM', 'ZOLVE']\n
                    Only output the card issuer name from the given names and nothing else. \n"""
        )
    except Exception as e:
        print(f"Error during card issuer detection: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    print("Card issuer detection response:", response)
    if response == 'AMEX':
        print("Detected card issuer: AMEX")
        postprocessing_function = parse_amex_transaction
        # Post processing function Addition here
        try:
            # Extract text from PDF
            text_list = []
            with pdfplumber.open(temp_file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_list.append(page_text)
            
            # Extract transactions from text
            # first_page = text_list[0]
            transactions = extract_transactions(text_list)
            print("Length of transactions:", len(transactions))
            
            # Store each transaction
            stored_transactions = []
            for transaction in transactions:
                try:
                    # Format transaction for database
                    if postprocessing_function(transaction):
                        # Skip incomplete transactions
                        print(f"Skipping incomplete transaction: {transaction}")
                        continue
                    print(f"Processing transaction: {transaction}")
                    
                    db_transaction = {
                        'date': transaction.get('Date'),
                        'merchant': transaction.get('Merchant'),
                        'amount': parse_amount(transaction.get('Charge', '0')),
                        'card': transaction.get('Card', 'UNKNOWN'),
                        # Category and note will be filled later by LLM
                    }
                    analysis = get_category_and_note(db_transaction)
                    print("Analysis result:", analysis)
                    if analysis and 'category' in analysis and 'note' in analysis:
                        db_transaction['category'] = analysis['category']
                        db_transaction['note'] = analysis['note']

                    
                    # print("Created db dict:", db_transaction)
                    if db_transaction['amount'] == 0:
                        print(f"Skipping transaction with zero amount: {db_transaction}")
                        continue
                
                    # Store in database
                    result = await store_transaction(user_id, db_transaction)
                    if result:
                        stored_transactions.append(result)
                        
                        # Generate note for the transaction (will be updated later by LLM)
                        if not db_transaction.get('note'):
                            note = f"{transaction.get('Date')} {transaction.get('Merchant')} {transaction.get('Charge')}"
                        else:
                            note = db_transaction['note']
                        
                        # Create and store embedding
                        print(f"Creating embedding for note: {note}")
                        embedding = create_embedding(note)
                        # table_name = f"transactions_{result['date'].month:02d}_{result['date'].year}"
                        table_name = 'transactions_sample'  # For simplicity, using a static table name
                        print("Storing embedding now ...")
                        await store_embedding(result['id'], table_name, embedding.tolist(), {
                            'merchant': transaction.get('Merchant'),
                            'amount': parse_amount(transaction.get('Charge', '0'))
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
        # print(f"Creating embedding for text: {text}")
        embedding = embedding_model.encode([text])
        # print(f"Embedding shape: {embedding.shape}")
        # print(f"Embedding len: {len(embedding)}")
    except Exception as e:
        print(f"Error creating embedding: {e}")
    return embedding[0]