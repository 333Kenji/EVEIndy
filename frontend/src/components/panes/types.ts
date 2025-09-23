export type PaneId = 'structures' | 'analytics' | 'materials'

export type PaneState = {
  id: PaneId
  width: number
  order: number
  stacked?: boolean
}

export type PaneDescriptor = {
  id: PaneId
  title: string
  description: string
}

export const PANE_DEFS: PaneDescriptor[] = [
  { id: 'structures', title: 'Structures Config', description: 'Configure structures, roles, and rigs per system.' },
  { id: 'analytics', title: 'Analytics', description: 'Indicators, SPP⁺ snapshots, and queue projections.' },
  { id: 'materials', title: 'Materials Coverage', description: 'On-hand vs WIP materials for planning.' },
]
