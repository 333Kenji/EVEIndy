import React from 'react'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom'
import PaneManager from './PaneManager'

vi.mock('../../lib/uiState', () => ({
  loadUiState: vi.fn().mockResolvedValue({}),
  patchUiState: vi.fn().mockResolvedValue({}),
}))

describe('PaneManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens and closes panes', async () => {
    render(<PaneManager />)
    const button = screen.getAllByText('+ Structures Config')[0]
    fireEvent.click(button)
    expect(screen.getByRole('heading', { name: /Structures Config/i })).toBeTruthy()
    const close = screen.getByRole('button', { name: /close/i })
    fireEvent.click(close)
    expect(screen.queryByRole('heading', { name: /Structures Config/i })).toBeNull()
  })

  it('supports drag reorder and resize', async () => {
    render(<PaneManager />)
    fireEvent.click(screen.getAllByText('+ Structures Config')[0])
    fireEvent.click(screen.getAllByText('+ Analytics')[0])
    const headers = screen.getAllByRole('heading', { level: 4 })
    expect(headers[0].textContent).toContain('Structures Config')
    const paneElements = Array.from(document.querySelectorAll('.pane'))
    const firstPane = paneElements[0] as HTMLElement
    const secondPane = paneElements[1] as HTMLElement
    fireEvent.dragStart(firstPane)
    fireEvent.dragOver(secondPane)
    fireEvent.drop(secondPane)
    const reordered = document.querySelectorAll('.pane strong')
    expect(reordered[0].textContent).toContain('Analytics')
    const slider = screen.getAllByRole('slider')[0]
    fireEvent.change(slider, { target: { value: '40' } })
    expect((slider as HTMLInputElement).value).toBe('40')
  })
})
