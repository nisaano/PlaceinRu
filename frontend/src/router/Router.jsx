import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const RouterContext = createContext(null)

export function RouterProvider({ children }) {
  const [path, setPath] = useState(() => `${window.location.pathname}${window.location.search}`)

  useEffect(() => {
    const onPopState = () => setPath(`${window.location.pathname}${window.location.search}`)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const value = useMemo(
    () => ({
      path,
      navigate(to, { replace = false } = {}) {
        if (replace) window.history.replaceState({}, '', to)
        else window.history.pushState({}, '', to)
        setPath(`${window.location.pathname}${window.location.search}`)
        window.scrollTo({ top: 0, behavior: 'instant' })
      },
    }),
    [path],
  )

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>
}

RouterProvider.useRouter = function useRouter() {
  const value = useContext(RouterContext)
  if (!value) throw new Error('useRouter должен использоваться внутри RouterProvider')
  return value
}

export function Link({ to, onClick, children, ...props }) {
  const { navigate } = RouterProvider.useRouter()
  return (
    <a
      href={to}
      onClick={(event) => {
        onClick?.(event)
        if (
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        )
          return
        event.preventDefault()
        navigate(to)
      }}
      {...props}
    >
      {children}
    </a>
  )
}
