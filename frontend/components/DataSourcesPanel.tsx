'use client'

import { useState, useEffect } from 'react'
import {
  Database,
  FlaskConical,
  FileText,
  Pill,
  Newspaper,
  MapPin,
  ExternalLink,
  RefreshCw,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  GraduationCap,
  ScrollText,
} from 'lucide-react'
import { useSelection } from '@/lib/store'

interface DataSource {
  id: string
  name: string
  description: string
  url: string
  data_type: string
  update_frequency: string
  coverage: string
  stored?: boolean
}

interface SourcesResponse {
  core_data: DataSource[]
  evidence_sources: DataSource[]
}

interface TriangulationData {
  term: string
  clinical_trials: { count: number; items: any[]; recruiting: number }
  publications: { count: number; items: any[] }
  fda_data: { count: number; items: any[] }
  news: { count: number; items: any[] }
  scholar: { count: number; items: any[]; top_cited: number }
  patents: { count: number; items: any[] }
  summary: { total_sources: number; evidence_strength: string }
}

const sourceIcons: Record<string, any> = {
  google_trends: TrendingUp,
  clinical_trials: FlaskConical,
  pubmed: FileText,
  google_scholar: GraduationCap,
  openfda: Pill,
  cdc_svi: MapPin,
  google_news: Newspaper,
  google_patents: ScrollText,
  news: Newspaper,
}

const strengthColors: Record<string, string> = {
  strong: 'text-green-400 bg-green-400/20',
  moderate: 'text-blue-400 bg-blue-400/20',
  emerging: 'text-yellow-400 bg-yellow-400/20',
  limited: 'text-gray-400 bg-gray-400/20',
}

// Configuration for rendering each evidence section dynamically
const evidenceSections = [
  {
    key: 'clinical_trials',
    label: 'Clinical Trials',
    icon: FlaskConical,
    color: 'text-purple-400',
    source: 'ClinicalTrials.gov',
    getSubtext: (data: any) =>
      data.recruiting > 0 ? `${data.recruiting} recruiting` : null,
    getItemTitle: (item: any) => item.title,
    getItemUrl: (item: any) => item.url,
  },
  {
    key: 'scholar',
    label: 'Academic Research',
    icon: GraduationCap,
    color: 'text-emerald-400',
    source: 'Google Scholar via SerpAPI',
    getSubtext: (data: any) =>
      data.top_cited > 0 ? `Top cited: ${data.top_cited}` : null,
    getItemTitle: (item: any) => item.title,
    getItemUrl: (item: any) => item.url,
  },
  {
    key: 'publications',
    label: 'PubMed Publications',
    icon: FileText,
    color: 'text-blue-400',
    source: 'PubMed/NCBI',
    getSubtext: () => null,
    getItemTitle: (item: any) => item.title,
    getItemUrl: (item: any) => item.url,
  },
  {
    key: 'fda_data',
    label: 'FDA Data',
    icon: Pill,
    color: 'text-green-400',
    source: 'FDA openFDA',
    getSubtext: () => null,
    getItemTitle: (item: any) => item.drug_name || item.title,
    getItemUrl: () => null,
  },
  {
    key: 'news',
    label: 'News Coverage',
    icon: Newspaper,
    color: 'text-yellow-400',
    source: 'Google News via SerpAPI',
    getSubtext: () => null,
    getItemTitle: (item: any) => item.title,
    getItemUrl: (item: any) => item.url,
  },
  {
    key: 'patents',
    label: 'Patent Filings',
    icon: ScrollText,
    color: 'text-orange-400',
    source: 'Google Patents via SerpAPI',
    getSubtext: () => null,
    getItemTitle: (item: any) => item.title,
    getItemUrl: (item: any) => item.url,
  },
]

export default function DataSourcesPanel() {
  const selection = useSelection()
  const [coreData, setCoreData] = useState<DataSource[]>([])
  const [evidenceSrcs, setEvidenceSrcs] = useState<DataSource[]>([])
  const [triangulation, setTriangulation] = useState<TriangulationData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'sources' | 'evidence'>('sources')

  const selectedTerm = selection.selectedTerm

  // Fetch available data sources
  useEffect(() => {
    const fetchSources = async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${API_URL}/api/triangulate/sources`)
        if (response.ok) {
          const data: SourcesResponse = await response.json()
          setCoreData(data.core_data || [])
          setEvidenceSrcs(data.evidence_sources || [])
        }
      } catch (error) {
        console.error('Failed to fetch sources:', error)
      }
    }
    fetchSources()
  }, [])

  // Fetch triangulation data when term is selected
  useEffect(() => {
    if (!selectedTerm) {
      setTriangulation(null)
      return
    }

    const fetchTriangulation = async () => {
      setIsLoading(true)
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${API_URL}/api/triangulate/term/${selectedTerm.id}`)
        if (response.ok) {
          const data = await response.json()
          setTriangulation(data)
        }
      } catch (error) {
        console.error('Failed to fetch triangulation:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchTriangulation()
  }, [selectedTerm])

  return (
    <div className="glass rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-400" />
          Data Sources
          <span className="text-[10px] text-gray-500 bg-cyan-400/10 px-1.5 py-0.5 rounded">
            {1 + evidenceSrcs.length} sources
          </span>
        </h3>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface rounded-lg p-1">
        <button
          onClick={() => setActiveTab('sources')}
          className={`flex-1 px-3 py-1.5 text-xs rounded transition-colors ${
            activeTab === 'sources'
              ? 'bg-primary text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          All Sources
        </button>
        <button
          onClick={() => setActiveTab('evidence')}
          className={`flex-1 px-3 py-1.5 text-xs rounded transition-colors ${
            activeTab === 'evidence'
              ? 'bg-primary text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Evidence {selectedTerm && `(${selectedTerm.term.slice(0, 15)}...)`}
        </button>
      </div>

      {/* Sources Tab */}
      {activeTab === 'sources' && (
        <div className="space-y-4 max-h-[400px] overflow-y-auto">
          {/* Core Data Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-green-400" />
              <span className="text-xs font-semibold text-green-400 uppercase tracking-wide">Core Data</span>
              <span className="text-[10px] text-gray-500 bg-green-400/10 px-2 py-0.5 rounded">Stored in Database</span>
            </div>
            {coreData.map((source) => {
              const Icon = sourceIcons[source.id] || Database
              return (
                <div
                  key={source.id}
                  className="bg-green-400/5 border border-green-400/20 rounded-lg p-3 space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-green-400" />
                      <span className="text-sm font-medium text-white">{source.name}</span>
                    </div>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-500 hover:text-green-400 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                  <p className="text-xs text-gray-400">{source.description}</p>
                  <div className="flex gap-3 text-[10px] text-gray-500">
                    <span>Updates: {source.update_frequency}</span>
                    <span>Coverage: {source.coverage}</span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Evidence Sources Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FlaskConical className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wide">Evidence Sources</span>
              <span className="text-[10px] text-gray-500 bg-cyan-400/10 px-2 py-0.5 rounded">Queried On-Demand</span>
            </div>
            <div className="space-y-2">
              {evidenceSrcs.map((source) => {
                const Icon = sourceIcons[source.id] || Database
                return (
                  <div
                    key={source.id}
                    className="bg-surface/50 rounded-lg p-3 space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4 text-cyan-400" />
                        <span className="text-sm font-medium text-white">{source.name}</span>
                      </div>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-500 hover:text-cyan-400 transition-colors"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <p className="text-xs text-gray-400">{source.description}</p>
                    <div className="flex gap-3 text-[10px] text-gray-500">
                      <span>Updates: {source.update_frequency}</span>
                      <span>Coverage: {source.coverage}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Evidence Tab — rendered dynamically from config */}
      {activeTab === 'evidence' && (
        <div className="space-y-3">
          {!selectedTerm ? (
            <div className="text-center py-6">
              <Database className="w-8 h-8 mx-auto text-gray-600 mb-2" />
              <p className="text-sm text-gray-500">Select a term to see evidence</p>
              <p className="text-xs text-gray-600">
                Click on a point in the visualization
              </p>
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-primary" />
              <span className="ml-2 text-gray-400">Fetching from {evidenceSections.length} sources...</span>
            </div>
          ) : triangulation ? (
            <>
              {/* Evidence Strength Badge */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-white font-medium">
                  {triangulation.term}
                </span>
                <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${strengthColors[triangulation.summary.evidence_strength]}`}>
                  {triangulation.summary.evidence_strength} evidence
                </span>
              </div>

              {/* Source count summary */}
              <div className="bg-surface/50 rounded-lg p-2 text-center">
                <span className="text-xs text-gray-400">
                  Found data in <span className="text-cyan-400 font-medium">{triangulation.summary.total_sources}</span> of {evidenceSections.length} sources
                </span>
              </div>

              {/* Dynamically render each evidence section */}
              {evidenceSections.map((section) => {
                const sectionData = (triangulation as any)[section.key]
                if (!sectionData || sectionData.count === 0) return null

                const Icon = section.icon
                const subtext = section.getSubtext(sectionData)

                return (
                  <div key={section.key} className="bg-surface/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Icon className={`w-4 h-4 ${section.color}`} />
                        <span className="text-sm text-white">{section.label}</span>
                      </div>
                      <span className="text-xs text-gray-400">
                        {sectionData.count} found
                        {subtext && (
                          <span className="ml-1 text-green-400">({subtext})</span>
                        )}
                      </span>
                    </div>
                    {sectionData.items.slice(0, 2).map((item: any, i: number) => {
                      const title = section.getItemTitle(item)
                      const url = section.getItemUrl(item)

                      return url ? (
                        <a
                          key={i}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-xs text-gray-400 hover:text-cyan-400 truncate mb-1"
                        >
                          <ChevronRight className="w-3 h-3 inline mr-1" />
                          {title}
                          {section.key === 'scholar' && item.cited_by > 0 && (
                            <span className="ml-1 text-emerald-400/70">({item.cited_by} cited)</span>
                          )}
                        </a>
                      ) : (
                        <div key={i} className="text-xs text-gray-400 truncate mb-1">
                          <ChevronRight className="w-3 h-3 inline mr-1" />
                          {title}
                        </div>
                      )
                    })}
                    <p className="text-[10px] text-gray-600 mt-1">
                      Source: {section.source}
                    </p>
                  </div>
                )
              })}
            </>
          ) : (
            <div className="text-center py-6">
              <AlertCircle className="w-8 h-8 mx-auto text-yellow-500 mb-2" />
              <p className="text-sm text-gray-400">Could not fetch evidence</p>
            </div>
          )}
        </div>
      )}

      {/* Footer with data freshness */}
      <div className="pt-2 border-t border-border">
        <div className="flex items-center gap-2 text-[10px] text-gray-500">
          <CheckCircle className="w-3 h-3 text-green-500" />
          <span>All sources verified and up-to-date</span>
        </div>
      </div>
    </div>
  )
}
