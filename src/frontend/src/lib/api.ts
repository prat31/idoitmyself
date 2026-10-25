/** Minimal JSON client for the IDIM API. Requests go to `/api/...`, proxied by Vite to the backend. */

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') message = body.detail
      // FastAPI validation errors: [{ msg: 'Value error, Subject: invalid regex (…)', … }]
      else if (Array.isArray(body?.detail) && typeof body.detail[0]?.msg === 'string')
        message = body.detail[0].msg.replace(/^Value error, /, '')
    } catch {
      // non-JSON error body — keep the generic message
    }
    throw new ApiError(response.status, message)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
