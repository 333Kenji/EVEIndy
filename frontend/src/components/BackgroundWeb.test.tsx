import React from 'react'
import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import BackgroundWeb from './BackgroundWeb'

describe('BackgroundWeb', () => {
  it('applies density and gradient props', () => {
    const { container } = render(<BackgroundWeb density={2} velocity={1.5} filamentAmplitude={1.3} gradient={{ stops: ['#123456', '#abcdef'] }} />)
    const canvas = container.querySelector('canvas') as HTMLCanvasElement
    expect(canvas).toBeTruthy()
    expect(canvas.dataset.density).toBe('2')
    expect(canvas.dataset.velocity).toBe('1.5')
    expect(canvas.dataset.filament).toBe('1.3')
    expect(canvas.dataset.gradient).toBe('#123456,#abcdef')
  })
})
