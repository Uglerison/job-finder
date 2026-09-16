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
const job = (id: number) => ({
  id,
  title: 'Vaga ' + id,
  company: 'Empresa',
  location: 'Curitiba',
  status: 'found',
  status_label: 'ENCONTRADA',
  origin_count: 1,
  canonical_url: 'https://example.com/' + id,
  created_at: '2026-09-01T10:00:00Z',
});
const detail = (id: number) => ({
  ...job(id),
  origins: [],
  content_versions: [
    {
      id,
      version_number: 1,
      raw_content: 'SQL e Python',
      content_type: 'text',
      valid_from: '',
      valid_until: null,
    },
  ],
});
const analysis = {
  analysis_version: 1,
  analysis: {
    assessment: {
      summary: 'Combina com seu perfil.',
      strengths: ['SQL comprovado'],
      gaps: ['Inglês não informado'],
      warnings: [],
      confidence: 80,
    },
  },
  explanation: {
    supported_evidence: [{ claim: 'SQL', quote: 'SQL e Python' }],
  },
  fit: { accepted: true, score: 85 },
  usage: { fallback: false, estimated_cost_usd: 0.001 },
  model: 'gpt-5.6-luna',
};
function setup({ total = 2, slowDetail = false, slowAnalysis = false } = {}) {
  let releaseDetail!: (value: Response) => void;
  let releaseAnalysis!: (value: Response) => void;
  const request = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
    if (url === '/api/jobs/1' && slowDetail)
      return new Promise<Response>((resolve) => {
        releaseDetail = resolve;
      });
    if (
      url === '/api/jobs/1/analysis' &&
      init?.method === 'POST' &&
      slowAnalysis
    )
      return new Promise<Response>((resolve) => {
        releaseAnalysis = resolve;
      });
    if (url === '/api/jobs/1/analysis' && init?.method === 'POST')
      return new Response(JSON.stringify(analysis));
    const data =
      url === '/api/jobs'
        ? {
            items: Array.from({ length: Math.min(total, 25) }, (_, i) =>
              job(i + 1),
            ),
            page: 1,
            pages: Math.ceil(total / 25),
            page_size: 25,
          }
        : String(url).startsWith('/api/jobs?')
          ? {
              items: Array.from({ length: total - 25 }, (_, i) => job(i + 26)),
              page: 2,
              pages: 2,
              page_size: 25,
            }
          : url === '/api/jobs/1'
            ? detail(1)
            : url === '/api/jobs/2'
              ? detail(2)
              : url === '/api/saved-filters'
                ? []
                : null;
    return new Response(JSON.stringify(data));
  });
  vi.stubGlobal('fetch', request);
  vi.stubGlobal('confirm', () => true);
  window.history.replaceState({}, '', '/vagas');
  render(<App />);
  return {
    request,
    finishDetail: () => releaseDetail(new Response(JSON.stringify(detail(1)))),
    finishAnalysis: () =>
      releaseAnalysis(new Response(JSON.stringify(analysis))),
  };
}
describe('JF-817 caixa e análise contextual', () => {
  it('oferece lista e painel de detalhe separados, com filtros salvos recolhidos', async () => {
    setup();
    expect(
      await screen.findByRole('region', { name: 'Oportunidades salvas' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('region', { name: 'Revisão da vaga' }),
    ).toHaveTextContent('Selecione uma vaga');
    expect(
      screen.getByText('Filtros salvos').closest('details'),
    ).not.toHaveAttribute('open');
  });
  it('mantém todas as páginas acessíveis e informa contagem ao filtrar', async () => {
    setup({ total: 37 });
    await screen.findByRole('heading', { name: 'Vaga 37' });
    expect(screen.getByText('37 de 37 vagas')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Buscar na caixa de entrada'), {
      target: { value: 'Vaga 37' },
    });
    expect(screen.getByText('1 de 37 vagas')).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'Vaga 1' }),
    ).not.toBeInTheDocument();
  });
  it('descarta detalhe antigo que termine depois da seleção mais recente', async () => {
    const controls = setup({ slowDetail: true });
    await screen.findByRole('heading', { name: 'Vaga 1' });
    fireEvent.click(screen.getAllByRole('button', { name: 'Ver detalhes' })[0]);
    fireEvent.click(screen.getAllByRole('button', { name: 'Ver detalhes' })[1]);
    await waitFor(() =>
      expect(
        screen.getByRole('region', { name: 'Revisão da vaga' }),
      ).toHaveTextContent('Vaga 2'),
    );
    controls.finishDetail();
    await waitFor(() =>
      expect(screen.queryByText('Carregando detalhe…')).not.toBeInTheDocument(),
    );
    expect(
      screen.getByRole('region', { name: 'Revisão da vaga' }),
    ).not.toHaveTextContent('Vaga 1');
  });
  it('associa análise pendente e completa à vaga correta e exibe forças e lacunas no detalhe', async () => {
    const controls = setup({ slowAnalysis: true });
    await screen.findByLabelText('Selecionar Vaga 1');
    fireEvent.click(screen.getByLabelText('Selecionar Vaga 1'));
    fireEvent.click(
      screen.getByRole('button', { name: 'Analisar selecionadas' }),
    );
    expect(
      await screen.findByLabelText('Análise em andamento: Vaga 1'),
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText('Análise em andamento: Vaga 2'),
    ).not.toBeInTheDocument();
    controls.finishAnalysis();
    await screen.findByRole('region', { name: 'Análise concluída: Vaga 1' });
    fireEvent.click(
      screen.getByRole('button', { name: 'Abrir análise completa de Vaga 1' }),
    );
    const review = screen.getByRole('region', { name: 'Revisão da vaga' });
    expect(
      await within(review).findByText('SQL comprovado'),
    ).toBeInTheDocument();
    expect(
      within(review).getByText('Inglês não informado'),
    ).toBeInTheDocument();
    expect(
      within(review).getByRole('heading', { name: 'Análise de Vaga 1' }),
    ).toBeInTheDocument();
  });
});
