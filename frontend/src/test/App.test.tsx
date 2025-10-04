import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

describe('App', () => {
  it('renders HabitatCanvas title', () => {
    render(<App />)
    expect(screen.getByText('HabitatCanvas')).toBeInTheDocument()
  })

  it('renders subtitle', () => {
    render(<App />)
    expect(screen.getByText('Generative Layout Studio for Space Habitats')).toBeInTheDocument()
  })
})