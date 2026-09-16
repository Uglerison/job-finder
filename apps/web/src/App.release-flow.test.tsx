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

const job = {
  id: 91,
  title: 'Pessoa Analista de Dados',
  company: 'Empresa Exemplo',
  location: 'Remoto',
  status: 'found',
  status_label: 'ENCONTRADA',
  origin_count: 1,
  canonical_url: 'https://example.com/vaga-91',
  created_at: '2026-09-05T10:00:00Z',
};

const detail = {
  ...job,
  origins: [],
  content_versions: [
    {
      id: 1,
      version_number: 1,
      raw_content: 'SQL, Python e análise de dados.',
      content_type: 'text',
      valid_from: '2026-09-05T10:00:00Z',
      valid_until: null,
    },
  ],
};

const analysis = {
  analysis_version: 1,
  analysis: {
    assessment: {
      summary: 'A vaga combina com o perfil.',
      strengths: ['SQL e Python'],
      gaps: [],
      warnings: [],
      confidence: 90,
    },
  },
  explanation: {
    supported_evidence: [
      { claim: 'SQL', quote: 'SQL, Python e análise de dados.' },
    ],
  },
  fit: { accepted: true, score: 92 },
  usage: { fallback: false, estimated_cost_usd: 0.001 },
  model: 'gpt-5.6-luna',
};

describe('JF-820 fluxo principal entre rotas', () => {
  it('desbloqueia, busca, avalia, aplica e acompanha sem perder o estado', async () => {
    let unlocked = false;
    let applied = false;
    const request = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);

        if (url === '/api/vault/unlock') unlocked = true;
        if (
          url === '/api/jobs/91/application/applied' &&
          init?.method === 'POST'
        ) {
          applied = true;
        }

        let payload: unknown = null;
        let status = 200;
        if (url.startsWith('/api/vault')) {
          payload = { configured: true, unlocked };
        } else if (url === '/api/search/providers') {
          payload = [
            {
              provider: 'jsearch',
              configured: true,
              unlocked,
              storage: 'encrypted_database',
            },
          ];
        } else if (url === '/api/sources') {
          payload = [
            {
              source_key: 'remoteok',
              display_name: 'Remote OK',
              enabled: true,
            },
          ];
        } else if (url === '/api/search') {
          payload = {
            jobs: [
              {
                job_id: 91,
                review_required: false,
                title: job.title,
                company: job.company,
                description: 'SQL e Python',
                url: job.canonical_url,
                source: 'JSearch',
                location: job.location,
                work_model: 'remote',
                published_at: null,
                salary: null,
              },
            ],
            cache_hit: false,
            message: 'Encontramos 1 vaga.',
            outcome: 'results',
            partial: false,
            provider_runs: [],
            warnings: [],
          };
        } else if (url === '/api/jobs') {
          payload = { items: [job], page: 1, pages: 1, page_size: 50 };
        } else if (url === '/api/jobs/91') payload = detail;
        else if (url === '/api/jobs/91/analyses') payload = [];
        else if (url === '/api/jobs/91/analysis' && init?.method === 'POST') {
          payload = analysis;
        } else if (url === '/api/jobs/91/application/applied') {
          payload = {
            id: 31,
            job_id: 91,
            current_status: 'applied',
            events: [],
            created_at: '2026-09-05T10:05:00Z',
            updated_at: '2026-09-05T10:05:00Z',
          };
        } else if (url === '/api/jobs/91/application') {
          if (applied) {
            payload = {
              id: 31,
              job_id: 91,
              current_status: 'applied',
              events: [],
              created_at: '2026-09-05T10:05:00Z',
              updated_at: '2026-09-05T10:05:00Z',
            };
          } else {
            status = 404;
            payload = { detail: 'Candidatura não encontrada.' };
          }
        } else if (url === '/api/events' || url === '/api/scheduled-searches') {
          payload = [];
        }

        return new Response(JSON.stringify(payload), { status });
      },
    );

    vi.stubGlobal('fetch', request);
    vi.stubGlobal('confirm', () => true);
    window.history.replaceState({}, '', '/busca');
    render(<App />);

    fireEvent.change(screen.getByLabelText('Cargo ou palavra-chave'), {
      target: { value: 'Analista de Dados' },
    });
    await screen.findByText('Desbloqueie o cofre para usar suas integrações.');
    fireEvent.click(screen.getByRole('button', { name: 'Buscar vagas' }));

    const password = await screen.findByLabelText('Senha do cofre');
    fireEvent.change(password, { target: { value: 'senha local longa' } });
    fireEvent.submit(
      within(screen.getByRole('dialog'))
        .getByRole('button', { name: 'Desbloquear cofre' })
        .closest('form')!,
    );

    const result = await screen.findByRole('region', {
      name: 'Resultados da busca unificada',
    });
    fireEvent.click(
      within(result).getByRole('link', { name: /Revisar oportunidades/ }),
    );

    expect(window.location.pathname).toBe('/vagas');
    await screen.findByRole('heading', { name: job.title });
    fireEvent.click(screen.getByRole('button', { name: 'Ver detalhes' }));

    const review = screen.getByRole('region', { name: 'Revisão da vaga' });
    fireEvent.click(
      await within(review).findByRole('button', {
        name: 'Analisar esta vaga com IA',
      }),
    );
    expect(
      await within(review).findByRole('heading', {
        name: `Análise de ${job.title}`,
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      within(review).getByRole('button', { name: 'Marcar como aplicada' }),
    );
    expect(
      await screen.findByText(`Vaga marcada como aplicada: ${job.title}.`),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: 'Candidaturas' }));
    expect(window.location.pathname).toBe('/candidaturas');
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: job.title }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole('heading', { level: 3, name: 'APLICADA' }),
    ).toBeInTheDocument();
    expect(
      request.mock.calls.filter(([url]) => String(url) === '/api/search'),
    ).toHaveLength(1);
  });
});
