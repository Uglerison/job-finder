import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import App from './App';

describe('App', () => {
  it('apresenta a promessa principal do espaço local de vagas', () => {
    render(<App />);

    expect(
      screen.getByRole('heading', {
        name: 'Encontre oportunidades. Prepare-se para avançar.',
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('Job Finder')).toBeInTheDocument();
  });

  it('adota o shell editorial da referência visual', () => {
    render(<App />);

    expect(screen.getByRole('banner')).toHaveTextContent('Job Finder');
    expect(screen.getByText('PLATAFORMA LOCAL DE VAGAS')).toBeInTheDocument();
    expect(
      screen.getByText('Dados ficam neste computador.'),
    ).toBeInTheDocument();
    expect(document.querySelector('.paper-app')).not.toBeNull();
  });
});
