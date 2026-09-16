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

const opportunity = {
  job_id: 41 as number | null,
  review_required: false,
  title: 'Analista de Dados Pleno',
  company: 'Empresa',
  description: 'SQL e Python',
  url: 'https://example.com/41',
  source: 'Fonte pública',
  location: null,
  work_model: 'remote',
  published_at: null,
  salary: null,
};
const success = {
  cache_hit: false,
  jobs: [opportunity],
  message: 'Encontramos 1 vaga.',
  outcome: 'results',
  partial: false,
  provider_runs: [],
  warnings: [],
};
function setup({
  locked = false,
  source = true,
  sourceError = false,
  refreshError = false,
  result = success,
  waitForSearch = null as Promise<void> | null,
} = {}) {
  let searched = false;
  let failNext = false;
  const request = vi.fn(async (input: RequestInfo | URL) => {
    if (input === '/api/search') {
      searched = true;
      await waitForSearch;
      if (failNext) throw new TypeError('Failed to fetch');
      return new Response(JSON.stringify(result));
    }
    if (
      (input === '/api/sources' && sourceError) ||
      (input === '/api/jobs' && searched && refreshError)
    )
      return new Response('{}', { status: 500 });
    const payload =
      input === '/api/search/providers'
        ? locked
          ? [
              {
                provider: 'jsearch',
                configured: true,
                unlocked: false,
                storage: 'encrypted_database',
              },
            ]
          : []
        : input === '/api/vault'
          ? { configured: locked, unlocked: false }
          : input === '/api/sources'
            ? source
              ? [
                  {
                    source_key: 'remoteok',
                    display_name: 'Remote OK',
                    enabled: true,
                  },
                ]
              : []
            : input === '/api/jobs'
              ? { items: [], total: 0, pages: 1, page: 1, page_size: 50 }
              : null;
    return new Response(JSON.stringify(payload));
  });
  vi.stubGlobal('fetch', request);
  window.history.replaceState({}, '', '/busca');
  render(<App />);
  return {
    request,
    failNextSearch: () => {
      failNext = true;
    },
  };
}
async function search() {
  fireEvent.change(screen.getByLabelText('Cargo ou palavra-chave'), {
    target: { value: '  Dados  ' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar vagas' }));
  return screen.findByRole('region', { name: 'Resultados da busca unificada' });
}

describe('busca como uma tarefa única', () => {
  it('mostra a consulta em andamento e impede novo envio até a resposta', async () => {
    let finish!: () => void;
    const waitForSearch = new Promise<void>((resolve) => {
      finish = resolve;
    });
    const { request } = setup({ waitForSearch });
    expect(screen.getByText('Verificando fontes…')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Cargo ou palavra-chave'), {
      target: { value: 'Dados' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar vagas' }));
    expect(
      await screen.findByText(
        'Consultando fontes e organizando oportunidades…',
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Buscando…' })).toBeDisabled();
    expect(screen.getByLabelText('Cargo ou palavra-chave')).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Buscando…' }));
    expect(
      request.mock.calls.filter(([url]) => url === '/api/search'),
    ).toHaveLength(1);
    finish();
    const region = await screen.findByRole('region', {
      name: 'Resultados da busca unificada',
    });
    await waitFor(() => expect(region.parentElement).toHaveFocus());
  });

  it('identifica cache e não conta duas vezes a mesma vaga persistida', async () => {
    setup({
      result: { ...success, cache_hit: true, jobs: [opportunity, opportunity] },
    });
    const region = await search();
    expect(
      within(region).getByText('RESULTADO REUTILIZADO · CACHE'),
    ).toBeInTheDocument();
    expect(
      within(region).getByText('1 vaga disponível na caixa de entrada.'),
    ).toBeInTheDocument();
  });

  it('resultado parcial vazio não afirma que não existem vagas', async () => {
    setup({
      result: { ...success, outcome: 'partial', partial: true, jobs: [] },
    });
    const region = await search();
    expect(
      within(region).getByRole('heading', {
        name: 'Busca parcialmente concluída',
      }),
    ).toBeInTheDocument();
    expect(
      within(region).queryByRole('heading', {
        name: 'Nenhuma vaga para estes filtros',
      }),
    ).not.toBeInTheDocument();
    expect(
      within(region).getByText(/Nem todas as fontes responderam/),
    ).toBeInTheDocument();
  });
  it('prioriza formulário, usa fontes públicas sem chave e mantém configurações fora da página', async () => {
    setup();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Buscar vagas' }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText('1 fonte habilitada para a busca.'),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/senha/i)).not.toBeInTheDocument();
  });

  it('sinaliza cofre bloqueado e abre o diálogo global sem perder os filtros', async () => {
    setup({ locked: true });
    expect(
      await screen.findByText(
        'Desbloqueie o cofre para usar suas integrações.',
      ),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Cargo ou palavra-chave'), {
      target: { value: 'Dados' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Desbloquear cofre' }));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText('Cargo ou palavra-chave')).toHaveValue(
      'Dados',
    );
  });

  it('não confunde falta de fontes com falha ao consultar a configuração', async () => {
    setup({ source: false });
    expect(
      await screen.findByText('Nenhuma fonte habilitada.'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Configurar fontes' }),
    ).toHaveAttribute('href', '/configuracoes/fontes');
  });

  it('informa que não conseguiu verificar fontes sem declarar ausência de configuração', async () => {
    setup({ sourceError: true });
    expect(
      await screen.findByText('Não foi possível verificar todas as fontes.'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Nenhuma fonte habilitada.'),
    ).not.toBeInTheDocument();
  });

  it.each([
    ['results', 'Busca concluída'],
    ['no_results', 'Nenhuma vaga para estes filtros'],
    ['partial', 'Busca parcialmente concluída'],
    ['not_configured', 'Configure uma fonte para buscar'],
    ['rate_limited', 'Limite de consultas atingido'],
    ['failed', 'Não foi possível concluir a busca'],
  ])('distingue o resultado %s', async (outcome, title) => {
    setup({
      result: {
        ...success,
        outcome,
        jobs:
          outcome === 'results' || outcome === 'partial' ? [opportunity] : [],
        message: 'Mensagem do serviço.',
        partial: outcome === 'partial',
      },
    });
    const region = await search();
    expect(
      within(region).getByRole('heading', { name: title }),
    ).toBeInTheDocument();
    expect(
      within(region).getByText('Mensagem do serviço.'),
    ).toBeInTheDocument();
    expect(
      within(region)
        .getByText('Ver detalhes da busca e do log')
        .closest('details'),
    ).not.toHaveAttribute('open');
    if (outcome === 'rate_limited')
      expect(
        within(region).getByText(/Aguarde a renovação do limite/),
      ).toBeInTheDocument();
  });

  it('resume a busca, identifica os filtros enviados e leva às vagas sem cards de candidatura', async () => {
    setup();
    const region = await search();
    expect(
      within(region).getByText('1 vaga disponível na caixa de entrada.'),
    ).toBeInTheDocument();
    expect(
      within(region).queryByText(opportunity.title),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Marcar como aplicada' }),
    ).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Cargo ou palavra-chave'), {
      target: { value: 'Produto' },
    });
    expect(
      within(region).getByText(
        /Dados · Qualquer localização · Todas as modalidades/,
      ),
    ).toBeInTheDocument();
    fireEvent.click(
      within(region).getByRole('link', { name: /Revisar oportunidades/ }),
    );
    expect(window.location.pathname).toBe('/vagas');
    fireEvent.click(screen.getByRole('link', { name: 'Buscar' }));
    expect(screen.getByLabelText('Cargo ou palavra-chave')).toHaveValue(
      'Produto',
    );
    expect(
      screen.getByRole('heading', { name: 'Busca concluída' }),
    ).toBeInTheDocument();
  });

  it('não mantém resultado antigo como sucesso depois de falhar uma nova busca', async () => {
    const controls = setup();
    await search();
    controls.failNextSearch();
    fireEvent.click(screen.getByRole('button', { name: 'Buscar vagas' }));
    expect(
      await screen.findByText(/Não foi possível conectar ao serviço local/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'Busca concluída' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('region', { name: 'Resultados da busca unificada' }),
    ).not.toBeInTheDocument();
  });

  it('diferencia busca concluída de falha ao atualizar a caixa de entrada', async () => {
    setup({ refreshError: true });
    await search();
    expect(
      await screen.findByText(
        /A busca terminou, mas não foi possível atualizar a caixa de entrada/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Busca concluída' }),
    ).toBeInTheDocument();
  });

  it('não apresenta resultados sem ID persistido como vagas salvas e preserva acesso à origem', async () => {
    setup({
      result: {
        ...success,
        jobs: [
          {
            ...opportunity,
            job_id: null,
            review_required: true,
          },
        ],
      },
    });
    const region = await search();
    expect(
      within(region).queryByText('1 vaga disponível na caixa de entrada.'),
    ).not.toBeInTheDocument();
    fireEvent.click(
      within(region).getByText(
        'Ver resultados ainda fora da caixa de entrada (1)',
      ),
    );
    expect(
      within(region).getByRole('link', { name: opportunity.title }),
    ).toHaveAttribute('href', opportunity.url);
    expect(within(region).getByText(/Possível duplicata/)).toBeInTheDocument();
  });

  it('mantém o diagnóstico recolhido ao receber outra resposta', async () => {
    setup();
    await search();
    fireEvent.click(screen.getByText('Ver detalhes da busca e do log'));
    await waitFor(() =>
      expect(
        screen.getByText('Ver detalhes da busca e do log').closest('details'),
      ).toHaveAttribute('open'),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Buscar vagas' }));
    await screen.findByRole('region', {
      name: 'Resultados da busca unificada',
    });
    expect(
      screen.getByText('Ver detalhes da busca e do log').closest('details'),
    ).not.toHaveAttribute('open');
  });
});
