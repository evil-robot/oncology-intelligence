'use client'

import { useState, useEffect } from 'react'
import { Globe, TrendingUp, TrendingDown, Minus, Calendar, Database, BarChart3, RefreshCw } from 'lucide-react'
import api, { DataSource, TopTermComparison, CategoryComparison } from '@/lib/api'

interface RegionComparisonPanelProps {
  selectedRegions?: string[]
}

export default function RegionComparisonPanel({ selectedRegions = ['US'] }: RegionComparisonPanelProps) {
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [topTerms, setTopTerms] = useState<TopTermComparison[]>([])
  const [categoryComparison, setCategoryComparison] = useState<CategoryComparison[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'sources' | 'terms' | 'categories'>('sources')

  const regionNames: Record<string, string> = {
    US: 'United States',
    GB: 'United Kingdom',
    CA: 'Canada',
    AU: 'Australia',
    DE: 'Germany',
    FR: 'France',
    JP: 'Japan',
  }

  const regionFlags: Record<string, string> = {
    US: '🇺🇸',
    GB: '🇬🇧',
    CA: '🇨🇦',
    AU: '🇦🇺',
    DE: '🇩🇪',
    FR: '🇫🇷',
    JP: '🇯🇵',
  }

  useEffect(() => {
    loadData()
  }, [selectedRegions])

  const loadData = async () => {
    setLoading(true)
    try {
      const [sourcesData, termsData, categoryData] = await Promise.all([
        api.getDataSources(),
        api.getTopTermsByRegion(selectedRegions, 10),
        api.getCategoryComparison(selectedRegions),
      ])
      setDataSources(sourcesData)
      setTopTerms(termsData)
      setCategoryComparison(categoryData)
    } catch (error) {
      console.error('Failed to load comparison data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const formatTimeframe = (timeframe: string) => {
    const mapping: Record<string, string> = {
      'today 1-m': 'Past Month',
      'today 3-m': 'Past 3 Months',
      'today 12-m': 'Past Year',
      'today 5-y': 'Past 5 Years',
      'all': 'All Time (2004+)',
    }
    return mapping[timeframe] || timeframe
  }

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-400" />
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-400" />
      default:
        return <Minus className="w-4 h-4 text-gray-400" />
    }
  }

  if (loading) {
    return (
      <div className="glass rounded-lg p-4">
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="w-6 h-6 animate-spin text-primary" />
          <span className="ml-2 text-gray-400">Loading comparison data...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="glass rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Globe className="w-4 h-4" />
          Region Comparison
        </h3>
        <div className="flex gap-2">
          {selectedRegions.map((region) => (
            <span
              key={region}
              className="px-2 py-1 bg-surface rounded text-xs text-gray-300"
            >
              {regionFlags[region]} {region}
            </span>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface rounded-lg p-1">
        <button
          onClick={() => setActiveTab('sources')}
          className={`flex-1 px-3 py-1.5 text-xs rounded transition-colors flex items-center justify-center gap-1 ${
            activeTab === 'sources'
              ? 'bg-primary text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <Database className="w-3 h-3" />
          Data Sources
        </button>
        <button
          onClick={() => setActiveTab('terms')}
          className={`flex-1 px-3 py-1.5 text-xs rounded transition-colors flex items-center justify-center gap-1 ${
            activeTab === 'terms'
              ? 'bg-primary text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <TrendingUp className="w-3 h-3" />
          Top Terms
        </button>
        <button
          onClick={() => setActiveTab('categories')}
          className={`flex-1 px-3 py-1.5 text-xs rounded transition-colors flex items-center justify-center gap-1 ${
            activeTab === 'categories'
              ? 'bg-primary text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <BarChart3 className="w-3 h-3" />
          Categories
        </button>
      </div>

      {/* Data Sources Tab */}
      {activeTab === 'sources' && (
        <div className="space-y-3">
          {dataSources.length === 0 ? (
            <div className="text-center py-6">
              <Database className="w-8 h-8 mx-auto text-gray-600 mb-2" />
              <p className="text-sm text-gray-500">No data sources found</p>
              <p className="text-xs text-gray-600 mt-1">
                Run the pipeline to fetch data for different regions
              </p>
            </div>
          ) : (
            dataSources.map((source) => (
              <div
                key={source.id}
                className="bg-surface/50 rounded-lg p-3 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-white flex items-center gap-2">
                    {regionFlags[source.geo_code]} {regionNames[source.geo_code] || source.geo_code}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatTimeframe(source.timeframe)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1 text-gray-400">
                    <Calendar className="w-3 h-3" />
                    <span>Data: {formatDate(source.data_start_date)} - {formatDate(source.data_end_date)}</span>
                  </div>
                  <div className="text-gray-400 text-right">
                    Fetched: {formatDate(source.fetched_at)}
                  </div>
                </div>
                <div className="flex gap-4 text-xs">
                  <span className="text-primary">{source.term_count} terms</span>
                  <span className="text-cyan-400">{source.trend_count?.toLocaleString()} data points</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Top Terms Tab */}
      {activeTab === 'terms' && (
        <div className="space-y-4">
          {topTerms.length === 0 ? (
            <div className="text-center py-6">
              <TrendingUp className="w-8 h-8 mx-auto text-gray-600 mb-2" />
              <p className="text-sm text-gray-500">No trend data available</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {topTerms.map((regionData) => (
                <div key={regionData.geo_code} className="space-y-2">
                  <h4 className="text-sm font-medium text-white flex items-center gap-2">
                    {regionFlags[regionData.geo_code]} {regionData.geo_name}
                  </h4>
                  <div className="space-y-1">
                    {regionData.top_terms.map((term, idx) => (
                      <div
                        key={term.term}
                        className="flex items-center justify-between bg-surface/30 rounded px-2 py-1"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500 w-4">{idx + 1}.</span>
                          <span className="text-sm text-gray-300">{term.term}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">{term.category}</span>
                          <span className="text-xs text-primary font-medium">
                            {term.avg_interest.toFixed(0)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Categories Tab */}
      {activeTab === 'categories' && (
        <div className="space-y-3">
          {categoryComparison.length === 0 ? (
            <div className="text-center py-6">
              <BarChart3 className="w-8 h-8 mx-auto text-gray-600 mb-2" />
              <p className="text-sm text-gray-500">No category data available</p>
            </div>
          ) : (
            categoryComparison.slice(0, 8).map((cat) => (
              <div key={cat.category} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-white capitalize">
                    {cat.category.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex gap-2">
                  {cat.regions.map((region) => {
                    const maxInterest = Math.max(...cat.regions.map((r) => r.avg_interest))
                    const widthPercent = maxInterest > 0 ? (region.avg_interest / maxInterest) * 100 : 0
                    return (
                      <div key={region.geo_code} className="flex-1">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-gray-500">
                            {regionFlags[region.geo_code]} {region.geo_code}
                          </span>
                          <span className="text-gray-400">
                            {region.avg_interest.toFixed(0)}
                          </span>
                        </div>
                        <div className="h-2 bg-surface rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              region.geo_code === 'US' ? 'bg-blue-500' : 'bg-purple-500'
                            }`}
                            style={{ width: `${widthPercent}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Legend */}
      <div className="pt-2 border-t border-border">
        <p className="text-xs text-gray-500">
          Interest scores range from 0-100, representing relative search volume.
          Data via SerpAPI.
        </p>
      </div>
    </div>
  )
}
