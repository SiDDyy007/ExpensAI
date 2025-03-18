# app.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import jwt
import os
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import asyncio
from typing import Optional, Dict

from pdf_handler import process_pdf_and_store
from database import (
    get_user_transactions, 
    get_monthly_summary,
    update_transaction_category
)

router = APIRouter()

# Simple in-memory storage for pending feedback requests
pending_feedback_requests = {}
feedback_responses = {}

class FeedbackRequest(BaseModel):
    merchant: str
    charge: float
    transaction_id: str

class FeedbackResponse(BaseModel):
    transaction_id: str
    feedback: str

@router.post("/transactions/request-feedback")
async def request_feedback(request: FeedbackRequest):
    """Endpoint for the AI to request user feedback on a transaction"""
    transaction_id = request.transaction_id
    pending_feedback_requests[transaction_id] = {
        "merchant": request.merchant,
        "charge": request.charge,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    return {"success": True, "message": "Feedback request registered"}

@router.get("/transactions/pending-feedback")
async def get_pending_feedback():
    """Endpoint for the frontend to check if there are any feedback requests"""
    # Get the oldest pending request if any exist
    if pending_feedback_requests:
        transaction_id = next(iter(pending_feedback_requests))
        transaction = pending_feedback_requests[transaction_id]
        return {
            "transaction": {
                "id": transaction_id,
                "merchant": transaction["merchant"],
                "charge": transaction["charge"]
            }
        }
    
    return {"transaction": None}

@router.post("/transactions/submit-feedback")
async def submit_feedback(response: FeedbackResponse):
    """Endpoint for the frontend to submit user feedback"""
    transaction_id = response.transaction_id
    
    if transaction_id not in pending_feedback_requests:
        raise HTTPException(status_code=404, detail="Feedback request not found")
    
    # Store the feedback
    feedback_responses[transaction_id] = response.feedback
    
    # Remove from pending requests
    if transaction_id in pending_feedback_requests:
        del pending_feedback_requests[transaction_id]
    
    return {"success": True, "message": "Feedback submitted successfully"}

@router.get("/transactions/get-feedback/{transaction_id}")
async def get_feedback(transaction_id: str):
    """Endpoint for the AI to retrieve user feedback"""
    if transaction_id not in feedback_responses:
        return {"success": False, "message": "No feedback available"}
    
    feedback = feedback_responses.pop(transaction_id)
    return {"success": True, "feedback": feedback}

app = FastAPI()

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
        payload = jwt.decode(token, JWT_SECRET, audience='authenticated',algorithms=["HS256"])
        return payload.get("sub")  # sub contains the user_id
    except Exception as e:
        print("Invalid authentication:", str(e))
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {str(e)}")

@app.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    authorization: str = Header(None),
):
    """
    Upload and process PDF files
    """
    user_id = await get_current_user(authorization)

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

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

@app.get("/")
async def root():
    return {"message": "PDF Processing API"}

