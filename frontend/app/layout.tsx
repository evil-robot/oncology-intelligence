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
      <head>
        <script defer src="https://cloud.umami.is/script.js" data-website-id="b1213d91-30dc-4392-997e-7f0ff1ef15c1"></script>
      </head>
      <body className="antialiased">{children}</body>
    </html>
  )
}
