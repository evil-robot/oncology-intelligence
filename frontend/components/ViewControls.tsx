'use client'

import { Eye, EyeOff, Link2, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react'
import { useStore, useView } from '@/lib/store'
import Tooltip from './Tooltip'

export default function ViewControls() {
  const view = useView()
  const setView = useStore((s) => s.setView)
  const resetCamera = useStore((s) => s.resetCamera)

  const controls = [
    {
      icon: view.showLabels ? Eye : EyeOff,
      label: 'Labels',
      active: view.showLabels,
      onClick: () => setView('showLabels', !view.showLabels),
      tooltip: (
        <div>
          <p className="font-medium text-white mb-1">Toggle Labels</p>
          <p className="text-gray-400 text-xs">
            {view.showLabels ? 'Click to hide' : 'Click to show'} term labels when hovering
            over data points in the 3D visualization.
          </p>
        </div>
      ),
    },
    {
      icon: Link2,
      label: 'Connections',
      active: view.showConnections,
      onClick: () => setView('showConnections', !view.showConnections),
      tooltip: (
        <div>
          <p className="font-medium text-white mb-1">Toggle Connections</p>
          <p className="text-gray-400 text-xs">
            {view.showConnections ? 'Click to hide' : 'Click to show'} lines connecting
            search terms to their cluster centers, revealing grouping relationships.
          </p>
        </div>
      ),
    },
  ]

  return (
    <div className="glass rounded-lg p-2 flex items-center gap-1">
      {controls.map((control) => (
        <Tooltip key={control.label} content={control.tooltip} position="bottom">
          <button
            onClick={control.onClick}
            className={`p-2 rounded-lg transition-colors ${
              control.active
                ? 'bg-primary/20 text-primary'
                : 'text-gray-400 hover:text-white hover:bg-surface'
            }`}
          >
            <control.icon className="w-4 h-4" />
          </button>
        </Tooltip>
      ))}

      <div className="w-px h-6 bg-border mx-1" />

      <Tooltip
        content={
          <div>
            <p className="font-medium text-white mb-1">Reset Camera</p>
            <p className="text-gray-400 text-xs">
              Return to the default camera position and zoom level.
              Useful after exploring different angles of the visualization.
            </p>
          </div>
        }
        position="bottom"
      >
        <button
          onClick={resetCamera}
          className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-surface transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </Tooltip>

      <div className="w-px h-6 bg-border mx-1" />

      <div className="flex items-center gap-1">
        <Tooltip
          content={
            <div>
              <p className="font-medium text-white mb-1">Decrease Point Size</p>
              <p className="text-gray-400 text-xs">
                Make data points smaller to reduce visual clutter
                when many terms overlap.
              </p>
            </div>
          }
          position="bottom"
        >
          <button
            onClick={() => setView('pointSize', Math.max(0.5, view.pointSize - 0.25))}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-surface transition-colors"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
        </Tooltip>

        <Tooltip
          content={
            <div>
              <p className="font-medium text-white mb-1">Point Size</p>
              <p className="text-gray-400 text-xs">
                Current scale multiplier for data point sizes.
                Adjust to find the right balance between visibility and clarity.
              </p>
            </div>
          }
          position="bottom"
        >
          <span className="text-xs text-gray-500 w-8 text-center cursor-help">{view.pointSize.toFixed(1)}x</span>
        </Tooltip>

        <Tooltip
          content={
            <div>
              <p className="font-medium text-white mb-1">Increase Point Size</p>
              <p className="text-gray-400 text-xs">
                Make data points larger for better visibility,
                especially useful when zoomed out.
              </p>
            </div>
          }
          position="bottom"
        >
          <button
            onClick={() => setView('pointSize', Math.min(3, view.pointSize + 0.25))}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-surface transition-colors"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </Tooltip>
      </div>
    </div>
  )
}
