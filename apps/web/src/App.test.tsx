import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('presents Job Finder as a local job search workspace', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Job Finder' })).toBeInTheDocument()
    expect(screen.getByText('Sua central local para encontrar e acompanhar vagas.')).toBeInTheDocument()
  })
})
