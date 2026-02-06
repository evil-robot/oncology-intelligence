'use client'

import { useEffect, useState } from 'react'
import { Database, Layers, TrendingUp, Globe, Clock, Search, Sparkles } from 'lucide-react'
import api from '@/lib/api'
import Tooltip from './Tooltip'

interface Stats {
  terms: number
  clusters: number
  trend_data_points: number
  geographic_regions: number
  related_queries: number
  discovered_terms: number
}

export default function StatsBar() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    api.getPipelineStats().then(setStats).catch(console.error)
  }, [])

  const items = [
    {
      icon: Database,
      label: 'Terms',
      value: stats?.terms || 0,
      tooltip: (
        <div>
          <p className="font-medium text-white mb-1">Search Terms</p>
          <p className="text-gray-400 text-xs">
            Total oncology and rare disease search terms being tracked.
            Includes cancer types, treatments, symptoms, clinical trials, and caregiver queries.
          </p>
        </div>
      ),
    },
    {
      icon: Layers,
      label: 'Clusters',
      value: stats?.clusters || 0,
      tooltip: (
        <div>
          <p className="font-medium text-white mb-1">Topic Clusters</p>
          <p className="text-gray-400 text-xs">
            AI-generated groupings of semantically similar search terms.
            Terms are clustered using OpenAI embeddings and HDBSCAN algorithm.
          </p>
        </div>
      ),
    },
    {
      icon: TrendingUp,
      label: 'Data Points',
      value: stats?.trend_data_points || 0,
      tooltip: (
        <div>
          <p className="font-medium text-white mb-1">Trend Data Points</p>
          <p className="text-gray-400 text-xs">
            Individual data points from search interest data collected via SerpAPI.
            Each point represents search interest (0-100) for a term at a specific time.
          </p>
        </div>
      ),
    },
    {
      icon: Globe,
      label: 'Regions',
      value: stats?.geographic_regions || 0,
      tooltip: (
        <div>
          <p className="font-medium text-white mb-1">Geographic Regions</p>
          <p className="text-gray-400 text-xs">
            US states/regions with SDOH (Social Determinants of Health) data
            from CDC's Social Vulnerability Index.
          </p>
        </div>
      ),
    },
  ]

  return (
    <div className="glass rounded-lg px-4 py-2 flex items-center gap-4">
      {items.map((item) => (
        <Tooltip key={item.label} content={item.tooltip} position="bottom">
          <div className="flex items-center gap-2 cursor-help group">
            <item.icon className="w-4 h-4 text-gray-500 group-hover:text-primary transition-colors" />
            <div>
              <p className="text-xs text-gray-500 group-hover:text-gray-400 transition-colors">{item.label}</p>
              <p className="text-sm font-medium">{item.value.toLocaleString()}</p>
            </div>
          </div>
        </Tooltip>
      ))}

      {/* Separator */}
      <div className="h-8 w-px bg-border" />

      {/* Time Period */}
      <Tooltip
        content={
          <div>
            <p className="font-medium text-white mb-1">Data Time Period</p>
            <p className="text-gray-400 text-xs">
              Search trend data covers the past year of historical data,
              providing trend analysis and seasonal pattern detection.
            </p>
          </div>
        }
        position="bottom"
      >
        <div className="flex items-center gap-2 cursor-help group">
          <Clock className="w-4 h-4 text-gray-500 group-hover:text-primary transition-colors" />
          <div>
            <p className="text-xs text-gray-500 group-hover:text-gray-400 transition-colors">Period</p>
            <p className="text-sm font-medium">5 Years</p>
          </div>
        </div>
      </Tooltip>

      {/* Data Source */}
      <Tooltip
        content={
          <div>
            <p className="font-medium text-white mb-1">Data Source</p>
            <p className="text-gray-400 text-xs">
              Search trends via SerpAPI, academic research from Google Scholar,
              patent filings, news, clinical trials, PubMed, and FDA data.
              SDOH overlay from CDC SVI. Embeddings by OpenAI.
            </p>
          </div>
        }
        position="bottom"
      >
        <div className="flex items-center gap-2 cursor-help group">
          <Search className="w-4 h-4 text-gray-500 group-hover:text-primary transition-colors" />
          <div>
            <p className="text-xs text-gray-500 group-hover:text-gray-400 transition-colors">Source</p>
            <p className="text-sm font-medium">8 Sources</p>
          </div>
        </div>
      </Tooltip>
    </div>
  )
}
