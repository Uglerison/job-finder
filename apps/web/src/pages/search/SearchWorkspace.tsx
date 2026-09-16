import { useEffect, useRef, type FormEvent, type MouseEvent } from 'react';
import {
  Button,
  Card,
  Field,
  LoadingState,
  Notice,
  PageHeader,
} from '../../components/ui/primitives';
import type { AppPath } from '../../routes';
import {
  outcomeCopy,
  providerRunStatusLabel,
  providerRunSummary,
  workModelLabels,
  type AggregatedSearchResponse,
  type SearchFilters,
} from './search-model';
import './search.css';

type Props = {
  filters: SearchFilters;
  onFiltersChange: (filters: SearchFilters) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onNavigate: (path: AppPath) => void;
  onOpenVault: () => void;
  readiness: {
    loading: boolean;
    error: boolean;
    locked: boolean;
    enabled: number;
  };
  searching: boolean;
  result: AggregatedSearchResponse | null;
  submittedFilters: SearchFilters | null;
  error: string | null;
  refreshWarning: string | null;
};

export function SearchWorkspace({
  filters,
  onFiltersChange,
  onSubmit,
  onNavigate,
  onOpenVault,
  readiness,
  searching,
  result,
  submittedFilters,
  error,
  refreshWarning,
}: Props) {
  const feedbackRef = useRef<HTMLDivElement>(null);
  const wasSearching = useRef(false);
  useEffect(() => {
    if (wasSearching.current && !searching) {
      feedbackRef.current?.focus({ preventScroll: true });
      feedbackRef.current?.scrollIntoView?.({
        block: 'start',
        behavior: 'instant',
      });
    }
    wasSearching.current = searching;
  }, [searching]);
  const follow = (event: MouseEvent<HTMLAnchorElement>, path: AppPath) => {
    if (
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      event.button !== 0
    )
      return;
    event.preventDefault();
    onNavigate(path);
  };
  const savedCount = result
    ? new Set(
        result.jobs.flatMap((job) =>
          typeof job.job_id === 'number' ? [job.job_id] : [],
        ),
      ).size
    : 0;
  const unsaved =
    result?.jobs.filter((job) => typeof job.job_id !== 'number') ?? [];
  const copy = result ? outcomeCopy[result.outcome] : null;
  return (
    <div className="search-workspace">
      <PageHeader
        eyebrow="ENCONTRAR OPORTUNIDADES"
        title="Buscar vagas"
        description="Escolha o que procura. Depois, avalie os resultados em Vagas."
      />
      <Card className="search-form-card">
        <form
          aria-label="Pesquisar vagas"
          className="search-task-form"
          onSubmit={onSubmit}
        >
          <Field htmlFor="aggregated-query" label="Cargo ou palavra-chave">
            <input
              id="aggregated-query"
              value={filters.query}
              onChange={(event) =>
                onFiltersChange({ ...filters, query: event.target.value })
              }
              placeholder="ex.: Analista de Dados"
              required
              disabled={searching}
            />
          </Field>
          <div className="search-filter-row">
            <Field htmlFor="aggregated-location" label="Localização">
              <input
                id="aggregated-location"
                value={filters.location}
                onChange={(event) =>
                  onFiltersChange({ ...filters, location: event.target.value })
                }
                placeholder="Qualquer localização"
                disabled={searching}
              />
            </Field>
            <Field htmlFor="aggregated-work-model" label="Modalidade">
              <select
                id="aggregated-work-model"
                value={filters.workModel}
                onChange={(event) =>
                  onFiltersChange({ ...filters, workModel: event.target.value })
                }
                disabled={searching}
              >
                <option value="all">Todos</option>
                <option value="remote">Remoto</option>
                <option value="hybrid">Híbrido</option>
                <option value="on_site">Presencial</option>
              </select>
            </Field>
          </div>
          <div className="search-submit-row">
            <Button
              type="submit"
              size="large"
              loading={searching}
              loadingLabel="Buscando…"
            >
              Buscar vagas
            </Button>
            <span>A análise por IA não é executada nesta etapa.</span>
          </div>
        </form>
        <div className="search-readiness" aria-label="Estado das fontes">
          {readiness.loading ? (
            <LoadingState label="Verificando fontes…" />
          ) : (
            <>
              <p role="status">
                {readiness.error
                  ? 'Não foi possível verificar todas as fontes.'
                  : readiness.locked
                    ? 'Desbloqueie o cofre para usar suas integrações.'
                    : readiness.enabled > 0
                      ? `${readiness.enabled} ${readiness.enabled === 1 ? 'fonte habilitada' : 'fontes habilitadas'} para a busca.`
                      : 'Nenhuma fonte habilitada.'}
              </p>
              {readiness.locked && (
                <Button variant="secondary" onClick={onOpenVault}>
                  Desbloquear cofre
                </Button>
              )}
              <a
                href="/configuracoes/fontes"
                onClick={(event) => follow(event, '/configuracoes/fontes')}
              >
                {readiness.enabled === 0 && !readiness.error
                  ? 'Configurar fontes'
                  : 'Revisar fontes'}
              </a>
            </>
          )}
        </div>
      </Card>
      <div
        ref={feedbackRef}
        tabIndex={-1}
        className="search-feedback"
        aria-live="polite"
        aria-atomic="false"
      >
        {searching && (
          <LoadingState label="Consultando fontes e organizando oportunidades…" />
        )}
        {error && (
          <Notice tone="error" title="A busca não foi concluída">
            {error}
          </Notice>
        )}
        {!searching && result && copy && (
          <section
            aria-label="Resultados da busca unificada"
            className="search-outcome"
            data-outcome={result.outcome}
          >
            <span className="ui-meta-label">
              {result.cache_hit
                ? 'RESULTADO REUTILIZADO · CACHE'
                : 'RESULTADO DA BUSCA'}
            </span>
            <h2>{copy.title}</h2>
            {submittedFilters && (
              <p className="search-query-context">
                {submittedFilters.query} ·{' '}
                {submittedFilters.location || 'Qualquer localização'} ·{' '}
                {workModelLabels[submittedFilters.workModel]}
              </p>
            )}
            <Notice tone={copy.tone}>
              <strong>{result.message}</strong>
              <p>{copy.hint}</p>
            </Notice>
            <p className="search-provider-summary">
              {providerRunSummary(result.provider_runs)}
            </p>
            {result.jobs.length > 0 && (
              <div className="search-result-next">
                <div>
                  <strong>
                    {result.jobs.length}{' '}
                    {result.jobs.length === 1
                      ? 'vaga encontrada'
                      : 'vagas encontradas'}
                  </strong>
                  <p>
                    {savedCount > 0
                      ? `${savedCount} ${savedCount === 1 ? 'vaga disponível' : 'vagas disponíveis'} na caixa de entrada.`
                      : 'Nenhum destes resultados está disponível na caixa de entrada.'}
                  </p>
                </div>
                <a
                  className="ui-button ui-button--primary ui-button--large"
                  href="/vagas"
                  onClick={(event) => follow(event, '/vagas')}
                >
                  {savedCount > 0
                    ? 'Revisar oportunidades →'
                    : 'Abrir caixa de entrada →'}
                </a>
              </div>
            )}
            {refreshWarning && <Notice tone="warning">{refreshWarning}</Notice>}
            {(result.outcome === 'not_configured' ||
              result.outcome === 'failed' ||
              result.outcome === 'rate_limited') && (
              <a
                className="search-help-link"
                href="/configuracoes/fontes"
                onClick={(event) => follow(event, '/configuracoes/fontes')}
              >
                Revisar configuração das fontes →
              </a>
            )}
            {unsaved.length > 0 && (
              <details className="search-details">
                <summary>
                  Ver resultados ainda fora da caixa de entrada (
                  {unsaved.length})
                </summary>
                <p>
                  Estes resultados não têm vínculo com uma vaga salva. Você pode
                  consultar o anúncio original; eles ainda não estão prontos
                  para acompanhamento.
                </p>
                <ul>
                  {unsaved.map((job, index) => (
                    <li key={`${job.url}-${index}`}>
                      <a href={job.url} target="_blank" rel="noreferrer">
                        {job.title}
                      </a>
                      <span>
                        {job.review_required
                          ? 'Possível duplicata: requer revisão antes de criar uma candidatura.'
                          : 'Sem vínculo com uma vaga salva.'}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <details className="search-details">
              <summary>Ver detalhes da busca e do log</summary>
              {result.provider_runs.length === 0 ? (
                <p>A resposta não incluiu detalhes por fonte.</p>
              ) : (
                <ul>
                  {result.provider_runs.map((run) => (
                    <li key={run.provider}>
                      <strong>
                        {run.display_name} ·{' '}
                        {providerRunStatusLabel(run.status)}
                      </strong>
                      <span>
                        {run.candidates} vaga(s) · {run.duration_ms} ms
                        {run.error ? ` · ${run.error}` : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {result.warnings.length > 0 && (
                <p>{result.warnings.join(' · ')}</p>
              )}
            </details>
          </section>
        )}
      </div>
      <p className="search-footer-note">
        Já tem uma entrevista?{' '}
        <a href="https://sepreparai.com.br/" target="_blank" rel="noreferrer">
          Treinar entrevista no Se Prepara AI ↗
        </a>
      </p>
    </div>
  );
}
