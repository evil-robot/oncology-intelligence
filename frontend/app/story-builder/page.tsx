'use client'

import { useState, useEffect, useRef } from 'react'
import SuperTruthLogo from '@/components/SuperTruthLogo'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface SheetContext {
  epics: string[]
  sprints: { id: string; theme: string; start: string; end: string; version: string; status: string }[]
  features: string[]
  assignees: string[]
}

interface StoryDraft {
  epic: string
  feature: string
  user_story: string
  priority: string
  story_points: number
  assigned_to: string
  dependency: string
  sprint: string
  demo_critical: string
  acceptance_criteria: string
  notes: string
}

const EMPTY_DRAFT: StoryDraft = {
  epic: '',
  feature: '',
  user_story: '',
  priority: 'Medium',
  story_points: 3,
  assigned_to: '',
  dependency: 'None',
  sprint: '',
  demo_critical: 'No',
  acceptance_criteria: '',
  notes: '',
}

const STEPS = [
  { key: 'idea', label: 'Ideate', icon: '01' },
  { key: 'story', label: 'Shape', icon: '02' },
  { key: 'criteria', label: 'Define', icon: '03' },
  { key: 'review', label: 'Ship', icon: '04' },
]

// Animated background particles
function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number
    const particles: { x: number; y: number; vx: number; vy: number; r: number; a: number }[] = []

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // Create particles
    for (let i = 0; i < 60; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 2 + 0.5,
        a: Math.random() * 0.3 + 0.05,
      })
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 150) {
            ctx.beginPath()
            ctx.strokeStyle = `rgba(99, 102, 241, ${0.06 * (1 - dist / 150)})`
            ctx.lineWidth = 0.5
            ctx.moveTo(particles[i].x, particles[i].y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.stroke()
          }
        }
      }

      // Draw particles
      particles.forEach(p => {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1

        ctx.beginPath()
        ctx.fillStyle = `rgba(139, 92, 246, ${p.a})`
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fill()
      })

      animId = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none" />
}

// Pulsing AI indicator
function AIPulse() {
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-violet-500" />
    </span>
  )
}

export default function StoryBuilderPage() {
  const [step, setStep] = useState(0)
  const [draft, setDraft] = useState<StoryDraft>({ ...EMPTY_DRAFT })
  const [ideaText, setIdeaText] = useState('')
  const [context, setContext] = useState<SheetContext | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null)
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    fetch(`${API_URL}/api/stories/context`)
      .then(r => r.json())
      .then(setContext)
      .catch(() => setContext({ epics: [], sprints: [], features: [], assignees: ['JAS Bots', 'Dustin', 'JAS'] }))
  }, [])

  const callAssist = async (stepKey: string, inputText: string) => {
    setAiLoading(true)
    setAiSuggestion(null)
    try {
      const res = await fetch(`${API_URL}/api/stories/assist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: stepKey, input_text: inputText, context: draft }),
      })
      const data = await res.json()
      if (data.structured) {
        if (stepKey === 'idea') {
          setDraft(prev => ({ ...prev, epic: data.structured.epic || prev.epic, feature: data.structured.feature || prev.feature, user_story: data.structured.user_story || prev.user_story }))
        } else if (stepKey === 'story') {
          setDraft(prev => ({ ...prev, user_story: data.structured.user_story || prev.user_story, priority: data.structured.priority || prev.priority, story_points: data.structured.story_points || prev.story_points }))
        } else if (stepKey === 'criteria') {
          setDraft(prev => ({ ...prev, acceptance_criteria: data.structured.acceptance_criteria || prev.acceptance_criteria, dependency: data.structured.dependencies || prev.dependency, notes: data.structured.notes || prev.notes }))
        }
        setAiSuggestion(data.structured.rationale || data.structured.reasoning || data.structured.feedback || 'Suggestions applied to the form below.')
      } else {
        setAiSuggestion(data.suggestion)
      }
    } catch {
      setAiSuggestion('Could not reach AI assistant. You can still fill in the fields manually.')
    } finally {
      setAiLoading(false)
    }
  }

  const handleSubmit = async () => {
    setSubmitStatus('submitting')
    setErrorMsg('')
    try {
      const res = await fetch(`${API_URL}/api/stories/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      })
      if (!res.ok) throw new Error('Failed to submit')
      setSubmitStatus('done')
    } catch (e) {
      setSubmitStatus('error')
      setErrorMsg(e instanceof Error ? e.message : 'Submit failed')
    }
  }

  const resetForm = () => {
    setDraft({ ...EMPTY_DRAFT })
    setIdeaText('')
    setStep(0)
    setSubmitStatus('idle')
    setAiSuggestion(null)
  }

  return (
    <div className="min-h-screen bg-[#06060b] text-white relative overflow-hidden">
      <ParticleField />

      {/* Gradient orbs */}
      <div className="fixed top-[-200px] right-[-200px] w-[600px] h-[600px] rounded-full bg-violet-600/10 blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-200px] left-[-200px] w-[500px] h-[500px] rounded-full bg-teal-600/8 blur-[100px] pointer-events-none" />

      {/* Header */}
      <header className="relative z-10 border-b border-white/5 backdrop-blur-xl bg-black/30">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <SuperTruthLogo className="h-7 w-auto" />
            <div className="h-6 w-px bg-white/10" />
            <div className="flex items-center gap-2">
              <div className="px-2.5 py-1 bg-violet-500/15 border border-violet-500/25 rounded-md">
                <span className="text-violet-400 text-[11px] font-bold tracking-[0.15em]">VIOLET</span>
              </div>
              <span className="text-white/90 font-semibold text-sm">Story Builder</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-[11px] text-gray-500 uppercase tracking-wider">
              <AIPulse />
              <span>AI-Assisted</span>
            </div>
            <a href="/" className="text-xs text-gray-500 hover:text-white transition-colors border border-white/10 rounded-md px-3 py-1.5 hover:border-white/20">
              Dashboard
            </a>
          </div>
        </div>
      </header>

      <div className="relative z-10 max-w-3xl mx-auto px-6 py-10">
        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 mb-12">
          {STEPS.map((s, i) => (
            <div key={s.key} className="flex items-center">
              <button
                onClick={() => i <= step && setStep(i)}
                className={`group relative flex items-center gap-2.5 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${
                  i === step
                    ? 'bg-gradient-to-r from-violet-600 to-violet-500 text-white shadow-lg shadow-violet-600/25 scale-105'
                    : i < step
                    ? 'bg-violet-500/10 text-violet-400 cursor-pointer hover:bg-violet-500/20 border border-violet-500/20'
                    : 'bg-white/[0.03] text-gray-600 cursor-default border border-white/5'
                }`}
              >
                <span className={`font-mono text-[10px] tracking-wider ${i === step ? 'text-violet-200' : i < step ? 'text-violet-500' : 'text-gray-700'}`}>
                  {s.icon}
                </span>
                <span className="hidden sm:inline">{s.label}</span>
                {i < step && (
                  <svg className="w-3.5 h-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
              {i < STEPS.length - 1 && (
                <div className={`w-6 sm:w-10 h-px mx-1 transition-colors duration-500 ${i < step ? 'bg-violet-500/50' : 'bg-white/5'}`} />
              )}
            </div>
          ))}
        </div>

        {/* Main Card */}
        <div className="relative rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl shadow-2xl shadow-black/40 overflow-hidden">
          {/* Card glow */}
          <div className="absolute inset-0 bg-gradient-to-b from-violet-600/[0.03] to-transparent pointer-events-none" />

          <div className="relative p-8 sm:p-10">
            {/* Step 1: Ideate */}
            {step === 0 && (
              <div className="space-y-7 animate-in">
                <div>
                  <h2 className="text-2xl font-semibold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                    What do you want to build?
                  </h2>
                  <p className="text-gray-500 text-sm mt-2 leading-relaxed">
                    Describe your idea in plain language. Our AI will extract the epic, feature, and craft a user story for you.
                  </p>
                </div>

                <div className="relative">
                  <textarea
                    value={ideaText}
                    onChange={(e) => setIdeaText(e.target.value)}
                    placeholder="e.g., I want researchers to compare two clusters and understand why they're semantically related, with a plain-language explanation..."
                    className="w-full h-36 bg-white/[0.03] border border-white/10 rounded-xl px-5 py-4 text-white text-sm resize-none focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 placeholder-gray-600 transition-all"
                  />
                  <div className="absolute bottom-3 right-3 text-[10px] text-gray-600">
                    {ideaText.length > 0 ? `${ideaText.length} chars` : 'Just describe it naturally'}
                  </div>
                </div>

                <button
                  onClick={() => callAssist('idea', ideaText)}
                  disabled={!ideaText.trim() || aiLoading}
                  className="group relative px-6 py-3 bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-500 hover:to-violet-400 disabled:from-gray-800 disabled:to-gray-800 disabled:cursor-not-allowed rounded-xl font-medium transition-all text-sm shadow-lg shadow-violet-600/20 disabled:shadow-none"
                >
                  <span className="flex items-center gap-2">
                    {aiLoading ? (
                      <>
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        AI is thinking...
                      </>
                    ) : (
                      'Generate User Story'
                    )}
                  </span>
                </button>

                {aiSuggestion && (
                  <div className="relative p-5 rounded-xl bg-violet-500/[0.06] border border-violet-500/20 overflow-hidden">
                    <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-violet-500 to-violet-600" />
                    <div className="flex items-start gap-3 ml-3">
                      <AIPulse />
                      <div>
                        <p className="text-violet-300 text-xs font-semibold uppercase tracking-wider mb-1.5">AI Suggestion</p>
                        <p className="text-gray-300 text-sm leading-relaxed">{aiSuggestion}</p>
                      </div>
                    </div>
                  </div>
                )}

                {(draft.epic || draft.feature || draft.user_story) && (
                  <div className="space-y-4 pt-6 border-t border-white/5">
                    <p className="text-[11px] text-gray-500 uppercase tracking-widest font-medium">Extracted Fields</p>
                    <Field label="Epic" value={draft.epic} onChange={(v) => setDraft(d => ({ ...d, epic: v }))} />
                    <Field label="Feature" value={draft.feature} onChange={(v) => setDraft(d => ({ ...d, feature: v }))} />
                    <Field label="User Story" value={draft.user_story} onChange={(v) => setDraft(d => ({ ...d, user_story: v }))} multiline />
                  </div>
                )}

                <div className="flex justify-end pt-4">
                  <NavButton direction="next" onClick={() => setStep(1)} disabled={!draft.user_story} />
                </div>
              </div>
            )}

            {/* Step 2: Shape */}
            {step === 1 && (
              <div className="space-y-6 animate-in">
                <div>
                  <h2 className="text-2xl font-semibold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                    Shape the Story
                  </h2>
                  <p className="text-gray-500 text-sm mt-2">Refine the details. AI can help with priority and sizing.</p>
                </div>

                <Field label="Epic" value={draft.epic} onChange={(v) => setDraft(d => ({ ...d, epic: v }))}
                  options={context?.epics} placeholder="Or type a new epic..." />
                <Field label="Feature" value={draft.feature} onChange={(v) => setDraft(d => ({ ...d, feature: v }))}
                  options={context?.features} placeholder="Or type a new feature..." />
                <Field label="User Story" value={draft.user_story} onChange={(v) => setDraft(d => ({ ...d, user_story: v }))} multiline />

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Priority" value={draft.priority} onChange={(v) => setDraft(d => ({ ...d, priority: v }))}
                    options={['Critical', 'High', 'Medium', 'Low']} />
                  <Field label="Story Points" value={String(draft.story_points)} onChange={(v) => setDraft(d => ({ ...d, story_points: parseInt(v) || 3 }))}
                    options={['1', '2', '3', '5', '8', '13']} />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Sprint" value={draft.sprint} onChange={(v) => setDraft(d => ({ ...d, sprint: v }))}
                    options={context?.sprints.map(s => s.id) || []} placeholder="e.g., 2026-S1" />
                  <Field label="Assigned To" value={draft.assigned_to} onChange={(v) => setDraft(d => ({ ...d, assigned_to: v }))}
                    options={context?.assignees || []} placeholder="Who's building this?" />
                </div>

                <Field label="Demo Critical?" value={draft.demo_critical} onChange={(v) => setDraft(d => ({ ...d, demo_critical: v }))}
                  options={['Yes', 'No']} />

                <button
                  onClick={() => callAssist('story', JSON.stringify(draft))}
                  disabled={aiLoading}
                  className="flex items-center gap-2 px-5 py-2.5 bg-white/[0.04] text-violet-400 border border-violet-500/20 hover:bg-violet-500/10 rounded-xl font-medium transition-all text-sm"
                >
                  {aiLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                      Improving...
                    </>
                  ) : 'AI: Improve & Size'}
                </button>

                {aiSuggestion && <AISuggestionBox text={aiSuggestion} />}

                <div className="flex justify-between pt-4">
                  <NavButton direction="back" onClick={() => setStep(0)} />
                  <NavButton direction="next" onClick={() => { setAiSuggestion(null); setStep(2) }} />
                </div>
              </div>
            )}

            {/* Step 3: Define Acceptance Criteria */}
            {step === 2 && (
              <div className="space-y-6 animate-in">
                <div>
                  <h2 className="text-2xl font-semibold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                    Define Done
                  </h2>
                  <p className="text-gray-500 text-sm mt-2">How will you know this story is complete? AI can draft testable criteria.</p>
                </div>

                <button
                  onClick={() => callAssist('criteria', JSON.stringify(draft))}
                  disabled={aiLoading}
                  className="group relative px-6 py-3 bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-500 hover:to-violet-400 disabled:from-gray-800 disabled:to-gray-800 rounded-xl font-medium transition-all text-sm shadow-lg shadow-violet-600/20"
                >
                  {aiLoading ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                      Generating criteria...
                    </span>
                  ) : 'Generate Acceptance Criteria'}
                </button>

                {aiSuggestion && <AISuggestionBox text={aiSuggestion} />}

                <Field label="Acceptance Criteria" value={draft.acceptance_criteria}
                  onChange={(v) => setDraft(d => ({ ...d, acceptance_criteria: v }))} multiline rows={6}
                  placeholder="1) Given... When... Then...\n2) ...\n3) ..." />

                <Field label="Dependencies" value={draft.dependency}
                  onChange={(v) => setDraft(d => ({ ...d, dependency: v }))}
                  placeholder="What must be done first?" />

                <Field label="Notes" value={draft.notes}
                  onChange={(v) => setDraft(d => ({ ...d, notes: v }))} multiline
                  placeholder="Implementation hints, links, context..." />

                <div className="flex justify-between pt-4">
                  <NavButton direction="back" onClick={() => setStep(1)} />
                  <NavButton direction="next" onClick={() => { setAiSuggestion(null); setStep(3) }} />
                </div>
              </div>
            )}

            {/* Step 4: Review & Ship */}
            {step === 3 && (
              <div className="space-y-6 animate-in">
                {submitStatus === 'done' ? (
                  <div className="text-center py-12 space-y-6">
                    <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-green-600/30">
                      <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-2xl font-semibold text-white mb-2">Shipped to Sprint Backlog</h2>
                      <p className="text-gray-400">
                        <span className="text-white font-medium">{draft.feature}</span> has been added to{' '}
                        <span className="text-violet-400 font-medium">{draft.sprint}</span>
                      </p>
                    </div>
                    <div className="flex gap-3 justify-center pt-4">
                      <button onClick={resetForm} className="px-6 py-3 bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-500 hover:to-violet-400 rounded-xl font-medium text-sm shadow-lg shadow-violet-600/20 transition-all">
                        Create Another
                      </button>
                      <a href="/" className="px-6 py-3 bg-white/[0.04] border border-white/10 hover:border-white/20 rounded-xl text-sm transition-all inline-flex items-center">
                        Back to Dashboard
                      </a>
                    </div>
                  </div>
                ) : (
                  <>
                    <div>
                      <h2 className="text-2xl font-semibold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                        Review & Ship
                      </h2>
                      <p className="text-gray-500 text-sm mt-2">Verify everything before pushing to the sprint sheet.</p>
                    </div>

                    {/* Story Card Preview */}
                    <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] overflow-hidden">
                      {/* Card Header */}
                      <div className="px-6 py-4 border-b border-white/5 flex items-center gap-3 flex-wrap">
                        <PriorityBadge priority={draft.priority} />
                        <span className="px-3 py-1 rounded-lg bg-violet-500/10 text-violet-400 text-xs font-bold border border-violet-500/20">
                          {draft.story_points} pts
                        </span>
                        {draft.sprint && (
                          <span className="px-3 py-1 rounded-lg bg-blue-500/10 text-blue-400 text-xs font-bold border border-blue-500/20">
                            {draft.sprint}
                          </span>
                        )}
                        {draft.demo_critical === 'Yes' && (
                          <span className="px-3 py-1 rounded-lg bg-pink-500/10 text-pink-400 text-xs font-bold border border-pink-500/20">
                            Demo Critical
                          </span>
                        )}
                      </div>

                      {/* Card Body */}
                      <div className="p-6 space-y-5">
                        <div>
                          <p className="text-[10px] text-gray-600 uppercase tracking-[0.2em] mb-1">Epic / Feature</p>
                          <p className="text-white font-medium">{draft.epic} <span className="text-gray-600 mx-2">/</span> {draft.feature}</p>
                        </div>

                        <div>
                          <p className="text-[10px] text-gray-600 uppercase tracking-[0.2em] mb-1">User Story</p>
                          <p className="text-gray-300 italic leading-relaxed border-l-2 border-violet-500/30 pl-4">{draft.user_story}</p>
                        </div>

                        <div>
                          <p className="text-[10px] text-gray-600 uppercase tracking-[0.2em] mb-1">Acceptance Criteria</p>
                          <pre className="text-gray-400 text-sm whitespace-pre-wrap font-sans leading-relaxed">{draft.acceptance_criteria}</pre>
                        </div>

                        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/5">
                          <MetaField label="Assigned" value={draft.assigned_to || 'Unassigned'} />
                          <MetaField label="Dependency" value={draft.dependency || 'None'} />
                          <MetaField label="Notes" value={draft.notes || '—'} />
                        </div>
                      </div>
                    </div>

                    {errorMsg && (
                      <div className="p-4 bg-red-500/[0.06] border border-red-500/20 rounded-xl">
                        <p className="text-red-400 text-sm">{errorMsg}</p>
                      </div>
                    )}

                    <div className="flex justify-between pt-4">
                      <NavButton direction="back" onClick={() => setStep(2)} />
                      <button
                        onClick={handleSubmit}
                        disabled={submitStatus === 'submitting'}
                        className="px-8 py-3 bg-gradient-to-r from-emerald-600 to-green-500 hover:from-emerald-500 hover:to-green-400 disabled:from-gray-800 disabled:to-gray-800 rounded-xl font-medium text-sm shadow-lg shadow-emerald-600/20 disabled:shadow-none transition-all flex items-center gap-2"
                      >
                        {submitStatus === 'submitting' ? (
                          <>
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                            Pushing to Sheet...
                          </>
                        ) : (
                          'Ship to Sprint Backlog'
                        )}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-[11px] text-gray-700">
            SuperTruth Inc. &middot; VIOLET Story Builder &middot; Sprint Planning Assistant
          </p>
        </div>
      </div>
    </div>
  )
}

// --- Sub-components ---

function AISuggestionBox({ text }: { text: string }) {
  return (
    <div className="relative p-5 rounded-xl bg-violet-500/[0.06] border border-violet-500/20 overflow-hidden">
      <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-violet-500 to-violet-600" />
      <div className="flex items-start gap-3 ml-3">
        <AIPulse />
        <div>
          <p className="text-violet-300 text-xs font-semibold uppercase tracking-wider mb-1.5">AI Insight</p>
          <p className="text-gray-300 text-sm leading-relaxed">{text}</p>
        </div>
      </div>
    </div>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const styles: Record<string, string> = {
    Critical: 'bg-red-500/10 text-red-400 border-red-500/20',
    High: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    Medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    Low: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  }
  return (
    <span className={`px-3 py-1 rounded-lg text-xs font-bold border ${styles[priority] || styles.Medium}`}>
      {priority}
    </span>
  )
}

function MetaField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] text-gray-600 uppercase tracking-[0.2em]">{label}</p>
      <p className="text-sm text-gray-400 mt-0.5">{value}</p>
    </div>
  )
}

function NavButton({ direction, onClick, disabled }: { direction: 'back' | 'next'; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-6 py-2.5 rounded-xl text-sm font-medium transition-all ${
        direction === 'back'
          ? 'bg-white/[0.03] border border-white/10 hover:border-white/20 text-gray-400 hover:text-white'
          : 'bg-white text-black hover:bg-gray-200 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed shadow-lg shadow-white/5'
      }`}
    >
      {direction === 'back' ? 'Back' : 'Continue'}
    </button>
  )
}

function Field({ label, value, onChange, multiline, rows, options, placeholder }: {
  label: string
  value: string
  onChange: (v: string) => void
  multiline?: boolean
  rows?: number
  options?: string[]
  placeholder?: string
}) {
  const baseClass = "w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all placeholder-gray-600"

  return (
    <div>
      <label className="block text-[10px] text-gray-500 uppercase tracking-[0.2em] mb-2 font-medium">{label}</label>
      {options && options.length > 0 ? (
        <div className="space-y-2">
          <select
            value={options.includes(value) ? value : '__custom__'}
            onChange={(e) => { if (e.target.value !== '__custom__') onChange(e.target.value) }}
            className={baseClass + ' appearance-none cursor-pointer'}
          >
            {!options.includes(value) && value && <option value="__custom__">{value} (custom)</option>}
            {!value && <option value="__custom__">{placeholder || 'Select...'}</option>}
            {options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
          {!options.includes(value) && (
            <input type="text" value={value} onChange={(e) => onChange(e.target.value)}
              placeholder={placeholder || `Or type a custom ${label.toLowerCase()}...`}
              className={baseClass} />
          )}
        </div>
      ) : multiline ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={rows || 3}
          placeholder={placeholder} className={baseClass + ' resize-none'} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder} className={baseClass} />
      )}
    </div>
  )
}
