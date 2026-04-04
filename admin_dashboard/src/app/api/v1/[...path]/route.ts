import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { SERVER_API_BASE_URL } from '@/lib/constants';
import { ADMIN_TOKEN_COOKIE } from '@/lib/auth';

async function proxyRequest(request: Request, params: Promise<{ path: string[] }>) {
  const { path } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get(ADMIN_TOKEN_COOKIE)?.value;

  const incomingUrl = new URL(request.url);
  const upstreamUrl = `${SERVER_API_BASE_URL}/${path.join('/')}${incomingUrl.search}`;
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
