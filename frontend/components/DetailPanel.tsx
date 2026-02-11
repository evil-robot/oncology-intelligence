'use client'

import { useEffect, useState } from 'react'
import { X, TrendingUp, MapPin, ExternalLink, Sparkles, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useStore, useSelection } from '@/lib/store'
import api, { TrendPoint, Term, RegionData, QuestionData } from '@/lib/api'

interface TopRegion {
  name: string
  geo_code: string
  interest: number
}

export default function DetailPanel() {
  const selection = useSelection()
  const resetView = useStore((s) => s.resetView)
  const selectTerm = useStore((s) => s.selectTerm)
  const filters = useStore((s) => s.filters)

  const [trendData, setTrendData] = useState<TrendPoint[]>([])
  const [similarTerms, setSimilarTerms] = useState<Term[]>([])
  const [topRegions, setTopRegions] = useState<TopRegion[]>([])
  const [questions, setQuestions] = useState<QuestionData[]>([])
  const [questionsExpanded, setQuestionsExpanded] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const selected = selection.selectedTerm || selection.selectedCluster

  useEffect(() => {
    if (!selected) {
      setTrendData([])
      setSimilarTerms([])
      setTopRegions([])
      setQuestions([])
      return
    }

    setIsLoading(true)

    const fetchData = async () => {
      try {
        if (selection.selectedTerm) {
          const [trends, similar, regions, questionResponse] = await Promise.all([
            api.getTermTrends(selection.selectedTerm.id, filters.geoCode),
            api.getSimilarTerms(selection.selectedTerm.id),
            api.getHeatmapData({ termId: selection.selectedTerm.id }),
            api.getTermQuestions(selection.selectedTerm.id),
          ])
          setTrendData(trends.data)
          setSimilarTerms(similar)
          setQuestions(questionResponse.questions || [])
          // Sort by interest and take top 5
          const sortedRegions = regions
            .filter((r: RegionData) => r.interest > 0)
            .sort((a: RegionData, b: RegionData) => b.interest - a.interest)
            .slice(0, 5)
            .map((r: RegionData) => ({
              name: r.name,
              geo_code: r.geo_code,
              interest: r.interest,
            }))
          setTopRegions(sortedRegions)
        } else if (selection.selectedCluster) {
          const [trends, regions] = await Promise.all([
            api.getClusterTrends(selection.selectedCluster.id, filters.geoCode),
            api.getHeatmapData({ clusterId: selection.selectedCluster.id }),
          ])
          setTrendData(trends.data)
          setSimilarTerms([])
          // Sort by interest and take top 5
          const sortedRegions = regions
            .filter((r: RegionData) => r.interest > 0)
            .sort((a: RegionData, b: RegionData) => b.interest - a.interest)
            .slice(0, 5)
            .map((r: RegionData) => ({
              name: r.name,
              geo_code: r.geo_code,
              interest: r.interest,
            }))
          setTopRegions(sortedRegions)
        }
      } catch (error) {
        console.error('Failed to fetch details:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [selection.selectedTerm, selection.selectedCluster, filters.geoCode])

  if (!selected) {
    return (
      <div className="glass rounded-lg p-6 flex flex-col items-center justify-center text-center h-full">
        <Sparkles className="w-8 h-8 text-gray-500 mb-3" />
        <p className="text-gray-400">Select a cluster or term to view details</p>
        <p className="text-xs text-gray-500 mt-1">Click on points in the 3D visualization</p>
      </div>
    )
  }

  const handleClose = () => {
    resetView()
  }

  const isCluster = 'termCount' in selected

  return (
    <div className="glass rounded-lg p-4 space-y-4 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">
            {isCluster ? 'Cluster' : 'Search Term'}
          </p>
          <h3 className="text-lg font-medium">
            {isCluster ? (selected as any).name : (selected as any).term}
          </h3>
          {!isCluster && (selected as Term).category && (
            <span className="inline-block mt-1 px-2 py-0.5 bg-primary/20 text-primary text-xs rounded">
              {(selected as Term).category}
            </span>
          )}
        </div>
        <button
          onClick={handleClose}
          className="p-1 hover:bg-surface rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Trend Chart */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <TrendingUp className="w-4 h-4" />
          <span>Interest Over Time</span>
        </div>

        {isLoading ? (
          <div className="h-32 flex items-center justify-center">
            <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        ) : trendData.length > 0 ? (
          <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <XAxis
                  dataKey="date"
                  tick={false}
                  axisLine={{ stroke: '#333' }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: '#666' }}
                  axisLine={{ stroke: '#333' }}
                  width={30}
                />
                <Tooltip
                  contentStyle={{
                    background: '#12121a',
                    border: '1px solid #333',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                  labelFormatter={(label) => new Date(label).toLocaleDateString()}
                />
                <Line
                  type="monotone"
                  dataKey="interest"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-32 flex items-center justify-center text-gray-500 text-sm">
            No trend data available
          </div>
        )}
      </div>

      {/* Cluster Stats */}
      {isCluster && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-surface rounded-lg p-3">
            <p className="text-xs text-gray-500">Terms</p>
            <p className="text-xl font-medium">{(selected as any).termCount}</p>
          </div>
          <div className="bg-surface rounded-lg p-3">
            <p className="text-xs text-gray-500">Avg Volume</p>
            <p className="text-xl font-medium">
              {(selected as any).avgSearchVolume?.toFixed(0) || '—'}
            </p>
          </div>
        </div>
      )}

      {/* Similar Terms */}
      {!isCluster && similarTerms.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-gray-400">Similar Terms</p>
          <div className="space-y-1">
            {similarTerms.slice(0, 5).map((term) => (
              <button
                key={term.id}
                onClick={() => selectTerm(term)}
                className="w-full text-left px-3 py-2 bg-surface hover:bg-border rounded-lg text-sm transition-colors"
              >
                {term.term}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* People Also Ask */}
      {!isCluster && questions.length > 0 && (
        <div className="space-y-2">
          <button
            onClick={() => setQuestionsExpanded(!questionsExpanded)}
            className="flex items-center justify-between w-full text-sm text-gray-400 hover:text-gray-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <HelpCircle className="w-4 h-4" />
              <span>People Also Ask</span>
              <span className="text-xs text-gray-600">({questions.length})</span>
            </div>
            {questionsExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          {questionsExpanded && (
            <div className="space-y-2">
              {questions.slice(0, 10).map((q) => (
                <div
                  key={q.id}
                  className="bg-surface rounded-lg p-3 space-y-1"
                >
                  <p className="text-sm font-medium text-gray-200">
                    {q.question}
                  </p>
                  {q.snippet && (
                    <p className="text-xs text-gray-500 line-clamp-2">
                      {q.snippet}
                    </p>
                  )}
                  {q.source_url && (
                    <a
                      href={q.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-primary/70 hover:text-primary transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" />
                      {q.source_title || 'Source'}
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Geographic Info */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <MapPin className="w-4 h-4" />
          <span>Top Regions</span>
        </div>
        <div className="space-y-1 text-sm">
          {topRegions.length > 0 ? (
            topRegions.map((region) => (
              <div key={region.geo_code} className="flex justify-between py-1 px-2 bg-surface rounded">
                <span>{region.name}</span>
                <span className="text-primary">{Math.round(region.interest)}</span>
              </div>
            ))
          ) : (
            <div className="py-2 px-2 text-gray-500 text-center">
              {isLoading ? 'Loading...' : 'No regional data available'}
            </div>
          )}
        </div>
      </div>

      {/* Links / Resources */}
      <div className="pt-2 border-t border-border">
        <a
          href={`https://www.google.com/search?q=${encodeURIComponent(
            isCluster ? (selected as any).name : (selected as any).term
          )}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-primary transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          Search on Google
        </a>
      </div>
    </div>
  )
}
