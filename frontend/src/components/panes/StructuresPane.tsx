import React from 'react'
import { loadUiState } from '../../lib/uiState'

type StructureCfg = { type: string; role: string; rigs: number[] }

type Facility = {
  system_id: number
  name: string
  structures: StructureCfg[]
}

const StructuresPane: React.FC = () => {
  const [facilities, setFacilities] = React.useState<Facility[]>([])
  const [rigNames, setRigNames] = React.useState<Record<number, string>>({})

  React.useEffect(() => {
    loadUiState().then((state) => {
      const list = (state.facilities as { systems: Facility[] })?.systems || []
      setFacilities(list)
    }).catch(() => setFacilities([]))
    fetch('/structures/rigs')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        const names: Record<number, string> = {}
        (data.rigs || []).forEach((rig: any) => { names[rig.rig_id] = rig.name })
        setRigNames(names)
      })
      .catch(() => setRigNames({}))
  }, [])

  if (!facilities.length) {
    return <div style={{ opacity: 0.7 }}>No structures configured yet. Add systems and structures from the Production Facilities view.</div>
  }

  return (
    <div className="pane-structures">
      {facilities.map(f => (
        <div key={f.system_id} className="pane-structures__system">
          <h4>{f.name} <span>#{f.system_id}</span></h4>
          {!f.structures.length && <div className="pane-structures__empty">No structures configured.</div>}
          {f.structures.map((s, idx) => (
            <div key={idx} className="pane-structures__item">
              <div className="pane-structures__label">{s.type}</div>
              <div className="pane-structures__role">Role: {s.role}</div>
              <div className="pane-structures__rigs">
                Rigs: {s.rigs.length ? s.rigs.map(id => rigNames[id] || `Rig ${id}`).join(', ') : 'None'}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

export default StructuresPane
