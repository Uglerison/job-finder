import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AppNavigation } from './AppNavigation';

describe('AppNavigation', () => {
  it('destaca a rota ativa e mantém as áreas principais em uma única navegação', () => {
    render(
      <AppNavigation onNavigate={vi.fn()} pathname="/vagas">
        <p>Conteúdo</p>
      </AppNavigation>,
    );

    expect(screen.getByRole('link', { name: 'Vagas' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: 'Buscar' })).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Candidaturas' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Agenda' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Painel' })).toBeInTheDocument();
    expect(screen.queryByText('Principal')).not.toBeInTheDocument();
    expect(screen.queryByText('Acompanhar')).not.toBeInTheDocument();
  });

  it('abre e fecha o menu compacto, incluindo o fechamento ao navegar', () => {
    const onNavigate = vi.fn();
    render(
      <AppNavigation onNavigate={onNavigate} pathname="/">
        <p>Conteúdo</p>
      </AppNavigation>,
    );

    const menuButton = screen.getByRole('button', { name: 'Abrir menu' });
    fireEvent.click(menuButton);
    expect(menuButton).toHaveAttribute('aria-expanded', 'true');

    fireEvent.click(screen.getByRole('link', { name: 'Buscar' }));
    expect(onNavigate).toHaveBeenCalledWith('/busca');
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');
  });
});
