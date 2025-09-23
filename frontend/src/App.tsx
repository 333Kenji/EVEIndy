import React from 'react'
import Dashboard from './pages/Dashboard'
import Calculator from './pages/Calculator'
import BOMExplorer from './pages/BOMExplorer'
import Systems from './pages/Systems'
import ShipBasket from './pages/ShipBasket'
import BackgroundWeb from './components/BackgroundWeb'

export default function App() {
  return (
    <>
      <BackgroundWeb density={2} velocity={1.2} filamentAmplitude={1.2} gradient={{stops:['#0ea5e9','#7c3aed']}} />
      <div className="container" style={{ position: 'relative', zIndex: 1 }}>
        <h1 className="title" style={{ fontSize: 28, marginBottom: 12 }}>EVEINDY</h1>
        <div className="grid grid-2">
          <div className="card" style={{ gridColumn: '1 / span 2' }}>
            <Calculator />
          </div>
          <BOMExplorer />
          <Systems />
          <ShipBasket />
        </div>
      </div>
    </>
  )
}
