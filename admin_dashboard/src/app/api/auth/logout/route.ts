import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { ADMIN_TOKEN_COOKIE } from '@/lib/auth';

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(ADMIN_TOKEN_COOKIE);
  return NextResponse.json({ success: true });
}
