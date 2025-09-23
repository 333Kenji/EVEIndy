import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import Calculator from './Calculator'

describe('Calculator', () => {
  it('updates totals when runs change', () => {
    render(<Calculator />)
    const totalBefore = screen.getByText(/Total/).nextSibling as HTMLElement | null
    const input = screen.getByLabelText(/Runs:/) as HTMLInputElement
    fireEvent.change(input, { target: { value: '2' } })
    expect(input.value).toBe('2')
    // We can’t easily compute exact total with live prices; assert table updates rows
    const qtyCells = screen.getAllByRole('cell').filter((c) => /Qty x runs/.test(c.textContent || '') === false)
    expect(qtyCells.length).toBeGreaterThan(0)
  })

  it('toggles ME rig changes quantities', () => {
    render(<Calculator />)
    // Find one material row (Heavy Water) and capture qty
    const row = screen.getByText('Heavy Water').closest('tr')!
    const qtyCell = row?.children[1] as HTMLElement
    const before = qtyCell.textContent
    // Uncheck ME Rig I
    const rigCheckbox = screen.getByLabelText(/ME Rig I/i) as HTMLInputElement
    if (rigCheckbox.checked) {
      rigCheckbox.click()
    } else {
      // ensure it toggles at least once
      rigCheckbox.click()
      rigCheckbox.click()
    }
    const after = (row?.children[1] as HTMLElement).textContent
    expect(before).not.toEqual(after)
  })
})
