import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('returns a successful JSON response and sets the JSON content type', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"status":"ok"}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(api<{ status: string }>('/health', { method: 'POST', body: '{}' }))
      .resolves.toEqual({ status: 'ok' })

    const [, options] = fetchMock.mock.calls[0]
    expect(new Headers(options.headers).get('Content-Type')).toBe('application/json')
  })

  it('surfaces API error details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"Repository not found"}', { status: 404 })))

    await expect(api('/missing')).rejects.toThrow('Repository not found')
  })
})
