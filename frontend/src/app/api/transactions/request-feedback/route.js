// src/app/api/transactions/request-feedback/route.js
import { NextResponse } from 'next/server';
// import { pendingFeedbackRequests } from '@/lib/feedbackStore';
import { pendingFeedbackRequests } from '../../../../lib/feedbackStore';

export async function POST(request) {
  try {
    const { merchant, charge } = await request.json();
    
    // Generate a unique ID for this request
    const requestId = Date.now().toString();
    
    // Create a new feedback request
    const feedbackRequest = {
      id: requestId,
      merchant,
      charge,
      status: 'pending',
      created_at: new Date().toISOString()
    };
    
    // Add to the pending requests queue
    pendingFeedbackRequests.push(feedbackRequest);
    
    return NextResponse.json({ 
      success: true, 
      requestId 
    });
  } catch (error) {
    console.error('Error requesting feedback:', error);
    return NextResponse.json({ 
      success: false, 
      error: error.message 
    }, { status: 400 });
  }
}