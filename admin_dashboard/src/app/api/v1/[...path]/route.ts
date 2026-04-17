import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { SERVER_API_BASE_URL } from '@/lib/constants';
import { ADMIN_TOKEN_COOKIE } from '@/lib/auth';

function getTokenFromCookieHeader(cookieHeader: string | null): string | null {
  if (!cookieHeader) return null;
  const match = cookieHeader.match(new RegExp(`(?:^|;\\s*)${ADMIN_TOKEN_COOKIE}=([^;]+)`));
  return match?.[1] ?? null;
}

async function proxyRequest(request: Request, params: Promise<{ path: string[] }>) {
  const { path } = await params;
  const cookieStore = await cookies();
  const cookieToken = cookieStore.get(ADMIN_TOKEN_COOKIE)?.value;
  const headerToken = getTokenFromCookieHeader(request.headers.get('cookie'));
  const token = cookieToken ?? headerToken;

  const incomingUrl = new URL(request.url);
  const normalizedPath = path.join('/');
  const pathSuffix = path.length === 1 ? '/' : '';
  const upstreamUrl = `${SERVER_API_BASE_URL}/${normalizedPath}${pathSuffix}${incomingUrl.search}`;
  const headers = new Headers(request.headers);
  headers.delete('host');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body: request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.text(),
    cache: 'no-store',
  });

  return new NextResponse(response.body, {
    status: response.status,
    headers: response.headers,
  });
}

export async function GET(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}

export async function POST(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}

export async function PATCH(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}

export async function PUT(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}

export async function DELETE(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, context.params);
}
