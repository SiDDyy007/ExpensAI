// 5. Create a middleware to handle auth
// src/middleware.js
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';
import { NextResponse } from 'next/server';


export async function middleware(req) {
  const res = NextResponse.next();
  const supabase = createMiddlewareClient({ req, res });
  
  const {
    data: { session },
  } = await supabase.auth.getSession();

  console.log("Current session:", session);

  // If no session and trying to access protected route
  if (!session && req.nextUrl.pathname.startsWith('/dashboard')) {
    const redirectUrl = req.nextUrl.clone();
    console.log("Redirecting to login page");
    await new Promise(r => setTimeout(r, 5000));
    redirectUrl.pathname = '/auth/login';
    return NextResponse.redirect(redirectUrl);
  }

  // If session and trying to access auth pages
  if (session && (req.nextUrl.pathname.startsWith('/auth'))) {
    const redirectUrl = req.nextUrl.clone();
    redirectUrl.pathname = '/dashboard';
    return NextResponse.redirect(redirectUrl);
  }

  return res;
}

export const config = {
  matcher: ['/', '/dashboard/:path*', '/auth/:path*'],
//   matcher: ['/dashboard/:path*', '/auth/:path*'],
};
