'use client'

import { useState, useRef, ReactNode, useEffect } from 'react'

interface TooltipProps {
  content: string | ReactNode
  children: ReactNode
  position?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
}

export default function Tooltip({ content, children, position = 'bottom', delay = 150 }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [actualPosition, setActualPosition] = useState(position)
  const containerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Adjust position if tooltip would go off screen
  useEffect(() => {
    if (isVisible && tooltipRef.current && containerRef.current) {
      const tooltipRect = tooltipRef.current.getBoundingClientRect()
      const containerRect = containerRef.current.getBoundingClientRect()

      let newPosition = position

      // Check if tooltip goes off screen and adjust
      if (position === 'bottom' && tooltipRect.bottom > window.innerHeight) {
        newPosition = 'top'
      } else if (position === 'top' && tooltipRect.top < 0) {
        newPosition = 'bottom'
      } else if (position === 'right' && tooltipRect.right > window.innerWidth) {
        newPosition = 'left'
      } else if (position === 'left' && tooltipRect.left < 0) {
        newPosition = 'right'
      }

      if (newPosition !== actualPosition) {
        setActualPosition(newPosition)
      }
    }
  }, [isVisible, position, actualPosition])

  const showTooltip = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true)
      setActualPosition(position) // Reset to default position
    }, delay)
  }

  const hideTooltip = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
    setIsVisible(false)
  }

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  // Position classes based on direction
  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }

  return (
    <div
      ref={containerRef}
      className="relative inline-flex"
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onFocus={showTooltip}
      onBlur={hideTooltip}
    >
      {children}

      {isVisible && (
        <div
          ref={tooltipRef}
          role="tooltip"
          className={`absolute z-[9999] px-3 py-2 text-sm bg-gray-900 border border-gray-700 rounded-lg shadow-2xl max-w-[280px] pointer-events-none whitespace-normal animate-in ${positionClasses[actualPosition]}`}
        >
          {content}
        </div>
      )}
    </div>
  )
}
