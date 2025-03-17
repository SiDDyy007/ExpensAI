// src/app/api/transactions/get-feedback-result/route.js
import { NextResponse } from 'next/server';
import { completedFeedback } from '@/lib/feedbackStore';

export async function GET(request) {
  // Get the requestId from the query parameters
  const { searchParams } = new URL(request.url);
  const requestId = searchParams.get('requestId');
  
  if (!requestId) {
    return NextResponse.json({
      success: false,
      error: 'Missing requestId parameter'
    }, { status: 400 });
  }
  
  // Check if feedback is available
  if (!completedFeedback.has(requestId)) {
    return NextResponse.json({
      success: false,
      error: 'Feedback not found or still pending'
    }, { status: 404 });
  }
  
  // Get the feedback
  const result = completedFeedback.get(requestId);
  
  // Remove it from the map to free up memory
  completedFeedback.delete(requestId);
  
  return NextResponse.json({
    success: true,
    feedback: result.feedback
  });
}