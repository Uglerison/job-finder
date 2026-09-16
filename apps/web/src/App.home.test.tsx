import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';

afterEach(() => vi.unstubAllGlobals());

const profile = {
  profile_id: 1,
  version_number: 1,
  criteria: {
    target_roles: ['Analista de Dados'],
    skills: [],
    languages: [],
    salary_expectation: null,
    restrictions: { excluded_keywords: [], locations: [], work_models: [] },
    weights: {},
  },
};

function setup({
  locked = false,
  failed = false,
  populated = false,
  failedApplication = false,
} = {}) {
  const jobs = populated
    ? Array.from({ length: 37 }, (_, index) => ({
        id: index + 1,
        title: `Oportunidade ${index + 1}`,
        company: 'Empresa',
        status: 'found',
        status_label: 'ENCONTRADA',
        created_at: '2026-08-31T10:00:00Z',
        origin_count: 1,
        location: null,
        canonical_url: null,
      }))
    : [];
  const request = vi.fn(async (input: RequestInfo | URL) => {
    if (input === '/api/jobs' && failed)
      return new Response('{}', { status: 500 });
    if (input === '/api/jobs/1/application' && failedApplication)
      return new Response('{}', { status: 500 });
    const payload =
      input === '/api/profile'
        ? profile
        : input === '/api/profile/versions'
          ? [profile]
          : input === '/api/jobs'
            ? {
                items: jobs,
                page: 1,
                pages: 1,
                page_size: 50,
                total: jobs.length,
              }
            : input === '/api/sources'
              ? []
              : input === '/api/search/providers'
                ? locked
                  ? [
                      {
                        configured: true,
                        unlocked: false,
                        storage: 'encrypted_database',
                        provider: 'jsearch',
                      },
                    ]
                  : []
                : input === '/api/vault'
                  ? { configured: locked, unlocked: false }
                  : input === '/api/events'
                    ? []
                    : null;
    return new Response(JSON.stringify(payload));
  });
  vi.stubGlobal('fetch', request);
  window.history.replaceState({}, '', '/');
  render(<App />);
  return request;
}

describe('início como central de próxima ação', () => {
  it('substitui o hero e os passos repetidos por uma única página compacta', async () => {
    setup();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Seu espaço de busca' }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole('link', { name: 'Configurar fontes' }),
    ).toHaveAttribute('href', '/configuracoes/fontes');
    expect(document.querySelector('.editorial-hero')).toBeNull();
    expect(screen.queryByText('COMO FUNCIONA')).not.toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });

  it('mostra todas as vagas no resumo e navega para a caixa com os dados preservados', async () => {
    setup({ populated: true });
    const review = await screen.findByRole('link', { name: 'Revisar vagas' });
    expect(
      within(
        screen.getByRole('region', { name: 'Resumo do acompanhamento' }),
      ).getByText('37'),
    ).toBeInTheDocument();
    fireEvent.click(review);
    expect(window.location.pathname).toBe('/vagas');
    expect(
      screen.getByRole('heading', { name: 'Oportunidade 37' }),
    ).toBeInTheDocument();
  });

  it('abre o diálogo global pelo próximo passo sem navegar nem expor campos na página', async () => {
    const request = setup({ locked: true });
    const action = await screen.findByRole('button', {
      name: 'Desbloquear cofre',
    });
    expect(screen.queryByLabelText('Senha do cofre')).not.toBeInTheDocument();
    fireEvent.click(action);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText('Senha do cofre')).toHaveFocus();
    expect(window.location.pathname).toBe('/');
    expect(
      request.mock.calls.some(([path]) => path === '/api/vault/unlock'),
    ).toBe(false);
  });

  it('não interpreta erro no pipeline como ausência de candidaturas', async () => {
    setup({ populated: true, failedApplication: true });
    await screen.findByRole('link', { name: 'Verificar vagas' });
    expect(
      within(
        screen.getByRole('region', { name: 'Resumo do acompanhamento' }),
      ).getAllByText('Indisponível'),
    ).toHaveLength(2);
  });

  it('distingue falha no carregamento de caixa vazia', async () => {
    setup({ failed: true });
    expect(
      await screen.findByRole('link', { name: 'Verificar vagas' }),
    ).toHaveAttribute('href', '/vagas');
    expect(screen.getByText('Resumo parcial')).toBeInTheDocument();
    expect(
      within(
        screen.getByRole('region', { name: 'Resumo do acompanhamento' }),
      ).getAllByText('Indisponível'),
    ).toHaveLength(2);
  });
});
