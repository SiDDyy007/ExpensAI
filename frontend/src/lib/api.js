// src/lib/api.js
import { supabase } from './supabase';

/**
 * Get transactions for a specific month and year
 */
export async function getTransactions(month, year, category = null, card = null) {
  try {
    const tableName = `transactions_${month.toString().padStart(2, '0')}_${year}`;
    
    // Start building the query
    let query = supabase
      .from(`expense_tracker.${tableName}`)
      .select('*')
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

/**
 * Get monthly summary for a specific month and year
 */
export async function getMonthlySummary(month, year) {
  try {
    const { data, error } = await supabase
      .from('expense_tracker.monthly_summaries')
      .select('*')
      .eq('month', month)
      .eq('year', year)
      .single();
    
    if (error && error.code !== 'PGRST116') { // PGRST116 is "Results contain 0 rows"
      throw error;
    }
    
    return data || {
      month,
      year,
      total_expenses: 0,
      total_income: 0,
      expenses_by_card: {},
      expenses_by_category: {},
      summary: null
    };
  } catch (error) {
    console.error('Error fetching monthly summary:', error);
    return null;
  }
}

/**
 * Update transaction category and note
 */
export async function updateTransactionCategory(transactionId, tableName, category, note = null) {
  try {
    const updateData = { category };
    if (note !== null) {
      updateData.note = note;
    }
    
    const { data, error } = await supabase
      .from(`expense_tracker.${tableName}`)
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



