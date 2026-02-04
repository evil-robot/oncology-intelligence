'use client'

export default function SuperTruthLogo({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 200 40"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <text
        x="0"
        y="32"
        fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
        fontSize="36"
        fontWeight="500"
        fill="#0d9488"
        letterSpacing="-0.5"
      >
        SuperTruth
      </text>
    </svg>
  )
}
