/**
 * API client for the Pediatric Oncology Intelligence backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface FetchOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

async function fetchApi<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options

  const response = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

// Types
export interface Cluster {
  id: number
  name: string
  x: number
  y: number
  z: number
  color: string
  size: number
  termCount: number
}

export interface Term {
  id: number
  term: string
  category: string
  subcategory?: string
  x: number
  y: number
  z: number
  clusterId?: number
}

export interface Post {
  id: number
  title: string
  url?: string
  source: string
  x: number
  y: number
  z: number
  clusterId?: number
}

export interface VisualizationData {
  clusters: Cluster[]
  terms: Term[]
  posts: Post[]
}

export interface TrendPoint {
  date: string
  interest: number
}

export interface RegionData {
  geo_code: string
  name: string
  latitude: number
  longitude: number
  interest: number
  svi_overall?: number
  population?: number
  vulnerability_adjusted_intent?: number
}

export interface TaxonomyCategory {
  name: string
  count: number
  subcategories: { name: string; count: number }[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  response: string
  sources?: Array<{ type: string; count: number }>
  suggested_questions?: string[]
}

export interface DataSource {
  id: number
  geo_code: string
  geo_name: string
  timeframe: string
  data_start_date: string
  data_end_date: string
  fetched_at: string
  term_count: number
  trend_count: number
}

export interface RegionComparison {
  term: string
  regions: Array<{
    geo_code: string
    geo_name: string
    avg_interest: number
    peak_interest: number
    peak_date: string
    trend_direction: string
    data_points: number
  }>
}

export interface TopTermComparison {
  geo_code: string
  geo_name: string
  top_terms: Array<{
    term: string
    category: string
    avg_interest: number
  }>
}

export interface CategoryComparison {
  category: string
  regions: Array<{
    geo_code: string
    geo_name: string
    avg_interest: number
    term_count: number
  }>
}

// API functions
export const api = {
  // Visualization
  getVisualizationData: (params?: { category?: string; clusterId?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.category) searchParams.set('category', params.category)
    if (params?.clusterId) searchParams.set('cluster_id', String(params.clusterId))
    const query = searchParams.toString()
    return fetchApi<VisualizationData>(`/api/clusters/visualization${query ? `?${query}` : ''}`)
  },

  // Clusters
  getClusters: () => fetchApi<Cluster[]>('/api/clusters/'),
  getCluster: (id: number) => fetchApi<Cluster & { terms: Term[]; posts: Post[] }>(`/api/clusters/${id}`),

  // Terms
  getTerms: (params?: { category?: string; search?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.category) searchParams.set('category', params.category)
    if (params?.search) searchParams.set('search', params.search)
    if (params?.limit) searchParams.set('limit', String(params.limit))
    return fetchApi<Term[]>(`/api/terms/?${searchParams.toString()}`)
  },
  getTaxonomy: () => fetchApi<{ categories: TaxonomyCategory[]; total_terms: number }>('/api/terms/taxonomy'),
  getSimilarTerms: (id: number) => fetchApi<Term[]>(`/api/terms/${id}/similar`),

  // Trends
  getTermTrends: (termId: number, geo?: string) => {
    const params = geo ? `?geo_code=${geo}` : ''
    return fetchApi<{ term: string; data: TrendPoint[] }>(`/api/trends/term/${termId}${params}`)
  },
  getClusterTrends: (clusterId: number, geo?: string) => {
    const params = geo ? `?geo_code=${geo}` : ''
    return fetchApi<{ cluster_name: string; data: TrendPoint[] }>(`/api/trends/cluster/${clusterId}${params}`)
  },
  getTopTrending: (days?: number) => {
    const params = days ? `?days=${days}` : ''
    return fetchApi<Array<{ id: number; term: string; category: string; avg_interest: number }>>(`/api/trends/top${params}`)
  },

  // Geography
  getRegions: () => fetchApi<RegionData[]>('/api/geography/regions'),
  getHeatmapData: (params?: { clusterId?: number; termId?: number; category?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.clusterId) searchParams.set('cluster_id', String(params.clusterId))
    if (params?.termId) searchParams.set('term_id', String(params.termId))
    if (params?.category) searchParams.set('category', params.category)
    return fetchApi<RegionData[]>(`/api/geography/heatmap?${searchParams.toString()}`)
  },
  getRegion: (geoCode: string) => fetchApi<RegionData & { top_terms: Term[] }>(`/api/geography/regions/${geoCode}`),

  // Pipeline
  getPipelineStats: () => fetchApi<{
    terms: number
    clusters: number
    trend_data_points: number
    geographic_regions: number
  }>('/api/pipeline/stats'),
  triggerPipeline: (config?: { fetch_trends?: boolean; timeframe?: string; geo?: string }) =>
    fetchApi<{ run_id: number }>('/api/pipeline/run', { method: 'POST', body: config }),

  // Chat
  chat: (message: string, conversationHistory: ChatMessage[] = []) =>
    fetchApi<ChatResponse>('/api/chat/', {
      method: 'POST',
      body: { message, conversation_history: conversationHistory }
    }),
  getChatSuggestions: () =>
    fetchApi<{ suggestions: string[] }>('/api/chat/suggestions'),

  // Region Comparison
  getDataSources: () => fetchApi<DataSource[]>('/api/compare/sources'),
  compareRegions: (term: string, regions: string[]) => {
    const params = new URLSearchParams({ term })
    regions.forEach(r => params.append('regions', r))
    return fetchApi<RegionComparison>(`/api/compare/regions?${params.toString()}`)
  },
  getTopTermsByRegion: (regions: string[], limit?: number) => {
    const params = new URLSearchParams()
    regions.forEach(r => params.append('regions', r))
    if (limit) params.set('limit', String(limit))
    return fetchApi<TopTermComparison[]>(`/api/compare/top-terms?${params.toString()}`)
  },
  getCategoryComparison: (regions: string[]) => {
    const params = new URLSearchParams()
    regions.forEach(r => params.append('regions', r))
    return fetchApi<CategoryComparison[]>(`/api/compare/category-comparison?${params.toString()}`)
  },
}

export default api
