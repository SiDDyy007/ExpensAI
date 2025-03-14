# app.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import jwt
from datetime import datetime
import os
from typing import List
import tempfile
import shutil

from pdf_handler import process_pdf_and_store
from database import (
    get_user_transactions, 
    get_monthly_summary,
    update_transaction_category
)


from pdf_processor import extract_text_from_pdf
from bert_model import process_text_with_bert
from smolagents import CodeAgent, LiteLLMModel, tool
from parser_tools.statement_parser_tools import parse_amex_statement, parse_zolve_statement, parse_freedom_statement
# from agents import ExpenseAI


app = FastAPI()
# agent = ExpenseAI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Your NextJS frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT secret from Supabase (should match your Supabase JWT secret)
JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")

async def get_current_user(authorization: str = Header(None)):
    """
    Validate JWT token and extract user_id
    """
    print("Authorization header:", authorization)
    # Check if authorization header is present
    if not authorization:
        print("Not authenticated: No authorization header")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Extract token from Bearer token
        token = authorization.split(" ")[1]
        # print("JWT token:", token)
        payload = jwt.decode(token, JWT_SECRET, audience='authenticated',algorithms=["HS256"])
        print("Decoded JWT payload:", payload)
        return payload.get("sub")  # sub contains the user_id
    except Exception as e:
        print("Invalid authentication:", str(e))
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {str(e)}")

@app.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    authorization: str = Header(None),
    # user_id: str = Depends(get_current_user)
    refresh_token = Header(None)  #  refresh tokens
):
    """
    Upload and process PDF files
    """
    print("Processing files")

    user_id = await get_current_user(authorization)
    print("Authenticated user_id:", user_id)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # session_token = authorization.split(" ")[1]

    results = []
    
    for file in files:
        if file.content_type != "application/pdf":
            results.append({
                "filename": file.filename,
                "error": "Not a PDF file"
            })
            continue
        
        try:
            # Process the PDF and store transactions
            result = await process_pdf_and_store(file, user_id)
            results.append({
                "filename": file.filename,
                "result": result
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
        finally:
            await file.close()
    
    return {"results": results}

@app.get("/transactions/{year}/{month}")
async def get_transactions(
    year: int,
    month: int,
    category: Optional[str] = None,
    card: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Get user transactions for a specific month
    """
    try:
        transactions = await get_user_transactions(user_id, month, year, category, card)
        return {"transactions": transactions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/summary/{year}/{month}")
async def get_summary(
    year: int,
    month: int,
    user_id: str = Depends(get_current_user)
):
    """
    Get monthly summary
    """
    try:
        summary = await get_monthly_summary(user_id, month, year)
        if not summary:
            return {
                "user_id": user_id,
                "month": month,
                "year": year,
                "total_expenses": 0,
                "total_income": 0,
                "expenses_by_card": {},
                "expenses_by_category": {},
                "summary": None
            }
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/transactions/{table_name}/{transaction_id}")
async def update_category(
    table_name: str,
    transaction_id: str,
    category: str,
    note: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """
    Update transaction category and note
    """
    try:
        result = await update_transaction_category(transaction_id, table_name, category, note)
        return {"success": True, "transaction": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Expense Tracker API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)



# def process_text(text, first_page_text, file_path):
#     """
#     Process text using the ExpenseAI agent
#     """
#     model = LiteLLMModel(
#             model_id=os.environ('ANTHROPIC_MODEL_ID'),
#             api_key=os.environ('ANTHROPIC_API_KEY')
#     )
    
#     extraction_agent = CodeAgent(
#         tools=[parse_amex_statement, parse_zolve_statement, parse_freedom_statement],
#         model=model,
#         add_base_tools=True
#     )

#     response = extraction_agent.run(
#                 f"""Determine the card issue from the given first page text: \n
#                   {first_page_text} and extract all expense from the statement using the appropriate tool. \n
#                    Here is the file pdf path for the given text: {file_path} \n"""
#     )

    
#     return response

@app.get("/")
async def root():
    return {"message": "PDF Processing API"}

# if __name__ == "__main__":
#     uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
