'use client'

import { useEffect } from 'react'
import dynamic from 'next/dynamic'
import { useStore } from '@/lib/store'
import SuperTruthLogo from '@/components/SuperTruthLogo'
import api from '@/lib/api'
import FilterPanel from '@/components/FilterPanel'
import DetailPanel from '@/components/DetailPanel'
import ViewControls from '@/components/ViewControls'
import StatsBar from '@/components/StatsBar'
import InsightsPanel from '@/components/InsightsPanel'
import ExplainerPanel from '@/components/ExplainerPanel'
import ChatPanel from '@/components/ChatPanel'
import DataSourcesPanel from '@/components/DataSourcesPanel'

// Dynamic import for Three.js component (no SSR)
const ClusterVisualization = dynamic(
  () => import('@/components/ClusterVisualization'),
  { ssr: false, loading: () => <LoadingState /> }
)

function LoadingState() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-background">
      <div className="text-center">
        <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-gray-400">Loading visualization...</p>
      </div>
    </div>
  )
}

export default function HomePage() {
  const setData = useStore((s) => s.setData)
  const setLoading = useStore((s) => s.setLoading)
  const setError = useStore((s) => s.setError)
  const isLoading = useStore((s) => s.isLoading)
  const error = useStore((s) => s.error)
  const filters = useStore((s) => s.filters)

  // Load data on mount and when filters change
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        const data = await api.getVisualizationData({
          category: filters.category || undefined,
          clusterId: filters.clusterId || undefined,
        })
        setData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      }
    }

    loadData()
  }, [filters.category, filters.clusterId, setData, setLoading, setError])

  return (
    <div className="h-screen w-screen overflow-hidden bg-background flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <SuperTruthLogo className="h-8 w-auto" />
          <div className="border-l border-border pl-4">
            <h1 className="text-lg font-semibold">Oncology & Rare Disease Intelligence</h1>
            <p className="text-xs text-gray-500">Search trends across cancer types and rare conditions with SDOH overlay</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <StatsBar />
          <ExplainerPanel />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Filters & Insights */}
        <aside className="w-72 flex-shrink-0 border-r border-border p-4 overflow-y-auto space-y-4">
          <FilterPanel />
          <InsightsPanel />
        </aside>

        {/* Center - 3D Visualization */}
        <div className="flex-1 relative">
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="glass rounded-lg p-6 max-w-md text-center">
                <p className="text-red-400 mb-2">Error loading data</p>
                <p className="text-sm text-gray-400">{error}</p>
                <button
                  onClick={() => window.location.reload()}
                  className="mt-4 px-4 py-2 bg-primary rounded-lg text-sm"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : (
            <ClusterVisualization />
          )}

          {/* View Controls Overlay */}
          <div className="absolute top-4 left-4">
            <ViewControls />
          </div>

          {/* Loading Overlay */}
          {isLoading && (
            <div className="absolute inset-0 bg-background/50 flex items-center justify-center">
              <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          )}
        </div>

        {/* Right Sidebar - Detail Panel & Data Sources */}
        <aside className="w-96 flex-shrink-0 border-l border-border p-4 overflow-y-auto space-y-4">
          <DetailPanel />
          <DataSourcesPanel />
        </aside>
      </main>

      {/* Footer */}
      <footer className="flex-shrink-0 border-t border-border px-6 py-2 text-center">
        <p className="text-xs text-gray-500 tracking-wide">
          COPYRIGHT 2026 SuperTruth ALL RIGHTS RESERVED
        </p>
      </footer>

      {/* AI Chat Panel */}
      <ChatPanel />
    </div>
  )
}
