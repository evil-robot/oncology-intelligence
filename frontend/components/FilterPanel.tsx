'use client'

import { useState, useEffect, useMemo } from 'react'
import { Search, Filter, X, ChevronDown, MapPin, MousePointerClick } from 'lucide-react'
import { useStore, useFilters, useTerms, useSelection } from '@/lib/store'
import api, { TaxonomyCategory, Term } from '@/lib/api'

export default function FilterPanel() {
  const filters = useFilters()
  const allTerms = useTerms()
  const selection = useSelection()
  const setFilter = useStore((s) => s.setFilter)
  const resetFilters = useStore((s) => s.resetFilters)
  const selectAndFocusTerm = useStore((s) => s.selectAndFocusTerm)
  const focusOnCategory = useStore((s) => s.focusOnCategory)
  const [taxonomy, setTaxonomy] = useState<TaxonomyCategory[]>([])
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)

  // Calculate filtered terms
  const filteredTerms = useMemo(() => {
    let filtered = allTerms

    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase()
      filtered = filtered.filter((term) =>
        term.term.toLowerCase().includes(query) ||
        (term.category && term.category.toLowerCase().includes(query))
      )
    }

    if (filters.category) {
      filtered = filtered.filter((term) =>
        term.category?.toLowerCase() === filters.category?.toLowerCase()
      )
    }

    return filtered
  }, [allTerms, filters.searchQuery, filters.category])

  useEffect(() => {
    api.getTaxonomy().then((data) => setTaxonomy(data.categories)).catch(console.error)
  }, [])

  // Expanded category colors for oncology and rare diseases
  const categoryColors: Record<string, string> = {
    // Oncology
    pediatric_oncology: 'bg-blue-500',
    adult_oncology: 'bg-indigo-500',

    // Treatment
    treatment: 'bg-green-500',

    // Clinical Trials
    clinical_trials: 'bg-cyan-500',

    // Rare Diseases
    rare_genetic: 'bg-purple-500',
    rare_neurological: 'bg-pink-500',
    rare_autoimmune: 'bg-rose-500',
    rare_pulmonary: 'bg-sky-500',
    rare_metabolic: 'bg-amber-500',
    rare_immune: 'bg-orange-500',
    rare_cancer: 'bg-red-500',

    // Symptoms & Diagnosis
    symptoms: 'bg-yellow-500',
    diagnosis: 'bg-lime-500',

    // Caregiver & Support
    caregiver: 'bg-orange-400',
    support: 'bg-teal-500',

    // Survivorship
    survivorship: 'bg-emerald-500',

    // Costs & Financial
    costs: 'bg-slate-500',

    // Emerging & Integrative
    emerging: 'bg-violet-500',
    integrative: 'bg-fuchsia-500',

    // Prevention
    prevention: 'bg-green-400',
  }

  const handleTermClick = (term: Term) => {
    selectAndFocusTerm(term)
  }

  return (
    <div className="glass rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Filter className="w-4 h-4" />
          Filters
        </h3>
        {(filters.category || filters.searchQuery) && (
          <button
            onClick={resetFilters}
            className="text-xs text-gray-400 hover:text-white flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            Clear
          </button>
        )}
      </div>

      {/* Search */}
      <div className="space-y-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search terms..."
            value={filters.searchQuery}
            onChange={(e) => setFilter('searchQuery', e.target.value)}
            className="w-full bg-surface border border-border rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-primary"
          />
        </div>

        {/* Search Results */}
        {filters.searchQuery && filteredTerms.length > 0 && (
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <p className="text-xs text-primary flex items-center gap-1">
                <MousePointerClick className="w-3 h-3" />
                {filteredTerms.length} results - click to focus
              </p>
            </div>
            <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
              {filteredTerms.slice(0, 20).map((term) => (
                <button
                  key={term.id}
                  onClick={() => handleTermClick(term)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                    selection.selectedTerm?.id === term.id
                      ? 'bg-primary/30 text-white ring-1 ring-primary'
                      : 'bg-surface/50 hover:bg-surface text-gray-300 hover:text-white'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate">{term.term}</span>
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ml-2 ${categoryColors[term.category] || 'bg-gray-500'}`} />
                  </div>
                  {term.category && (
                    <p className="text-xs text-gray-500 capitalize mt-0.5">{term.category.replace('_', ' ')}</p>
                  )}
                </button>
              ))}
              {filteredTerms.length > 20 && (
                <p className="text-xs text-gray-500 text-center py-2">
                  +{filteredTerms.length - 20} more results
                </p>
              )}
            </div>
          </div>
        )}

        {filters.searchQuery && filteredTerms.length === 0 && (
          <p className="text-xs text-gray-500">No matching terms found</p>
        )}
      </div>

      {/* Categories */}
      <div className="space-y-1">
        <p className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1">
          <MousePointerClick className="w-3 h-3" />
          Categories - click to zoom
        </p>
        {taxonomy.map((cat) => (
          <div key={cat.name}>
            <button
              onClick={() => {
                if (filters.category === cat.name) {
                  // Clicking same category - clear filter and reset view
                  setFilter('category', null)
                  setExpandedCategory(null)
                } else {
                  // Focus on this category - zoom camera and set filter
                  focusOnCategory(cat.name)
                  setExpandedCategory(cat.name)
                }
              }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all ${
                filters.category === cat.name
                  ? 'bg-primary/20 text-primary ring-1 ring-primary/50'
                  : 'hover:bg-surface text-gray-300 hover:text-white'
              }`}
            >
              <span className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${categoryColors[cat.name] || 'bg-gray-500'}`} />
                <span className="capitalize">{cat.name.replace(/_/g, ' ')}</span>
              </span>
              <span className="flex items-center gap-2">
                <span className="text-xs text-gray-500">{cat.count}</span>
                <ChevronDown
                  className={`w-4 h-4 transition-transform ${
                    expandedCategory === cat.name ? 'rotate-180' : ''
                  }`}
                />
              </span>
            </button>

            {/* Expanded subcategories with terms */}
            {expandedCategory === cat.name && (
              <div className="ml-4 mt-1 space-y-1 max-h-40 overflow-y-auto">
                {cat.subcategories.length > 0 ? (
                  cat.subcategories.map((sub) => (
                    <button
                      key={sub.name}
                      className="w-full text-left px-3 py-1 text-xs text-gray-400 hover:text-white hover:bg-surface/50 rounded transition-colors"
                    >
                      {sub.name.replace(/_/g, ' ')} ({sub.count})
                    </button>
                  ))
                ) : (
                  <p className="px-3 py-1 text-xs text-gray-500 italic">
                    {cat.count} terms in this category
                  </p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Geography */}
      <div className="space-y-2">
        <p className="text-xs text-gray-500 uppercase tracking-wide flex items-center gap-1">
          <MapPin className="w-3 h-3" />
          Geography (US Only)
        </p>
        <select
          value={filters.geoCode}
          onChange={(e) => setFilter('geoCode', e.target.value)}
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
        >
          <option value="US">🇺🇸 All United States</option>
          <optgroup label="States">
            <option value="US-CA">California</option>
            <option value="US-TX">Texas</option>
            <option value="US-NY">New York</option>
            <option value="US-FL">Florida</option>
            <option value="US-IL">Illinois</option>
            <option value="US-PA">Pennsylvania</option>
            <option value="US-OH">Ohio</option>
            <option value="US-GA">Georgia</option>
            <option value="US-NC">North Carolina</option>
            <option value="US-MI">Michigan</option>
            <option value="US-AZ">Arizona</option>
            <option value="US-WA">Washington</option>
            <option value="US-MA">Massachusetts</option>
            <option value="US-CO">Colorado</option>
            <option value="US-TN">Tennessee</option>
          </optgroup>
        </select>
      </div>
    </div>
  )
}
