import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';

describe('App', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockImplementation(
      (_input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'PUT') {
          return Promise.resolve({
            json: async () => ({
              criteria: JSON.parse(init.body as string),
              profile_id: 1,
              version_number: 1,
            }),
            ok: true,
          });
        }

        return Promise.resolve({
          json: async () => null,
          ok: true,
        });
      },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

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

  it('abre o onboarding e salva critérios válidos no perfil local', async () => {
    render(<App />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/profile'));
    fireEvent.click(
      screen.getByRole('button', { name: 'Configurar meu perfil' }),
    );

    expect(
      screen.getByRole('heading', { name: 'Configure seu perfil' }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Cargos desejados'), {
      target: { value: 'Backend Engineer' },
    });
    fireEvent.change(screen.getByLabelText('Competências'), {
      target: { value: 'Python, FastAPI' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar perfil' }));

    await waitFor(() =>
      expect(screen.getByText('Perfil salvo localmente.')).toBeInTheDocument(),
    );

    const [, options] = fetchMock.mock.calls.at(-1) as [string, RequestInit];
    expect(options.method).toBe('PUT');
    expect(JSON.parse(options.body as string)).toMatchObject({
      skills: ['Python', 'FastAPI'],
      target_roles: ['Backend Engineer'],
      restrictions: { work_models: ['remote'] },
    });
  });

  it('exibe o histórico imutável e destaca a versão ativa', async () => {
    const history = [
      {
        created_at: '2026-08-01T10:00:00Z',
        criteria: {
          languages: [{ code: 'en', minimum_level: 'professional' }],
          restrictions: {
            excluded_keywords: [],
            locations: [],
            work_models: ['remote'],
          },
          salary_expectation: null,
          skills: ['Python'],
          target_roles: ['Backend Engineer'],
          weights: { experience: 35, location: 25, skills: 40 },
        },
        profile_id: 1,
        version_number: 1,
      },
      {
        created_at: '2026-08-15T10:00:00Z',
        criteria: {
          languages: [{ code: 'en', minimum_level: 'professional' }],
          restrictions: {
            excluded_keywords: [],
            locations: ['São Paulo'],
            work_models: ['hybrid'],
          },
          salary_expectation: null,
          skills: ['Python', 'FastAPI'],
          target_roles: ['Staff Backend Engineer'],
          weights: { experience: 35, location: 25, skills: 40 },
        },
        profile_id: 1,
        version_number: 2,
      },
    ];

    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'PUT') {
          return Promise.resolve({ json: async () => history[1], ok: true });
        }
        if (input === '/api/profile/versions') {
          return Promise.resolve({ json: async () => history, ok: true });
        }
        return Promise.resolve({ json: async () => history[1], ok: true });
      },
    );

    render(<App />);

    expect(
      await screen.findByRole('heading', {
        name: 'Cada versão preserva o contexto da busca.',
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Backend Engineer' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Staff Backend Engineer' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Versão 1')).toBeInTheDocument();
    expect(screen.getByText('Ativa')).toBeInTheDocument();
  });

  it('mostra a prévia exata do texto redigido antes da IA', async () => {
    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (input === '/api/privacy/redact') {
          return Promise.resolve({
            json: async () => ({
              redacted_text: 'Contato: [E-MAIL REMOVIDO].',
              replacements: [
                { count: 1, kind: 'email', token: '[E-MAIL REMOVIDO]' },
              ],
            }),
            ok: true,
          });
        }
        if (init?.method === 'PUT') {
          return Promise.resolve({ json: async () => null, ok: true });
        }
        return Promise.resolve({ json: async () => null, ok: true });
      },
    );

    render(<App />);
    fireEvent.click(
      screen.getByRole('button', { name: 'Configurar meu perfil' }),
    );
    fireEvent.change(screen.getByLabelText('Texto para análise da IA'), {
      target: { value: 'Contato: ana@example.com.' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'Gerar prévia segura' }),
    );

    expect(
      await screen.findByText('Contato: [E-MAIL REMOVIDO].'),
    ).toBeInTheDocument();
    expect(screen.getByText('1 e-mail removido')).toBeInTheDocument();
  });

  it('carrega e persiste preferências gerais aplicadas à interface', async () => {
    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (input === '/api/preferences' && init?.method === 'PUT') {
          return Promise.resolve({
            json: async () => ({
              currency: 'USD',
              locale: 'en-US',
              retention_days: 90,
              timezone: 'America/New_York',
            }),
            ok: true,
          });
        }
        if (input === '/api/preferences') {
          return Promise.resolve({
            json: async () => ({
              currency: 'BRL',
              locale: 'pt-BR',
              retention_days: 365,
              timezone: 'America/Sao_Paulo',
            }),
            ok: true,
          });
        }
        return Promise.resolve({ json: async () => null, ok: true });
      },
    );

    render(<App />);
    expect(
      await screen.findByRole('heading', { name: 'Preferências gerais' }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Idioma da interface'), {
      target: { value: 'en-US' },
    });
    fireEvent.change(screen.getByLabelText('Retenção local (dias)'), {
      target: { value: '90' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'Salvar preferências' }),
    );

    expect(
      await screen.findByText('Preferências salvas localmente.'),
    ).toBeInTheDocument();
    const [, options] = fetchMock.mock.calls.at(-1) as [string, RequestInit];
    expect(options.method).toBe('PUT');
    expect(JSON.parse(options.body as string)).toMatchObject({
      locale: 'en-US',
      retention_days: 90,
    });
  });
});
