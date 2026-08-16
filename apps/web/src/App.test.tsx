import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';

describe('App', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockImplementation(
      (_input: RequestInfo | URL, init?: RequestInit) => {
        if (_input === '/api/ai/settings') {
          return Promise.resolve({
            json: async () => ({
              configured: false,
              unlocked: false,
              model: 'gpt-5.6-luna',
              storage: 'not_configured',
            }),
            ok: true,
          });
        }
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

  it('reanalisisa somente as vagas selecionadas e preserva falhas parciais', async () => {
    const confirmMock = vi.fn(() => true);
    vi.stubGlobal('confirm', confirmMock);
    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (input === '/api/jobs') {
          return Promise.resolve({
            json: async () => ({
              items: [
                {
                  canonical_url: 'https://example.com/1',
                  company: 'Acme',
                  created_at: '2026-08-15T10:00:00Z',
                  id: 1,
                  location: 'Remoto',
                  origin_count: 1,
                  status: 'found',
                  status_label: 'ENCONTRADA',
                  title: 'Backend Engineer',
                },
              ],
            }),
            ok: true,
          });
        }
        if (input === '/api/jobs/1/analysis' && init?.method === 'POST') {
          return Promise.resolve({
            json: async () => ({
              analysis: {
                assessment: {
                  confidence: 90,
                  gaps: [],
                  strengths: ['Python'],
                  summary: 'Boa aderência.',
                  warnings: [],
                },
              },
              analysis_version: 1,
              explanation: { supported_evidence: [] },
              fit: { accepted: true, score: 82 },
              model: 'gpt-5.6-luna',
              prompt_version: '2026-08-15.1',
              usage: {
                estimated_cost_usd: 0.001,
                fallback: false,
                fallback_reason: null,
                input_tokens: 100,
                latency_ms: 30,
                metered: true,
                output_tokens: 50,
              },
            }),
            ok: true,
          });
        }
        return Promise.resolve({ json: async () => null, ok: true });
      },
    );

    render(<App />);
    expect(
      await screen.findByRole('heading', { name: 'Backend Engineer' }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Selecionar Backend Engineer'));
    fireEvent.click(screen.getByRole('button', { name: 'Analisar selecionadas' }));

    expect(confirmMock).toHaveBeenCalledWith('Analisar 1 vaga com a IA?');
    expect(
      await screen.findByText('1 análise concluída.'),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/jobs/1/analysis',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('envia a chave somente ao backend local e nunca a exibe novamente', async () => {
    const apiKey = 'sk-test-only-12345678901234567890';
    const vaultPassword = 'uma senha local longa';
    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (input === '/api/ai/settings') {
          return Promise.resolve({
            json: async () => ({
              configured: false,
              unlocked: false,
              model: 'gpt-5.6-luna',
              storage: 'not_configured',
            }),
            ok: true,
          });
        }
        if (input === '/api/ai/api-key' && init?.method === 'PUT') {
          return Promise.resolve({
            json: async () => ({
              configured: true,
              unlocked: true,
              model: 'gpt-5.6-luna',
              storage: 'encrypted_database',
            }),
            ok: true,
          });
        }
        if (input === '/api/ai/connection/test' && init?.method === 'POST') {
          return Promise.resolve({
            json: async () => ({ model: 'gpt-5.6-luna', status: 'connected' }),
            ok: true,
          });
        }
        return Promise.resolve({ json: async () => null, ok: true });
      },
    );

    render(<App />);

    expect(
      await screen.findByRole('heading', { name: 'Conecte sua chave OpenAI' }),
    ).toBeInTheDocument();
    const input = screen.getByLabelText('Chave da API OpenAI');
    expect(input).toHaveAttribute('type', 'password');
    fireEvent.change(input, { target: { value: apiKey } });
    fireEvent.change(
      screen.getByLabelText('Crie uma senha para o cofre local'),
      {
        target: { value: vaultPassword },
      },
    );
    fireEvent.change(screen.getByLabelText('Confirme a senha do cofre local'), {
      target: { value: vaultPassword },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'Criptografar e salvar chave' }),
    );

    expect(
      await screen.findByText('Chave criptografada e salva no banco local.'),
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText('Chave da API OpenAI'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText('Crie uma senha para o cofre local'),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(apiKey)).not.toBeInTheDocument();
    expect(screen.queryByText(vaultPassword)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Testar conexão' }));
    expect(
      await screen.findByText('Conexão com gpt-5.6-luna confirmada.'),
    ).toBeInTheDocument();
    const [, options] = fetchMock.mock.calls.find(
      ([calledInput, init]) =>
        calledInput === '/api/ai/api-key' && init?.method === 'PUT',
    ) as [string, RequestInit];
    expect(JSON.parse(options.body as string)).toEqual({
      api_key: apiKey,
      vault_password: vaultPassword,
    });
    expect(
      fetchMock.mock.calls.some(
        ([calledInput, init]) =>
          calledInput === '/api/ai/connection/test' && init?.method === 'POST',
      ),
    ).toBe(true);
  });

  it('carrega a caixa de entrada e adiciona uma vaga manual rapidamente', async () => {
    const jobs = {
      items: [
        {
          canonical_url: 'https://jobs.example.com/backend-1',
          company: 'Example Labs',
          created_at: '2026-08-15T10:00:00Z',
          id: 1,
          location: 'São Paulo',
          origin_count: 1,
          status: 'found',
          status_label: 'ENCONTRADA',
          title: 'Backend Engineer',
        },
      ],
      page: 1,
      page_size: 20,
      pages: 1,
      total: 1,
    };

    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (input === '/api/jobs' && init?.method === 'POST') {
          return Promise.resolve({
            json: async () => ({
              canonical_url: 'https://jobs.example.com/data-2',
              company: 'Data Co',
              created_at: '2026-08-15T11:00:00Z',
              id: 2,
              location: null,
              origins: [{ id: 2, source: 'manual', url: null }],
              status: 'found',
              status_label: 'ENCONTRADA',
              title: 'Data Engineer',
            }),
            ok: true,
          });
        }
        if (input === '/api/jobs') {
          return Promise.resolve({ json: async () => jobs, ok: true });
        }
        if (init?.method === 'PUT') {
          return Promise.resolve({ json: async () => null, ok: true });
        }
        return Promise.resolve({ json: async () => null, ok: true });
      },
    );

    render(<App />);

    expect(
      await screen.findByRole('heading', { name: 'Caixa de entrada de vagas' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar vaga' }));
    fireEvent.change(screen.getByLabelText('URL canônica'), {
      target: { value: 'https://jobs.example.com/data-2' },
    });
    fireEvent.change(screen.getByLabelText('Título da vaga'), {
      target: { value: 'Data Engineer' },
    });
    fireEvent.change(screen.getByLabelText('Empresa'), {
      target: { value: 'Data Co' },
    });
    fireEvent.change(screen.getByLabelText('Conteúdo da vaga'), {
      target: { value: 'Descrição de Data Engineer' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar vaga' }));

    expect(
      await screen.findByText('Vaga adicionada à caixa de entrada.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Data Engineer')).toBeInTheDocument();
    const [, options] = fetchMock.mock.calls.find(
      ([input, init]) => input === '/api/jobs' && init?.method === 'POST',
    ) as [string, RequestInit];
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body as string)).toMatchObject({
      company: 'Data Co',
      title: 'Data Engineer',
    });
  });

  it('exibe fontes de busca e inicia uma execução com contadores auditáveis', async () => {
    const sources = [
      {
        backoff_until: null,
        consecutive_failures: 0,
        daily_limit: 50,
        data_format: 'json',
        display_name: 'Remote OK',
        enabled: true,
        endpoint: 'https://remoteok.com/api',
        frequency_minutes: 1440,
        id: 1,
        last_error: null,
        last_run_at: null,
        next_run_at: null,
        per_run_limit: 50,
        schedule_enabled: false,
        source_key: 'remoteok',
        terms_url: 'https://remoteok.com/terms',
        timeout_seconds: 15,
      },
    ];
    const run = {
      approximate_duplicates: 1,
      candidates_seen: 4,
      cancellation_requested: false,
      current_cursor: null,
      duration_ms: 120,
      error_message: null,
      exact_duplicates: 1,
      finished_at: null,
      id: 1,
      jobs_created: 2,
      query: { query: 'Backend Engineer' },
      requested_at: '2026-08-15T10:00:00Z',
      source_key: 'remoteok',
      source_name: 'Remote OK',
      started_at: null,
      status: 'running',
    };

    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (input === '/api/sources') {
          return Promise.resolve({ json: async () => sources, ok: true });
        }
        if (input === '/api/search-runs?limit=12') {
          return Promise.resolve({ json: async () => [], ok: true });
        }
        if (input === '/api/search-runs' && init?.method === 'POST') {
          return Promise.resolve({ json: async () => run, ok: true });
        }
        if (init?.method === 'PUT') {
          return Promise.resolve({ json: async () => sources[0], ok: true });
        }
        return Promise.resolve({ json: async () => null, ok: true });
      },
    );

    render(<App />);

    expect(
      await screen.findByRole('heading', { name: 'Fontes e execuções' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Remote OK' }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Cargo ou palavra-chave'), {
      target: { value: 'Backend Engineer' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar agora' }));

    expect(
      await screen.findByText('Busca iniciada em Remote OK.'),
    ).toBeInTheDocument();
    expect(screen.getByText('1 para revisar')).toBeInTheDocument();
    const [, options] = fetchMock.mock.calls.find(
      ([input, init]) =>
        input === '/api/search-runs' && init?.method === 'POST',
    ) as [string, RequestInit];
    expect(JSON.parse(options.body as string)).toMatchObject({
      query: 'Backend Engineer',
      source_key: 'remoteok',
    });
  });

  it('abre o detalhe seguro sem executar HTML externo', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      if (input === '/api/jobs') {
        return Promise.resolve({
          json: async () => ({
            items: [
              {
                canonical_url: 'https://jobs.example.com/backend-1',
                company: 'Example Labs',
                created_at: '2026-08-15T10:00:00Z',
                id: 1,
                location: 'São Paulo',
                origin_count: 1,
                status: 'found',
                status_label: 'ENCONTRADA',
                title: 'Backend Engineer',
              },
            ],
            page: 1,
            page_size: 20,
            pages: 1,
            total: 1,
          }),
          ok: true,
        });
      }
      if (input === '/api/jobs/1') {
        return Promise.resolve({
          json: async () => ({
            canonical_url: 'https://jobs.example.com/backend-1',
            company: 'Example Labs',
            content_versions: [
              {
                captured_at: '2026-08-15T10:00:00Z',
                content_type: 'text/plain',
                id: 1,
                raw_content: '<script>alert(1)</script> Python e FastAPI',
                valid_from: '2026-08-15T10:00:00Z',
                valid_until: null,
                version_number: 1,
              },
            ],
            created_at: '2026-08-15T10:00:00Z',
            expires_at: null,
            id: 1,
            location: 'São Paulo',
            origins: [
              {
                external_id: null,
                id: 1,
                source: 'manual',
                url: 'https://jobs.example.com/backend-1',
              },
            ],
            published_at: null,
            status: 'found',
            status_label: 'ENCONTRADA',
            title: 'Backend Engineer',
            updated_at: '2026-08-15T10:00:00Z',
          }),
          ok: true,
        });
      }
      return Promise.resolve({ json: async () => null, ok: true });
    });

    render(<App />);
    await screen.findByText('Backend Engineer');
    fireEvent.click(screen.getByRole('button', { name: 'Ver detalhes' }));

    expect(
      await screen.findByRole('heading', { name: 'Detalhe da vaga' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('<script>alert(1)</script> Python e FastAPI'),
    ).toBeInTheDocument();
    expect(document.querySelector('.job-detail-content script')).toBeNull();
    expect(screen.getByText('manual')).toBeInTheDocument();
  });

  it('exibe o pipeline e move uma candidatura por teclado', async () => {
    const job = {
      canonical_url: 'https://jobs.example.com/backend-1',
      company: 'Example Labs',
      created_at: '2026-08-15T10:00:00Z',
      id: 1,
      location: 'São Paulo',
      origin_count: 1,
      status: 'found',
      status_label: 'ENCONTRADA',
      title: 'Backend Engineer',
    };
    const application = {
      created_at: '2026-08-15T10:05:00Z',
      current_status: 'found',
      events: [],
      id: 7,
      job_id: 1,
      updated_at: '2026-08-15T10:05:00Z',
    };

    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (input === '/api/jobs') {
          return Promise.resolve({
            json: async () => ({ items: [job] }),
            ok: true,
          });
        }
        if (input === '/api/jobs/1/application') {
          return Promise.resolve({ json: async () => application, ok: true });
        }
        if (input === '/api/applications/7/transition') {
          return Promise.resolve({
            json: async () => ({
              ...application,
              current_status: 'applied',
              updated_at: '2026-08-15T10:06:00Z',
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

    expect(
      await screen.findByRole('heading', { name: 'Pipeline de candidaturas' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument();
    fireEvent.change(
      await screen.findByLabelText('Próxima fase para Backend Engineer'),
      { target: { value: 'applied' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Mover candidatura' }));

    await waitFor(() =>
      expect(screen.getAllByText('APLICADA').length).toBeGreaterThanOrEqual(1),
    );
    const transitionCall = fetchMock.mock.calls.find(
      ([input]) => input === '/api/applications/7/transition',
    );
    expect(transitionCall).toBeDefined();
    expect(JSON.parse(transitionCall?.[1]?.body as string)).toMatchObject({
      to_status: 'applied',
    });
  });

  it('reverte a movimentação otimista quando a transição é rejeitada', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      if (input === '/api/jobs') {
        return Promise.resolve({
          json: async () => ({
            items: [
              {
                canonical_url: null,
                company: 'Example Labs',
                created_at: '2026-08-15T10:00:00Z',
                id: 1,
                location: null,
                origin_count: 1,
                status: 'found',
                status_label: 'ENCONTRADA',
                title: 'Backend Engineer',
              },
            ],
          }),
          ok: true,
        });
      }
      if (input === '/api/jobs/1/application') {
        return Promise.resolve({
          json: async () => ({
            created_at: '2026-08-15T10:05:00Z',
            current_status: 'found',
            events: [],
            id: 7,
            job_id: 1,
            updated_at: '2026-08-15T10:05:00Z',
          }),
          ok: true,
        });
      }
      if (input === '/api/applications/7/transition') {
        return Promise.resolve({
          json: async () => ({ detail: 'Transição não permitida.' }),
          ok: false,
        });
      }
      return Promise.resolve({ json: async () => null, ok: true });
    });

    render(<App />);
    await screen.findByRole('heading', { name: 'Pipeline de candidaturas' });
    fireEvent.change(
      await screen.findByLabelText('Próxima fase para Backend Engineer'),
      { target: { value: 'interview' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Mover candidatura' }));

    expect(
      await screen.findByText(
        'Não foi possível mover Backend Engineer. A fase foi restaurada.',
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText('ENCONTRADA').length).toBeGreaterThanOrEqual(1);
  });

  it('exibe a agenda com próximos eventos e prazos vencidos', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      if (input === '/api/events') {
        return Promise.resolve({
          json: async () => [
            {
              application_id: 7,
              ends_at: '2099-08-15T12:00:00Z',
              id: 1,
              kind: 'interview',
              link: 'https://meet.example.com/room',
              notes: null,
              participants: ['ana@example.com'],
              starts_at: '2099-08-15T11:00:00Z',
              status: 'scheduled',
              timezone_name: 'UTC',
              title: 'Entrevista técnica',
            },
            {
              application_id: 7,
              ends_at: null,
              id: 2,
              kind: 'deadline',
              link: null,
              notes: 'Enviar exercício',
              participants: [],
              starts_at: '2020-08-01T11:00:00Z',
              status: 'scheduled',
              timezone_name: 'UTC',
              title: 'Prazo do desafio',
            },
          ],
          ok: true,
        });
      }
      return Promise.resolve({ json: async () => null, ok: true });
    });

    render(<App />);

    expect(
      await screen.findByRole('heading', {
        name: 'Agenda do processo seletivo',
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('Entrevista técnica')).toBeInTheDocument();
    expect(screen.getByText('Prazo do desafio')).toBeInTheDocument();
    expect(screen.getByText('PRÓXIMO')).toBeInTheDocument();
    expect(screen.getByText('VENCIDO')).toBeInTheDocument();
  });

  it('lista a lixeira e restaura uma vaga sem perder o controle local', async () => {
    fetchMock.mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        if (input === '/api/trash') {
          return Promise.resolve({
            json: async () => [
              {
                company: 'Example Labs',
                deleted_at: '2026-08-15T10:00:00Z',
                id: 3,
                purge_after: '2027-08-15T10:00:00Z',
                status: 'found',
                title: 'Data Engineer',
              },
            ],
            ok: true,
          });
        }
        if (input === '/api/jobs/3/restore' && init?.method === 'POST') {
          return Promise.resolve({
            json: async () => ({
              company: 'Example Labs',
              deleted_at: null,
              id: 3,
              purge_after: null,
              status: 'found',
              title: 'Data Engineer',
            }),
            ok: true,
          });
        }
        if (input === '/api/jobs') {
          return Promise.resolve({
            json: async () => ({ items: [] }),
            ok: true,
          });
        }
        return Promise.resolve({ json: async () => null, ok: true });
      },
    );

    render(<App />);

    expect(
      await screen.findByRole('heading', { name: 'Lixeira recuperável' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Data Engineer')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Restaurar vaga' }));

    await waitFor(() =>
      expect(screen.queryByText('Data Engineer')).not.toBeInTheDocument(),
    );
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) =>
          input === '/api/jobs/3/restore' && init?.method === 'POST',
      ),
    ).toBe(true);
  });
});
