// src/app/page.js
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Check authentication status and redirect accordingly
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      console.log("Home page - auth session:", session);
      
      if (session) {
        // If user is logged in, redirect to dashboard
        console.log("User is authenticated, redirecting to dashboard");
        router.push('/dashboard');
      } else {
        // If user is not logged in, redirect to login page
        console.log("User is not authenticated, redirecting to login");
        router.push('/auth/login');
      }
    };
    
    checkUser();
  }, [router]);

  // While checking auth status, show a simple loading state
  return (
    <div className="flex min-h-screen flex-col items-center justify-center py-2">
      <div className="animate-pulse text-xl mb-4">Loading...</div>
      <div className="text-sm text-gray-500">Checking authentication status...</div>
    </div>
  );
}