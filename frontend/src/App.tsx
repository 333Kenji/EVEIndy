import React from 'react'
import Calculator from './pages/Calculator'
import BOMExplorer from './pages/BOMExplorer'
import Systems from './pages/Systems'
import ShipBasket from './pages/ShipBasket'
import BackgroundWeb from './components/BackgroundWeb'
import MarketAnalysis from './pages/MarketAnalysis'

type PaneDefinition = {
  key: string
  title: string
  icon: string
  component: React.ComponentType
}

const PANE_DEFS: PaneDefinition[] = [
  { key: 'market', title: 'Market Analysis', icon: '📊', component: MarketAnalysis },
  { key: 'calculator', title: 'Industry Calculator', icon: '🧮', component: Calculator },
  { key: 'bom', title: 'BOM Explorer', icon: '🧾', component: BOMExplorer },
  { key: 'systems', title: 'System Indices', icon: '🛰️', component: Systems },
  { key: 'basket', title: 'Ship Basket', icon: '🛒', component: ShipBasket }
]

const STORAGE_KEY_OPEN = 'eveindy:pane:open'
const STORAGE_KEY_ACTIVE = 'eveindy:pane:active'

function loadStoredKeys(): string[] {
  if (typeof window === 'undefined') return ['market']
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY_OPEN)
    if (!raw) return ['market']
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed) && parsed.every((k) => typeof k === 'string')) {
      return parsed.length ? parsed : ['market']
    }
  } catch (err) {
    console.warn('Failed to read stored pane state', err)
  }
  return ['market']
}

function loadActiveKey(defaultKey: string, available: string[]): string {
  if (typeof window === 'undefined') return defaultKey
  const raw = window.localStorage.getItem(STORAGE_KEY_ACTIVE)
  if (raw && available.includes(raw)) return raw
  return defaultKey
}

function persistState(open: string[], active: string) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY_OPEN, JSON.stringify(open))
  window.localStorage.setItem(STORAGE_KEY_ACTIVE, active)
}

function PaneContainer({ paneKey, title, component: Component, isActive, onClose, onFocus }: {
  paneKey: string
  title: string
  component: React.ComponentType
  isActive: boolean
  onClose: (key: string) => void
  onFocus: (key: string) => void
}) {
  return (
    <section className={`pane ${isActive ? 'pane-active' : ''}`}>
      <header className="pane-header">
        <div>
          <strong>{title}</strong>
          {!isActive && (
            <button className="pane-focus" onClick={() => onFocus(paneKey)}>Focus</button>
          )}
        </div>
        <button className="pane-close" onClick={() => onClose(paneKey)} title="Close pane">✕</button>
      </header>
      <div className="pane-content">
        <Component />
      </div>
    </section>
  )
}

export default function App() {
  const [openKeys, setOpenKeys] = React.useState<string[]>(() => loadStoredKeys())
  const [activeKey, setActiveKey] = React.useState<string>(() => loadActiveKey('market', loadStoredKeys()))

  React.useEffect(() => {
    if (!openKeys.includes(activeKey)) {
      const fallback = openKeys[0] || 'market'
      setActiveKey(fallback)
      persistState(openKeys, fallback)
      return
    }
    persistState(openKeys, activeKey)
  }, [openKeys, activeKey])

  const togglePane = (key: string) => {
    setOpenKeys((prev) => {
      if (prev.includes(key)) {
        const next = prev.filter((k) => k !== key)
        return next.length ? next : ['market']
      }
      return [...prev, key]
    })
    setActiveKey(key)
  }

  const closePane = (key: string) => {
    setOpenKeys((prev) => {
      const next = prev.filter((k) => k !== key)
      if (!next.length) {
        setActiveKey('market')
        return ['market']
      }
      if (key === activeKey) {
        setActiveKey(next[next.length - 1])
      }
      return next
    })
  }

  const focusPane = (key: string) => {
    if (!openKeys.includes(key)) setOpenKeys((prev) => [...prev, key])
    setActiveKey(key)
  }

  const openPanes = PANE_DEFS.filter((p) => openKeys.includes(p.key))

  return (
    <>
      <BackgroundWeb density={2} velocity={1.2} filamentAmplitude={1.2} gradient={{stops:['#0ea5e9','#7c3aed']}} />
      <div className="app-shell">
        <aside className="app-sidebar">
          <div className="app-sidebar-title">EVEINDY</div>
          <nav className="app-sidebar-nav">
            {PANE_DEFS.map((pane) => {
              const isActive = activeKey === pane.key
              const isOpen = openKeys.includes(pane.key)
              return (
                <button
                  key={pane.key}
                  className={`sidebar-button ${isOpen ? 'open' : ''} ${isActive ? 'active' : ''}`}
                  onClick={() => togglePane(pane.key)}
                  title={pane.title}
                >
                  <span className="sidebar-icon" aria-hidden>{pane.icon}</span>
                  <span className="sidebar-label">{pane.title}</span>
                </button>
              )
            })}
          </nav>
        </aside>
        <main className="pane-stack">
          {openPanes.length ? (
            openPanes.map((pane) => (
              <PaneContainer
                key={pane.key}
                paneKey={pane.key}
                title={pane.title}
                component={pane.component}
                isActive={activeKey === pane.key}
                onClose={closePane}
                onFocus={focusPane}
              />
            ))
          ) : (
            <div className="pane-empty">Select a pane from the sidebar to get started.</div>
          )}
        </main>
      </div>
    </>
  )
}
