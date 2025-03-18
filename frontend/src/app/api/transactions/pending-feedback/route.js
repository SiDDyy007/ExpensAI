// src/app/api/transactions/pending-feedback/route.js
import { NextResponse } from 'next/server';
import { pendingFeedbackRequests } from '@/lib/feedbackStore';

export async function GET() {
  // Return the oldest pending request if available
  const pendingRequest = pendingFeedbackRequests[0] || null;
  
  return NextResponse.json({ 
    transaction: pendingRequest 
  });
}
