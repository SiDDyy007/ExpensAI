// src/components/feedback/FeedbackPopup.js
import React, { useState } from 'react';

const FeedbackPopup = ({ isOpen, transaction, onSubmit, onClose }) => {
  const [feedback, setFeedback] = useState('');

  if (!isOpen || !transaction) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (feedback.trim()) {
      onSubmit(feedback);
      setFeedback('');
    }
  };

  // Format the charge to display as currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount || 0));
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 sm:mx-0 sm:h-10 sm:w-10">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                <h3 className="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                  Transaction Needs Categorization
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-gray-500">
                    This transaction couldn't be automatically categorized. Please provide context or select a category.
                  </p>
                  
                  <div className="mt-4 bg-gray-50 p-4 rounded-md">
                    <div className="flex justify-between">
                      <span className="font-medium">Merchant:</span>
                      <span>{transaction.merchant}</span>
                    </div>
                    <div className="flex justify-between mt-2">
                      <span className="font-medium">Amount:</span>
                      <span className={transaction.charge < 0 ? 'text-green-600' : 'text-red-600'}>
                        {formatCurrency(transaction.charge)}
                      </span>
                    </div>
                  </div>
                  
                  <form onSubmit={handleSubmit} className="mt-4">
                    <label htmlFor="feedback" className="block text-sm font-medium text-gray-700">
                      Please provide feedback or select a category:
                    </label>
                    <textarea
                      id="feedback"
                      name="feedback"
                      rows={3}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      placeholder="e.g., This is for monthly grocery shopping"
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      required
                    />
                    
                    <div className="mt-4 grid grid-cols-2 gap-2">
                      {[
                        'Food & Dining', 'Shopping', 'Transportation', 
                        'Entertainment', 'Utilities', 'Health', 
                        'Travel', 'Education', 'Other'
                      ].map(category => (
                        <button
                          key={category}
                          type="button"
                          onClick={() => setFeedback(category)}
                          className={`px-3 py-1.5 text-xs border rounded-md ${
                            feedback === category 
                              ? 'bg-indigo-100 border-indigo-300 text-indigo-800' 
                              : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          {category}
                        </button>
                      ))}
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm"
              onClick={handleSubmit}
            >
              Submit
            </button>
            <button
              type="button"
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              onClick={onClose}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FeedbackPopup;