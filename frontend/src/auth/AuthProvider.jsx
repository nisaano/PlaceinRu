import { useCallback, useEffect, useMemo, useState } from 'react'
import { authApi } from '../api/auth'
import { getStoredAuth, storeAuth } from '../api/client'
import { AuthContext } from './AuthContext'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(() => Boolean(getStoredAuth()?.accessToken))

  useEffect(() => {
    const auth = getStoredAuth()
    if (!auth?.accessToken) return
    authApi
      .me()
      .then((profile) => setUser(profile))
      .catch(() => {
        storeAuth(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const acceptAuth = useCallback(async (authResponse) => {
    storeAuth(authResponse)
    try {
      const profile = await authApi.me()
      setUser(profile)
      return profile
    } catch (error) {
      storeAuth(null)
      throw error
    }
  }, [])

  const logout = useCallback(() => {
    storeAuth(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      acceptAuth,
      logout,
      refreshProfile: async () => setUser(await authApi.me()),
    }),
    [user, loading, acceptAuth, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
