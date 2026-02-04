/**
 * Global state management using Zustand.
 */

import { create } from 'zustand'
import type { Cluster, Term, Post } from './api'

interface FilterState {
  category: string | null
  clusterId: number | null
  searchQuery: string
  dateRange: { start: Date; end: Date } | null
  geoCode: string
}

interface SelectionState {
  selectedCluster: Cluster | null
  selectedTerm: Term | null
  hoveredTerm: Term | null
}

interface ViewState {
  cameraPosition: [number, number, number]
  cameraTarget: [number, number, number]
  showLabels: boolean
  showPosts: boolean
  showConnections: boolean
  pointSize: number
}

interface AppState {
  // Data
  clusters: Cluster[]
  terms: Term[]
  posts: Post[]
  isLoading: boolean
  error: string | null

  // Filters
  filters: FilterState
  setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void
  resetFilters: () => void

  // Selection
  selection: SelectionState
  selectCluster: (cluster: Cluster | null) => void
  selectTerm: (term: Term | null) => void
  setHoveredTerm: (term: Term | null) => void

  // View
  view: ViewState
  setView: <K extends keyof ViewState>(key: K, value: ViewState[K]) => void
  focusOnCluster: (cluster: Cluster) => void
  focusOnTerm: (term: Term) => void
  selectAndFocusTerm: (term: Term) => void
  selectAndFocusCluster: (cluster: Cluster) => void
  focusOnCategory: (category: string) => void
  resetCamera: () => void

  // Data loading
  setData: (data: { clusters: Cluster[]; terms: Term[]; posts: Post[] }) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

const initialFilters: FilterState = {
  category: null,
  clusterId: null,
  searchQuery: '',
  dateRange: null,
  geoCode: 'US',
}

const initialSelection: SelectionState = {
  selectedCluster: null,
  selectedTerm: null,
  hoveredTerm: null,
}

const initialView: ViewState = {
  cameraPosition: [0, 0, 15],
  cameraTarget: [0, 0, 0],
  showLabels: true,
  showPosts: true,
  showConnections: false,
  pointSize: 1,
}

export const useStore = create<AppState>((set, get) => ({
  // Data
  clusters: [],
  terms: [],
  posts: [],
  isLoading: false,
  error: null,

  // Filters
  filters: initialFilters,
  setFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    })),
  resetFilters: () => set({ filters: initialFilters }),

  // Selection
  selection: initialSelection,
  selectCluster: (cluster) =>
    set((state) => ({
      selection: { ...state.selection, selectedCluster: cluster, selectedTerm: null },
    })),
  selectTerm: (term) =>
    set((state) => ({
      selection: { ...state.selection, selectedTerm: term },
    })),
  setHoveredTerm: (term) =>
    set((state) => ({
      selection: { ...state.selection, hoveredTerm: term },
    })),

  // View
  view: initialView,
  setView: (key, value) =>
    set((state) => ({
      view: { ...state.view, [key]: value },
    })),
  focusOnCluster: (cluster) =>
    set((state) => ({
      view: {
        ...state.view,
        cameraTarget: [cluster.x, cluster.y, cluster.z],
        cameraPosition: [cluster.x, cluster.y, cluster.z + 5],
      },
    })),
  focusOnTerm: (term) =>
    set((state) => ({
      view: {
        ...state.view,
        cameraTarget: [term.x, term.y, term.z],
        cameraPosition: [term.x, term.y + 1, term.z + 4],
      },
    })),
  selectAndFocusTerm: (term) =>
    set((state) => ({
      selection: { ...state.selection, selectedTerm: term, selectedCluster: null },
      view: {
        ...state.view,
        cameraTarget: [term.x, term.y, term.z],
        cameraPosition: [term.x, term.y + 1, term.z + 4],
      },
    })),
  selectAndFocusCluster: (cluster) =>
    set((state) => ({
      selection: { ...state.selection, selectedCluster: cluster, selectedTerm: null },
      view: {
        ...state.view,
        cameraTarget: [cluster.x, cluster.y, cluster.z],
        cameraPosition: [cluster.x, cluster.y, cluster.z + 5],
      },
    })),
  focusOnCategory: (category) => {
    const state = get()
    const categoryTerms = state.terms.filter(
      (t) => t.category?.toLowerCase() === category.toLowerCase()
    )

    if (categoryTerms.length === 0) return

    // Calculate center of all terms in this category
    const sumX = categoryTerms.reduce((acc, t) => acc + t.x, 0)
    const sumY = categoryTerms.reduce((acc, t) => acc + t.y, 0)
    const sumZ = categoryTerms.reduce((acc, t) => acc + t.z, 0)
    const centerX = sumX / categoryTerms.length
    const centerY = sumY / categoryTerms.length
    const centerZ = sumZ / categoryTerms.length

    // Calculate spread to determine zoom distance
    const maxDist = Math.max(
      ...categoryTerms.map((t) =>
        Math.sqrt(
          Math.pow(t.x - centerX, 2) +
          Math.pow(t.y - centerY, 2) +
          Math.pow(t.z - centerZ, 2)
        )
      )
    )
    const zoomDistance = Math.max(maxDist * 1.5, 5)

    set({
      filters: { ...state.filters, category },
      selection: { ...state.selection, selectedCluster: null, selectedTerm: null },
      view: {
        ...state.view,
        cameraTarget: [centerX, centerY, centerZ],
        cameraPosition: [centerX, centerY + zoomDistance * 0.3, centerZ + zoomDistance],
      },
    })
  },
  resetCamera: () =>
    set((state) => ({
      view: {
        ...state.view,
        cameraPosition: initialView.cameraPosition,
        cameraTarget: initialView.cameraTarget,
      },
    })),

  // Data loading
  setData: (data) => set({ ...data, isLoading: false, error: null }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
}))

// Selectors
export const useFilters = () => useStore((state) => state.filters)
export const useSelection = () => useStore((state) => state.selection)
export const useView = () => useStore((state) => state.view)
export const useClusters = () => useStore((state) => state.clusters)
export const useTerms = () => useStore((state) => state.terms)
export const usePosts = () => useStore((state) => state.posts)
