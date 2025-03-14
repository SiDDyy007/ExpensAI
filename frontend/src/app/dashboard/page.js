// src/app/dashboard/page.js (updated with transaction display)
'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import PdfDropzone from '@/components/upload/PdfDropzone';
import { getTransactions, getMonthlySummary } from '@/lib/api';

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const router = useRouter();

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

  // Load transactions and summary when month/year changes
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

  if (loading && !user) {
    return <div className="flex justify-center items-center min-h-screen">Loading...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Expense Tracker Dashboard</h1>
        
        <div className="flex items-center">
          {user && (
            <span className="mr-4 text-sm text-gray-600">
              Logged in as: {user.email}
            </span>
          )}
          <button
            onClick={handleSignOut}
            className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300"
          >
            Sign Out
          </button>
        </div>
      </div>
      
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Upload Credit Card Statements</h2>
        <p className="mb-4 text-gray-600">
          Drag and drop your credit card statement PDFs below to extract expense data.
        </p>
        
        <PdfDropzone />
      </div>
      
      {/* Month/Year Selector */}
      <div className="flex space-x-4 mb-6">
        <div>
          <label htmlFor="month" className="block text-sm font-medium text-gray-700">Month</label>
          <select
            id="month"
            value={selectedMonth}
            onChange={handleMonthChange}
            className="mt-1 block w-32 p-2 border border-gray-300 rounded-md"
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map(month => (
              <option key={month} value={month}>
                {new Date(2000, month - 1, 1).toLocaleString('default', { month: 'long' })}
              </option>
            ))}
          </select>
        </div>
        
        <div>
          <label htmlFor="year" className="block text-sm font-medium text-gray-700">Year</label>
          <select
            id="year"
            value={selectedYear}
            onChange={handleYearChange}
            className="mt-1 block w-24 p-2 border border-gray-300 rounded-md"
          >
            {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i).map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>
      </div>
      
      {/* Summary */}
      {summary && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Monthly Summary</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="text-lg font-medium text-blue-800">Total Expenses</h3>
              <p className="text-2xl font-bold">${summary.total_expenses?.toFixed(2) || '0.00'}</p>
            </div>
            
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="text-lg font-medium text-green-800">Total Income</h3>
              <p className="text-2xl font-bold">${Math.abs(summary.total_income || 0).toFixed(2)}</p>
            </div>
            
            <div className="bg-purple-50 p-4 rounded-lg">
              <h3 className="text-lg font-medium text-purple-800">Net</h3>
              <p className="text-2xl font-bold">
                ${(Math.abs(summary.total_income || 0) - (summary.total_expenses || 0)).toFixed(2)}
              </p>
            </div>
          </div>
          
          {/* Category and Card Breakdowns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            {/* Categories */}
            <div>
              <h3 className="text-lg font-medium mb-2">Spending by Category</h3>
              {Object.entries(summary.expenses_by_category || {}).length > 0 ? (
                <ul className="space-y-2">
                  {Object.entries(summary.expenses_by_category || {}).map(([category, amount]) => (
                    <li key={category} className="flex justify-between">
                      <span>{category}</span>
                      <span className="font-medium">${Math.abs(amount).toFixed(2)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500">No category data available</p>
              )}
            </div>
            
            {/* Cards */}
            <div>
              <h3 className="text-lg font-medium mb-2">Spending by Card</h3>
              {Object.entries(summary.expenses_by_card || {}).length > 0 ? (
                <ul className="space-y-2">
                  {Object.entries(summary.expenses_by_card || {}).map(([card, amount]) => (
                    <li key={card} className="flex justify-between">
                      <span>{card}</span>
                      <span className="font-medium">${Math.abs(amount).toFixed(2)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500">No card data available</p>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Transactions */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Transactions</h2>
        
        {loading ? (
          <p className="text-center py-4">Loading transactions...</p>
        ) : transactions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Date</th>
                  <th className="px-4 py-2 text-left">Merchant</th>
                  <th className="px-4 py-2 text-left">Category</th>
                  <th className="px-4 py-2 text-left">Card</th>
                  <th className="px-4 py-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id} className="border-t">
                    <td className="px-4 py-2">{new Date(tx.date).toLocaleDateString()}</td>
                    <td className="px-4 py-2">{tx.merchant}</td>
                    <td className="px-4 py-2">
                      {tx.category || <span className="text-gray-400">Uncategorized</span>}
                    </td>
                    <td className="px-4 py-2">{tx.card}</td>
                    <td className="px-4 py-2 text-right">
                      <span className={tx.charge < 0 ? 'text-green-600' : 'text-red-600'}>
                        ${Math.abs(tx.charge).toFixed(2)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500">No transactions found for this period.</p>
            <p className="mt-2 text-sm text-gray-400">
              Upload credit card statements to see your transactions here.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}