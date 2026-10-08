const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(status, message, details = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

export function getStoredAuth() {
  try {
    return JSON.parse(sessionStorage.getItem('placeinru.auth') || 'null')
  } catch {
    return null
  }
}

export function storeAuth(auth) {
  if (auth) sessionStorage.setItem('placeinru.auth', JSON.stringify(auth))
  else sessionStorage.removeItem('placeinru.auth')
}

export function readableError(
  error,
  fallback = 'Не получилось выполнить запрос. Попробуйте ещё раз.',
) {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Срок действия входа закончился. Войдите в аккаунт ещё раз.'
    if (error.status === 404) return 'Запрошенные данные не найдены.'
    if (error.status === 409)
      return 'Данные изменились в другом окне. Обновите страницу и попробуйте снова.'
    if (error.status === 422) return error.message || 'Проверьте заполненные поля.'
    if (error.status === 503) return 'Сервис временно недоступен. Попробуйте позже.'
    return error.message || fallback
  }
  if (error instanceof TypeError)
    return 'Не удалось связаться с сервисом. Проверьте подключение и адрес API.'
  return fallback
}

async function parseResponse(response) {
  if (response.status === 204) return null
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function errorMessage(data, status) {
  const details = data?.detail ?? data
  if (typeof details === 'string') return details
  if (Array.isArray(details))
    return details
      .map((item) => item.msg)
      .filter(Boolean)
      .join('. ')
  return details?.message || details?.error || data?.message || `Ошибка сервера (${status})`
}

async function refreshAccessToken() {
  const auth = getStoredAuth()
  if (!auth?.refreshToken) return false
  const response = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken: auth.refreshToken }),
  })
  if (!response.ok) {
    storeAuth(null)
    return false
  }
  const next = await response.json()
  storeAuth({ ...auth, ...next })
  return true
}

export async function backendRequest(path, options = {}, { auth = true, retry401 = true } = {}) {
  const current = getStoredAuth()
  const headers = new Headers(options.headers || {})
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (auth && current?.accessToken) headers.set('Authorization', `Bearer ${current.accessToken}`)

  let response = await fetch(`${BACKEND_URL}${path}`, { ...options, headers })
  if (response.status === 401 && auth && retry401 && (await refreshAccessToken())) {
    return backendRequest(path, options, { auth, retry401: false })
  }
  const data = await parseResponse(response)
  if (!response.ok) throw new ApiError(response.status, errorMessage(data, response.status), data)
  return data
}

const MRT_URL = (import.meta.env.VITE_MRT_URL || '').replace(/\/$/, '')

export async function mrtRequest(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${MRT_URL}${path}`, { ...options, headers })
  const data = await parseResponse(response)
  if (!response.ok) throw new ApiError(response.status, errorMessage(data, response.status), data)
  return data
}

export const jsonBody = (body) => JSON.stringify(body)
