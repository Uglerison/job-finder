import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';

afterEach(() => vi.unstubAllGlobals());

function setup(path: string, protectedSearch = false) {
  let unlocked = false;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (input === '/api/vault/unlock') unlocked = true;
    const payload = String(input).startsWith('/api/vault')
      ? { configured: true, unlocked }
      : input === '/api/search/providers'
        ? protectedSearch
          ? [
              {
                provider: 'jsearch',
                configured: true,
                unlocked,
                storage: 'encrypted_database',
              },
            ]
          : []
        : input === '/api/search'
          ? {
              jobs: [],
              cache_hit: false,
              message: 'Nenhuma vaga encontrada.',
              outcome: 'no_results',
              partial: false,
              provider_runs: [],
              warnings: [],
            }
          : null;
    return new Response(JSON.stringify(payload));
  });
  vi.stubGlobal('fetch', fetchMock);
  window.history.replaceState({}, '', path);
  render(<App />);
  return fetchMock;
}

describe('acesso global ao cofre', () => {
  it.each([
    '/',
    '/busca',
    '/vagas',
    '/candidaturas',
    '/agenda',
    '/insights',
    '/painel',
    '/perfil',
    '/configuracoes',
    '/configuracoes/fontes',
    '/configuracoes/preferencias',
    '/configuracoes/historico',
    '/configuracoes/lixeira',
  ])('fica disponível no cabeçalho em %s', async (path) => {
    setup(path);
    const button = await within(screen.getByRole('banner')).findByRole(
      'button',
      { name: 'Cofre bloqueado' },
    );
    fireEvent.click(button);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText('Senha do cofre')).toHaveFocus();
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(window.location.pathname).toBe(path);
  });

  it('retoma a busca protegida somente após desbloquear', async () => {
    const fetchMock = setup('/busca', true);
    await screen.findByRole('button', { name: 'Cofre bloqueado' });
    fireEvent.change(screen.getByLabelText('Cargo ou palavra-chave'), {
      target: { value: 'Analista de Dados' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar vagas' }));
    const password = await screen.findByLabelText('Senha do cofre');
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/search')).toBe(
      false,
    );
    fireEvent.change(password, { target: { value: 'senha local longa' } });
    fireEvent.submit(
      screen
        .getByRole('button', { name: 'Desbloquear cofre' })
        .closest('form')!,
    );
    expect(
      await screen.findByText('Nenhuma vaga encontrada.'),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([url]) => url === '/api/search'),
    ).toHaveLength(1);
  });

  it('cancelar o desbloqueio não dispara busca e mantém os filtros', async () => {
    const fetchMock = setup('/busca', true);
    await screen.findByRole('button', { name: 'Cofre bloqueado' });
    fireEvent.change(screen.getByLabelText('Cargo ou palavra-chave'), {
      target: { value: 'SQL' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar vagas' }));
    fireEvent.keyDown(await screen.findByRole('dialog'), { key: 'Escape' });
    await waitFor(() =>
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument(),
    );
    expect(fetchMock.mock.calls.some(([url]) => url === '/api/search')).toBe(
      false,
    );
    expect(screen.getByLabelText('Cargo ou palavra-chave')).toHaveValue('SQL');
  });
});
