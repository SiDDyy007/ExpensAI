// src/components/summary/RecalculateButton.jsx
import { useState } from 'react';
import { recalculateMonthlySummary } from '@/lib/api';

export default function RecalculateButton({ month, year, onSuccess }) {
  const [isCalculating, setIsCalculating] = useState(false);
  const [status, setStatus] = useState(null);

  const handleRecalculate = async () => {
    setIsCalculating(true);
    setStatus('Recalculating summaries...');
    
    try {
      const result = await recalculateMonthlySummary(month, year);
      
      if (result.success) {
        setStatus('Recalculation complete!');
        if (onSuccess) onSuccess();
      } else {
        setStatus(`Error: ${result.error}`);
      }
    } catch (error) {
      setStatus(`Error: ${error.message}`);
    } finally {
      setIsCalculating(false);
      
      // Clear status after 3 seconds
      setTimeout(() => {
        setStatus(null);
      }, 3000);
    }
  };

  return (
    <div className="flex items-center">
      <button 
        onClick={handleRecalculate}
        disabled={isCalculating}
        className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        {isCalculating ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Calculating...
          </>
        ) : (
          <>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Recalculate
          </>
        )}
      </button>
      
      {status && (
        <span className={`ml-3 text-sm ${status.includes('Error') ? 'text-red-600' : 'text-green-600'}`}>
          {status}
        </span>
      )}
    </div>
  );
}