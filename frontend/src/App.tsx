import React from 'react'
import Dashboard from './pages/Dashboard'
import Calculator from './pages/Calculator'
import BOMExplorer from './pages/BOMExplorer'
import ShipBasket from './pages/ShipBasket'
import BackgroundWeb from './components/BackgroundWeb'
import Sidebar from './components/Sidebar'
import StructuresPane from './components/panes/StructuresPane'
import AnalyticsPane from './components/panes/AnalyticsPane'
import MaterialsPane from './components/panes/MaterialsPane'
import { PaneId } from './components/panes/types'
import { loadUiState, patchUiState } from './lib/uiState'

export default function App() {
  const [activePane, setActivePane] = React.useState<PaneId | null>(null)

  React.useEffect(() => {
    loadUiState()
      .then((state) => {
        const pane = (state.workspaceActivePane as PaneId | null) || null
        setActivePane(pane)
      })
      .catch(() => setActivePane(null))
  }, [])

  const selectPane = React.useCallback((pane: PaneId | null) => {
    setActivePane(pane)
    patchUiState({ workspaceActivePane: pane }).catch(() => {})
  }, [])

  const renderPane = () => {
    switch (activePane) {
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

  return (
    <>
      <BackgroundWeb density={2} velocity={1.2} filamentAmplitude={1.2} gradient={{stops:['#0ea5e9','#7c3aed']}} />
      <div className="app-shell" style={{ position: 'relative', zIndex: 1 }}>
        <Sidebar activePane={activePane} onSelect={selectPane} />
        <main className="app-main">
          <h1 className="title" style={{ fontSize: 28, marginBottom: 12 }}>EVEINDY</h1>
          {activePane ? (
            <div className="pane-full card">
              {renderPane()}
            </div>
          ) : (
            <div className="grid grid-2">
              <div className="card" style={{ gridColumn: '1 / span 2' }}>
                <Calculator />
              </div>
              <BOMExplorer />
              <ShipBasket />
            </div>
          )}
        </main>
      </div>
    </>
  )
}
