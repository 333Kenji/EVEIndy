import React from 'react'
import { loadUiState, patchUiState } from '../../lib/uiState'
import { PANE_DEFS, PaneId, PaneState } from './types'
import StructuresPane from './StructuresPane'
import AnalyticsPane from './AnalyticsPane'
import MaterialsPane from './MaterialsPane'

const MIN_WIDTH = 25
const MAX_WIDTH = 90

function paneComponent(id: PaneId) {
  switch (id) {
    case 'structures':
      return <StructuresPane />
    case 'analytics':
      return <AnalyticsPane />
    case 'materials':
      return <MaterialsPane />
    default:
      return null
  }
}

const PaneManager: React.FC = () => {
  const [panes, setPanes] = React.useState<PaneState[]>([])
  const dragId = React.useRef<PaneId | null>(null)

  React.useEffect(() => {
    loadUiState()
      .then(state => {
        const saved = (state.panes as PaneState[]) || []
        if (saved.length) setPanes(saved)
      })
      .catch(() => {})
  }, [])

  const persist = React.useCallback((next: PaneState[]) => {
    setPanes(next)
    patchUiState({ panes: next }).catch(() => {})
  }, [])

  const openPane = (id: PaneId) => {
    if (panes.some(p => p.id === id)) return
    const defaultWidth = panes.length ? Math.max(MIN_WIDTH, 60 - panes.length * 5) : 60
    const next = [...panes, { id, width: defaultWidth, order: panes.length }]
    persist(next)
  }

  const closePane = (id: PaneId) => {
    persist(panes.filter(p => p.id !== id).map((p, idx) => ({ ...p, order: idx })))
  }

  const onResize = (id: PaneId, width: number) => {
    persist(panes.map(p => (p.id === id ? { ...p, width } : p)))
  }

  const onDragStart = (id: PaneId) => {
    dragId.current = id
  }

  const onDrop = (targetId: PaneId) => {
    const sourceId = dragId.current
    dragId.current = null
    if (!sourceId || sourceId === targetId) return
    const sourceIndex = panes.findIndex(p => p.id === sourceId)
    const targetIndex = panes.findIndex(p => p.id === targetId)
    if (sourceIndex === -1 || targetIndex === -1) return
    const reordered = [...panes]
    const [moved] = reordered.splice(sourceIndex, 1)
    reordered.splice(targetIndex, 0, moved)
    persist(reordered.map((p, idx) => ({ ...p, order: idx })))
  }

  const toggleStack = (id: PaneId) => {
    persist(panes.map(p => (p.id === id ? { ...p, stacked: !p.stacked } : p)))
  }

  const available = PANE_DEFS.filter(def => !panes.some(p => p.id === def.id))

  return (
    <div className="pane-layout">
      <div className="pane-layout__toolbar">
        <h3>Workspace Panes</h3>
        <div className="pane-layout__actions">
          {available.map(def => (
            <button key={def.id} className="btn" onClick={() => openPane(def.id)}>
              + {def.title}
            </button>
          ))}
        </div>
      </div>
      <div className="pane-layout__container">
        {panes.map((pane) => {
          const descriptor = PANE_DEFS.find(d => d.id === pane.id)!
          const widthStyle = pane.stacked ? { flex: '1 0 100%' } : { flex: `0 0 ${pane.width}%` }
          return (
            <div
              key={pane.id}
              className="pane"
              style={widthStyle}
              draggable
              onDragStart={() => onDragStart(pane.id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onDrop(pane.id)}
            >
              <div className="pane__header">
                <div>
                  <strong>{descriptor.title}</strong>
                  <div className="pane__subtitle">{descriptor.description}</div>
                </div>
                <div className="pane__controls">
                  <label>
                    Width
                    <input
                      type="range"
                      min={MIN_WIDTH}
                      max={MAX_WIDTH}
                      value={pane.width}
                      onChange={(e) => onResize(pane.id, Number(e.target.value))}
                      disabled={pane.stacked}
                    />
                  </label>
                  <button className="btn" onClick={() => toggleStack(pane.id)}>{pane.stacked ? 'Unstack' : 'Stack'}</button>
                  <button className="btn" onClick={() => closePane(pane.id)}>Close</button>
                </div>
              </div>
              <div className="pane__body">
                {paneComponent(pane.id)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default PaneManager
