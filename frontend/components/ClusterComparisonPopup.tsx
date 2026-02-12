'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useComparison, useStore } from '@/lib/store'
import api, { type ClusterCompareResponse } from '@/lib/api'

export default function ClusterComparisonPopup() {
  const { clusterA, clusterB } = useComparison()
  const clearComparison = useStore((s) => s.clearComparison)

  const [data, setData] = useState<ClusterCompareResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Session cache: avoids re-fetching the same pair
  const cache = useRef<Map<string, ClusterCompareResponse>>(new Map())

  const dismiss = useCallback(() => {
    clearComparison()
    setData(null)
    setError(null)
  }, [clearComparison])

  // ESC to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && clusterA && clusterB) {
        dismiss()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [clusterA, clusterB, dismiss])

  // Auto-fetch when both clusters are selected
  useEffect(() => {
    if (!clusterA || !clusterB) {
      setData(null)
      setError(null)
      return
    }

    const key = `${clusterA.id}-${clusterB.id}`

    // Check cache first
    const cached = cache.current.get(key)
    if (cached) {
      setData(cached)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    api.compareClusterPair(clusterA.id, clusterB.id)
      .then((res) => {
        if (cancelled) return
        cache.current.set(key, res)
        setData(res)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to compare clusters')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [clusterA, clusterB])

  // Nothing selected — don't render
  if (!clusterA || !clusterB) return null

  const showSkeleton = loading && !data

  return (
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center pointer-events-none"
      role="dialog"
      aria-label="Cluster comparison"
    >
      <div
        className="pointer-events-auto w-[480px] max-h-[70vh] overflow-y-auto rounded-2xl border"
        style={{
          background: 'rgba(5, 5, 20, 0.92)',
          backdropFilter: 'blur(16px)',
          borderColor: 'rgba(0, 212, 255, 0.3)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-white/10">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="shrink-0 text-xs font-bold px-2 py-0.5 rounded"
              style={{ background: 'rgba(0,212,255,0.15)', color: '#00d4ff' }}
            >
              A
            </span>
            <span className="text-sm font-medium text-white truncate">
              {data?.cluster_a.name ?? clusterA.name}
            </span>
            <span className="text-gray-500 mx-1">&harr;</span>
            <span
              className="shrink-0 text-xs font-bold px-2 py-0.5 rounded"
              style={{ background: 'rgba(255,107,157,0.15)', color: '#ff6b9d' }}
            >
              B
            </span>
            <span className="text-sm font-medium text-white truncate">
              {data?.cluster_b.name ?? clusterB.name}
            </span>
          </div>
          <button
            onClick={dismiss}
            className="ml-3 shrink-0 text-gray-500 hover:text-white transition-colors"
            aria-label="Close comparison"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          {showSkeleton ? (
            <SkeletonBody />
          ) : error ? (
            <p className="text-red-400 text-sm">{error}</p>
          ) : data ? (
            <>
              <MetricsBar metrics={data.metrics} summaryA={data.cluster_a} summaryB={data.cluster_b} />
              {data.metrics.shared_categories.length > 0 && (
                <SharedCategories categories={data.metrics.shared_categories} />
              )}
              <ExplanationBody text={data.explanation} fallback={data.fallback} />
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MetricsBar({
  metrics,
  summaryA,
  summaryB,
}: {
  metrics: ClusterCompareResponse['metrics']
  summaryA: ClusterCompareResponse['cluster_a']
  summaryB: ClusterCompareResponse['cluster_b']
}) {
  return (
    <div className="space-y-3">
      {/* Proximity gauge */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-400">Proximity Index</span>
          <span className="text-xs font-mono text-white">{metrics.proximity_index}/100</span>
        </div>
        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${metrics.proximity_index}%`,
              background: proximityGradient(metrics.proximity_index),
            }}
          />
        </div>
      </div>

      {/* Scale comparison */}
      <div className="flex items-center gap-4 text-xs">
        <span style={{ color: '#00d4ff' }}>
          A: {summaryA.term_count} terms
        </span>
        <span className="text-gray-600">vs</span>
        <span style={{ color: '#ff6b9d' }}>
          B: {summaryB.term_count} terms
        </span>
      </div>
    </div>
  )
}

function SharedCategories({ categories }: { categories: string[] }) {
  return (
    <div>
      <span className="text-xs text-gray-400 block mb-1.5">Shared Categories</span>
      <div className="flex flex-wrap gap-1.5">
        {categories.map((cat) => (
          <span
            key={cat}
            className="text-xs px-2 py-0.5 rounded-full"
            style={{ background: 'rgba(168,85,247,0.2)', color: '#a855f7' }}
          >
            {cat.replace(/_/g, ' ')}
          </span>
        ))}
      </div>
    </div>
  )
}

function ExplanationBody({ text, fallback }: { text: string; fallback: boolean }) {
  return (
    <div>
      <p className="text-sm leading-relaxed" style={{ color: '#ddd', lineHeight: 1.6 }}>
        {text}
      </p>
      {fallback && (
        <p className="text-[10px] text-gray-600 mt-2 italic">Template-based explanation (AI unavailable)</p>
      )}
    </div>
  )
}

function SkeletonBody() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-2 bg-white/10 rounded-full w-full" />
      <div className="flex gap-4">
        <div className="h-3 bg-white/10 rounded w-20" />
        <div className="h-3 bg-white/10 rounded w-20" />
      </div>
      <div className="space-y-2 pt-2">
        <div className="h-3 bg-white/10 rounded w-full" />
        <div className="h-3 bg-white/10 rounded w-5/6" />
        <div className="h-3 bg-white/10 rounded w-4/6" />
        <div className="h-3 bg-white/10 rounded w-full" />
        <div className="h-3 bg-white/10 rounded w-3/6" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Returns a CSS color along a red → yellow → green gradient based on 0-100 value. */
function proximityGradient(value: number): string {
  if (value <= 33) return '#ef4444'
  if (value <= 66) return '#eab308'
  return '#22c55e'
}
