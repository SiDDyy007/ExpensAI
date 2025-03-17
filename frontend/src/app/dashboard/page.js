// src/app/dashboard/page.js
'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import PdfDropzone from '@/components/upload/PdfDropzone';
import { getTransactions, getMonthlySummary } from '@/lib/api';
import FeedbackPopup from '@/components/feedback/FeedbackPopup';
import RecalculateButton from '@/components/summary/RecalculateButton';

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [view, setView] = useState('summary'); // 'summary' or 'transactions'
  const [searchTerm, setSearchTerm] = useState('');
  const router = useRouter();
  // Feedback popup state
  const [feedbackPopupOpen, setFeedbackPopupOpen] = useState(false);
  const [currentFeedbackTransaction, setCurrentFeedbackTransaction] = useState(null);

  useEffect(() => {
    const getUser = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        
        if (session?.user) {
          setUser(session.user);
        } else {
          router.push('/auth/login');
        }
      } catch (error) {
        console.error("Error getting user session:", error.message);
      } finally {
        setLoading(false);
      }
    };
    
    getUser();
  }, [router]);

  useEffect(() => {
    if (user) {
      const loadData = async () => {
        setLoading(true);
        try {
          const [txData, summaryData] = await Promise.all([
            getTransactions(selectedMonth, selectedYear),
            getMonthlySummary(selectedMonth, selectedYear)
          ]);
          
          setTransactions(txData);
          setSummary(summaryData);
        } catch (error) {
          console.error("Error loading data:", error);
        } finally {
          setLoading(false);
        }
      };
      
      loadData();
    }
  }, [user, selectedMonth, selectedYear]);

  // Function to check for pending feedback requests
  const checkFeedbackRequests = async () => {
    try {
      const response = await fetch('/api/transactions/pending-feedback');
      const data = await response.json();
      
      if (data.transaction) {
        setCurrentFeedbackTransaction(data.transaction);
        setFeedbackPopupOpen(true);
      }
    } catch (error) {
      console.error("Error checking feedback requests:", error);
    }
  };

  // Poll for feedback requests
  useEffect(() => {
    // Check on initial load
    checkFeedbackRequests();
    
    // Set up polling (every 10 seconds)
    const interval = setInterval(checkFeedbackRequests, 10000);
    
    return () => clearInterval(interval);
  }, []);
  

  const handleMonthChange = (e) => {
    setSelectedMonth(parseInt(e.target.value));
  };

  const handleYearChange = (e) => {
    setSelectedYear(parseInt(e.target.value));
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/auth/login');
  };

  // Function to handle feedback submission
  const handleFeedbackSubmit = async (feedback) => {
    try {
      await fetch('/api/transactions/submit-feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transactionId: currentFeedbackTransaction.id,
          feedback
        }),
      });
      
      setFeedbackPopupOpen(false);
      setCurrentFeedbackTransaction(null);
    } catch (error) {
      console.error("Error submitting feedback:", error);
    }
  };

  // Filter transactions based on search term
  const filteredTransactions = transactions.filter(tx => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      tx.merchant?.toLowerCase().includes(term) ||
      tx.category?.toLowerCase().includes(term) ||
      tx.card?.toLowerCase().includes(term) ||
      tx.note?.toLowerCase().includes(term)
    );
  });

  // Format currency consistently
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount || 0));
  };

  // Get month name
  const getMonthName = (month) => {
    return new Date(2000, month - 1, 1).toLocaleString('default', { month: 'long' });
  };

  if (loading && !user) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-50">
        <div className="flex flex-col items-center">
          <svg className="animate-spin h-10 w-10 text-indigo-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-gray-600">Loading your financial data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center">
                <div className="h-8 w-8 rounded-full bg-indigo-600 flex items-center justify-center mr-2">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 14a6 6 0 110-12 6 6 0 010 12zm-1-5a1 1 0 011-1h1a1 1 0 110 2h-1a1 1 0 01-1-1zm0-3a1 1 0 011-1h1a1 1 0 110 2h-1a1 1 0 01-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <span className="font-bold text-gray-900 text-lg">Expense Tracker</span>
              </div>
              <div className="ml-6 flex space-x-4">
                <button 
                  onClick={() => setView('summary')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${view === 'summary' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-700 hover:bg-gray-100'}`}
                >
                  Summary
                </button>
                <button 
                  onClick={() => setView('transactions')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${view === 'transactions' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-700 hover:bg-gray-100'}`}
                >
                  Transactions
                </button>
              </div>
            </div>

            <div className="flex items-center">
              {user && (
                <div className="flex items-center">
                  <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center">
                    <span className="text-indigo-700 font-medium text-sm">
                      {user.email.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <span className="ml-2 text-sm text-gray-700 hidden md:block">
                    {user.email}
                  </span>
                  <button
                    onClick={handleSignOut}
                    className="ml-4 px-3 py-1 text-sm text-gray-700 hover:text-gray-900 border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Date selector and upload area */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="md:col-span-2 bg-white rounded-lg shadow p-6">
  <div className="flex flex-col md:flex-row md:items-end justify-between">
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        {getMonthName(selectedMonth)} {selectedYear} Overview
      </h2>
      <div className="flex space-x-4">
        <div>
          <label htmlFor="month" className="block text-sm font-medium text-gray-700 mb-1">Month</label>
          <select
            id="month"
            value={selectedMonth}
            onChange={handleMonthChange}
            className="block w-32 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map(month => (
              <option key={month} value={month}>
                {getMonthName(month)}
              </option>
            ))}
          </select>
        </div>
        
        <div>
          <label htmlFor="year" className="block text-sm font-medium text-gray-700 mb-1">Year</label>
          <select
            id="year"
            value={selectedYear}
            onChange={handleYearChange}
            className="block w-24 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
          >
            {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i).map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
   
    <div className="mt-4 md:mt-0 flex space-x-3">
      <RecalculateButton 
        month={selectedMonth} 
        year={selectedYear} 
        onSuccess={() => {
          // Refresh data after recalculation
          setLoading(true);
          Promise.all([
            getTransactions(selectedMonth, selectedYear),
            getMonthlySummary(selectedMonth, selectedYear)
          ]).then(([txData, summaryData]) => {
            setTransactions(txData);
            setSummary(summaryData);
            setLoading(false);
          }).catch(error => {
            console.error("Error refreshing data:", error);
            setLoading(false);
          });
        }} 
      />
      
      <button 
        onClick={() => window.print()} 
        className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
        </svg>
        Export Report
      </button>
    </div>
  </div>
</div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Statements</h2>
            <PdfDropzone />
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center my-12">
            <svg className="animate-spin h-8 w-8 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        ) : view === 'summary' ? (
          <>
            {/* Summary Cards */}
            {summary ? (
              <div className="mb-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-white rounded-lg shadow p-6 border-l-4 border-red-500">
                    <p className="text-sm font-medium text-gray-500">Total Expenses</p>
                    <p className="mt-2 text-3xl font-semibold text-gray-900">{formatCurrency(summary.total_expenses || 0)}</p>
                    <div className="mt-2">
                      <span className="text-xs font-medium text-red-600 bg-red-100 rounded-full px-2 py-1">
                        {Math.round((summary.total_expenses || 0) / (Math.abs(summary.total_income || 1) + (summary.total_expenses || 0)) * 100)}% of Total
                      </span>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
                    <p className="text-sm font-medium text-gray-500">Total Income</p>
                    <p className="mt-2 text-3xl font-semibold text-gray-900">{formatCurrency(Math.abs(summary.total_income || 0))}</p>
                    <div className="mt-2">
                      <span className="text-xs font-medium text-green-600 bg-green-100 rounded-full px-2 py-1">
                        {Math.round(Math.abs(summary.total_income || 0) / (Math.abs(summary.total_income || 1) + (summary.total_expenses || 0)) * 100)}% of Total
                      </span>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-lg shadow p-6 border-l-4 border-indigo-500">
                    <p className="text-sm font-medium text-gray-500">Net Balance</p>
                    <p className="mt-2 text-3xl font-semibold text-gray-900">
                      {formatCurrency(Math.abs(summary.total_income || 0) - (summary.total_expenses || 0))}
                    </p>
                    <div className="mt-2">
                      <span className={`text-xs font-medium ${(Math.abs(summary.total_income || 0) - (summary.total_expenses || 0)) >= 0 ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100'} rounded-full px-2 py-1`}>
                        {(Math.abs(summary.total_income || 0) - (summary.total_expenses || 0)) >= 0 ? 'Surplus' : 'Deficit'}
                      </span>
                    </div>
                  </div>
                </div>
              
                {/* Spending Breakdowns */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
                  {/* By Category */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-medium text-gray-900 mb-4">Spending by Category</h3>
                    
                    {Object.entries(summary.expenses_by_category || {}).length > 0 ? (
                      <div className="space-y-4">
                        {Object.entries(summary.expenses_by_category || {})
                          .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                          .map(([category, amount]) => {
                            const percentage = Math.round(Math.abs(amount) / (summary.total_expenses || 1) * 100);
                            return (
                              <div key={category}>
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-sm font-medium text-gray-700">{category}</span>
                                  <span className="text-sm font-medium text-gray-900">{formatCurrency(Math.abs(amount))}</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div className="bg-indigo-600 h-2 rounded-full" style={{ width: `${percentage}%` }}></div>
                                </div>
                                <span className="text-xs text-gray-500">{percentage}%</span>
                              </div>
                            );
                          })
                        }
                      </div>
                    ) : (
                      <div className="py-6 text-center text-gray-500">
                        <p>No category data available for this period</p>
                      </div>
                    )}
                  </div>
                  
                  {/* By Card */}
                  <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-medium text-gray-900 mb-4">Spending by Card</h3>
                    
                    {Object.entries(summary.expenses_by_card || {}).length > 0 ? (
                      <div className="space-y-4">
                        {Object.entries(summary.expenses_by_card || {})
                          .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
                          .map(([card, amount]) => {
                            const percentage = Math.round(Math.abs(amount) / (summary.total_expenses || 1) * 100);
                            let cardColor;
                            
                            // Assign colors based on card name
                            if (card.toLowerCase().includes('amex') || card.toLowerCase().includes('american')) {
                              cardColor = 'bg-blue-600';
                            } else if (card.toLowerCase().includes('visa')) {
                              cardColor = 'bg-blue-800';
                            } else if (card.toLowerCase().includes('master')) {
                              cardColor = 'bg-orange-600';
                            } else if (card.toLowerCase().includes('discover')) {
                              cardColor = 'bg-orange-500';
                            } else {
                              cardColor = 'bg-purple-600';
                            }
                            
                            return (
                              <div key={card}>
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-sm font-medium text-gray-700">{card}</span>
                                  <span className="text-sm font-medium text-gray-900">{formatCurrency(Math.abs(amount))}</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                  <div className={`${cardColor} h-2 rounded-full`} style={{ width: `${percentage}%` }}></div>
                                </div>
                                <span className="text-xs text-gray-500">{percentage}%</span>
                              </div>
                            );
                          })
                        }
                      </div>
                    ) : (
                      <div className="py-6 text-center text-gray-500">
                        <p>No card data available for this period</p>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Recent Transactions */}
                <div className="mt-8 bg-white rounded-lg shadow overflow-hidden">
                  <div className="px-6 py-5 border-b border-gray-200">
                    <h3 className="text-lg font-medium text-gray-900">Recent Transactions</h3>
                  </div>
                  
                  {transactions.length > 0 ? (
                    <div className="max-h-96 overflow-y-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Merchant</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Card</th>
                            <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {transactions.slice(0, 5).map((tx) => (
                            <tr key={tx.id} className="hover:bg-gray-50">
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {new Date(tx.date).toLocaleDateString()}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{tx.merchant}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {tx.category ? (
                                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                                    {tx.category}
                                  </span>
                                ) : (
                                  <span className="text-gray-400">Uncategorized</span>
                                )}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{tx.card}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                                <span className={tx.charge < 0 ? 'text-green-600' : 'text-red-600'}>
                                  {formatCurrency(tx.charge)}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      
                      {transactions.length > 5 && (
                        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
                          <button
                            onClick={() => setView('transactions')}
                            className="text-sm text-indigo-600 hover:text-indigo-900"
                          >
                            View all transactions
                          </button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="px-6 py-10 text-center text-gray-500">
                      <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                      <p className="mt-2 text-sm font-medium">No transactions found for this period</p>
                      <p className="mt-1 text-sm text-gray-400">
                        Upload credit card statements to see your transactions
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow p-10 text-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
                <h3 className="mt-2 text-lg font-medium text-gray-900">No data available for this period</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Upload your credit card statements to start tracking your expenses.
                </p>
              </div>
            )}
          </>
        ) : (
          /* Transactions View */
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900 mb-3 sm:mb-0">
                All Transactions
              </h3>
              
              <div className="w-full sm:w-64">
                <input
                  type="text"
                  placeholder="Search transactions..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>
            
            {filteredTransactions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Merchant</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Card</th>
                      <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                      <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Note</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredTransactions.map((tx) => (
                      <tr key={tx.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {new Date(tx.date).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">{tx.merchant}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {tx.category ? (
                            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                              {tx.category}
                            </span>
                          ) : (
                            <span className="text-gray-400 text-sm">Uncategorized</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{tx.card}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                          <span className={tx.charge < 0 ? 'text-green-600' : 'text-red-600'}>
                            {formatCurrency(tx.charge)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                          {tx.note ? (
                            <button
                              className="text-gray-400 hover:text-gray-500"
                              title={tx.note}
                              onClick={() => alert(tx.note)}
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-12">
                <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <h3 className="mt-2 text-lg font-medium text-gray-900">No transactions found</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Try changing the search term, month, or year, or upload credit card statements.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
      {/* Feedback Popup */}
      <FeedbackPopup
        isOpen={feedbackPopupOpen}
        transaction={currentFeedbackTransaction}
        onSubmit={handleFeedbackSubmit}
        onClose={() => setFeedbackPopupOpen(false)}
      />
    </div>
  );
}