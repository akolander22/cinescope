import { useState, useEffect, useCallback } from 'react'

/**
 * Generic data fetching hook.
 * 
 * Usage:
 *   const { data, loading, error, refetch } = useApi(getLibrary)
 * 
 * `refetch` lets you manually re-trigger the call (e.g. after a sync).
 */
export function useApi(apiFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiFn()
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => { fetch() }, [fetch])

  return { data, loading, error, refetch: fetch }
}

/**
 * Hook for actions (POST/PATCH) that aren't triggered on mount.
 * 
 * Usage:
 *   const { execute, loading, error } = useAction(syncLibrary)
 *   <button onClick={execute}>Sync</button>
 */
export function useAction(apiFn) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const execute = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiFn(...args)
      setResult(res)
      return res
    } catch (e) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [apiFn])

  return { execute, loading, error, result }
}
