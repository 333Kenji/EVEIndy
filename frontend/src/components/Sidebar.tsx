import React from 'react'
import { PaneId } from './panes/types'

type SidebarProps = {
  activePane: PaneId | null
  onSelect: (pane: PaneId | null) => void
}

const entries: { label: string; pane: PaneId }[] = [
  { label: 'Production Facilities', pane: 'structures' },
  { label: 'Analytics', pane: 'analytics' },
  { label: 'Materials Coverage', pane: 'materials' },
]

const Sidebar: React.FC<SidebarProps> = ({ activePane, onSelect }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar__logo">EVEINDY</div>
      <nav className="sidebar__nav">
        {entries.map(({ label, pane }) => (
          <button
            key={pane}
            className={activePane === pane ? 'sidebar__item active' : 'sidebar__item'}
            onClick={() => onSelect(pane)}
          >
            {label}
          </button>
        ))}
        {activePane && (
          <button className="sidebar__item sidebar__item--secondary" onClick={() => onSelect(null)}>
            Close Pane
          </button>
        )}
      </nav>
    </aside>
  )
}

export default Sidebar
