'use client'

import { useState, useEffect } from 'react'
import { HelpCircle, X, Layers, TrendingUp, MapPin, Sparkles, MousePointer, Search, Eye, RotateCcw, ChevronRight, Lightbulb } from 'lucide-react'
import Tooltip from './Tooltip'

interface Section {
  icon: React.ElementType
  title: string
  description: string
  tips?: string[]
  color: string
}

const sections: Section[] = [
  {
    icon: Layers,
    title: '3D Semantic Map',
    description: 'Search terms are positioned in 3D space based on their meaning. Terms with similar meanings cluster together. This uses AI embeddings to measure semantic similarity.',
    tips: [
      'Drag to rotate the view',
      'Scroll to zoom in/out',
      'Click any point to see details',
    ],
    color: 'from-indigo-500 to-purple-500',
  },
  {
    icon: MousePointer,
    title: 'Clusters & Points',
    description: 'Each colored group represents a topic cluster. The octahedron shapes mark cluster centers. Individual points are search terms. Colors indicate categories like Pediatric Oncology, Adult Cancers, Rare Genetic Diseases, Rare Neurological Conditions, and more.',
    tips: [
      'Hover over points to see term names',
      'Click clusters to filter by topic',
      'Use the Links toggle to see relationships',
    ],
    color: 'from-pink-500 to-rose-500',
  },
  {
    icon: TrendingUp,
    title: 'Google Trends Data',
    description: 'Each term has associated search interest data from Google Trends. Values range from 0-100 (relative interest). This shows what people are actively searching for over time.',
    tips: [
      'Select a term to see its trend chart',
      'Compare trends across regions',
      'Look for spikes indicating emerging interest',
    ],
    color: 'from-green-500 to-emerald-500',
  },
  {
    icon: MapPin,
    title: 'SDOH & Geography',
    description: 'Social Determinants of Health data from CDC overlays vulnerability metrics. Higher SVI (Social Vulnerability Index) indicates populations facing more health-related challenges.',
    tips: [
      'Filter by state using the Geography dropdown',
      'Cross-reference search patterns with vulnerability data',
      'Identify underserved areas with high search interest',
    ],
    color: 'from-blue-500 to-cyan-500',
  },
  {
    icon: Sparkles,
    title: 'AI-Powered Insights',
    description: 'Machine learning identifies anomalies: sudden spikes, emerging topics, regional outliers, and unusual patterns. The Insights panel surfaces these automatically.',
    tips: [
      'Check the Insights panel for alerts',
      'Filter insights by severity (High/Medium/Low)',
      'Click insights to navigate to relevant data',
    ],
    color: 'from-yellow-500 to-orange-500',
  },
]

const quickTips = [
  { icon: Search, text: 'Use the search box to find specific terms or topics' },
  { icon: Eye, text: 'Toggle visibility controls to show/hide labels, posts, and connections' },
  { icon: RotateCcw, text: 'Click Reset Camera if you get lost in the 3D space' },
]

export default function ExplainerPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const [activeSection, setActiveSection] = useState<number | null>(null)
  const [hasSeenGuide, setHasSeenGuide] = useState(true)

  // Check if user has seen the guide before
  useEffect(() => {
    const seen = localStorage.getItem('posi-guide-seen')
    if (!seen) {
      setHasSeenGuide(false)
    }
  }, [])

  const handleClose = () => {
    setIsOpen(false)
    localStorage.setItem('posi-guide-seen', 'true')
    setHasSeenGuide(true)
  }

  return (
    <>
      {/* Help Button with pulse animation if guide not seen */}
      <Tooltip
        content={
          <div>
            <p className="font-medium text-white mb-1">Dashboard Guide</p>
            <p className="text-gray-400 text-xs">
              Click to learn what you're looking at and how to navigate this visualization.
            </p>
          </div>
        }
        position="bottom"
      >
        <button
          onClick={() => setIsOpen(true)}
          className={`glass p-2 rounded-lg hover:bg-white/10 transition-colors group relative ${
            !hasSeenGuide ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''
          }`}
        >
          <HelpCircle className="w-5 h-5 text-gray-400 group-hover:text-white" />
          {!hasSeenGuide && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full animate-pulse" />
          )}
        </button>
      </Tooltip>

      {/* Modal Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/80 backdrop-blur-md z-[100]"
            onClick={handleClose}
          />

          {/* Panel */}
          <div className="relative z-[101] glass rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden shadow-2xl flex flex-col">
            {/* Header */}
            <div className="flex-shrink-0 p-6 border-b border-white/10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
                    <Lightbulb className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold">Understanding This Dashboard</h2>
                    <p className="text-sm text-gray-400">
                      Oncology & Rare Disease Intelligence
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleClose}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Quick Overview */}
              <div className="bg-white/5 rounded-xl p-4">
                <p className="text-sm text-gray-300 leading-relaxed">
                  This dashboard visualizes <span className="text-primary font-medium">what people search for</span> related
                  to cancer and rare diseases—from pediatric oncology to adult cancers to genetic conditions. Search terms are mapped in 3D space based on meaning, overlaid with
                  <span className="text-secondary font-medium"> social vulnerability data</span>, and analyzed by AI to surface
                  <span className="text-yellow-400 font-medium"> actionable insights</span>.
                </p>
              </div>

              {/* Sections */}
              <div className="space-y-3">
                {sections.map((section, index) => (
                  <div
                    key={index}
                    className={`rounded-xl border transition-all cursor-pointer ${
                      activeSection === index
                        ? 'border-white/20 bg-white/5'
                        : 'border-transparent hover:bg-white/5'
                    }`}
                    onClick={() => setActiveSection(activeSection === index ? null : index)}
                  >
                    <div className="p-4 flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${section.color} flex items-center justify-center flex-shrink-0`}>
                        <section.icon className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium">{section.title}</h3>
                        <p className={`text-sm text-gray-400 ${activeSection === index ? '' : 'line-clamp-1'}`}>
                          {section.description}
                        </p>
                      </div>
                      <ChevronRight className={`w-5 h-5 text-gray-500 transition-transform flex-shrink-0 ${
                        activeSection === index ? 'rotate-90' : ''
                      }`} />
                    </div>

                    {/* Expanded Tips */}
                    {activeSection === index && section.tips && (
                      <div className="px-4 pb-4 pt-2 border-t border-white/5 ml-14">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Tips</p>
                        <ul className="space-y-1">
                          {section.tips.map((tip, i) => (
                            <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                              <span className="text-primary mt-1">•</span>
                              {tip}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Quick Tips Bar */}
              <div className="bg-gradient-to-r from-primary/10 to-secondary/10 rounded-xl p-4">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">Quick Tips</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {quickTips.map((tip, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-gray-300">
                      <tip.icon className="w-4 h-4 text-primary flex-shrink-0" />
                      <span>{tip.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex-shrink-0 p-4 border-t border-white/10 bg-black/20">
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500">
                  <strong>Data:</strong> Google Trends • CDC SVI • OpenAI Embeddings
                </p>
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-primary hover:bg-primary/80 rounded-lg text-sm font-medium transition-colors"
                >
                  Got it, let's explore
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
