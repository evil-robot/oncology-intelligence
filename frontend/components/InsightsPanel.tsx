'use client'

import { useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  Zap,
  MapPin,
  Link2,
  AlertTriangle,
  Sparkles,
  ChevronRight,
  RefreshCw
} from 'lucide-react'
import { useStore } from '@/lib/store'

interface Insight {
  type: 'spike' | 'drop' | 'emerging' | 'regional_outlier' | 'correlation'
  severity: 'high' | 'medium' | 'low'
  title: string
  description: string
  term_id?: number
  term_name?: string
  cluster_id?: number
  geo_code?: string
  metric_value?: number
  baseline_value?: number
  percent_change?: number
  detected_at?: string
}

const typeConfig = {
  spike: { icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-400/10' },
  drop: { icon: TrendingDown, color: 'text-red-400', bg: 'bg-red-400/10' },
  emerging: { icon: Zap, color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
  regional_outlier: { icon: MapPin, color: 'text-blue-400', bg: 'bg-blue-400/10' },
  correlation: { icon: Link2, color: 'text-purple-400', bg: 'bg-purple-400/10' },
}

const severityConfig = {
  high: { color: 'text-red-400', dot: 'bg-red-400' },
  medium: { color: 'text-yellow-400', dot: 'bg-yellow-400' },
  low: { color: 'text-gray-400', dot: 'bg-gray-400' },
}

function InsightCard({ insight, onClick }: { insight: Insight; onClick: () => void }) {
  const config = typeConfig[insight.type]
  const severity = severityConfig[insight.severity]
  const Icon = config.icon

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg ${config.bg} hover:brightness-110 transition-all group`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg bg-black/20`}>
          <Icon className={`w-4 h-4 ${config.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${severity.dot}`} />
            <span className="text-xs text-gray-400 capitalize">{insight.type.replace('_', ' ')}</span>
          </div>
          <h4 className="text-sm font-medium mt-1 truncate">{insight.title}</h4>
          <p className="text-xs text-gray-400 mt-1 line-clamp-2">{insight.description}</p>
          {insight.percent_change != null && (
            <div className={`text-xs mt-2 ${insight.percent_change > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {insight.percent_change > 0 ? '+' : ''}{insight.percent_change.toFixed(0)}% change
            </div>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-white transition-colors" />
      </div>
    </button>
  )
}

export default function InsightsPanel() {
  const [insights, setInsights] = useState<Insight[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<string | null>(null)
  const [demoMode, setDemoMode] = useState(false)
  const terms = useStore((s) => s.terms)
  const clusters = useStore((s) => s.clusters)
  const selectAndFocusTerm = useStore((s) => s.selectAndFocusTerm)
  const selectAndFocusCluster = useStore((s) => s.selectAndFocusCluster)

  const fetchInsights = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = filter ? `?type=${filter}` : ''
      const response = await fetch(`${API_URL}/api/insights/${params}`)
      if (!response.ok) throw new Error('Failed to fetch insights')
      const data = await response.json()
      // Handle new response format: {insights: [...], demo_mode: bool, trend_data_points: int}
      if (data.insights) {
        setInsights(data.insights)
        setDemoMode(data.demo_mode || false)
      } else if (Array.isArray(data)) {
        // Fallback for old format
        setInsights(data)
        setDemoMode(false)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load insights')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchInsights()
  }, [filter])

  const handleInsightClick = (insight: Insight) => {
    // First try to find by term_id
    if (insight.term_id) {
      const term = terms.find(t => t.id === insight.term_id)
      if (term) {
        selectAndFocusTerm(term)
        return
      }
    }

    // Then try by term_name
    if (insight.term_name) {
      const term = terms.find(t =>
        t.term.toLowerCase() === insight.term_name?.toLowerCase()
      )
      if (term) {
        selectAndFocusTerm(term)
        return
      }
    }

    // Try cluster_id
    if (insight.cluster_id) {
      const cluster = clusters.find(c => c.id === insight.cluster_id)
      if (cluster) {
        selectAndFocusCluster(cluster)
        return
      }
    }

    // Try to match by title (often contains the term name)
    const titleMatch = terms.find(t =>
      insight.title.toLowerCase().includes(t.term.toLowerCase())
    )
    if (titleMatch) {
      selectAndFocusTerm(titleMatch)
    }
  }

  const filterButtons = [
    { key: null, label: 'All' },
    { key: 'spike', label: 'Spikes' },
    { key: 'emerging', label: 'Emerging' },
    { key: 'regional_outlier', label: 'Regional' },
  ]

  return (
    <div className="glass rounded-lg p-4 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-yellow-400" />
          Insights & Anomalies
          {demoMode && (
            <span className="px-1.5 py-0.5 text-[10px] bg-yellow-500/20 text-yellow-400 rounded uppercase font-bold">
              Demo
            </span>
          )}
        </h3>
        <button
          onClick={fetchInsights}
          disabled={isLoading}
          className="p-1.5 hover:bg-surface rounded-lg transition-colors"
        >
          <RefreshCw className={`w-4 h-4 text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Demo Mode Banner */}
      {demoMode && !isLoading && (
        <div className="mb-3 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
          <p className="text-xs text-yellow-400">
            Showing sample data. Run the pipeline to get real insights from Google Trends.
          </p>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-1 mb-4">
        {filterButtons.map(btn => (
          <button
            key={btn.key || 'all'}
            onClick={() => setFilter(btn.key)}
            className={`px-2 py-1 text-xs rounded-lg transition-colors ${
              filter === btn.key
                ? 'bg-primary text-white'
                : 'bg-surface text-gray-400 hover:text-white'
            }`}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <AlertTriangle className="w-8 h-8 text-yellow-400 mx-auto mb-2" />
            <p className="text-sm text-gray-400">{error}</p>
            <button
              onClick={fetchInsights}
              className="mt-2 text-xs text-primary hover:underline"
            >
              Retry
            </button>
          </div>
        ) : insights.length === 0 ? (
          <div className="text-center py-8">
            <Sparkles className="w-8 h-8 text-gray-500 mx-auto mb-2" />
            <p className="text-sm text-gray-400">No anomalies detected</p>
            <p className="text-xs text-gray-500 mt-1">Run the pipeline to generate more data</p>
          </div>
        ) : (
          insights.map((insight, i) => (
            <InsightCard
              key={i}
              insight={insight}
              onClick={() => handleInsightClick(insight)}
            />
          ))
        )}
      </div>

      {/* Summary */}
      {!isLoading && insights.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex justify-between text-xs text-gray-400">
            <span>{insights.length} insights detected</span>
            <span>
              {insights.filter(i => i.severity === 'high').length} high priority
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
