'use client'

import { useState, useEffect, useCallback } from 'react'
import { Play, RefreshCw, CheckCircle, XCircle, Clock, Database, TrendingUp, MapPin, Loader2, Sparkles, HelpCircle } from 'lucide-react'

interface PipelineStats {
  terms: number
  terms_with_embeddings: number
  clusters: number
  trend_data_points: number
  geographic_regions: number
  regions_with_sdoh: number
  related_queries: number
  discovered_terms: number
  questions: number
}

interface PipelineRun {
  id: number
  status: string
  started_at: string
  completed_at?: string
  records_processed: number
  errors: string[]
}

// 4 API calls per term: timeseries + regions + related queries + related topics
// ~0.5s per call + overhead = ~3s per term
const ESTIMATED_TIME_PER_TERM = 3

export default function PipelinePanel() {
  const [stats, setStats] = useState<PipelineStats | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [currentRun, setCurrentRun] = useState<PipelineRun | null>(null)
  const [progress, setProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState('')
  const [elapsedTime, setElapsedTime] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Fetch current stats
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/pipeline/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [API_URL])

  // Check for running pipelines
  const checkRunningPipeline = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/pipeline/runs?limit=1`)
      if (response.ok) {
        const runs = await response.json()
        if (runs.length > 0 && (runs[0].status === 'running' || runs[0].status === 'queued')) {
          setCurrentRun(runs[0])
          setIsRunning(true)
          return true
        }
      }
    } catch (err) {
      console.error('Failed to check pipeline status:', err)
    }
    return false
  }, [API_URL])

  // Initial load
  useEffect(() => {
    fetchStats()
    checkRunningPipeline()
  }, [fetchStats, checkRunningPipeline])

  // Poll for progress when running
  useEffect(() => {
    if (!isRunning || !currentRun) return

    const startTime = Date.now()
    const estimatedTotal = (stats?.terms || 100) * ESTIMATED_TIME_PER_TERM

    const interval = setInterval(async () => {
      // Update elapsed time
      const elapsed = Math.floor((Date.now() - startTime) / 1000)
      setElapsedTime(elapsed)

      // Estimate progress based on time (since we don't have detailed progress from backend)
      const estimatedProgress = Math.min(95, (elapsed / estimatedTotal) * 100)
      setProgress(estimatedProgress)

      // Update status message based on progress
      if (estimatedProgress < 10) {
        setStatusMessage('Loading taxonomy and generating embeddings...')
      } else if (estimatedProgress < 20) {
        setStatusMessage('Clustering search terms...')
      } else if (estimatedProgress < 65) {
        setStatusMessage('Fetching trends, related queries & topics via SerpAPI...')
      } else if (estimatedProgress < 75) {
        setStatusMessage('Discovering new terms from related queries...')
      } else if (estimatedProgress < 85) {
        setStatusMessage('Fetching hourly search patterns (anxiety windows)...')
      } else if (estimatedProgress < 92) {
        setStatusMessage('Embedding and clustering discovered terms...')
      } else {
        setStatusMessage('Loading SDOH data and finalizing...')
      }

      // Check actual status
      try {
        const response = await fetch(`${API_URL}/api/pipeline/runs/${currentRun.id}`)
        if (response.ok) {
          const run = await response.json()
          setCurrentRun(run)

          if (run.status === 'completed') {
            setProgress(100)
            setStatusMessage('Pipeline completed successfully!')
            setIsRunning(false)
            fetchStats()
            clearInterval(interval)
          } else if (run.status === 'failed') {
            setError(run.errors?.[0] || 'Pipeline failed')
            setIsRunning(false)
            clearInterval(interval)
          }
        }
      } catch (err) {
        console.error('Failed to check run status:', err)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [isRunning, currentRun, stats, API_URL, fetchStats])

  // Start pipeline
  const startPipeline = async () => {
    setError(null)
    setProgress(0)
    setElapsedTime(0)
    setStatusMessage('Starting pipeline...')

    try {
      const response = await fetch(`${API_URL}/api/pipeline/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fetch_trends: true,
          timeframe: 'today 5-y',  // 5 years of data
          geo: 'US',
        }),
      })

      if (response.ok) {
        const data = await response.json()
        setCurrentRun({ id: data.run_id, status: 'running', started_at: new Date().toISOString(), records_processed: 0, errors: [] })
        setIsRunning(true)
      } else {
        setError('Failed to start pipeline')
      }
    } catch (err) {
      setError('Failed to connect to server')
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }

  const estimatedTotalTime = (stats?.terms || 100) * ESTIMATED_TIME_PER_TERM
  const remainingTime = Math.max(0, estimatedTotalTime - elapsedTime)

  const hasTrendData = stats && stats.trend_data_points > 0

  return (
    <div className="glass rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-400" />
          Data Pipeline
        </h3>
        <button
          onClick={fetchStats}
          className="p-1.5 hover:bg-surface rounded-lg transition-colors"
          title="Refresh stats"
        >
          <RefreshCw className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* Current Stats */}
      {stats && (
        <div className="space-y-2">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="bg-surface rounded-lg p-2 text-center">
              <div className="text-lg font-semibold text-white">{stats.terms}</div>
              <div className="text-gray-500">Terms</div>
            </div>
            <div className="bg-surface rounded-lg p-2 text-center">
              <div className="text-lg font-semibold text-white">{stats.trend_data_points.toLocaleString()}</div>
              <div className="text-gray-500">Trend Points</div>
            </div>
            <div className="bg-surface rounded-lg p-2 text-center">
              <div className="text-lg font-semibold text-white">{stats.geographic_regions}</div>
              <div className="text-gray-500">Regions</div>
            </div>
          </div>
          {/* Secondary stats row */}
          {(stats.related_queries > 0 || stats.discovered_terms > 0 || stats.questions > 0) && (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="bg-surface rounded-lg p-2 text-center">
                <div className="text-lg font-semibold text-purple-400">{stats.related_queries.toLocaleString()}</div>
                <div className="text-gray-500">Related Queries</div>
              </div>
              <div className="bg-surface rounded-lg p-2 text-center">
                <div className="text-lg font-semibold text-yellow-400">{stats.discovered_terms}</div>
                <div className="text-gray-500">Discovered</div>
              </div>
              <div className="bg-surface rounded-lg p-2 text-center">
                <div className="text-lg font-semibold text-cyan-400">{stats.questions.toLocaleString()}</div>
                <div className="text-gray-500">Questions</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Status Banner */}
      {hasTrendData ? (
        <div className="flex items-center gap-2 p-2 bg-green-500/10 border border-green-500/20 rounded-lg">
          <CheckCircle className="w-4 h-4 text-green-400" />
          <span className="text-xs text-green-400">
            5-year trend data loaded
            {stats && stats.discovered_terms > 0 && ` · ${stats.discovered_terms} terms auto-discovered`}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
          <Clock className="w-4 h-4 text-yellow-400" />
          <span className="text-xs text-yellow-400">Using demo data - run pipeline for real trends</span>
        </div>
      )}

      {/* Progress Bar (when running) */}
      {isRunning && (
        <div className="space-y-3 p-3 bg-gradient-to-br from-cyan-500/10 to-pink-500/10 border border-cyan-500/30 rounded-lg">
          {/* Big progress percentage */}
          <div className="text-center">
            <div className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-pink-400">
              {progress.toFixed(0)}%
            </div>
            <div className="text-sm text-gray-300 mt-1">{statusMessage}</div>
          </div>

          {/* Large progress bar */}
          <div className="h-4 bg-surface rounded-full overflow-hidden shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500 transition-all duration-500 relative"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute inset-0 bg-white/20 animate-pulse" />
            </div>
          </div>

          {/* Time info */}
          <div className="flex justify-between text-sm">
            <span className="flex items-center gap-2 text-cyan-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              {formatTime(elapsedTime)} elapsed
            </span>
            <span className="text-pink-400">~{formatTime(remainingTime)} remaining</span>
          </div>

          {/* Step indicators */}
          <div className="flex justify-between pt-2 border-t border-white/10">
            <div className={`flex flex-col items-center ${progress > 0 ? 'text-cyan-400' : 'text-gray-600'}`}>
              <div className={`w-3 h-3 rounded-full transition-all ${progress > 0 ? 'bg-cyan-400 shadow-lg shadow-cyan-400/50' : 'bg-gray-600'}`} />
              <span className="text-[10px] mt-1">Taxonomy</span>
            </div>
            <div className={`flex flex-col items-center ${progress > 10 ? 'text-cyan-400' : 'text-gray-600'}`}>
              <div className={`w-3 h-3 rounded-full transition-all ${progress > 10 ? 'bg-cyan-400 shadow-lg shadow-cyan-400/50' : 'bg-gray-600'}`} />
              <span className="text-[10px] mt-1">Embed</span>
            </div>
            <div className={`flex flex-col items-center ${progress > 20 ? 'text-pink-400' : 'text-gray-600'}`}>
              <div className={`w-3 h-3 rounded-full transition-all ${progress > 20 ? 'bg-pink-400 shadow-lg shadow-pink-400/50 animate-pulse' : 'bg-gray-600'}`} />
              <span className="text-[10px] mt-1">Trends</span>
            </div>
            <div className={`flex flex-col items-center ${progress > 65 ? 'text-yellow-400' : 'text-gray-600'}`}>
              <div className={`w-3 h-3 rounded-full transition-all ${progress > 65 ? 'bg-yellow-400 shadow-lg shadow-yellow-400/50 animate-pulse' : 'bg-gray-600'}`} />
              <span className="text-[10px] mt-1">Discover</span>
            </div>
            <div className={`flex flex-col items-center ${progress > 75 ? 'text-violet-400' : 'text-gray-600'}`}>
              <div className={`w-3 h-3 rounded-full transition-all ${progress > 75 ? 'bg-violet-400 shadow-lg shadow-violet-400/50 animate-pulse' : 'bg-gray-600'}`} />
              <span className="text-[10px] mt-1">Hourly</span>
            </div>
            <div className={`flex flex-col items-center ${progress > 92 ? 'text-green-400' : 'text-gray-600'}`}>
              <div className={`w-3 h-3 rounded-full transition-all ${progress > 92 ? 'bg-green-400 shadow-lg shadow-green-400/50' : 'bg-gray-600'}`} />
              <span className="text-[10px] mt-1">SDOH</span>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-2 bg-red-500/10 border border-red-500/20 rounded-lg">
          <XCircle className="w-4 h-4 text-red-400" />
          <span className="text-xs text-red-400">{error}</span>
        </div>
      )}

      {/* Run Button */}
      <button
        onClick={startPipeline}
        disabled={isRunning}
        className={`w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-all ${
          isRunning
            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
            : hasTrendData
              ? 'bg-gradient-to-r from-cyan-500 to-pink-500 hover:from-cyan-400 hover:to-pink-400 text-white'
              : 'bg-gradient-to-r from-cyan-500 to-pink-500 hover:from-cyan-400 hover:to-pink-400 text-white animate-pulse shadow-lg shadow-cyan-500/30'
        }`}
      >
        {isRunning ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-base">Fetching Intelligence Data...</span>
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            <span className="text-base">{hasTrendData ? 'Refresh Data' : '▶ Fetch Intelligence Data'}</span>
          </>
        )}
      </button>

      {/* Info */}
      <p className="text-[10px] text-gray-500 text-center">
        Fetches 5-year trends, hourly patterns, related queries, topics & People Also Ask questions via SerpAPI for all {stats?.terms || '~300'} terms.
        Auto-discovers emerging terms. Surfaces the actual human questions behind each search.
      </p>
    </div>
  )
}
