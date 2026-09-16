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
  id: 1,
  title: 'Analista de Dados',
  company: 'Empresa',
  status: 'applied',
  status_label: 'APLICADA',
  origin_count: 1,
  created_at: '2026-09-01T10:00:00Z',
  canonical_url: null,
  location: null,
};
const stored = {
  version_number: 2,
  analysis: {
    assessment: {
      summary: 'Perfil alinhado.',
      confidence: 80,
      strengths: ['SQL'],
      gaps: [],
      warnings: [],
    },
  },
  fit: { score: 88 },
  explanation: { supported_evidence: [] },
  usage: { fallback: false, estimated_cost_usd: 0.001 },
  model: 'gpt-5.6-luna',
};
function setup(
  path: string,
  { populated = false, analysisError = false } = {},
) {
  const request = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
    if (url === '/api/jobs/1/analyses' && analysisError)
      return new Response('{}', { status: 500 });
    let data: unknown = null;
    if (url === '/api/jobs')
      data = {
        items: populated ? [job] : [],
        page: 1,
        pages: 1,
        page_size: 50,
      };
    if (url === '/api/jobs/1')
      data = { ...job, origins: [], content_versions: [] };
    if (url === '/api/jobs/1/application')
      data = {
        id: 4,
        job_id: 1,
        current_status: 'applied',
        events: [],
        created_at: '',
        updated_at: '',
      };
    if (url === '/api/jobs/1/analyses') data = [stored];
    if (url === '/api/scheduled-searches')
      data =
        init?.method === 'POST'
          ? { ...JSON.parse(init.body as string), id: 5, last_run_at: null }
          : [];
    if (url === '/api/events') data = [];
    return new Response(JSON.stringify(data));
  });
  vi.stubGlobal('fetch', request);
  window.history.replaceState({}, '', path);
  render(<App />);
  return request;
}
describe('JF-818 acompanhamento', () => {
  it('cria agenda diretamente com filtros próprios, sem depender da busca manual', async () => {
    const request = setup('/agenda');
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    fireEvent.change(screen.getByLabelText('Nome da agenda'), {
      target: { value: 'Dados diário' },
    });
    fireEvent.change(screen.getByLabelText('Cargo da busca automática'), {
      target: { value: ' Analista de Dados ' },
    });
    fireEvent.change(screen.getByLabelText('Localização da busca automática'), {
      target: { value: ' Curitiba ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar agenda' }));
    expect(
      await screen.findByRole('heading', { name: 'Dados diário' }),
    ).toBeInTheDocument();
    const call = request.mock.calls.find(
      ([url, init]) =>
        url === '/api/scheduled-searches' && init?.method === 'POST',
    );
    expect(JSON.parse(call?.[1]?.body as string)).toMatchObject({
      query: 'Analista de Dados',
      location: 'Curitiba',
      enabled: false,
    });
    expect(
      screen.getByRole('heading', { name: 'Compromissos' }),
    ).toBeInTheDocument();
  });
  it('filtra o pipeline por fase sem perder candidaturas ao voltar', async () => {
    setup('/candidaturas', { populated: true });
    await screen.findByText('Analista de Dados');
    fireEvent.change(screen.getByLabelText('Filtrar por fase'), {
      target: { value: 'interview' },
    });
    expect(screen.queryByText('Analista de Dados')).not.toBeInTheDocument();
    expect(
      screen.getByText('Nenhuma candidatura nesta fase.'),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Filtrar por fase'), {
      target: { value: 'all' },
    });
    expect(screen.getByText('Analista de Dados')).toBeInTheDocument();
  });
  it('recupera análises salvas nos insights sem executar IA e abre a vaga correta', async () => {
    const request = setup('/insights', { populated: true });
    const analysis = await screen.findByRole('region', {
      name: 'Análises disponíveis',
    });
    fireEvent.click(
      await within(analysis).findByRole('button', {
        name: 'Ver análise de Analista de Dados',
      }),
    );
    expect(window.location.pathname).toBe('/vagas');
    expect(
      await screen.findByRole('heading', {
        name: 'Análise de Analista de Dados',
      }),
    ).toBeInTheDocument();
    expect(
      request.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith('/analysis') && init?.method === 'POST',
      ),
    ).toBe(false);
  });
  it('não trata falha ao carregar análises como ausência de análise', async () => {
    setup('/insights', { populated: true, analysisError: true });
    expect(
      await screen.findByText(
        'Não foi possível carregar todas as análises salvas.',
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Nenhuma análise disponível'),
    ).not.toBeInTheDocument();
  });
  it('oferece próximo passo no pipeline vazio', async () => {
    setup('/candidaturas');
    fireEvent.click(
      await screen.findByRole('button', { name: 'Revisar vagas' }),
    );
    expect(window.location.pathname).toBe('/vagas');
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: 'Caixa de entrada de vagas' }),
      ).toBeInTheDocument(),
    );
  });
});
