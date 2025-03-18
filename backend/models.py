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