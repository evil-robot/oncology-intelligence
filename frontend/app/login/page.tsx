'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import SuperTruthLogo from '@/components/SuperTruthLogo'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const res = await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })

      if (res.ok) {
        router.push('/')
        router.refresh()
      } else {
        setError('Invalid password')
      }
    } catch {
      setError('Authentication failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      {/* Main Login Card */}
      <div className="w-full max-w-md">
        {/* Logo & Branding */}
        <div className="text-center mb-8">
          <SuperTruthLogo className="h-16 w-auto mx-auto mb-4" />
          <div className="inline-block px-3 py-1 bg-violet-600/20 border border-violet-500/30 rounded text-violet-400 text-sm font-bold tracking-wider mb-4">
            VIOLET
          </div>
          <h1 className="text-2xl font-semibold text-white mb-2">
            Oncology & Rare Disease Intelligence
          </h1>
          <p className="text-gray-500 text-sm">
            Search trends across cancer types and rare conditions
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="glass rounded-xl p-8 space-y-6">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
              Access Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface border border-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500"
              placeholder="Enter password"
              autoFocus
            />
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !password}
            className="w-full py-3 bg-violet-600 hover:bg-violet-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
          >
            {isLoading ? 'Authenticating...' : 'Access Platform'}
          </button>
        </form>

        {/* Legal Disclaimer */}
        <div className="mt-8 p-4 border border-yellow-500/30 rounded-lg bg-yellow-500/5">
          <p className="text-yellow-500 font-bold text-xs mb-2 flex items-center gap-2">
            <span>⚠️</span> CONFIDENTIAL & PROPRIETARY
          </p>
          <p className="text-[11px] text-gray-500 leading-relaxed">
            This platform contains trade secrets and proprietary data of SuperTruth Inc.
            Unauthorized access, use, reproduction, or distribution is strictly prohibited
            and may result in civil and criminal penalties. All data is provided for research
            purposes only and does not constitute medical advice. By accessing this system,
            you acknowledge that your activity may be monitored and logged.
          </p>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-xs text-gray-600">
            © 2026 SuperTruth Inc. All Rights Reserved
          </p>
        </div>
      </div>
    </div>
  )
}
