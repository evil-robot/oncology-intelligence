'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import SuperTruthLogo from '@/components/SuperTruthLogo'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// --- Types ---

interface StoryCard {
  id: number
  epic: string
  feature: string
  user_story: string
  priority: string
  story_points: number
  status: string
  assigned_to: string
  dependency: string
  sprint_id: number | null
  sprint_name: string | null
  demo_critical: boolean
  acceptance_criteria: string
  notes: string
  sort_order: number
  created_at: string
  updated_at: string
}

interface SprintOption {
  id: number
  sprint_id: string
  theme: string
  status: string
}

interface BoardData {
  columns: Record<string, StoryCard[]>
  total_points: number
  done_points: number
  story_count: number
}

const COLUMN_CONFIG = [
  { key: 'backlog', label: 'Backlog', color: 'gray', dot: 'bg-gray-500' },
  { key: 'ready', label: 'Ready', color: 'blue', dot: 'bg-blue-500' },
  { key: 'in_progress', label: 'In Progress', color: 'violet', dot: 'bg-violet-500' },
  { key: 'review', label: 'Review', color: 'amber', dot: 'bg-amber-500' },
  { key: 'done', label: 'Done', color: 'emerald', dot: 'bg-emerald-500' },
]

const COLUMN_BORDER: Record<string, string> = {
  backlog: 'border-gray-500/30',
  ready: 'border-blue-500/30',
  in_progress: 'border-violet-500/30',
  review: 'border-amber-500/30',
  done: 'border-emerald-500/30',
}

const COLUMN_BG: Record<string, string> = {
  backlog: 'bg-gray-500/5',
  ready: 'bg-blue-500/5',
  in_progress: 'bg-violet-500/5',
  review: 'bg-amber-500/5',
  done: 'bg-emerald-500/5',
}

const PRIORITY_COLORS: Record<string, string> = {
  Critical: 'bg-red-500',
  High: 'bg-orange-500',
  Medium: 'bg-yellow-500',
  Low: 'bg-gray-400',
}

const PRIORITY_BADGE: Record<string, string> = {
  Critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  High: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  Medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  Low: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
}

const STATUS_TRANSITIONS: Record<string, string[]> = {
  backlog: ['ready', 'archived'],
  ready: ['backlog', 'in_progress', 'archived'],
  in_progress: ['ready', 'review', 'archived'],
  review: ['in_progress', 'done', 'archived'],
  done: ['review', 'archived'],
}

export default function BoardPage() {
  const [board, setBoard] = useState<BoardData | null>(null)
  const [sprints, setSprints] = useState<SprintOption[]>([])
  const [selectedSprint, setSelectedSprint] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Filters
  const [filterPriority, setFilterPriority] = useState('')
  const [filterAssignee, setFilterAssignee] = useState('')
  const [filterEpic, setFilterEpic] = useState('')
  const [searchText, setSearchText] = useState('')

  // Detail drawer
  const [selectedStory, setSelectedStory] = useState<StoryCard | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  // Unique values for filter dropdowns
  const allStories = board ? Object.values(board.columns).flat() : []
  const uniqueAssignees = Array.from(new Set(allStories.map(s => s.assigned_to).filter(Boolean)))
  const uniqueEpics = Array.from(new Set(allStories.map(s => s.epic).filter(Boolean)))

  const fetchBoard = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (selectedSprint !== null) params.set('sprint_id', String(selectedSprint))
      if (filterPriority) params.set('priority', filterPriority)
      if (filterAssignee) params.set('assigned_to', filterAssignee)
      if (filterEpic) params.set('epic', filterEpic)
      if (searchText) params.set('search', searchText)

      const res = await fetch(`${API_URL}/api/stories/board?${params}`)
      if (!res.ok) throw new Error(`Board API error ${res.status}`)
      const data = await res.json()
      setBoard(data)
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load board')
    } finally {
      setLoading(false)
    }
  }, [selectedSprint, filterPriority, filterAssignee, filterEpic, searchText])

  const fetchSprints = async () => {
    try {
      const res = await fetch(`${API_URL}/api/stories/sprints`)
      if (!res.ok) return
      const data = await res.json()
      setSprints(data)
    } catch { /* ignore */ }
  }

  useEffect(() => { fetchSprints() }, [])
  useEffect(() => { fetchBoard() }, [fetchBoard])

  const moveStatus = async (storyId: number, newStatus: string) => {
    try {
      const res = await fetch(`${API_URL}/api/stories/${storyId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Status update failed (${res.status})`)
      }
      await fetchBoard()
      // Update drawer if open
      if (selectedStory?.id === storyId) {
        const updated = await res.json().catch(() => null)
        if (updated) setSelectedStory(updated)
        else {
          const fresh = await fetch(`${API_URL}/api/stories/${storyId}`).then(r => r.json())
          setSelectedStory(fresh)
        }
      }
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to move story')
    }
  }

  const saveStory = async (updates: Record<string, unknown>) => {
    if (!selectedStory) return
    setSaving(true)
    try {
      const res = await fetch(`${API_URL}/api/stories/${selectedStory.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (!res.ok) throw new Error('Save failed')
      const updated = await res.json()
      setSelectedStory(updated)
      await fetchBoard()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const archiveStory = async () => {
    if (!selectedStory || !confirm('Archive this story?')) return
    try {
      await fetch(`${API_URL}/api/stories/${selectedStory.id}`, { method: 'DELETE' })
      setDrawerOpen(false)
      setSelectedStory(null)
      await fetchBoard()
    } catch { /* ignore */ }
  }

  const openDrawer = async (story: StoryCard) => {
    // Fetch fresh data
    try {
      const res = await fetch(`${API_URL}/api/stories/${story.id}`)
      if (res.ok) {
        const fresh = await res.json()
        setSelectedStory(fresh)
      } else {
        setSelectedStory(story)
      }
    } catch {
      setSelectedStory(story)
    }
    setDrawerOpen(true)
  }

  const progressPct = board && board.total_points > 0
    ? Math.round((board.done_points / board.total_points) * 100)
    : 0

  return (
    <div className="min-h-screen bg-[#06060b] text-white">
      {/* Header */}
      <header className="border-b border-white/5 backdrop-blur-xl bg-black/30 sticky top-0 z-30">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <SuperTruthLogo className="h-6 w-auto" />
            <div className="h-5 w-px bg-white/10" />
            <div className="flex items-center gap-2">
              <div className="px-2 py-0.5 bg-violet-500/15 border border-violet-500/25 rounded-md">
                <span className="text-violet-400 text-[10px] font-bold tracking-[0.15em]">VIOLET</span>
              </div>
              <span className="text-white/90 font-semibold text-sm">Story Board</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a href="/story-builder" className="text-xs text-violet-400 hover:text-white transition-colors border border-violet-500/20 rounded-md px-3 py-1.5 hover:border-violet-500/40">
              + New Story
            </a>
            <a href="/" className="text-xs text-gray-500 hover:text-white transition-colors border border-white/10 rounded-md px-3 py-1.5 hover:border-white/20">
              Dashboard
            </a>
          </div>
        </div>
      </header>

      {/* Board Header: Sprint selector + progress */}
      <div className="max-w-[1600px] mx-auto px-6 py-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <select
              value={selectedSprint ?? ''}
              onChange={(e) => setSelectedSprint(e.target.value ? Number(e.target.value) : null)}
              className="bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500/50 appearance-none cursor-pointer min-w-[180px]"
            >
              <option value="">All Sprints</option>
              {sprints.map(s => (
                <option key={s.id} value={s.id}>{s.sprint_id}{s.theme ? ` — ${s.theme}` : ''}</option>
              ))}
            </select>

            {board && (
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">{board.story_count} stories</span>
                <div className="w-32 h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-violet-500 to-emerald-500 rounded-full transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400">
                  {board.done_points}/{board.total_points} pts
                  <span className="text-gray-600 ml-1">({progressPct}%)</span>
                </span>
              </div>
            )}
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search..."
              className="bg-white/[0.03] border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white w-36 focus:outline-none focus:border-violet-500/50 placeholder-gray-600"
            />
            <FilterSelect value={filterPriority} onChange={setFilterPriority}
              options={['Critical', 'High', 'Medium', 'Low']} placeholder="Priority" />
            <FilterSelect value={filterAssignee} onChange={setFilterAssignee}
              options={uniqueAssignees} placeholder="Assignee" />
            <FilterSelect value={filterEpic} onChange={setFilterEpic}
              options={uniqueEpics} placeholder="Epic" />
            {(filterPriority || filterAssignee || filterEpic || searchText) && (
              <button
                onClick={() => { setFilterPriority(''); setFilterAssignee(''); setFilterEpic(''); setSearchText('') }}
                className="text-[10px] text-gray-500 hover:text-white px-2 py-1.5 border border-white/5 rounded-lg hover:border-white/20 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Board */}
      <div className="max-w-[1600px] mx-auto px-6 pb-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin h-6 w-6 border-2 border-violet-500 border-t-transparent rounded-full" />
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <p className="text-red-400 text-sm">{error}</p>
            <button onClick={fetchBoard} className="mt-4 text-xs text-violet-400 hover:text-white">Retry</button>
          </div>
        ) : board ? (
          <div className="grid grid-cols-5 gap-4 min-h-[calc(100vh-180px)]">
            {COLUMN_CONFIG.map(col => (
              <BoardColumn
                key={col.key}
                config={col}
                stories={board.columns[col.key] || []}
                onCardClick={openDrawer}
                onStatusChange={moveStatus}
              />
            ))}
          </div>
        ) : null}
      </div>

      {/* Detail Drawer */}
      {drawerOpen && selectedStory && (
        <StoryDetailDrawer
          story={selectedStory}
          onClose={() => { setDrawerOpen(false); setSelectedStory(null) }}
          onSave={saveStory}
          onStatusChange={moveStatus}
          onArchive={archiveStory}
          saving={saving}
          sprints={sprints}
        />
      )}
    </div>
  )
}

// --- Sub-components ---

function FilterSelect({ value, onChange, options, placeholder }: {
  value: string; onChange: (v: string) => void; options: string[]; placeholder: string
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-white/[0.03] border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-violet-500/50 appearance-none cursor-pointer"
    >
      <option value="">{placeholder}</option>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}

function BoardColumn({ config, stories, onCardClick, onStatusChange }: {
  config: typeof COLUMN_CONFIG[0]
  stories: StoryCard[]
  onCardClick: (s: StoryCard) => void
  onStatusChange: (id: number, status: string) => void
}) {
  const totalPoints = stories.reduce((sum, s) => sum + (s.story_points || 0), 0)

  return (
    <div className={`rounded-xl border ${COLUMN_BORDER[config.key]} ${COLUMN_BG[config.key]} flex flex-col`}>
      {/* Column header */}
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${config.dot}`} />
          <span className="text-sm font-medium text-white/80">{config.label}</span>
          <span className="text-[10px] text-gray-600 bg-white/5 rounded-full px-1.5 py-0.5">{stories.length}</span>
        </div>
        <span className="text-[10px] text-gray-600">{totalPoints} pts</span>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-[200px]">
        {stories.map(story => (
          <Card key={story.id} story={story} onClick={() => onCardClick(story)} />
        ))}
        {stories.length === 0 && (
          <div className="flex items-center justify-center h-20 text-gray-700 text-xs">
            No stories
          </div>
        )}
      </div>
    </div>
  )
}

function Card({ story, onClick }: { story: StoryCard; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 rounded-lg bg-white/[0.03] border border-white/[0.06] hover:border-white/[0.12] hover:bg-white/[0.05] transition-all group cursor-pointer"
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 min-w-0">
          <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${PRIORITY_COLORS[story.priority] || 'bg-gray-400'}`} />
          <span className="text-xs font-medium text-white/90 truncate">{story.feature}</span>
        </div>
        <span className="text-[10px] bg-violet-500/10 text-violet-400 border border-violet-500/20 rounded px-1.5 py-0.5 flex-shrink-0 font-bold">
          {story.story_points}
        </span>
      </div>
      <p className="text-[11px] text-gray-500 truncate">{story.epic}</p>
      {story.assigned_to && (
        <div className="mt-2 flex items-center gap-1.5">
          <div className="w-4 h-4 rounded-full bg-white/10 flex items-center justify-center text-[8px] text-gray-400 font-bold">
            {story.assigned_to.charAt(0).toUpperCase()}
          </div>
          <span className="text-[10px] text-gray-600">{story.assigned_to}</span>
        </div>
      )}
      {story.demo_critical && (
        <div className="mt-1.5">
          <span className="text-[9px] bg-pink-500/10 text-pink-400 border border-pink-500/20 rounded px-1.5 py-0.5">
            Demo
          </span>
        </div>
      )}
    </button>
  )
}

function StoryDetailDrawer({ story, onClose, onSave, onStatusChange, onArchive, saving, sprints }: {
  story: StoryCard
  onClose: () => void
  onSave: (updates: Record<string, unknown>) => void
  onStatusChange: (id: number, status: string) => void
  onArchive: () => void
  saving: boolean
  sprints: SprintOption[]
}) {
  const [edit, setEdit] = useState({ ...story })
  const drawerRef = useRef<HTMLDivElement>(null)

  // Sync when story changes from parent
  useEffect(() => { setEdit({ ...story }) }, [story])

  const hasChanges = JSON.stringify(edit) !== JSON.stringify(story)

  const handleSave = () => {
    const updates: Record<string, unknown> = {}
    const fields: (keyof StoryCard)[] = ['epic', 'feature', 'user_story', 'priority', 'story_points', 'assigned_to', 'dependency', 'demo_critical', 'acceptance_criteria', 'notes']
    for (const f of fields) {
      if (edit[f] !== story[f]) updates[f] = edit[f]
    }
    if (Object.keys(updates).length > 0) onSave(updates)
  }

  const transitions = STATUS_TRANSITIONS[story.status] || []

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* Drawer */}
      <div ref={drawerRef} className="fixed top-0 right-0 h-full w-full max-w-lg bg-[#0a0a12] border-l border-white/5 z-50 overflow-y-auto shadow-2xl animate-slide-in">
        {/* Header */}
        <div className="sticky top-0 bg-[#0a0a12]/95 backdrop-blur-sm border-b border-white/5 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${PRIORITY_COLORS[story.priority] || 'bg-gray-400'}`} />
            <span className="text-sm font-medium text-white/90">Story #{story.id}</span>
            <span className={`text-[10px] px-2 py-0.5 rounded border ${PRIORITY_BADGE[story.priority] || ''}`}>
              {story.priority}
            </span>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Status transitions */}
          <div>
            <label className="block text-[10px] text-gray-500 uppercase tracking-[0.2em] mb-2 font-medium">Status</label>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white/70">
                {story.status.replace('_', ' ')}
              </span>
              <svg className="w-3 h-3 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              {transitions.filter(t => t !== 'archived').map(t => (
                <button
                  key={t}
                  onClick={() => onStatusChange(story.id, t)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-white/10 hover:border-violet-500/30 hover:bg-violet-500/5 text-gray-400 hover:text-violet-400 transition-all"
                >
                  {t.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Editable fields */}
          <DrawerField label="Epic" value={edit.epic} onChange={(v) => setEdit(e => ({ ...e, epic: v }))} />
          <DrawerField label="Feature" value={edit.feature} onChange={(v) => setEdit(e => ({ ...e, feature: v }))} />
          <DrawerField label="User Story" value={edit.user_story} onChange={(v) => setEdit(e => ({ ...e, user_story: v }))} multiline />

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[10px] text-gray-500 uppercase tracking-[0.2em] mb-2 font-medium">Priority</label>
              <select
                value={edit.priority}
                onChange={(e) => setEdit(p => ({ ...p, priority: e.target.value }))}
                className="w-full bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500/50 appearance-none"
              >
                {['Critical', 'High', 'Medium', 'Low'].map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-gray-500 uppercase tracking-[0.2em] mb-2 font-medium">Story Points</label>
              <select
                value={edit.story_points}
                onChange={(e) => setEdit(p => ({ ...p, story_points: Number(e.target.value) }))}
                className="w-full bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500/50 appearance-none"
              >
                {[1, 2, 3, 5, 8, 13].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <DrawerField label="Assigned To" value={edit.assigned_to} onChange={(v) => setEdit(e => ({ ...e, assigned_to: v }))} />
            <div>
              <label className="block text-[10px] text-gray-500 uppercase tracking-[0.2em] mb-2 font-medium">Demo Critical</label>
              <button
                onClick={() => setEdit(e => ({ ...e, demo_critical: !e.demo_critical }))}
                className={`px-4 py-2 rounded-lg text-xs font-medium border transition-all ${
                  edit.demo_critical
                    ? 'bg-pink-500/10 text-pink-400 border-pink-500/30'
                    : 'bg-white/[0.03] text-gray-500 border-white/10'
                }`}
              >
                {edit.demo_critical ? 'Yes' : 'No'}
              </button>
            </div>
          </div>

          <DrawerField label="Acceptance Criteria" value={edit.acceptance_criteria} onChange={(v) => setEdit(e => ({ ...e, acceptance_criteria: v }))} multiline rows={5} />
          <DrawerField label="Dependencies" value={edit.dependency} onChange={(v) => setEdit(e => ({ ...e, dependency: v }))} />
          <DrawerField label="Notes" value={edit.notes} onChange={(v) => setEdit(e => ({ ...e, notes: v }))} multiline rows={3} />

          {/* Sprint info */}
          {story.sprint_name && (
            <div>
              <label className="block text-[10px] text-gray-500 uppercase tracking-[0.2em] mb-1 font-medium">Sprint</label>
              <p className="text-sm text-violet-400">{story.sprint_name}</p>
            </div>
          )}

          {/* Meta */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/5 text-[10px] text-gray-600">
            <div>Created: {story.created_at ? new Date(story.created_at).toLocaleDateString() : '—'}</div>
            <div>Updated: {story.updated_at ? new Date(story.updated_at).toLocaleDateString() : '—'}</div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-white/5">
            <button
              onClick={onArchive}
              className="text-xs text-red-400/60 hover:text-red-400 transition-colors"
            >
              Archive
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges || saving}
              className="px-6 py-2 bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-500 hover:to-violet-400 disabled:from-gray-800 disabled:to-gray-800 disabled:text-gray-600 rounded-lg font-medium text-sm shadow-lg shadow-violet-600/20 disabled:shadow-none transition-all"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .animate-slide-in {
          animation: slideIn 0.2s ease-out;
        }
      `}</style>
    </>
  )
}

function DrawerField({ label, value, onChange, multiline, rows }: {
  label: string; value: string; onChange: (v: string) => void; multiline?: boolean; rows?: number
}) {
  const baseClass = "w-full bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 placeholder-gray-600 transition-all"

  return (
    <div>
      <label className="block text-[10px] text-gray-500 uppercase tracking-[0.2em] mb-2 font-medium">{label}</label>
      {multiline ? (
        <textarea value={value || ''} onChange={(e) => onChange(e.target.value)} rows={rows || 3} className={baseClass + ' resize-none'} />
      ) : (
        <input type="text" value={value || ''} onChange={(e) => onChange(e.target.value)} className={baseClass} />
      )}
    </div>
  )
}
