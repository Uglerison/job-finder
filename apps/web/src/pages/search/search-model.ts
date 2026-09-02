export type AggregatedJob = {
  company: string;
  description: string;
  job_id: number | null;
  location: string | null;
  published_at: string | null;
  review_required: boolean;
  salary: string | null;
  source: string | null;
  title: string;
  url: string;
  work_model: 'remote' | 'hybrid' | 'on_site' | 'unknown' | null;
};

export type AggregatedSearchResponse = {
  cache_hit: boolean;
  jobs: AggregatedJob[];
  message: string;
  outcome:
    | 'results'
    | 'no_results'
    | 'partial'
    | 'not_configured'
    | 'rate_limited'
    | 'failed';
  partial: boolean;
  provider_runs: {
    candidates: number;
    display_name: string;
    duration_ms: number;
    error: string | null;
    fallback: boolean;
    provider: string;
    status: 'success' | 'empty' | 'skipped' | 'failed';
  }[];
  warnings: string[];
};

export type SearchFilters = {
  query: string;
  location: string;
  workModel: string;
};
export const workModelLabels: Record<string, string> = {
  all: 'Todas as modalidades',
  remote: 'Remoto',
  hybrid: 'Híbrido',
  on_site: 'Presencial',
};
export const outcomeCopy = {
  results: {
    title: 'Busca concluída',
    hint: 'Revise as oportunidades na caixa de entrada para decidir os próximos passos.',
    tone: 'success',
  },
  no_results: {
    title: 'Nenhuma vaga para estes filtros',
    hint: 'Tente outro cargo, amplie a localização ou escolha todas as modalidades.',
    tone: 'info',
  },
  partial: {
    title: 'Busca parcialmente concluída',
    hint: 'Nem todas as fontes responderam. Este resultado não representa todas as oportunidades disponíveis.',
    tone: 'warning',
  },
  not_configured: {
    title: 'Configure uma fonte para buscar',
    hint: 'Habilite uma fonte pública ou cadastre uma integração em Configurações → Fontes.',
    tone: 'warning',
  },
  rate_limited: {
    title: 'Limite de consultas atingido',
    hint: 'Aguarde a renovação do limite ou revise outra fonte habilitada. Repetir agora pode não trazer novos resultados.',
    tone: 'warning',
  },
  failed: {
    title: 'Não foi possível concluir a busca',
    hint: 'Confira os detalhes abaixo e revise suas fontes antes de tentar novamente.',
    tone: 'error',
  },
} as const;

export function providerRunStatusLabel(
  status: AggregatedSearchResponse['provider_runs'][number]['status'],
): string {
  return {
    empty: 'sem resultados',
    failed: 'falhou',
    skipped: 'não configurado',
    success: 'respondeu',
  }[status];
}

export function providerRunSummary(
  runs: AggregatedSearchResponse['provider_runs'],
): string {
  const consulted = runs.filter((run) => run.status !== 'skipped').length;
  const failed = runs.filter((run) => run.status === 'failed').length;
  const empty = runs.filter((run) => run.status === 'empty').length;
  const skipped = runs.filter((run) => run.status === 'skipped').length;
  const parts = [
    `${consulted} ${consulted === 1 ? 'fonte consultada' : 'fontes consultadas'}`,
  ];
  if (failed > 0)
    parts.push(`${failed} ${failed === 1 ? 'falhou' : 'falharam'}`);
  if (empty > 0) parts.push(`${empty} sem resultados`);
  if (skipped > 0) {
    parts.push(
      `${skipped} ${skipped === 1 ? 'não configurada' : 'não configuradas'}`,
    );
  }
  return parts.join(' · ');
}
