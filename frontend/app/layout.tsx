import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Pediatric Oncology Search Intelligence',
  description: 'Visual exploration of pediatric oncology search trends with SDOH overlay',
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
