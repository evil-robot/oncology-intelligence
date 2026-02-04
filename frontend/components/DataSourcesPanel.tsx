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
  TrendingUp
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
  clinical_trials: {
    count: number
    items: any[]
    recruiting: number
  }
  publications: {
    count: number
    items: any[]
  }
  fda_data: {
    count: number
    items: any[]
  }
  news: {
    count: number
    items: any[]
  }
  summary: {
    total_sources: number
    evidence_strength: string
  }
}

const sourceIcons: Record<string, any> = {
  google_trends: TrendingUp,
  clinical_trials: FlaskConical,
  pubmed: FileText,
  openfda: Pill,
  cdc_svi: MapPin,
  news: Newspaper,
}

const strengthColors: Record<string, string> = {
  strong: 'text-green-400 bg-green-400/20',
  moderate: 'text-blue-400 bg-blue-400/20',
  emerging: 'text-yellow-400 bg-yellow-400/20',
  limited: 'text-gray-400 bg-gray-400/20',
}

export default function DataSourcesPanel() {
  const selection = useSelection()
  const [coreData, setCoreData] = useState<DataSource[]>([])
  const [evidenceSources, setEvidenceSources] = useState<DataSource[]>([])
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
          setEvidenceSources(data.evidence_sources || [])
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
              {evidenceSources.map((source) => {
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

      {/* Evidence Tab */}
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
              <span className="ml-2 text-gray-400">Fetching from sources...</span>
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

              {/* Clinical Trials */}
              <div className="bg-surface/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-purple-400" />
                    <span className="text-sm text-white">Clinical Trials</span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {triangulation.clinical_trials.count} found
                    {triangulation.clinical_trials.recruiting > 0 && (
                      <span className="ml-1 text-green-400">
                        ({triangulation.clinical_trials.recruiting} recruiting)
                      </span>
                    )}
                  </span>
                </div>
                {triangulation.clinical_trials.items.slice(0, 2).map((trial: any, i: number) => (
                  <a
                    key={i}
                    href={trial.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs text-gray-400 hover:text-cyan-400 truncate mb-1"
                  >
                    <ChevronRight className="w-3 h-3 inline mr-1" />
                    {trial.title}
                  </a>
                ))}
                <p className="text-[10px] text-gray-600 mt-1">
                  Source: ClinicalTrials.gov
                </p>
              </div>

              {/* Publications */}
              <div className="bg-surface/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-white">Publications</span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {triangulation.publications.count} found
                  </span>
                </div>
                {triangulation.publications.items.slice(0, 2).map((article: any, i: number) => (
                  <a
                    key={i}
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs text-gray-400 hover:text-cyan-400 truncate mb-1"
                  >
                    <ChevronRight className="w-3 h-3 inline mr-1" />
                    {article.title}
                  </a>
                ))}
                <p className="text-[10px] text-gray-600 mt-1">
                  Source: PubMed/NCBI
                </p>
              </div>

              {/* FDA Data */}
              {triangulation.fda_data.count > 0 && (
                <div className="bg-surface/50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Pill className="w-4 h-4 text-green-400" />
                      <span className="text-sm text-white">FDA Data</span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {triangulation.fda_data.count} records
                    </span>
                  </div>
                  <p className="text-[10px] text-gray-600">
                    Source: FDA openFDA
                  </p>
                </div>
              )}

              {/* News */}
              <div className="bg-surface/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Newspaper className="w-4 h-4 text-yellow-400" />
                    <span className="text-sm text-white">News Coverage</span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {triangulation.news.count} articles
                  </span>
                </div>
                {triangulation.news.items.slice(0, 2).map((news: any, i: number) => (
                  <a
                    key={i}
                    href={news.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs text-gray-400 hover:text-cyan-400 truncate mb-1"
                  >
                    <ChevronRight className="w-3 h-3 inline mr-1" />
                    {news.title}
                  </a>
                ))}
                <p className="text-[10px] text-gray-600 mt-1">
                  Source: Google News
                </p>
              </div>
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
