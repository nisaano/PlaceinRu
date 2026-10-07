import { backendRequest, jsonBody } from './client'

export const authApi = {
  register: (values) =>
    backendRequest(
      '/api/v1/auth/register',
      { method: 'POST', body: jsonBody(values) },
      { auth: false },
    ),
  login: (values) =>
    backendRequest(
      '/api/v1/auth/login',
      { method: 'POST', body: jsonBody(values) },
      { auth: false },
    ),
  refresh: (refreshToken) =>
    backendRequest(
      '/api/v1/auth/refresh',
      { method: 'POST', body: jsonBody({ refreshToken }) },
      { auth: false },
    ),
  me: () => backendRequest('/api/v1/auth/me'),
}
