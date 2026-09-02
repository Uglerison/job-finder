import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBrowserNavigation } from './useBrowserNavigation';

function NavigationProbe() {
  const { navigate, pathname } = useBrowserNavigation();

  return (
    <>
      <output aria-label="Rota atual">{pathname}</output>
      <button onClick={() => navigate('/vagas')} type="button">
        Ir para vagas
      </button>
    </>
  );
}

describe('useBrowserNavigation', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/');
  });

  it('navega por uma URL real e reage ao histórico do navegador', () => {
    render(<NavigationProbe />);

    fireEvent.click(screen.getByRole('button', { name: 'Ir para vagas' }));
    expect(window.location.pathname).toBe('/vagas');
    expect(screen.getByLabelText('Rota atual')).toHaveTextContent('/vagas');

    window.history.pushState({}, '', '/agenda');
    fireEvent.popState(window);
    expect(screen.getByLabelText('Rota atual')).toHaveTextContent('/agenda');
  });

  it('normaliza uma URL desconhecida para o início', () => {
    window.history.replaceState({}, '', '/nao-existe');
    render(<NavigationProbe />);

    expect(screen.getByLabelText('Rota atual')).toHaveTextContent('/');
  });
});
