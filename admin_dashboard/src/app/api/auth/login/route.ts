import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { ADMIN_TOKEN_COOKIE } from '@/lib/auth';
import { SERVER_API_BASE_URL } from '@/lib/constants';

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as { username?: string; password?: string } | null;
  const response = await fetch(`${SERVER_API_BASE_URL}/auth/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
    cache: 'no-store',
  });

  const data = (await response.json().catch(() => null)) as { access_token?: string; expires_in?: number; detail?: string } | null;
  if (!response.ok || !data?.access_token) {
    return NextResponse.json({ error: data?.detail || 'Invalid username or password' }, { status: 401 });
  }

  const cookieStore = await cookies();
  cookieStore.set(ADMIN_TOKEN_COOKIE, data.access_token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: data.expires_in || 60 * 30,
  });

  return NextResponse.json({ success: true });
}
