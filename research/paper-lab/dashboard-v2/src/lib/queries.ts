import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import { usePollInterval } from './live'
import { toEntry } from './board'

export function useOverview() {
  const poll = usePollInterval()
  return useQuery({ queryKey: ['overview'], queryFn: api.overview, refetchInterval: poll || 60_000 })
}
export function useSparks() {
  const poll = usePollInterval(60_000)
  return useQuery({ queryKey: ['sparks'], queryFn: () => api.sparks(60), refetchInterval: poll || 120_000, staleTime: 30_000 })
}
export function useHealth() {
  const poll = usePollInterval()
  return useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: poll || 30_000 })
}
export function useEntries() {
  const ov = useOverview()
  const entries = useMemo(() => (ov.data?.rows ?? []).map(toEntry), [ov.data])
  return { ov, entries }
}
