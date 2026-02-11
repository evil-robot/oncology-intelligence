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
import PipelinePanel from '@/components/PipelinePanel'
import VulnerabilityInsightsPanel from '@/components/VulnerabilityInsightsPanel'
import VulnerabilityWindow from '@/components/VulnerabilityWindow'

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
  const selectedTerm = useStore((s) => s.selection.selectedTerm)
  const terms = useStore((s) => s.terms)
  const selectAndFocusTerm = useStore((s) => s.selectAndFocusTerm)

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
      <header className="flex-shrink-0 border-b border-border px-6 py-3 flex items-center justify-between relative z-50 bg-surface/30">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <SuperTruthLogo className="h-10 w-auto" />
            <div className="px-2 py-1 bg-violet-600/20 border border-violet-500/30 rounded text-violet-400 text-xs font-bold tracking-wider">
              VIOLET
            </div>
          </div>
          <div className="border-l border-border pl-4">
            <h1 className="text-lg font-semibold">Oncology & Rare Disease Intelligence</h1>
            <p className="text-xs text-gray-500">Multi-source intelligence across cancer types and rare conditions</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <StatsBar />
          <ExplainerPanel />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Filters & Insights (hidden on small screens) */}
        <aside className="w-72 flex-shrink-0 border-r border-border p-4 overflow-y-auto space-y-4 hidden lg:block">
          <FilterPanel />
          <InsightsPanel />
          <VulnerabilityInsightsPanel />
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

        {/* Right Sidebar - Detail Panel, Pipeline & Data Sources (hidden on small screens) */}
        <aside className="w-96 flex-shrink-0 border-l border-border p-4 overflow-y-auto space-y-4 hidden xl:block">
          <DetailPanel />
          <VulnerabilityWindow
            selectedTermId={selectedTerm?.id ?? null}
            onTermSelect={(termId) => {
              const term = terms.find(t => t.id === termId)
              if (term) selectAndFocusTerm(term)
            }}
          />
          <DataSourcesPanel />
          <PipelinePanel />
        </aside>
      </main>

      {/* Footer with Legal Disclaimer */}
      <footer className="flex-shrink-0 border-t border-border px-6 py-2 bg-surface/50">
        <p className="text-[10px] text-gray-600 leading-relaxed">
          <span className="text-yellow-500 font-bold">⚠️ CONFIDENTIAL & PROPRIETARY</span> — This platform contains trade secrets and proprietary data of SuperTruth Inc.
          Unauthorized access, use, reproduction, or distribution is strictly prohibited and may result in civil and criminal penalties.
          All data is provided for research purposes only and does not constitute medical advice.
          By accessing this system, you acknowledge that your activity may be monitored and logged.
        </p>
      </footer>

      {/* AI Chat Panel */}
      <ChatPanel />
    </div>
  )
}
