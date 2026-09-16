import type { AppPath } from '../../routes';

type Domain =
  'profile' | 'jobs' | 'applications' | 'events' | 'sources' | 'providers';
export type HomeState = {
  profile: {
    version_number: number;
    created_at?: string;
    criteria: { target_roles: string[] };
  } | null;
  jobs: {
    id: number;
    title: string;
    company: string;
    status: string;
    created_at: string;
  }[];
  applications: {
    id: number;
    job_id: number;
    current_status: string;
    updated_at: string;
  }[];
  events: { status: string; starts_at: string; ends_at: string | null }[];
  sources: { enabled: boolean }[];
  providers: { configured: boolean; unlocked: boolean; storage: string }[];
  vault: { configured: boolean; unlocked: boolean } | null;
  vaultLoading: boolean;
  loading: Partial<Record<Domain, boolean>>;
  errors: Partial<Record<Domain, boolean>>;
};
type NextAction = {
  title: string;
  description: string;
  label: string;
  target: AppPath | 'vault' | null;
};
type Activity = {
  id: string;
  title: string;
  detail: string;
  at: string;
  target: AppPath;
};
const activeStatuses = new Set(['applied', 'interview', 'offer']);
const reviewStatuses = new Set(['found', 'pending']);
const phaseLabels: Record<string, string> = {
  pending: 'Em espera',
  applied: 'Aplicada',
  interview: 'Em entrevista',
  offer: 'Proposta recebida',
  hired: 'Contratação confirmada',
  rejected: 'Não aprovado',
  withdrawn: 'Desistência',
  expired: 'Encerrada',
};

export function buildHomeSummary(state: HomeState, now = Date.now()) {
  const unavailable = (...domains: Domain[]) =>
    domains.some((domain) => state.loading[domain] || state.errors[domain]);
  const applications = new Map(
    state.applications.map((application) => [application.job_id, application]),
  );
  const review = unavailable('jobs', 'applications')
    ? null
    : state.jobs.filter((job) =>
        reviewStatuses.has(
          applications.get(job.id)?.current_status ?? job.status,
        ),
      ).length;
  const active = unavailable('jobs', 'applications')
    ? null
    : [...applications.values()].filter((application) =>
        activeStatuses.has(application.current_status),
      ).length;
  const upcoming = unavailable('events')
    ? null
    : state.events.filter(
        (event) =>
          event.status === 'scheduled' &&
          Date.parse(event.ends_at ?? event.starts_at) >= now,
      ).length;
  const readySources = unavailable('sources', 'providers')
    ? null
    : state.sources.filter((source) => source.enabled).length +
      state.providers.filter(
        (provider) => provider.configured && provider.unlocked,
      ).length;
  const lockedProviders = state.providers.filter(
    (provider) =>
      provider.configured &&
      !provider.unlocked &&
      provider.storage === 'encrypted_database',
  ).length;

  let action: NextAction;
  if (
    state.loading.profile ||
    state.loading.jobs ||
    state.loading.applications
  ) {
    action = {
      title: 'Preparando seu resumo',
      description: 'Consultando os dados salvos neste computador.',
      label: 'Carregando…',
      target: null,
    };
  } else if (state.errors.profile) {
    action = {
      title: 'Vamos conferir seu perfil',
      description:
        'Não foi possível consultar o perfil salvo. Seus dados não foram apagados.',
      label: 'Verificar perfil',
      target: '/perfil',
    };
  } else if (!state.profile) {
    action = {
      title: 'Comece pelo seu perfil',
      description:
        'Defina cargos, competências e preferências para orientar sua busca.',
      label: 'Configurar meu perfil',
      target: '/perfil',
    };
  } else if (state.errors.jobs || state.errors.applications) {
    action = {
      title: 'Seu resumo está incompleto',
      description:
        'Não foi possível consultar todas as vagas e candidaturas. Confira os dados antes de continuar.',
      label: 'Verificar vagas',
      target: '/vagas',
    };
  } else if (review) {
    action = {
      title: 'Há oportunidades para revisar',
      description: `${review} vaga${review === 1 ? '' : 's'} encontrada${review === 1 ? '' : 's'} ou em espera. Escolha quais merecem uma candidatura.`,
      label: 'Revisar vagas',
      target: '/vagas',
    };
  } else if (active) {
    action = {
      title: 'Acompanhe suas candidaturas',
      description: `${active} processo${active === 1 ? '' : 's'} em andamento. Atualize as fases e confira os próximos passos.`,
      label: 'Acompanhar candidaturas',
      target: '/candidaturas',
    };
  } else if (
    state.loading.sources ||
    state.loading.providers ||
    state.vaultLoading
  ) {
    action = {
      title: 'Conferindo suas fontes',
      description: 'Verificando a configuração local antes da próxima busca.',
      label: 'Carregando…',
      target: null,
    };
  } else if (state.errors.sources || state.errors.providers) {
    action = {
      title: 'Confira as fontes de busca',
      description:
        'Não foi possível consultar a configuração das fontes. Isso não significa que não existam vagas.',
      label: 'Verificar fontes',
      target: '/configuracoes/fontes',
    };
  } else if (lockedProviders > 0 && !state.vault?.unlocked) {
    action = {
      title: 'Libere suas fontes de busca',
      description:
        'Uma senha libera as integrações cadastradas. Suas vagas salvas continuam acessíveis.',
      label: state.vault ? 'Desbloquear cofre' : 'Verificar cofre',
      target: 'vault',
    };
  } else if (!readySources) {
    action = {
      title: 'Escolha suas fontes de vagas',
      description:
        'Habilite uma fonte pública ou cadastre uma integração para começar a pesquisar.',
      label: 'Configurar fontes',
      target: '/configuracoes/fontes',
    };
  } else {
    action = {
      title: 'Tudo pronto para a próxima busca',
      description:
        'Pesquise por cargo e localização. As oportunidades encontradas ficam salvas para revisar depois.',
      label: 'Buscar vagas',
      target: '/busca',
    };
  }

  const activity: Activity[] = [];
  if (!unavailable('jobs')) {
    for (const job of state.jobs) {
      activity.push({
        id: `job-${job.id}`,
        title: job.title,
        detail: `Vaga salva · ${job.company}`,
        at: job.created_at,
        target: '/vagas',
      });
    }
  }
  if (!unavailable('jobs', 'applications')) {
    const jobs = new Map(state.jobs.map((job) => [job.id, job]));
    for (const application of applications.values()) {
      const phase = phaseLabels[application.current_status];
      if (phase)
        activity.push({
          id: `application-${application.id}`,
          title: jobs.get(application.job_id)?.title ?? 'Candidatura',
          detail: phase,
          at: application.updated_at,
          target: '/candidaturas',
        });
    }
  }
  if (!unavailable('profile') && state.profile?.created_at) {
    activity.push({
      id: `profile-${state.profile.version_number}`,
      title: 'Perfil profissional atualizado',
      detail: `Versão ${state.profile.version_number}`,
      at: state.profile.created_at,
      target: '/perfil',
    });
  }
  return {
    action,
    metrics: { review, active, upcoming },
    readySources,
    lockedProviders,
    activity: activity
      .filter(
        (item) =>
          Number.isFinite(Date.parse(item.at)) && Date.parse(item.at) <= now,
      )
      .sort(
        (a, b) =>
          Date.parse(b.at) - Date.parse(a.at) || a.id.localeCompare(b.id),
      )
      .slice(0, 5),
    partial: Object.values(state.errors).some(Boolean),
  };
}
