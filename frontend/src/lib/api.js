// src/lib/api.js
import { supabase } from './supabase';

/**
 * Get transactions for a specific month and year
 */
export async function getTransactions(month, year, category = null, card = null) {
  try {

    const monthStr = month.toString().padStart(2, '0');
    const yearMonthPrefix = `${year}-${monthStr}`;
    

    // Query the consolidated transactions table
    let query = supabase
      .from('transactions')
      .select('*')
      .filter('date', 'gte', `${yearMonthPrefix}-01`) // Start of month
      .filter('date', 'lt', month === 12 
        ? `${year + 1}-01-01`  // Next year if December
        : `${year}-${(month + 1).toString().padStart(2, '0')}-01`) // Next month
      .order('date', { ascending: false });
    
    // Add filters if provided
    if (category) {
      query = query.eq('category', category);
    }
    
    if (card) {
      query = query.eq('card', card);
    }
    
    const { data, error } = await query;
    
    if (error) throw error;
    
    return data || [];
  } catch (error) {
    console.error('Error fetching transactions:', error);
    return [];
  }
}

// Get monthly summary using the new tables
export const getMonthlySummary = async (month, year) => {
  try {
    const userId = (await supabase.auth.getUser()).data.user.id;

    // Fetch card summaries
    const { data: cardData, error: cardError } = await supabase
      .from('monthly_card_summaries')
      .select('card, total_expense')
      .eq('user_id', userId)
      .eq('month', month)
      .eq('year', year);
      
    if (cardError) throw cardError;
    
    // Fetch category summaries
    const { data: categoryData, error: categoryError } = await supabase
      .from('monthly_category_summaries')
      .select('category, total_expense')
      .eq('user_id', userId)
      .eq('month', month)
      .eq('year', year);
      
    if (categoryError) throw categoryError;
    
    // Fetch total expenses (sum of all positive charges) and income (sum of all negative charges)
    const { data: totalsData, error: totalsError } = await supabase
      .from('transactions')
      .select('charge')
      .eq('user_id', userId)
      .gte('date', `${year}-${String(month).padStart(2, '0')}-01`)
      .lt('date', month === 12 
        ? `${year + 1}-01-01` 
        : `${year}-${String(month + 1).padStart(2, '0')}-01`);
      
    if (totalsError) throw totalsError;
    
    const totalExpenses = totalsData
      .filter(tx => tx.charge > 0)
      .reduce((sum, tx) => sum + tx.charge, 0);
      
    const totalIncome = totalsData
      .filter(tx => tx.charge < 0)
      .reduce((sum, tx) => sum + tx.charge, 0);
    
    // Convert arrays to objects for easier access in the UI
    const expensesByCard = {};
    cardData.forEach(item => {
      expensesByCard[item.card] = item.total_expense;
    });
    
    const expensesByCategory = {};
    categoryData.forEach(item => {
      expensesByCategory[item.category] = item.total_expense;
    });
    
    return {
      month,
      year,
      total_expenses: totalExpenses,
      total_income: totalIncome,
      expenses_by_card: expensesByCard,
      expenses_by_category: expensesByCategory
    };
  } catch (error) {
    console.error('Error fetching monthly summary:', error);
    return {
      month,
      year,
      total_expenses: 0,
      total_income: 0,
      expenses_by_card: {},
      expenses_by_category: {}
    };
  }
};

/**
 * Update transaction category and note
 */
export async function updateTransactionCategory(transactionId, category, note = null) {
  try {
    const updateData = { category };
    if (note !== null) {
      updateData.note = note;
    }
    
    // Update in the consolidated transactions table
    const { data, error } = await supabase
      .from('transactions')
      .update(updateData)
      .eq('id', transactionId)
      .select()
      .single();
    
    if (error) throw error;
    
    return data;
  } catch (error) {
    console.error('Error updating transaction:', error);
    return null;
  }
}

/**
 * Search transactions across any time period
 */
export async function searchTransactions(searchTerm, startDate = null, endDate = null) {
  try {
    let query = supabase
      .from('transactions')
      .select('*');
    
    // Full-text search on merchant and note fields
    if (searchTerm && searchTerm.trim() !== '') {
      query = query.or(`merchant.ilike.%${searchTerm}%,note.ilike.%${searchTerm}%,category.ilike.%${searchTerm}%`);
    }
    
    // Date range filtering if provided
    if (startDate) {
      query = query.gte('date', startDate);
    }
    
    if (endDate) {
      query = query.lte('date', endDate);
    }
    
    const { data, error } = await query.order('date', { ascending: false });
    
    if (error) throw error;
    
    return data || [];
  } catch (error) {
    console.error('Error searching transactions:', error);
    return [];
  }
}

/**
 * Get all available categories from transactions
 */
export async function getCategories() {
  try {
    const { data, error } = await supabase
      .from('transactions')
      .select('category')
      .not('category', 'is', null);
    
    if (error) throw error;
    
    // Extract unique categories
    const categories = [...new Set(data.map(item => item.category))].filter(Boolean).sort();
    
    return categories;
  } catch (error) {
    console.error('Error fetching categories:', error);
    return [];
  }
}

export async function updateMonthlySummary(month, year, userId = null) {
  try {
    // If userId is not provided, try to get it from the current session
    if (!userId) {
      const { data: { session } } = await supabase.auth.getSession();
      userId = session?.user?.id;
      
      if (!userId) {
        throw new Error('User ID not available. Please ensure you are logged in.');
      }
    }
    
    // Call the stored procedure
    const { error } = await supabase.rpc('manually_update_monthly_summary', {
      user_uuid: userId,
      month_num: month,
      year_num: year
    });
    
    if (error) throw error;
    
    console.log(`Monthly summary updated for ${month}/${year}`);
    
    // Fetch the updated summary
    return await getMonthlySummary(month, year);
    
  } catch (error) {
    console.error('Error updating monthly summary:', error);
    throw error;
  }
}

// src/lib/api.js - Add these functions to your existing API file

/**
 * Submit user feedback for an anomalous transaction
 */
export async function submitFeedback(transactionData, feedback) {
  try {
    const { data, error } = await supabase
      .from('transaction_feedback')
      .insert([
        {
          transaction_id: transactionData.transaction_id,
          merchant: transactionData.merchant,
          charge: transactionData.charge,
          feedback: feedback,
          user_id: transactionData.user_id || null
        }
      ])
      .select()
      .single();
    
    if (error) throw error;
    
    // If the transaction needs to be updated with a category based on feedback
    if (transactionData.transaction_id) {
      await updateTransactionFromFeedback(transactionData.transaction_id, feedback);
    }
    
    return data;
  } catch (error) {
    console.error('Error submitting feedback:', error);
    throw error;
  }
}

/**
 * Update a transaction based on user feedback
 * This is an example function - you would need to implement the logic
 * to extract a category from feedback or assign a default category
 */
async function updateTransactionFromFeedback(transactionId, feedback) {
  try {
    // Here you might implement logic to:
    // 1. Extract keywords from feedback to determine category
    // 2. Or simply mark it as "Manually Categorized"
    
    const category = determineCategory(feedback);
    
    const { data, error } = await supabase
      .from('expense_tracker.transactions')
      .update({
        category: category,
        note: feedback // Optionally store feedback as note
      })
      .eq('id', transactionId)
      .select()
      .single();
    
    if (error) throw error;
    
    return data;
  } catch (error) {
    console.error('Error updating transaction from feedback:', error);
    // We don't throw here to prevent blocking the feedback submission
    return null;
  }
}

// Trigger a recalculation of summaries for a specific month
export const recalculateMonthlySummary = async (month, year) => {
  try {
    const { data, error } = await supabase
      .rpc('calculate_all_monthly_summaries', {
        p_month: month,
        p_year: year,
        p_user_id: (await supabase.auth.getUser()).data.user.id
      });
      
    if (error) throw error;
    return { success: true, data };
  } catch (error) {
    console.error('Error recalculating summary:', error);
    return { success: false, error: error.message };
  }
};