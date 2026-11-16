import { NextRequest } from 'next/server';
export async function GET(request: NextRequest, context: { params: Promise<{path: string[]}> }) { return proxy(request, context); }
export async function POST(request: NextRequest, context: { params: Promise<{path: string[]}> }) { return proxy(request, context); }
async function proxy(request: NextRequest, context: { params: Promise<{path: string[]}> }) {
  const {path} = await context.params;
  const suffix = path.join('/');
  if (!/^(demo|analyses(?:\/[a-f0-9-]{36}(?:\/(?:report|explain))?)?)$/.test(suffix)) return Response.json({detail:'Unknown route'}, {status:404});
  try {
    const response = await fetch(`${process.env.BACKEND_URL || 'http://127.0.0.1:8001'}/${suffix}`, {method: request.method, headers: {'Content-Type':'application/json', 'Authorization':request.headers.get('authorization') || ''}, body:request.method === 'POST' ? await request.text() : undefined, signal:AbortSignal.timeout(35000), cache:'no-store'});
    return new Response(await response.text(), {status:response.status,headers:{'Content-Type':response.headers.get('content-type') || 'application/json'}});
  } catch { return Response.json({detail:'Backend is unavailable. Start Docker Compose or use the bundled fixture.'}, {status:503}); }
}
