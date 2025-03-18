// src/components/AuthCheck.js
'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function AuthCheck() {
  const [authState, setAuthState] = useState('checking');
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    const checkAuth = async () => {
      // Get current session and user
      const { data: { session } } = await supabase.auth.getSession();
      const { data: { user } } = await supabase.auth.getUser();
      
      // console.log("Current session:", session);
      // console.log("Current user:", user);
      
      setSession(session);
      setUser(user);
      setAuthState(session ? 'authenticated' : 'unauthenticated');
      
      // Set up auth state change listener
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        (_event, session) => {
          console.log("Auth state changed:", _event);
          console.log("New session:", session);
          setSession(session);
          setUser(session?.user || null);
          setAuthState(session ? 'authenticated' : 'unauthenticated');
        }
      );
      
      // Clean up subscription
      return () => {
        subscription.unsubscribe();
      };
    };
    
    checkAuth();
  }, []);
  
  if (authState === 'checking') {
    return <div className="text-sm bg-gray-100 p-2 rounded">Checking authentication...</div>;
  }
  
  if (authState === 'unauthenticated') {
    return <div className="text-sm bg-red-100 p-2 rounded">Not authenticated</div>;
  }
  
  return (
    <div className="text-sm bg-green-100 p-2 rounded">
      Authenticated as: {user?.email}
    </div>
  );
}