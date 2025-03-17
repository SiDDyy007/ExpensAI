// src/lib/apiConfig.js

// Development environment
const DEV_API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:3000/api';

// Production environment - update when deploying
const PROD_API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://your-production-url.com/api';

// Use appropriate base URL based on environment
export const API_BASE = process.env.NODE_ENV === 'production' ? PROD_API_BASE : DEV_API_BASE;

// Transaction endpoints
export const TRANSACTION_ENDPOINTS = {
  REQUEST_FEEDBACK: `${API_BASE}/transactions/request-feedback`,
  SUBMIT_FEEDBACK: `${API_BASE}/transactions/submit-feedback`,
  PENDING_FEEDBACK: `${API_BASE}/transactions/pending-feedback`,
  GET_FEEDBACK_RESULT: `${API_BASE}/transactions/get-feedback-result`,
};