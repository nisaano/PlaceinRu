import { backendRequest, jsonBody } from './client'

export const tripsApi = {
  list: () => backendRequest('/api/v1/trips'),
  get: (tripId) => backendRequest(`/api/v1/trips/${encodeURIComponent(tripId)}`),
  create: (trip) => backendRequest('/api/v1/trips', { method: 'POST', body: jsonBody(trip) }),
  update: (tripId, trip) =>
    backendRequest(`/api/v1/trips/${encodeURIComponent(tripId)}`, {
      method: 'PATCH',
      body: jsonBody(trip),
    }),
  remove: (tripId) =>
    backendRequest(`/api/v1/trips/${encodeURIComponent(tripId)}`, { method: 'DELETE' }),
  budget: (tripId) => backendRequest(`/api/v1/trips/${encodeURIComponent(tripId)}/budget`),
  validateRoute: (tripId) => backendRequest(`/api/v1/trips/${encodeURIComponent(tripId)}/validate`),
  addRouteItem: (item) =>
    backendRequest('/api/v1/trips/items', { method: 'POST', body: jsonBody(item) }),
  replaceRouteItem: (tripId, itemId, candidate) =>
    backendRequest(
      `/api/v1/trips/${encodeURIComponent(tripId)}/items/${encodeURIComponent(itemId)}/replace`,
      { method: 'POST', body: jsonBody(candidate) },
    ),
  rebuildRoute: (tripId) =>
    backendRequest(`/api/v1/trips/${encodeURIComponent(tripId)}/route/rebuild`, { method: 'POST' }),
}
