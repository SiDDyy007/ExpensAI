// src/components/FeedbackPopup.js
import React, { useState } from 'react';

export default function FeedbackPopup({ 
  isOpen, 
  transaction, 
  onSubmit, 
  onClose 
}) {
  const [feedback, setFeedback] = useState('');

  if (!isOpen) return null;

  const handleSubmit = () => {
    onSubmit(feedback);
    setFeedback('');
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h2 className="text-xl font-semibold mb-4">Transaction Feedback Needed</h2>
        
        <div className="mb-4 p-4 bg-gray-50 rounded-md">
          <p className="font-medium">Merchant: {transaction.merchant}</p>
          <p className="font-medium">Charge: ${Math.abs(transaction.charge).toFixed(2)}</p>
        </div>
        
        <p className="mb-2 text-gray-700">
          This transaction has been flagged as anomalous. Please provide feedback:
        </p>
        
        <textarea
          className="w-full border border-gray-300 rounded-md p-2 mb-4 h-24"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Enter your explanation for future reference..."
        />
        
        <div className="flex justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            disabled={!feedback.trim()}
          >
            Submit Feedback
          </button>
        </div>
      </div>
    </div>
  );
}