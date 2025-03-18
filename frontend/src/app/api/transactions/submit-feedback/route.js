// src/app/api/transactions/submit-feedback/route.js
import { NextResponse } from 'next/server';
import { pendingFeedbackRequests, completedFeedback } from '@/lib/feedbackStore';

export async function POST(request) {
  try {
    const { transactionId, feedback } = await request.json();
    
    // Find the pending request
    const requestIndex = pendingFeedbackRequests.findIndex(req => req.id === transactionId);
    
    if (requestIndex === -1) {
      return NextResponse.json({ 
        success: false, 
        error: 'Transaction not found' 
      }, { status: 404 });
    }
    
    // Remove from pending requests
    const [requestData] = pendingFeedbackRequests.splice(requestIndex, 1);
    
    // Store the feedback response
    completedFeedback.set(transactionId, {
      feedback,
      request: requestData,
      completed_at: new Date().toISOString()
    });
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error submitting feedback:', error);
    return NextResponse.json({ 
      success: false, 
      error: error.message 
    }, { status: 400 });
  }
}