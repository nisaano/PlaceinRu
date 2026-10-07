import { jsonBody, mrtRequest } from './client'

export const mrtApi = {
  catalog: () => mrtRequest('/v1/catalog/regions'),
  createSession: (timezone = 'Europe/Moscow') =>
    mrtRequest('/v1/sessions', { method: 'POST', body: jsonBody({ timezone }) }),
  getSession: (sessionId) => mrtRequest(`/v1/sessions/${encodeURIComponent(sessionId)}`),
  turn: (sessionId, payload) =>
    mrtRequest(`/v1/sessions/${encodeURIComponent(sessionId)}/turns`, {
      method: 'POST',
      body: jsonBody(payload),
    }),
  updateTrip: (sessionId, payload) =>
    mrtRequest(`/v1/sessions/${encodeURIComponent(sessionId)}/trip`, {
      method: 'PATCH',
      body: jsonBody(payload),
    }),
  recommendations: (trip) =>
    mrtRequest('/v1/recommend', { method: 'POST', body: jsonBody({ trip }) }),
  candidates: (payload) =>
    mrtRequest('/v1/candidates/query', { method: 'POST', body: jsonBody(payload) }),
  searchPlaces: (payload) =>
    mrtRequest('/v1/search/places', { method: 'POST', body: jsonBody(payload) }),
  selectRegion: (sessionId, payload) =>
    mrtRequest(`/v1/sessions/${encodeURIComponent(sessionId)}/select-region`, {
      method: 'POST',
      body: jsonBody(payload),
    }),
}
