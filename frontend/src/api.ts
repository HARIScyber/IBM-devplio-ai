// Only public API origin configuration belongs in VITE_* variables.
const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '').replace(/\/api$/i, '')
const RETRY_DELAYS_MS = [2000, 5000, 10000]

function wait(ms: number) { return new Promise(resolve => setTimeout(resolve, ms)) }

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (import.meta.env.PROD && !BASE) {
    throw new Error('The backend URL is not configured. Set VITE_API_BASE_URL in the Vercel project settings and redeploy.')
  }
  const route = path.startsWith('/') ? path : `/${path}`
  const url = `${BASE}${route}`
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData) && options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const retryable = (options.method ?? 'GET').toUpperCase() === 'GET'
  for (let attempt = 0; ; attempt++) {
    let response: Response
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 20000)
      try { response = await fetch(url, { ...options, headers, signal: options.signal ?? controller.signal }) }
      finally { clearTimeout(timeout) }
    } catch (error) {
      if (retryable && attempt < RETRY_DELAYS_MS.length) { await wait(RETRY_DELAYS_MS[attempt]); continue }
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new Error('The backend took too long to respond. It may still be waking up; please retry in a few seconds.')
      }
      throw new Error('Backend is waking up or temporarily unavailable. Please retry in a few seconds.')
    }
    if (retryable && [502, 503, 504].includes(response.status) && attempt < RETRY_DELAYS_MS.length) {
      await wait(RETRY_DELAYS_MS[attempt]); continue
    }
    let data: any
    try { data = await response.json() } catch { data = null }
    if (!response.ok) throw new Error(data?.detail ?? `Request failed (${response.status})`)
    return data as T
  }
}

export type Finding = { id: string; severity: string; category: string; file: string; line: number; title: string; problem: string; evidence: string; suggested_fix: string; confidence: string; kind: string }
export type Repo = { id: string; name: string; source: string; primary_language: string; languages: { name: string; files: number }[]; frameworks: string[]; file_count: number; loc: number; files: { path: string; language: string; lines: number; bytes: number }[]; tree: string[]; components: string[]; entry_points: string[]; test_files: string[]; api_endpoints: string[]; has_tests: boolean; has_docs: boolean; findings: Finding[]; quality: { test_files: number; documentation_present: boolean; large_files: number; empty_files: number }; readme?: string }
export type ChatResult = { answer: string; sources: { file: string; line: number; excerpt: string }[]; reasoning_summary: string; suggested_actions: string[]; mode: string }
