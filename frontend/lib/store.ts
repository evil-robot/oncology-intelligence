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

interface ComparisonState {
  clusterA: Cluster | null
  clusterB: Cluster | null
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

  // Comparison pair
  comparison: ComparisonState
  setComparisonCluster: (cluster: Cluster) => void
  clearComparison: () => void

  // View
  view: ViewState
  setView: <K extends keyof ViewState>(key: K, value: ViewState[K]) => void
  focusOnCluster: (cluster: Cluster) => void
  focusOnTerm: (term: Term) => void
  selectAndFocusTerm: (term: Term) => void
  selectAndFocusCluster: (cluster: Cluster) => void
  focusOnCategory: (category: string) => void
  focusOnSubcategory: (subcategory: string) => void
  resetCamera: () => void
  resetView: () => void

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

const initialComparison: ComparisonState = {
  clusterA: null,
  clusterB: null,
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

  // Comparison pair
  comparison: initialComparison,
  setComparisonCluster: (cluster) =>
    set((state) => {
      const { clusterA, clusterB } = state.comparison
      // Shared: select cluster for DetailPanel + camera focus
      const selectionAndView = {
        selection: { ...state.selection, selectedCluster: cluster, selectedTerm: null },
        view: {
          ...state.view,
          cameraTarget: [cluster.x || 0, cluster.y || 0, cluster.z || 0] as [number, number, number],
          cameraPosition: [cluster.x || 0, cluster.y || 0, (cluster.z || 0) + 5] as [number, number, number],
        },
      }
      // Click A again → clear comparison
      if (clusterA?.id === cluster.id) {
        return { comparison: initialComparison, ...selectionAndView }
      }
      // Click B again → deselect B, keep A
      if (clusterB?.id === cluster.id) {
        return { comparison: { ...state.comparison, clusterB: null }, ...selectionAndView }
      }
      // No A yet → set A
      if (!clusterA) {
        return { comparison: { clusterA: cluster, clusterB: null }, ...selectionAndView }
      }
      // A exists, clicking different → set/replace B
      return { comparison: { ...state.comparison, clusterB: cluster }, ...selectionAndView }
    }),
  clearComparison: () => set({ comparison: initialComparison }),

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
        cameraTarget: [cluster.x || 0, cluster.y || 0, cluster.z || 0],
        cameraPosition: [cluster.x || 0, cluster.y || 0, (cluster.z || 0) + 5],
      },
    })),
  focusOnTerm: (term) =>
    set((state) => ({
      view: {
        ...state.view,
        cameraTarget: [term.x || 0, term.y || 0, term.z || 0],
        cameraPosition: [term.x || 0, (term.y || 0) + 1, (term.z || 0) + 4],
      },
    })),
  selectAndFocusTerm: (term) =>
    set((state) => ({
      selection: { ...state.selection, selectedTerm: term, selectedCluster: null },
      view: {
        ...state.view,
        cameraTarget: [term.x || 0, term.y || 0, term.z || 0],
        cameraPosition: [term.x || 0, (term.y || 0) + 1, (term.z || 0) + 4],
      },
    })),
  selectAndFocusCluster: (cluster) =>
    set((state) => ({
      selection: { ...state.selection, selectedCluster: cluster, selectedTerm: null },
      filters: { ...state.filters, clusterId: cluster.id },
      view: {
        ...state.view,
        cameraTarget: [cluster.x || 0, cluster.y || 0, cluster.z || 0],
        cameraPosition: [cluster.x || 0, cluster.y || 0, (cluster.z || 0) + 5],
      },
    })),
  focusOnCategory: (category) => {
    const state = get()

    // Try exact match first, then lowercase match
    let categoryTerms = state.terms.filter(
      (t) => t.category === category
    )

    // Fallback to case-insensitive
    if (categoryTerms.length === 0) {
      categoryTerms = state.terms.filter(
        (t) => t.category?.toLowerCase() === category.toLowerCase()
      )
    }

    if (categoryTerms.length === 0) {
      // Just set the filter even if no terms found
      set({
        filters: { ...state.filters, category },
      })
      return
    }

    // Filter out terms without valid coordinates
    const termsWithCoords = categoryTerms.filter(
      (t) => t.x !== 0 || t.y !== 0 || t.z !== 0
    )

    // Use terms with coords, or fall back to all terms
    const validTerms = termsWithCoords.length > 0 ? termsWithCoords : categoryTerms

    // Calculate center of all terms in this category
    const sumX = validTerms.reduce((acc, t) => acc + (t.x || 0), 0)
    const sumY = validTerms.reduce((acc, t) => acc + (t.y || 0), 0)
    const sumZ = validTerms.reduce((acc, t) => acc + (t.z || 0), 0)
    const centerX = sumX / validTerms.length
    const centerY = sumY / validTerms.length
    const centerZ = sumZ / validTerms.length

    // Calculate spread to determine zoom distance
    const distances = validTerms.map((t) =>
      Math.sqrt(
        Math.pow((t.x || 0) - centerX, 2) +
        Math.pow((t.y || 0) - centerY, 2) +
        Math.pow((t.z || 0) - centerZ, 2)
      )
    )
    const maxDist = distances.length > 0 ? Math.max(...distances) : 5
    const zoomDistance = Math.max(maxDist * 1.5, 5)

    // Add small unique offset based on category name hash to ensure different positions
    const categoryHash = category.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
    const offsetX = (categoryHash % 10) * 0.3 - 1.5
    const offsetY = ((categoryHash * 7) % 10) * 0.3 - 1.5

    set({
      filters: { ...state.filters, category },
      selection: { ...state.selection, selectedCluster: null, selectedTerm: null },
      view: {
        ...state.view,
        cameraTarget: [centerX, centerY, centerZ],
        cameraPosition: [centerX + offsetX, centerY + zoomDistance * 0.3 + offsetY, centerZ + zoomDistance],
      },
    })
  },
  focusOnSubcategory: (subcategory) => {
    const state = get()
    const displayName = subcategory.replace(/_/g, ' ')

    // Find terms matching this subcategory
    let subTerms = state.terms.filter(
      (t) => t.subcategory === subcategory
    )
    if (subTerms.length === 0) {
      subTerms = state.terms.filter(
        (t) => t.subcategory?.toLowerCase() === subcategory.toLowerCase()
      )
    }

    if (subTerms.length === 0) {
      // No matching terms — just set search query so the user sees the filter
      set({
        filters: { ...state.filters, searchQuery: displayName },
      })
      return
    }

    const termsWithCoords = subTerms.filter(
      (t) => t.x !== 0 || t.y !== 0 || t.z !== 0
    )
    const validTerms = termsWithCoords.length > 0 ? termsWithCoords : subTerms

    const sumX = validTerms.reduce((acc, t) => acc + (t.x || 0), 0)
    const sumY = validTerms.reduce((acc, t) => acc + (t.y || 0), 0)
    const sumZ = validTerms.reduce((acc, t) => acc + (t.z || 0), 0)
    const centerX = sumX / validTerms.length
    const centerY = sumY / validTerms.length
    const centerZ = sumZ / validTerms.length

    const distances = validTerms.map((t) =>
      Math.sqrt(
        Math.pow((t.x || 0) - centerX, 2) +
        Math.pow((t.y || 0) - centerY, 2) +
        Math.pow((t.z || 0) - centerZ, 2)
      )
    )
    const maxDist = distances.length > 0 ? Math.max(...distances) : 3
    const zoomDistance = Math.max(maxDist * 1.5, 3)

    const hash = subcategory.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
    const offsetX = (hash % 10) * 0.3 - 1.5
    const offsetY = ((hash * 7) % 10) * 0.3 - 1.5

    set({
      filters: { ...state.filters, searchQuery: displayName },
      selection: { ...state.selection, selectedCluster: null, selectedTerm: null },
      view: {
        ...state.view,
        cameraTarget: [centerX, centerY, centerZ],
        cameraPosition: [centerX + offsetX, centerY + zoomDistance * 0.3 + offsetY, centerZ + zoomDistance],
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
  resetView: () =>
    set((state) => ({
      selection: initialSelection,
      comparison: initialComparison,
      filters: { ...initialFilters, geoCode: state.filters.geoCode },
      view: { ...state.view, cameraPosition: initialView.cameraPosition, cameraTarget: initialView.cameraTarget },
    })),

  // Data loading
  setData: (data) => set({ ...data, isLoading: false, error: null }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
}))

// Selectors
export const useFilters = () => useStore((state) => state.filters)
export const useSelection = () => useStore((state) => state.selection)
export const useComparison = () => useStore((state) => state.comparison)
export const useView = () => useStore((state) => state.view)
export const useClusters = () => useStore((state) => state.clusters)
export const useTerms = () => useStore((state) => state.terms)
export const usePosts = () => useStore((state) => state.posts)
