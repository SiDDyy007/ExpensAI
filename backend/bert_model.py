# bert_model.py
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import torch

# Load the model and tokenizer once at module level
model_name = "dbmdz/bert-large-cased-finetuned-conll03-english"
tokenizer = None
model = None
ner_pipeline = None

def load_model():
    """
    Load BERT model and tokenizer for NER
    """
    global tokenizer, model, ner_pipeline
    
    if tokenizer is None or model is None:
        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        
        # Create NER pipeline
        ner_pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple"
        )
    
    return tokenizer, model

def process_text_with_bert(text):
    """
    Process text with BERT model for Named Entity Recognition
    
    Args:
        text (str): Text to process
        
    Returns:
        list: List of identified entities
    """
    # Make sure model is loaded
    if ner_pipeline is None:
        load_model()
    
    # Process text in chunks to avoid token length issues
    # BERT typically has a limit of 512 tokens
    MAX_LENGTH = 450  # Leaving some room for special tokens
    
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= MAX_LENGTH:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    # Process each chunk and combine results
    all_entities = []
    
    for chunk in chunks:
        try:
            entities = ner_pipeline(chunk)
            all_entities.extend(entities)
        except Exception as e:
            print(f"Error processing chunk: {str(e)}")
    
    # Extract expense-related entities (you may want to customize this)
    expense_entities = []
    for entity in all_entities:
        # Filter for relevant entity types (amounts, dates, organizations)
        if entity["entity_group"] in ["MONEY", "DATE", "ORG"]:
            expense_entities.append({
                "text": entity["word"],
                "type": entity["entity_group"],
                "score": float(entity["score"])
            })
    
    return expense_entities

def extract_transactions(model, tokenizer, text):
    """
    Extract transactions from the given text
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
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