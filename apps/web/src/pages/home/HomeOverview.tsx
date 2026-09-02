import type { MouseEvent, ReactNode } from 'react';
import {
  Button,
  Card,
  LoadingState,
  Notice,
  PageHeader,
} from '../../components/ui/primitives';
import type { AppPath } from '../../routes';
import { buildHomeSummary, type HomeState } from './home-model';
import './home.css';

type Props = {
  state: HomeState;
  onNavigate: (path: AppPath) => void;
  onOpenVault: () => void;
  timezone: string;
  locale: string;
};

export function HomeOverview({
  state,
  onNavigate,
  onOpenVault,
  timezone,
  locale,
}: Props) {
  const summary = buildHomeSummary(state);
  const { action, metrics } = summary;
  function link(path: AppPath, children: ReactNode, className?: string) {
    return (
      <a
        href={path}
        className={className}
        onClick={(event: MouseEvent<HTMLAnchorElement>) => {
          if (
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
          )
            return;
          event.preventDefault();
          onNavigate(path);
        }}
      >
        {children}
      </a>
    );
  }
  const vaultLabel = state.vaultLoading
    ? 'Verificando…'
    : !state.vault
      ? 'Indisponível'
      : !state.vault.configured
        ? 'Não configurado'
        : state.vault.unlocked
          ? 'Desbloqueado'
          : 'Bloqueado';
  const profileLabel = state.loading.profile
    ? 'Carregando…'
    : state.errors.profile
      ? 'Indisponível'
      : state.profile
        ? state.profile.criteria.target_roles.join(' · ') || 'Perfil salvo'
        : 'Ainda não configurado';
  const activityLoading =
    state.loading.profile || state.loading.jobs || state.loading.applications;
  const metricItems = [
    {
      key: 'review',
      label: 'Vagas para revisar',
      value: metrics.review,
      path: '/vagas',
      hint: 'Encontradas ou em espera',
      loading: state.loading.jobs || state.loading.applications,
    },
    {
      key: 'active',
      label: 'Candidaturas ativas',
      value: metrics.active,
      path: '/candidaturas',
      hint: 'Aplicadas, entrevistas e propostas',
      loading: state.loading.jobs || state.loading.applications,
    },
    {
      key: 'upcoming',
      label: 'Próximos compromissos',
      value: metrics.upcoming,
      path: '/agenda',
      hint: 'Futuros ou em andamento',
      loading: state.loading.events,
    },
  ] as const;
  const formatDate = (value: string) => {
    try {
      return new Intl.DateTimeFormat(locale, {
        dateStyle: 'short',
        timeStyle: 'short',
        timeZone: timezone,
      }).format(new Date(value));
    } catch {
      return new Intl.DateTimeFormat('pt-BR', {
        dateStyle: 'short',
        timeStyle: 'short',
        timeZone: 'UTC',
      }).format(new Date(value));
    }
  };

  return (
    <section className="home-overview" aria-label="Início">
      <PageHeader
        eyebrow="VISÃO GERAL"
        title="Seu espaço de busca"
        description="O que revisar, acompanhar e fazer a seguir."
      />
      {summary.partial && (
        <Notice tone="warning" title="Resumo parcial">
          Alguns dados não puderam ser consultados. As contagens indisponíveis
          não representam zero.
        </Notice>
      )}
      <div className="home-overview-top">
        <Card className="home-next-action" aria-labelledby="home-next-title">
          <span className="ui-meta-label">PRÓXIMA AÇÃO</span>
          <h2 id="home-next-title">{action.title}</h2>
          <p>{action.description}</p>
          <div className="home-next-action-footer">
            {action.target === null ? (
              <LoadingState label={action.label} />
            ) : action.target === 'vault' ? (
              <Button onClick={onOpenVault}>{action.label}</Button>
            ) : (
              link(
                action.target,
                action.label,
                'ui-button ui-button--primary ui-button--default home-primary-link',
              )
            )}
          </div>
        </Card>
        <section
          className="home-operational"
          aria-labelledby="home-operational-title"
        >
          <h2 id="home-operational-title">Seu ambiente</h2>
          <dl>
            <div>
              <dt>Perfil profissional</dt>
              <dd>{link('/perfil', profileLabel)}</dd>
            </div>
            <div>
              <dt>Cofre local</dt>
              <dd>
                <button
                  type="button"
                  onClick={onOpenVault}
                  disabled={state.vaultLoading}
                  aria-label={`Gerenciar cofre local: ${vaultLabel}`}
                >
                  {vaultLabel} <span aria-hidden="true">↗</span>
                </button>
              </dd>
            </div>
            <div>
              <dt>Fontes de busca</dt>
              <dd>
                {link(
                  '/configuracoes/fontes',
                  summary.readySources === null
                    ? state.loading.sources || state.loading.providers
                      ? 'Verificando…'
                      : 'Indisponível'
                    : `${summary.readySources} habilitada${summary.readySources === 1 ? '' : 's'}${summary.lockedProviders ? ` · ${summary.lockedProviders} bloqueada${summary.lockedProviders === 1 ? '' : 's'}` : ''}`,
                )}
              </dd>
            </div>
          </dl>
          <p className="home-local-note">Dados ficam neste computador.</p>
        </section>
      </div>
      <section aria-label="Resumo do acompanhamento" className="home-metrics">
        {metricItems.map((metric) => (
          <article key={metric.key}>
            {link(
              metric.path,
              <>
                <span className="home-metric-label">{metric.label}</span>
                <strong>{metric.value ?? '—'}</strong>
                <small>
                  {metric.value === null
                    ? metric.loading
                      ? 'Carregando…'
                      : 'Indisponível'
                    : metric.hint}
                </small>
              </>,
            )}
          </article>
        ))}
      </section>
      <section className="home-activity" aria-labelledby="home-activity-title">
        <div className="home-section-heading">
          <h2 id="home-activity-title">Atividade recente</h2>
          <span>Até 5 últimos registros</span>
        </div>
        {activityLoading ? (
          <LoadingState label="Carregando atividade…" />
        ) : summary.activity.length ? (
          <ol>
            {summary.activity.map((item) => (
              <li key={item.id}>
                {link(
                  item.target,
                  <>
                    <span>
                      <strong>{item.title}</strong>
                      <small>{item.detail}</small>
                    </span>
                    <time dateTime={item.at}>{formatDate(item.at)}</time>
                  </>,
                )}
              </li>
            ))}
          </ol>
        ) : (
          <p className="home-activity-empty">
            {summary.partial
              ? 'Não foi possível montar a atividade recente com os dados disponíveis.'
              : 'Nenhuma atividade registrada ainda. Seu perfil, vagas salvas e mudanças de fase aparecerão aqui.'}
          </p>
        )}
      </section>
    </section>
  );
}
