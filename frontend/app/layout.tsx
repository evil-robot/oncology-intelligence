import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'VIOLET — Oncology & Rare Disease Intelligence',
  description: 'Visual Intelligence Layer for Oncology Trends & Evidence Triangulation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
