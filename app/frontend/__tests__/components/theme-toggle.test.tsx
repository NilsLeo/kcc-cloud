import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ThemeToggle } from '@/components/theme-toggle'
import { ThemeProvider } from '@/components/theme-provider'

describe('ThemeToggle', () => {
  it('renders theme toggle button', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>
    )

    // Check if the toggle button is rendered
    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
  })
})
