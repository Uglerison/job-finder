import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';

import './App.css';

type WorkModel = 'remote' | 'hybrid' | 'on_site';
type ContractType =
  'full_time' | 'part_time' | 'contract' | 'temporary' | 'internship';
type LanguageLevel = 'basic' | 'intermediate' | 'professional' | 'native';

type ProfileCriteria = {
  target_roles: string[];
  skills: string[];
  languages: { code: string; minimum_level: LanguageLevel }[];
  salary_expectation: {
    currency: string;
    minimum_monthly: number;
    maximum_monthly: number;
  } | null;
  weights: Record<string, number>;
  restrictions: {
    countries: string[];
    contract_types: ContractType[];
    work_models: WorkModel[];
    locations: string[];
    excluded_keywords: string[];
  };
};

type ProfileResponse = {
  criteria: ProfileCriteria;
  created_at?: string;
  profile_id: number;
  version_number: number;
};

type RedactionPreview = {
  redacted_text: string;
  replacements: { count: number; kind: string; token: string }[];
};

type Preferences = {
  locale: 'pt-BR' | 'en-US';
  currency: string;
  timezone: string;
  retention_days: number;
};

type AiSettings = {
  configured: boolean;
  unlocked: boolean;
  model: 'gpt-5.6-luna';
  storage: 'encrypted_database' | 'environment' | 'not_configured';
};

type AiConnectionTest = {
  model: 'gpt-5.6-luna';
  status: 'connected';
};

type JobListItem = {
  canonical_url: string | null;
  company: string;
  created_at: string;
  id: number;
  location: string | null;
  origin_count: number;
  status: string;
  status_label: string;
  title: string;
};

type JobDetail = JobListItem & {
  content_versions: {
    content_type: string;
    id: number;
    raw_content: string;
    valid_from: string;
    valid_until: string | null;
    version_number: number;
  }[];
  origins: { id: number; source: string; url: string | null }[];
};

type TrashJob = {
  company: string;
  deleted_at: string;
  id: number;
  purge_after: string;
  status: string;
  title: string;
};

type ApplicationStatus =
  | 'found'
  | 'pending'
  | 'applied'
  | 'interview'
  | 'offer'
  | 'hired'
  | 'rejected'
  | 'withdrawn'
  | 'expired';

type ApplicationEvent = {
  from_status: string | null;
  id: number;
  kind: string;
  note: string | null;
  occurred_at: string;
  sequence_number: number;
  to_status: string;
};

type ApplicationResponse = {
  created_at: string;
  current_status: ApplicationStatus;
  events: ApplicationEvent[];
  id: number;
  job_id: number;
  updated_at: string;
};

type AgendaEvent = {
  application_id: number;
  ends_at: string | null;
  id: number;
  kind: 'interview' | 'challenge' | 'deadline';
  link: string | null;
  notes: string | null;
  participants: string[];
  starts_at: string;
  status: 'scheduled' | 'completed' | 'cancelled';
  timezone_name: string;
  title: string;
};

type SourceConfig = {
  source_key: string;
  display_name: string;
  endpoint: string;
  terms_url: string | null;
  data_format: 'json';
  enabled: boolean;
  schedule_enabled: boolean;
  frequency_minutes: number;
  daily_limit: number;
  per_run_limit: number;
  timeout_seconds: number;
  id: number;
  last_run_at: string | null;
  next_run_at: string | null;
  backoff_until: string | null;
  consecutive_failures: number;
  last_error: string | null;
};

type SearchRun = {
  id: number;
  source_key: string;
  source_name: string;
  status:
    'pending' | 'running' | 'completed' | 'partial' | 'failed' | 'cancelled';
  query: { query?: string; location?: string; limit?: number };
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  candidates_seen: number;
  jobs_created: number;
  exact_duplicates: number;
  approximate_duplicates: number;
  error_message: string | null;
  cancellation_requested: boolean;
  current_cursor: string | null;
};

type AggregatedJob = {
  company: string;
  description: string;
  location: string | null;
  published_at: string | null;
  salary: string | null;
  source: string | null;
  title: string;
  url: string;
  work_model: 'remote' | 'hybrid' | 'on_site' | 'unknown' | null;
};

type AggregatedSearchResponse = {
  cache_hit: boolean;
  jobs: AggregatedJob[];
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

type ProviderKey = 'jsearch' | 'adzuna' | 'jooble';

type ProviderCredentialStatus = {
  configured: boolean;
  provider: ProviderKey;
  storage: 'encrypted_database' | 'environment' | 'not_configured';
  unlocked: boolean;
};

type DashboardSummary = {
  agenda: { overdue: number; upcoming: number };
  cards: {
    active_pipeline: number;
    applications: number;
    hired: number;
    interviews: number;
    jobs_found: number;
    offers: number;
    rejected: number;
  };
  funnel: {
    conversion_percent: number | null;
    count: number;
    denominator: number;
    key: string;
    label: string;
  }[];
  period: {
    from_: string;
    source_key: string | null;
    timezone: string;
    to: string;
  };
  series: {
    applications: number;
    interviews: number;
    jobs: number;
    period_start: string;
  }[];
  sources: {
    application_rate_percent: number | null;
    applications: number;
    errors: number;
    interviews: number;
    jobs: number;
    source_key: string;
  }[];
};

type SavedFilter = {
  id: number;
  name: string;
  query: {
    days?: string | null;
    q?: string | null;
    source_key?: string | null;
    status?: string | null;
  };
};

type AnalysisUsage = {
  estimated_cost_usd: number | null;
  fallback: boolean;
  fallback_reason: string | null;
  input_tokens: number | null;
  latency_ms: number;
  metered: boolean;
  output_tokens: number | null;
};

type JobAnalysisResponse = {
  analysis: {
    assessment: {
      confidence: number;
      gaps: string[];
      strengths: string[];
      summary: string;
      warnings: string[];
    };
  };
  analysis_version: number;
  explanation: { supported_evidence: { claim: string; quote: string }[] };
  fit: { accepted: boolean; score: number };
  model: string;
  prompt_version: string;
  usage: AnalysisUsage;
};

function formatAgendaDate(value: string, timezoneName: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'data indisponível';
  }
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: timezoneName === 'UTC' ? 'UTC' : undefined,
  }).format(date);
}

const pipelineStages: { label: string; value: ApplicationStatus }[] = [
  { label: 'ENCONTRADA', value: 'found' },
  { label: 'EM ESPERA', value: 'pending' },
  { label: 'APLICADA', value: 'applied' },
  { label: 'ENTREVISTA', value: 'interview' },
  { label: 'OFERTA', value: 'offer' },
  { label: 'CONTRATADO', value: 'hired' },
  { label: 'NÃO APROVADO', value: 'rejected' },
  { label: 'DESISTIU', value: 'withdrawn' },
  { label: 'EXPIRADA', value: 'expired' },
];

function pipelineStatusLabel(status: ApplicationStatus): string {
  return (
    pipelineStages.find((stage) => stage.value === status)?.label ?? status
  );
}

function sourceRunStatusLabel(status: SearchRun['status']): string {
  return {
    pending: 'PENDENTE',
    running: 'EM EXECUÇÃO',
    completed: 'CONCLUÍDA',
    partial: 'PARCIAL',
    failed: 'FALHOU',
    cancelled: 'CANCELADA',
  }[status];
}

function formatRunDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'agora';
  }
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

type ManualJobFormState = {
  canonicalUrl: string;
  company: string;
  content: string;
  location: string;
  title: string;
};

type ProfileFormState = {
  targetRoles: string;
  skills: string;
  workModels: WorkModel[];
  countries: string;
  contractTypes: ContractType[];
  locations: string;
  excludedKeywords: string;
  languageCode: string;
  languageLevel: LanguageLevel;
  currency: string;
  minimumMonthly: string;
  maximumMonthly: string;
};

const defaultFormState: ProfileFormState = {
  contractTypes: [],
  countries: '',
  currency: 'BRL',
  excludedKeywords: '',
  languageCode: 'en',
  languageLevel: 'professional',
  locations: '',
  maximumMonthly: '',
  minimumMonthly: '',
  skills: '',
  targetRoles: '',
  workModels: ['remote'],
};

const defaultPreferences: Preferences = {
  currency: 'BRL',
  locale: 'pt-BR',
  retention_days: 365,
  timezone: 'America/Sao_Paulo',
};

const defaultAiSettings: AiSettings = {
  configured: false,
  unlocked: false,
  model: 'gpt-5.6-luna',
  storage: 'not_configured',
};

const defaultManualJobForm: ManualJobFormState = {
  canonicalUrl: '',
  company: '',
  content: '',
  location: '',
  title: '',
};

const productSteps = [
  {
    description:
      'Defina cargos, competências, localização e o que você prefere evitar.',
    number: '01',
    title: 'Dê contexto ao seu perfil',
  },
  {
    description:
      'Reúna vagas encontradas na web e compare cada uma com os seus critérios.',
    number: '02',
    title: 'Revise o que importa',
  },
  {
    description:
      'Registre candidaturas, entrevistas, ofertas e os próximos passos.',
    number: '03',
    title: 'Acompanhe o processo',
  },
];

function splitValues(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function formFromCriteria(criteria: ProfileCriteria): ProfileFormState {
  const salary = criteria.salary_expectation;
  const language = criteria.languages[0];

  return {
    contractTypes: criteria.restrictions.contract_types ?? [],
    countries: criteria.restrictions.countries?.join(', ') ?? '',
    currency: salary?.currency ?? 'BRL',
    excludedKeywords: criteria.restrictions.excluded_keywords.join(', '),
    languageCode: language?.code ?? 'en',
    languageLevel: language?.minimum_level ?? 'professional',
    locations: criteria.restrictions.locations.join(', '),
    maximumMonthly: salary?.maximum_monthly.toString() ?? '',
    minimumMonthly: salary?.minimum_monthly.toString() ?? '',
    skills: criteria.skills.join(', '),
    targetRoles: criteria.target_roles.join(', '),
    workModels: criteria.restrictions.work_models,
  };
}

function payloadFromForm(form: ProfileFormState): ProfileCriteria {
  const hasSalary = form.minimumMonthly !== '' || form.maximumMonthly !== '';

  return {
    languages: [
      {
        code: form.languageCode.trim().toLowerCase() || 'en',
        minimum_level: form.languageLevel,
      },
    ],
    restrictions: {
      contract_types: form.contractTypes,
      countries: splitValues(form.countries),
      excluded_keywords: splitValues(form.excludedKeywords),
      locations: splitValues(form.locations),
      work_models: form.workModels,
    },
    salary_expectation: hasSalary
      ? {
          currency: form.currency,
          maximum_monthly: Number(form.maximumMonthly),
          minimum_monthly: Number(form.minimumMonthly),
        }
      : null,
    skills: splitValues(form.skills),
    target_roles: splitValues(form.targetRoles),
    weights: { experience: 35, location: 25, skills: 40 },
  };
}

function validateForm(form: ProfileFormState): string | null {
  if (splitValues(form.targetRoles).length === 0) {
    return 'Informe ao menos um cargo desejado.';
  }

  if (form.workModels.length === 0) {
    return 'Selecione ao menos uma modalidade de trabalho.';
  }

  const hasMinimum = form.minimumMonthly !== '';
  const hasMaximum = form.maximumMonthly !== '';
  if (hasMinimum !== hasMaximum) {
    return 'Preencha os dois valores da pretensão mensal ou deixe ambos vazios.';
  }

  if (
    hasMinimum &&
    hasMaximum &&
    Number(form.minimumMonthly) > Number(form.maximumMonthly)
  ) {
    return 'A pretensão mínima não pode ser maior que a máxima.';
  }

  return null;
}

function formatVersionDate(value?: string): string {
  if (!value) {
    return 'agora';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'data indisponível';
  }

  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

function replacementLabel(kind: string): string {
  return (
    {
      address: 'endereço',
      email: 'e-mail',
      identifier: 'identificador',
      phone: 'telefone',
    }[kind] ?? kind
  );
}

function aiStorageLabel(storage: AiSettings['storage']): string {
  return {
    encrypted_database: 'banco local criptografado',
    environment: 'variável de ambiente local',
    not_configured: 'ainda não configurada',
  }[storage];
}

function App() {
  const [formState, setFormState] =
    useState<ProfileFormState>(defaultFormState);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [profileHistory, setProfileHistory] = useState<ProfileResponse[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState('');
  const [redactionPreview, setRedactionPreview] =
    useState<RedactionPreview | null>(null);
  const [redactionError, setRedactionError] = useState<string | null>(null);
  const [isRedacting, setIsRedacting] = useState(false);
  const [preferences, setPreferences] =
    useState<Preferences>(defaultPreferences);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [preferencesMessage, setPreferencesMessage] = useState<string | null>(
    null,
  );
  const [preferencesError, setPreferencesError] = useState<string | null>(null);
  const [aiSettings, setAiSettings] = useState<AiSettings>(defaultAiSettings);
  const [isLoadingAiSettings, setIsLoadingAiSettings] = useState(true);
  const [apiKeyDraft, setApiKeyDraft] = useState('');
  const [vaultPasswordDraft, setVaultPasswordDraft] = useState('');
  const [vaultPasswordConfirmation, setVaultPasswordConfirmation] =
    useState('');
  const [isSavingApiKey, setIsSavingApiKey] = useState(false);
  const [isTestingAiConnection, setIsTestingAiConnection] = useState(false);
  const [aiSettingsError, setAiSettingsError] = useState<string | null>(null);
  const [aiSettingsMessage, setAiSettingsMessage] = useState<string | null>(
    null,
  );
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [jobSearch, setJobSearch] = useState('');
  const [isJobFormOpen, setIsJobFormOpen] = useState(false);
  const [manualJobForm, setManualJobForm] =
    useState<ManualJobFormState>(defaultManualJobForm);
  const [isSavingJob, setIsSavingJob] = useState(false);
  const [jobFormError, setJobFormError] = useState<string | null>(null);
  const [jobMessage, setJobMessage] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null);
  const [selectedJobIds, setSelectedJobIds] = useState<number[]>([]);
  const [jobAnalyses, setJobAnalyses] = useState<
    Record<number, JobAnalysisResponse>
  >({});
  const [isAnalyzingJob, setIsAnalyzingJob] = useState(false);
  const [analysisMessage, setAnalysisMessage] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isLoadingJobDetail, setIsLoadingJobDetail] = useState(false);
  const [jobDetailError, setJobDetailError] = useState<string | null>(null);
  const [applications, setApplications] = useState<
    Record<number, ApplicationResponse>
  >({});
  const [isLoadingApplications, setIsLoadingApplications] = useState(true);
  const [applicationsError, setApplicationsError] = useState<string | null>(
    null,
  );
  const [pipelineActionId, setPipelineActionId] = useState<number | null>(null);
  const [pipelineTargets, setPipelineTargets] = useState<
    Record<number, ApplicationStatus>
  >({});
  const [agendaEvents, setAgendaEvents] = useState<AgendaEvent[]>([]);
  const [isLoadingAgenda, setIsLoadingAgenda] = useState(true);
  const [agendaError, setAgendaError] = useState<string | null>(null);
  const [trashJobs, setTrashJobs] = useState<TrashJob[]>([]);
  const [isLoadingTrash, setIsLoadingTrash] = useState(true);
  const [trashError, setTrashError] = useState<string | null>(null);
  const [sources, setSources] = useState<SourceConfig[]>([]);
  const [isLoadingSources, setIsLoadingSources] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);
  const [sourceRuns, setSourceRuns] = useState<SearchRun[]>([]);
  const [isLoadingSourceRuns, setIsLoadingSourceRuns] = useState(true);
  const [sourceRunsError, setSourceRunsError] = useState<string | null>(null);
  const [aggregatedQuery, setAggregatedQuery] = useState('');
  const [aggregatedLocation, setAggregatedLocation] = useState('');
  const [aggregatedWorkModel, setAggregatedWorkModel] = useState('all');
  const [aggregatedResults, setAggregatedResults] =
    useState<AggregatedSearchResponse | null>(null);
  const [aggregatedError, setAggregatedError] = useState<string | null>(null);
  const [isSearchingAggregated, setIsSearchingAggregated] = useState(false);
  const [providerStatuses, setProviderStatuses] = useState<
    ProviderCredentialStatus[]
  >([]);
  const [providerCredential, setProviderCredential] = useState('');
  const [providerAppId, setProviderAppId] = useState('');
  const [providerAppKey, setProviderAppKey] = useState('');
  const [providerVaultPassword, setProviderVaultPassword] = useState('');
  const [providerKey, setProviderKey] = useState<ProviderKey>('jsearch');
  const [isSavingProvider, setIsSavingProvider] = useState(false);
  const [providerSettingsMessage, setProviderSettingsMessage] = useState<
    string | null
  >(null);
  const [providerSettingsError, setProviderSettingsError] = useState<
    string | null
  >(null);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [dashboardDays, setDashboardDays] = useState('30');
  const [isJobsPayloadReady, setIsJobsPayloadReady] = useState(false);
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);
  const [savedFilterName, setSavedFilterName] = useState('');
  const [selectedSavedFilter, setSelectedSavedFilter] = useState('');
  const [savedFilterMessage, setSavedFilterMessage] = useState<string | null>(
    null,
  );

  useEffect(() => {
    let isMounted = true;

    const loadProfile = async () => {
      try {
        const [profileResponse, historyResponse] = await Promise.all([
          fetch('/api/profile'),
          fetch('/api/profile/versions'),
        ]);

        if (!profileResponse.ok || !historyResponse.ok) {
          throw new Error('Não foi possível carregar o perfil.');
        }

        const [currentProfile, history] = (await Promise.all([
          profileResponse.json(),
          historyResponse.json(),
        ])) as [ProfileResponse | null, ProfileResponse[]];

        if (!isMounted) {
          return;
        }

        if (currentProfile) {
          setProfile(currentProfile);
          setFormState(formFromCriteria(currentProfile.criteria));
        }
        setProfileHistory(Array.isArray(history) ? history : []);
      } catch {
        if (isMounted) {
          setLoadError('Não foi possível carregar o perfil local.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingProfile(false);
        }
      }
    };

    void loadProfile();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    void fetch('/api/search/providers')
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Não foi possível carregar as credenciais de busca.');
        }
        return (await response.json()) as ProviderCredentialStatus[];
      })
      .then((payload) => {
        if (isMounted && Array.isArray(payload)) {
          setProviderStatuses(payload);
        }
      })
      .catch(() => {
        if (isMounted) {
          setProviderSettingsError(
            'Não foi possível consultar as credenciais de busca.',
          );
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    if (!isJobsPayloadReady) {
      setIsLoadingDashboard(false);
      return () => {
        isMounted = false;
      };
    }
    const loadDashboard = async () => {
      setIsLoadingDashboard(true);
      try {
        const to = new Date();
        const from = new Date(to);
        from.setDate(to.getDate() - Number(dashboardDays));
        const params = new URLSearchParams({
          from: from.toISOString().slice(0, 10),
          to: to.toISOString().slice(0, 10),
          timezone: preferences.timezone,
        });
        const response = await fetch(
          `/api/dashboard/summary?${params.toString()}`,
        );
        if (!response.ok) {
          throw new Error('Não foi possível carregar o painel.');
        }
        const payload = (await response.json()) as DashboardSummary | null;
        if (isMounted) {
          setDashboard(
            payload &&
              typeof payload === 'object' &&
              'cards' in payload &&
              'funnel' in payload &&
              'series' in payload
              ? payload
              : null,
          );
          setDashboardError(null);
        }
      } catch {
        if (isMounted) {
          setDashboardError('Não foi possível carregar as métricas locais.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingDashboard(false);
        }
      }
    };
    void loadDashboard();
    return () => {
      isMounted = false;
    };
  }, [dashboardDays, isJobsPayloadReady, preferences.timezone]);

  useEffect(() => {
    if (!isJobsPayloadReady) {
      return;
    }
    let isMounted = true;
    void fetch('/api/saved-filters')
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Não foi possível carregar filtros salvos.');
        }
        return (await response.json()) as SavedFilter[];
      })
      .then((payload) => {
        if (isMounted) {
          setSavedFilters(Array.isArray(payload) ? payload : []);
        }
      })
      .catch(() => {
        if (isMounted) {
          setSavedFilterMessage('Não foi possível carregar os filtros salvos.');
        }
      });
    return () => {
      isMounted = false;
    };
  }, [isJobsPayloadReady]);

  useEffect(() => {
    let isMounted = true;

    const loadSources = async () => {
      try {
        const response = await fetch('/api/sources');
        if (!response.ok) {
          throw new Error('Não foi possível carregar as fontes.');
        }
        const payload = (await response.json()) as SourceConfig[] | null;
        if (isMounted) {
          const savedSources = Array.isArray(payload) ? payload : [];
          setSources(savedSources);
        }
      } catch {
        if (isMounted) {
          setSourcesError('Não foi possível carregar as fontes locais.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingSources(false);
        }
      }
    };

    void loadSources();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadAiSettings = async () => {
      try {
        const response = await fetch('/api/ai/settings');
        if (!response.ok) {
          throw new Error('Não foi possível carregar a configuração da IA.');
        }
        const payload = (await response.json()) as AiSettings;
        if (isMounted && payload) {
          setAiSettings(payload);
        }
      } catch {
        if (isMounted) {
          setAiSettingsError(
            'Não foi possível consultar a configuração local da IA.',
          );
        }
      } finally {
        if (isMounted) {
          setIsLoadingAiSettings(false);
        }
      }
    };

    void loadAiSettings();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadSourceRuns = async () => {
      try {
        const response = await fetch('/api/search-runs?limit=12');
        if (!response.ok) {
          throw new Error('Não foi possível carregar as execuções.');
        }
        const payload = (await response.json()) as SearchRun[] | null;
        if (isMounted) {
          setSourceRuns(Array.isArray(payload) ? payload : []);
        }
      } catch {
        if (isMounted) {
          setSourceRunsError(
            'Não foi possível carregar o histórico de buscas.',
          );
        }
      } finally {
        if (isMounted) {
          setIsLoadingSourceRuns(false);
        }
      }
    };

    void loadSourceRuns();
    const timer = window.setInterval(() => {
      if (isMounted) {
        void loadSourceRuns();
      }
    }, 2500);

    return () => {
      isMounted = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadTrash = async () => {
      try {
        const response = await fetch('/api/trash');
        if (!response.ok) {
          throw new Error('Não foi possível carregar a lixeira.');
        }
        const payload = (await response.json()) as TrashJob[] | null;
        if (isMounted) {
          setTrashJobs(Array.isArray(payload) ? payload : []);
        }
      } catch {
        if (isMounted) {
          setTrashError('Não foi possível carregar a lixeira local.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingTrash(false);
        }
      }
    };

    void loadTrash();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    if (isLoadingJobs) {
      return () => {
        isMounted = false;
      };
    }

    const loadApplications = async () => {
      setIsLoadingApplications(true);
      setApplicationsError(null);

      if (jobs.length === 0) {
        if (isMounted) {
          setApplications({});
          setPipelineTargets({});
          setIsLoadingApplications(false);
        }
        return;
      }

      try {
        const loaded = await Promise.all(
          jobs.map(async (job) => {
            const response = await fetch(`/api/jobs/${job.id}/application`);
            if (!response.ok) {
              return null;
            }
            const payload =
              (await response.json()) as ApplicationResponse | null;
            return payload?.id ? payload : null;
          }),
        );
        if (!isMounted) {
          return;
        }
        const nextApplications: Record<number, ApplicationResponse> = {};
        const nextTargets: Record<number, ApplicationStatus> = {};
        loaded.forEach((application) => {
          if (application) {
            nextApplications[application.id] = application;
            nextTargets[application.id] = application.current_status;
          }
        });
        setApplications(nextApplications);
        setPipelineTargets(nextTargets);
      } catch {
        if (isMounted) {
          setApplicationsError(
            'Não foi possível carregar o pipeline local de candidaturas.',
          );
        }
      } finally {
        if (isMounted) {
          setIsLoadingApplications(false);
        }
      }
    };

    void loadApplications();

    return () => {
      isMounted = false;
    };
  }, [isLoadingJobs, jobs]);

  useEffect(() => {
    let isMounted = true;

    const loadAgenda = async () => {
      try {
        const response = await fetch('/api/events');
        if (!response.ok) {
          throw new Error('Não foi possível carregar a agenda.');
        }
        const payload = (await response.json()) as AgendaEvent[] | null;
        if (isMounted) {
          setAgendaEvents(Array.isArray(payload) ? payload : []);
        }
      } catch {
        if (isMounted) {
          setAgendaError('Não foi possível carregar a agenda local.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingAgenda(false);
        }
      }
    };

    void loadAgenda();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadJobs = async () => {
      try {
        const response = await fetch('/api/jobs');
        if (!response.ok) {
          throw new Error('Não foi possível carregar as vagas.');
        }
        const payload = (await response.json()) as {
          items?: JobListItem[];
        } | null;
        if (isMounted) {
          const hasItems = Array.isArray(payload?.items);
          setJobs(hasItems ? (payload?.items ?? []) : []);
          setIsJobsPayloadReady(hasItems);
        }
      } catch {
        if (isMounted) {
          setJobsError('Não foi possível carregar a caixa de entrada local.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingJobs(false);
        }
      }
    };

    void loadJobs();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    fetch('/api/preferences')
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Não foi possível carregar as preferências.');
        }
        return (await response.json()) as Preferences | null;
      })
      .then((savedPreferences) => {
        if (
          isMounted &&
          savedPreferences?.locale &&
          savedPreferences.currency &&
          savedPreferences.timezone &&
          savedPreferences.retention_days
        ) {
          setPreferences(savedPreferences);
        }
      })
      .catch(() => {
        if (isMounted) {
          setPreferencesError(
            'Não foi possível carregar as preferências locais.',
          );
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const openProfileForm = () => {
    setFormError(null);
    setSaveMessage(null);
    setIsFormOpen(true);
  };

  const handleFormChange = (
    field: keyof ProfileFormState,
    event: ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >,
  ) => {
    setFormState((current) => ({ ...current, [field]: event.target.value }));
    setFormError(null);
    setSaveMessage(null);
  };

  const toggleWorkModel = (workModel: WorkModel) => {
    setFormState((current) => ({
      ...current,
      workModels: current.workModels.includes(workModel)
        ? current.workModels.filter((item) => item !== workModel)
        : [...current.workModels, workModel],
    }));
    setFormError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const validationMessage = validateForm(formState);
    if (validationMessage) {
      setFormError(validationMessage);
      return;
    }

    setIsSaving(true);
    setFormError(null);
    setSaveMessage(null);

    try {
      const response = await fetch('/api/profile', {
        body: JSON.stringify(payloadFromForm(formState)),
        headers: { 'Content-Type': 'application/json' },
        method: 'PUT',
      });

      if (!response.ok) {
        throw new Error('Não foi possível salvar o perfil.');
      }

      const savedProfile = (await response.json()) as ProfileResponse;
      setProfile(savedProfile);
      setFormState(formFromCriteria(savedProfile.criteria));
      setProfileHistory((currentHistory) => {
        const withoutSavedVersion = currentHistory.filter(
          (version) => version.version_number !== savedProfile.version_number,
        );
        return [...withoutSavedVersion, savedProfile].sort(
          (left, right) => left.version_number - right.version_number,
        );
      });
      setSaveMessage('Perfil salvo localmente.');
    } catch {
      setFormError('Não foi possível salvar o perfil. Tente novamente.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRedactionPreview = async () => {
    if (!previewText.trim()) {
      setRedactionError('Cole um texto para gerar a prévia segura.');
      return;
    }

    setIsRedacting(true);
    setRedactionError(null);
    try {
      const response = await fetch('/api/privacy/redact', {
        body: JSON.stringify({ text: previewText }),
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Não foi possível gerar a prévia.');
      }
      setRedactionPreview((await response.json()) as RedactionPreview);
    } catch {
      setRedactionError('Não foi possível gerar a prévia segura.');
    } finally {
      setIsRedacting(false);
    }
  };

  const handlePreferencesSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSavingPreferences(true);
    setPreferencesError(null);
    setPreferencesMessage(null);

    try {
      const response = await fetch('/api/preferences', {
        body: JSON.stringify(preferences),
        headers: { 'Content-Type': 'application/json' },
        method: 'PUT',
      });
      if (!response.ok) {
        throw new Error('Não foi possível salvar as preferências.');
      }
      const savedPreferences = (await response.json()) as Preferences;
      setPreferences(savedPreferences);
      setPreferencesMessage('Preferências salvas localmente.');
    } catch {
      setPreferencesError('Não foi possível salvar as preferências.');
    } finally {
      setIsSavingPreferences(false);
    }
  };

  const handleApiKeySubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const apiKey = apiKeyDraft.trim();
    const vaultPassword = vaultPasswordDraft;
    const needsUnlock =
      aiSettings.storage === 'encrypted_database' && !aiSettings.unlocked;

    if (!needsUnlock && !apiKey) {
      setAiSettingsError('Informe a chave da API antes de salvar.');
      return;
    }
    if (!vaultPassword) {
      setAiSettingsError('Informe a senha do cofre local.');
      return;
    }
    if (!needsUnlock && vaultPassword !== vaultPasswordConfirmation) {
      setAiSettingsError('A confirmação da senha do cofre não confere.');
      return;
    }

    setIsSavingApiKey(true);
    setAiSettingsError(null);
    setAiSettingsMessage(null);
    try {
      const response = await fetch(
        needsUnlock ? '/api/ai/unlock' : '/api/ai/api-key',
        {
          body: JSON.stringify(
            needsUnlock
              ? { vault_password: vaultPassword }
              : { api_key: apiKey, vault_password: vaultPassword },
          ),
          headers: { 'Content-Type': 'application/json' },
          method: needsUnlock ? 'POST' : 'PUT',
        },
      );
      const payload = (await response.json().catch(() => null)) as
        AiSettings | { detail?: string } | null;
      if (!response.ok || !payload || !('configured' in payload)) {
        const detail = payload && 'detail' in payload ? payload.detail : null;
        throw new Error(detail ?? 'Não foi possível salvar a chave.');
      }
      setAiSettings(payload);
      setApiKeyDraft('');
      setVaultPasswordDraft('');
      setVaultPasswordConfirmation('');
      setAiSettingsMessage(
        needsUnlock
          ? 'Cofre desbloqueado somente nesta execução.'
          : 'Chave criptografada e salva no banco local.',
      );
    } catch (error) {
      setAiSettingsError(
        error instanceof Error
          ? error.message
          : 'Não foi possível salvar a chave.',
      );
    } finally {
      setIsSavingApiKey(false);
    }
  };

  const handleApiKeyLock = async () => {
    setIsSavingApiKey(true);
    setAiSettingsError(null);
    setAiSettingsMessage(null);
    try {
      const response = await fetch('/api/ai/lock', { method: 'POST' });
      const payload = (await response.json().catch(() => null)) as
        AiSettings | { detail?: string } | null;
      if (!response.ok || !payload || !('configured' in payload)) {
        const detail = payload && 'detail' in payload ? payload.detail : null;
        throw new Error(detail ?? 'Não foi possível bloquear o cofre.');
      }
      setAiSettings(payload);
      setAiSettingsMessage('Cofre bloqueado; a chave saiu da memória.');
    } catch (error) {
      setAiSettingsError(
        error instanceof Error
          ? error.message
          : 'Não foi possível bloquear o cofre.',
      );
    } finally {
      setIsSavingApiKey(false);
    }
  };

  const handleOpenAiConnectionTest = async () => {
    setIsTestingAiConnection(true);
    setAiSettingsError(null);
    setAiSettingsMessage(null);
    try {
      const response = await fetch('/api/ai/connection/test', {
        method: 'POST',
      });
      const payload = (await response.json().catch(() => null)) as
        AiConnectionTest | { detail?: string } | null;
      if (!response.ok || !payload || !('status' in payload)) {
        const detail = payload && 'detail' in payload ? payload.detail : null;
        throw new Error(
          detail ?? 'Não foi possível testar a conexão com a OpenAI.',
        );
      }
      setAiSettingsMessage(`Conexão com ${payload.model} confirmada.`);
    } catch (error) {
      setAiSettingsError(
        error instanceof Error
          ? error.message
          : 'Não foi possível testar a conexão com a OpenAI.',
      );
    } finally {
      setIsTestingAiConnection(false);
    }
  };

  const handleApiKeyRemoval = async () => {
    setIsSavingApiKey(true);
    setAiSettingsError(null);
    setAiSettingsMessage(null);
    try {
      const response = await fetch('/api/ai/api-key', { method: 'DELETE' });
      const payload = (await response.json().catch(() => null)) as
        AiSettings | { detail?: string } | null;
      if (!response.ok || !payload || !('configured' in payload)) {
        const detail = payload && 'detail' in payload ? payload.detail : null;
        throw new Error(detail ?? 'Não foi possível remover a chave.');
      }
      setAiSettings(payload);
      setApiKeyDraft('');
      setVaultPasswordDraft('');
      setVaultPasswordConfirmation('');
      setAiSettingsMessage('Chave criptografada removida do banco local.');
    } catch (error) {
      setAiSettingsError(
        error instanceof Error
          ? error.message
          : 'Não foi possível remover a chave.',
      );
    } finally {
      setIsSavingApiKey(false);
    }
  };

  const openJobForm = () => {
    setManualJobForm(defaultManualJobForm);
    setJobFormError(null);
    setJobMessage(null);
    setIsJobFormOpen(true);
  };

  const handleManualJobSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (
      !manualJobForm.canonicalUrl.trim() ||
      !manualJobForm.title.trim() ||
      !manualJobForm.company.trim() ||
      !manualJobForm.content.trim()
    ) {
      setJobFormError('Preencha URL, título, empresa e conteúdo da vaga.');
      return;
    }

    setIsSavingJob(true);
    setJobFormError(null);
    setJobMessage(null);
    try {
      const response = await fetch('/api/jobs', {
        body: JSON.stringify({
          canonical_url: manualJobForm.canonicalUrl.trim(),
          company: manualJobForm.company.trim(),
          location: manualJobForm.location.trim() || null,
          raw_content: manualJobForm.content,
          title: manualJobForm.title.trim(),
        }),
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Não foi possível salvar a vaga.');
      }
      const savedJob = (await response.json()) as JobDetail;
      setJobs((currentJobs) => [
        {
          canonical_url: savedJob.canonical_url,
          company: savedJob.company,
          created_at: savedJob.created_at,
          id: savedJob.id,
          location: savedJob.location,
          origin_count: savedJob.origins?.length ?? 1,
          status: savedJob.status,
          status_label: savedJob.status_label,
          title: savedJob.title,
        },
        ...currentJobs,
      ]);
      setIsJobFormOpen(false);
      setJobMessage('Vaga adicionada à caixa de entrada.');
    } catch {
      setJobFormError('Não foi possível salvar a vaga. Tente novamente.');
    } finally {
      setIsSavingJob(false);
    }
  };

  const openJobDetail = async (jobId: number) => {
    setIsLoadingJobDetail(true);
    setJobDetailError(null);
    try {
      const response = await fetch(`/api/jobs/${jobId}`);
      if (!response.ok) {
        throw new Error('Não foi possível carregar o detalhe.');
      }
      setSelectedJob((await response.json()) as JobDetail);
    } catch {
      setJobDetailError('Não foi possível carregar o detalhe da vaga.');
    } finally {
      setIsLoadingJobDetail(false);
    }
  };

  const analyzeSelectedJobs = async (jobIds: number[]) => {
    if (jobIds.length === 0) {
      setAnalysisError('Selecione ao menos uma vaga para analisar.');
      return;
    }
    if (
      !window.confirm(
        `Analisar ${jobIds.length} vaga${jobIds.length === 1 ? '' : 's'} com a IA?`,
      )
    ) {
      return;
    }
    setIsAnalyzingJob(true);
    setAnalysisError(null);
    setAnalysisMessage(null);
    const results = await Promise.allSettled(
      jobIds.map(async (jobId) => {
        const response = await fetch(`/api/jobs/${jobId}/analysis`, {
          body: JSON.stringify({ mode: 'batch' }),
          headers: { 'Content-Type': 'application/json' },
          method: 'POST',
        });
        const payload = (await response.json().catch(() => null)) as
          JobAnalysisResponse | { detail?: string } | null;
        if (!response.ok || !payload || !('analysis_version' in payload)) {
          throw new Error(
            payload && 'detail' in payload
              ? (payload.detail ?? 'Falha na análise.')
              : 'Falha na análise.',
          );
        }
        return [jobId, payload] as const;
      }),
    );
    const successes = results.filter(
      (
        result,
      ): result is PromiseFulfilledResult<
        readonly [number, JobAnalysisResponse]
      > => result.status === 'fulfilled',
    );
    setJobAnalyses((current) => ({
      ...current,
      ...Object.fromEntries(successes.map((result) => result.value)),
    }));
    const failures = results.filter((result) => result.status === 'rejected');
    const analyzedTitles = successes.map((result) => {
      const [jobId] = result.value;
      return jobs.find((job) => job.id === jobId)?.title ?? `vaga #${jobId}`;
    });
    const completionMessage =
      successes.length === 0
        ? 'Nenhuma análise foi concluída.'
        : successes.length === 1
          ? `Análise concluída para: ${analyzedTitles[0]}.`
          : `${successes.length} análises concluídas para: ${analyzedTitles.join(', ')}.`;
    setAnalysisMessage(completionMessage);
    if (failures.length) {
      setAnalysisError(
        'Algumas vagas não puderam ser analisadas; as demais foram preservadas.',
      );
    }
    setIsAnalyzingJob(false);
  };

  const refreshJobs = async () => {
    const response = await fetch('/api/jobs');
    if (!response.ok) {
      throw new Error('Não foi possível atualizar a caixa de entrada.');
    }
    const payload = (await response.json()) as { items?: JobListItem[] } | null;
    setJobs(Array.isArray(payload?.items) ? payload.items : []);
  };

  const saveCurrentFilter = async () => {
    const name = savedFilterName.trim();
    if (!name) {
      setSavedFilterMessage('Dê um nome ao filtro antes de salvar.');
      return;
    }
    try {
      const response = await fetch('/api/saved-filters', {
        body: JSON.stringify({
          name,
          query: { days: dashboardDays, q: jobSearch.trim() || null },
        }),
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      });
      const payload = (await response.json().catch(() => null)) as
        SavedFilter | { detail?: string } | null;
      if (!response.ok || !payload || !('id' in payload)) {
        throw new Error(
          payload && 'detail' in payload
            ? payload.detail
            : 'Não foi possível salvar o filtro.',
        );
      }
      setSavedFilters((current) => [...current, payload]);
      setSavedFilterName('');
      setSavedFilterMessage('Filtro salvo localmente.');
    } catch (error) {
      setSavedFilterMessage(
        error instanceof Error
          ? error.message
          : 'Não foi possível salvar o filtro.',
      );
    }
  };

  const applySavedFilter = (filterId: string) => {
    setSelectedSavedFilter(filterId);
    const saved = savedFilters.find((filter) => String(filter.id) === filterId);
    if (!saved) {
      return;
    }
    setJobSearch(saved.query.q ?? '');
    if (saved.query.days) {
      setDashboardDays(saved.query.days);
    }
    setSavedFilterMessage(`Filtro “${saved.name}” aplicado.`);
  };

  const toggleSource = async (source: SourceConfig) => {
    setSourcesError(null);
    try {
      const response = await fetch(`/api/sources/${source.source_key}`, {
        body: JSON.stringify({
          display_name: source.display_name,
          endpoint: source.endpoint,
          terms_url: source.terms_url,
          enabled: !source.enabled,
          schedule_enabled: source.schedule_enabled,
          frequency_minutes: source.frequency_minutes,
          daily_limit: source.daily_limit,
          per_run_limit: source.per_run_limit,
          timeout_seconds: source.timeout_seconds,
        }),
        headers: { 'Content-Type': 'application/json' },
        method: 'PUT',
      });
      if (!response.ok) {
        throw new Error('Não foi possível alterar a fonte.');
      }
      const saved = (await response.json()) as SourceConfig;
      setSources((current) =>
        current.map((item) =>
          item.source_key === saved.source_key ? saved : item,
        ),
      );
    } catch {
      setSourcesError('Não foi possível atualizar a configuração da fonte.');
    }
  };

  const runAggregatedSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = aggregatedQuery.trim();
    if (query.length < 2) {
      setAggregatedError(
        'Informe ao menos duas letras no cargo ou palavra-chave.',
      );
      return;
    }
    setIsSearchingAggregated(true);
    setAggregatedError(null);
    try {
      const response = await fetch('/api/search', {
        body: JSON.stringify({
          query,
          location: aggregatedLocation.trim() || null,
          work_model: aggregatedWorkModel,
          limit: 20,
        }),
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
      });
      const payload = (await response.json().catch(() => null)) as
        AggregatedSearchResponse | { detail?: string } | null;
      if (!response.ok || !payload || !('jobs' in payload)) {
        throw new Error(
          payload && 'detail' in payload
            ? payload.detail
            : 'Não foi possível buscar vagas agora.',
        );
      }
      setAggregatedResults(payload);
    } catch (error) {
      setAggregatedError(
        error instanceof Error
          ? error.message
          : 'Não foi possível buscar vagas agora.',
      );
    } finally {
      setIsSearchingAggregated(false);
    }
  };

  const saveProviderCredential = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (providerVaultPassword.length < 12) {
      setProviderSettingsError(
        'A senha do cofre deve ter pelo menos 12 caracteres.',
      );
      return;
    }
    if (
      (providerKey === 'adzuna' &&
        (!providerAppId.trim() || !providerAppKey.trim())) ||
      (providerKey !== 'adzuna' && !providerCredential.trim())
    ) {
      setProviderSettingsError(
        providerKey === 'adzuna'
          ? 'Informe o app ID e a app key do Adzuna.'
          : 'Informe a API key do provider.',
      );
      return;
    }
    setIsSavingProvider(true);
    setProviderSettingsError(null);
    setProviderSettingsMessage(null);
    try {
      const response = await fetch(`/api/search/providers/${providerKey}`, {
        body: JSON.stringify({
          api_key:
            providerKey === 'adzuna' ? undefined : providerCredential.trim(),
          app_id: providerKey === 'adzuna' ? providerAppId.trim() : undefined,
          app_key: providerKey === 'adzuna' ? providerAppKey.trim() : undefined,
          vault_password: providerVaultPassword,
        }),
        headers: { 'Content-Type': 'application/json' },
        method: 'PUT',
      });
      const payload = (await response.json().catch(() => null)) as
        ProviderCredentialStatus | { detail?: string } | null;
      if (!response.ok || !payload || !('provider' in payload)) {
        throw new Error(
          payload && 'detail' in payload
            ? payload.detail
            : 'Não foi possível salvar a credencial.',
        );
      }
      setProviderStatuses((current) => [
        ...current.filter((item) => item.provider !== payload.provider),
        payload,
      ]);
      setProviderCredential('');
      setProviderAppId('');
      setProviderAppKey('');
      setProviderVaultPassword('');
      setProviderSettingsMessage('Credencial criptografada no banco local.');
    } catch (error) {
      setProviderSettingsError(
        error instanceof Error
          ? error.message
          : 'Não foi possível salvar a credencial.',
      );
    } finally {
      setIsSavingProvider(false);
    }
  };

  const cancelSourceRun = async (run: SearchRun) => {
    try {
      const response = await fetch(`/api/search-runs/${run.id}/cancel`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Não foi possível cancelar a busca.');
      }
      const cancelled = (await response.json()) as SearchRun;
      setSourceRuns((current) =>
        current.map((item) => (item.id === cancelled.id ? cancelled : item)),
      );
    } catch {
      setSourceRunsError('Não foi possível cancelar a busca.');
    }
  };

  const restoreTrashJob = async (jobId: number) => {
    setTrashError(null);
    try {
      const response = await fetch(`/api/jobs/${jobId}/restore`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Não foi possível restaurar a vaga.');
      }
      setTrashJobs((current) => current.filter((job) => job.id !== jobId));
      await refreshJobs();
    } catch {
      setTrashError('Não foi possível restaurar a vaga. Tente novamente.');
    }
  };

  const permanentlyDeleteTrashJob = async (jobId: number) => {
    if (!window.confirm('Excluir definitivamente esta vaga e seu histórico?')) {
      return;
    }
    setTrashError(null);
    try {
      const response = await fetch(`/api/jobs/${jobId}?confirm=true`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Não foi possível excluir a vaga.');
      }
      setTrashJobs((current) => current.filter((job) => job.id !== jobId));
    } catch {
      setTrashError('Não foi possível excluir a vaga definitivamente.');
    }
  };

  const moveApplication = async (
    application: ApplicationResponse,
    job: JobListItem,
  ) => {
    const targetStatus = pipelineTargets[application.id];
    if (!targetStatus || targetStatus === application.current_status) {
      return;
    }

    const previousStatus = application.current_status;
    setApplications((current) => ({
      ...current,
      [application.id]: { ...application, current_status: targetStatus },
    }));
    setPipelineActionId(application.id);
    setApplicationsError(null);

    try {
      const response = await fetch(
        `/api/applications/${application.id}/transition`,
        {
          body: JSON.stringify({ to_status: targetStatus }),
          headers: { 'Content-Type': 'application/json' },
          method: 'POST',
        },
      );
      if (!response.ok) {
        throw new Error('Transição rejeitada.');
      }
      const savedApplication = (await response.json()) as ApplicationResponse;
      setApplications((current) => ({
        ...current,
        [application.id]: savedApplication,
      }));
      setPipelineTargets((current) => ({
        ...current,
        [application.id]: savedApplication.current_status,
      }));
    } catch {
      setApplications((current) => ({
        ...current,
        [application.id]: { ...application, current_status: previousStatus },
      }));
      setPipelineTargets((current) => ({
        ...current,
        [application.id]: previousStatus,
      }));
      setApplicationsError(
        `Não foi possível mover ${job.title}. A fase foi restaurada.`,
      );
    } finally {
      setPipelineActionId(null);
    }
  };

  const visibleJobs = jobs.filter((job) => {
    const query = jobSearch.trim().toLocaleLowerCase();
    if (!query) {
      return true;
    }
    return `${job.title} ${job.company} ${job.location ?? ''}`
      .toLocaleLowerCase()
      .includes(query);
  });

  const pipelineEntries = jobs.flatMap((job) => {
    const application = Object.values(applications).find(
      (candidate) => candidate.job_id === job.id,
    );
    return application ? [{ application, job }] : [];
  });
  const now = new Date();
  const agendaUpcoming = agendaEvents.filter(
    (event) =>
      event.status === 'scheduled' &&
      new Date(event.ends_at ?? event.starts_at).getTime() >= now.getTime(),
  );
  const agendaOverdue = agendaEvents.filter(
    (event) =>
      event.status === 'scheduled' &&
      new Date(event.ends_at ?? event.starts_at).getTime() < now.getTime(),
  );

  const profileStatus = isLoadingProfile
    ? 'CARREGANDO'
    : profile
      ? 'CONFIGURADO'
      : 'PRONTO';

  return (
    <main className="paper-app">
      <header className="site-header" role="banner">
        <div className="header-inner">
          <a className="brand" href="#inicio" aria-label="Job Finder, início">
            <span className="brand-mark" aria-hidden="true" />
            <span className="brand-name">Job Finder</span>
          </a>

          <nav aria-label="Navegação principal">
            <a href="#como-funciona">Como funciona</a>
            <a href="#fluxo">Fluxo</a>
            <a href="#perfil">Perfil</a>
            <a href="#historico">Histórico</a>
            <a href="#busca">Busca</a>
            <a href="#vagas">Vagas</a>
            <a href="#agenda">Agenda</a>
            <a href="#lixeira">Lixeira</a>
            <a href="#ia">IA</a>
            <a href="#dashboard">Painel</a>
            <a href="#preferencias">Preferências</a>
          </nav>

          <div className="header-meta">
            <span className="meta-label">LOCAL · PRIVADO</span>
            <button
              className="header-action"
              onClick={openProfileForm}
              type="button"
            >
              Abrir perfil
            </button>
          </div>
        </div>
      </header>

      <section
        className="sources-section"
        id="busca"
        aria-labelledby="sources-title"
      >
        <div className="sources-intro">
          <p className="eyebrow">BUSCA UNIFICADA</p>
          <h2 id="sources-title">Encontre uma vaga para treinar</h2>
          <p>
            Pesquise em fontes públicas de forma seletiva. A gente organiza os
            resultados para você comparar oportunidades sem precisar escolher
            uma API.
          </p>
        </div>

        <div className="sources-workspace">
          <form className="source-search-form" onSubmit={runAggregatedSearch}>
            <div className="form-field">
              <label htmlFor="aggregated-query">Cargo ou palavra-chave</label>
              <input
                id="aggregated-query"
                onChange={(event) => setAggregatedQuery(event.target.value)}
                placeholder="ex.: Analista de Dados"
                value={aggregatedQuery}
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="aggregated-location">Localização</label>
              <input
                id="aggregated-location"
                onChange={(event) => setAggregatedLocation(event.target.value)}
                placeholder="ex.: Curitiba, PR"
                value={aggregatedLocation}
              />
            </div>
            <div className="form-field">
              <label htmlFor="aggregated-work-model">Modalidade</label>
              <select
                id="aggregated-work-model"
                onChange={(event) => setAggregatedWorkModel(event.target.value)}
                value={aggregatedWorkModel}
              >
                <option value="all">Todos</option>
                <option value="remote">Remoto</option>
                <option value="hybrid">Híbrido</option>
                <option value="on_site">Presencial</option>
              </select>
            </div>
            <button
              className="primary-button source-run-button"
              disabled={isSearchingAggregated}
              type="submit"
            >
              {isSearchingAggregated ? 'Buscando…' : 'Buscar vagas'}
            </button>
          </form>

          {aggregatedError && (
            <p className="sources-feedback is-error" role="status">
              {aggregatedError}
            </p>
          )}

          {aggregatedResults && (
            <div
              aria-live="polite"
              aria-label="Resultados da busca unificada"
              className="aggregated-results"
              role="region"
            >
              <div className="source-list-heading">
                <span className="meta-label">
                  {aggregatedResults.jobs.length} VAGAS ENCONTRADAS
                </span>
                <span className="mono-note">
                  {aggregatedResults.cache_hit
                    ? 'RESULTADO EM CACHE'
                    : 'ATUALIZADO AGORA'}
                </span>
              </div>
              {aggregatedResults.jobs.length === 0 ? (
                <p className="sources-empty">
                  Nenhuma vaga correspondeu a esses critérios. Tente ampliar a
                  localização ou a modalidade.
                </p>
              ) : (
                <ul className="aggregated-job-list">
                  {aggregatedResults.jobs.map((job) => (
                    <li
                      className="aggregated-job-card"
                      key={`${job.url}-${job.title}`}
                    >
                      <div className="aggregated-job-card-main">
                        <p className="eyebrow">
                          {job.source || 'VAGA ENCONTRADA'}
                        </p>
                        <h3>{job.title}</h3>
                        <p className="aggregated-job-company">{job.company}</p>
                        <p className="aggregated-job-meta">
                          {job.location || 'Localização não informada'}
                          {job.work_model && job.work_model !== 'unknown'
                            ? ` · ${
                                job.work_model === 'on_site'
                                  ? 'Presencial'
                                  : job.work_model === 'hybrid'
                                    ? 'Híbrido'
                                    : 'Remoto'
                              }`
                            : ''}
                          {job.published_at
                            ? ` · ${formatRunDate(job.published_at)}`
                            : ''}
                        </p>
                        <p className="aggregated-job-description">
                          {job.description}
                        </p>
                        {job.salary && (
                          <p className="aggregated-job-salary">{job.salary}</p>
                        )}
                      </div>
                      <div className="aggregated-job-actions">
                        <a
                          className="card-link"
                          href={job.url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          Ver vaga ↗
                        </a>
                        <a
                          className="text-button text-button-plain"
                          href="https://sepreparai.com.br/"
                          rel="noreferrer"
                          target="_blank"
                        >
                          Treinar entrevista no Se Prepara AI ↗
                        </a>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {aggregatedResults.partial &&
                aggregatedResults.warnings.length > 0 && (
                  <p className="sources-feedback" role="status">
                    Algumas fontes não responderam; mostramos o que foi possível
                    encontrar.
                  </p>
                )}
            </div>
          )}

          <section
            aria-labelledby="provider-credentials-title"
            className="provider-credentials"
          >
            <div className="source-list-heading">
              <span className="meta-label" id="provider-credentials-title">
                CREDENCIAIS OPCIONAIS
              </span>
              <span className="mono-note">CIFRADAS NO BANCO LOCAL</span>
            </div>
            <p className="sources-feedback">
              Cadastre as chaves uma vez para ampliar a busca brasileira. A
              senha do cofre não é armazenada.
            </p>
            <form
              className="provider-credentials-form"
              onSubmit={saveProviderCredential}
            >
              <div className="form-field">
                <label htmlFor="provider-key">Provider</label>
                <select
                  id="provider-key"
                  onChange={(event) =>
                    setProviderKey(event.target.value as ProviderKey)
                  }
                  value={providerKey}
                >
                  <option value="jsearch">JSearch</option>
                  <option value="adzuna">Adzuna</option>
                  <option value="jooble">Jooble</option>
                </select>
              </div>
              {providerKey === 'adzuna' ? (
                <>
                  <div className="form-field">
                    <label htmlFor="provider-app-id">Adzuna app ID</label>
                    <input
                      id="provider-app-id"
                      onChange={(event) => setProviderAppId(event.target.value)}
                      type="password"
                      value={providerAppId}
                    />
                  </div>
                  <div className="form-field">
                    <label htmlFor="provider-app-key">Adzuna app key</label>
                    <input
                      id="provider-app-key"
                      onChange={(event) =>
                        setProviderAppKey(event.target.value)
                      }
                      type="password"
                      value={providerAppKey}
                    />
                  </div>
                </>
              ) : (
                <div className="form-field">
                  <label htmlFor="provider-credential">API key</label>
                  <input
                    id="provider-credential"
                    onChange={(event) =>
                      setProviderCredential(event.target.value)
                    }
                    type="password"
                    value={providerCredential}
                  />
                </div>
              )}
              <div className="form-field">
                <label htmlFor="provider-vault-password">Senha do cofre</label>
                <input
                  id="provider-vault-password"
                  minLength={12}
                  onChange={(event) =>
                    setProviderVaultPassword(event.target.value)
                  }
                  type="password"
                  value={providerVaultPassword}
                />
              </div>
              <button
                className="primary-button"
                disabled={isSavingProvider}
                type="submit"
              >
                {isSavingProvider ? 'Salvando…' : 'Salvar credencial'}
              </button>
            </form>
            {(providerSettingsError || providerSettingsMessage) && (
              <p
                className={`form-message${providerSettingsError ? ' is-error' : ' is-success'}`}
                role="status"
              >
                {providerSettingsError || providerSettingsMessage}
              </p>
            )}
            {providerStatuses.length > 0 && (
              <ul className="provider-status-list">
                {providerStatuses.map((status) => (
                  <li key={status.provider}>
                    <span>{status.provider}</span>
                    <span>
                      {status.configured
                        ? status.unlocked
                          ? 'disponível nesta execução'
                          : 'bloqueada'
                        : 'não configurada'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <div className="source-list-heading">
            <span className="meta-label">CONFIGURAÇÕES TÉCNICAS</span>
            <span className="mono-note">OPCIONAL · SEM SELEÇÃO NA BUSCA</span>
          </div>
          {isLoadingSources && (
            <p className="sources-feedback" role="status">
              Carregando fontes…
            </p>
          )}
          {!isLoadingSources && sources.length === 0 && !sourcesError && (
            <p className="sources-feedback" role="status">
              Nenhuma fonte configurada.
            </p>
          )}
          {!isLoadingSources && sources.length > 0 && (
            <ul className="source-list">
              {sources.map((source) => (
                <li className="source-row" key={source.source_key}>
                  <div>
                    <span className="job-status">
                      {source.enabled ? 'ATIVA' : 'PAUSADA'}
                    </span>
                    <h3>{source.display_name}</h3>
                    <p>
                      {source.per_run_limit} vagas por execução · limite diário{' '}
                      {source.daily_limit}
                    </p>
                    {source.last_error && (
                      <span className="source-error-note">
                        {source.last_error}
                      </span>
                    )}
                  </div>
                  <div className="source-row-actions">
                    <button
                      className="text-button text-button-plain"
                      onClick={() => void toggleSource(source)}
                      type="button"
                    >
                      {source.enabled ? 'Pausar' : 'Ativar'}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="source-list-heading source-run-heading">
            <span className="meta-label">HISTÓRICO DE EXECUÇÕES</span>
            <span className="mono-note">CONTADORES AUDITÁVEIS</span>
          </div>
          {isLoadingSourceRuns && (
            <p className="sources-feedback" role="status">
              Carregando execuções…
            </p>
          )}
          {sourceRunsError && (
            <p className="sources-feedback is-error" role="status">
              {sourceRunsError}
            </p>
          )}
          {!isLoadingSourceRuns &&
            sourceRuns.length === 0 &&
            !sourceRunsError && (
              <div className="sources-empty">
                <span className="meta-label">NENHUMA BUSCA AINDA</span>
                <p>As execuções manuais e agendadas aparecerão aqui.</p>
              </div>
            )}
          {!isLoadingSourceRuns && sourceRuns.length > 0 && (
            <ul className="source-run-list">
              {sourceRuns.map((run) => (
                <li className="source-run-row" key={run.id}>
                  <div>
                    <span
                      className={`job-status source-run-status is-${run.status}`}
                    >
                      {sourceRunStatusLabel(run.status)}
                    </span>
                    <h3>{run.source_name}</h3>
                    <p>
                      {run.query.query || 'todos os cargos'}
                      {run.query.location ? ` · ${run.query.location}` : ''}
                    </p>
                  </div>
                  <div className="source-run-metrics">
                    <span>{run.candidates_seen} encontradas</span>
                    <span>{run.jobs_created} novas</span>
                    <span>{run.exact_duplicates} exatas</span>
                    <span>{run.approximate_duplicates} para revisar</span>
                    <time dateTime={run.requested_at}>
                      {formatRunDate(run.requested_at)}
                    </time>
                    {(run.status === 'pending' || run.status === 'running') && (
                      <button
                        className="text-button text-button-plain danger-button"
                        onClick={() => void cancelSourceRun(run)}
                        type="button"
                      >
                        Cancelar
                      </button>
                    )}
                  </div>
                  {run.error_message && (
                    <p className="source-error-note">{run.error_message}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section
        className="preferences-section ai-settings-section"
        id="ia"
        aria-labelledby="ai-settings-title"
      >
        <div className="preferences-intro">
          <p className="eyebrow">IA LOCAL E CONTROLADA</p>
          <h2 id="ai-settings-title">Conecte sua chave OpenAI</h2>
          <p>
            A chave é criptografada no banco local. A senha do cofre não é
            gravada: ela apenas desbloqueia a chave nesta execução do app.
          </p>
        </div>

        <form className="preferences-form" onSubmit={handleApiKeySubmit}>
          {!aiSettings.configured && (
            <div className="form-field form-field-wide">
              <label htmlFor="openai-api-key">Chave da API OpenAI</label>
              <input
                autoComplete="new-password"
                id="openai-api-key"
                onChange={(event) => {
                  setApiKeyDraft(event.target.value);
                  setAiSettingsError(null);
                  setAiSettingsMessage(null);
                }}
                placeholder="sk-…"
                spellCheck={false}
                type="password"
                value={apiKeyDraft}
              />
              <span>
                Modelo preparado: {aiSettings.model}. Nenhuma análise é iniciada
                automaticamente.
              </span>
            </div>
          )}

          {aiSettings.storage !== 'environment' && !aiSettings.unlocked && (
            <div className="form-field form-field-wide">
              <label htmlFor="vault-password">
                {aiSettings.configured
                  ? 'Senha do cofre local'
                  : 'Crie uma senha para o cofre local'}
              </label>
              <input
                autoComplete="new-password"
                id="vault-password"
                minLength={12}
                onChange={(event) => {
                  setVaultPasswordDraft(event.target.value);
                  setAiSettingsError(null);
                  setAiSettingsMessage(null);
                }}
                spellCheck={false}
                type="password"
                value={vaultPasswordDraft}
              />
              {!aiSettings.configured && (
                <span>Use ao menos 12 caracteres e guarde esta senha.</span>
              )}
            </div>
          )}

          {!aiSettings.configured && (
            <div className="form-field form-field-wide">
              <label htmlFor="vault-password-confirmation">
                Confirme a senha do cofre local
              </label>
              <input
                autoComplete="new-password"
                id="vault-password-confirmation"
                minLength={12}
                onChange={(event) => {
                  setVaultPasswordConfirmation(event.target.value);
                  setAiSettingsError(null);
                  setAiSettingsMessage(null);
                }}
                spellCheck={false}
                type="password"
                value={vaultPasswordConfirmation}
              />
            </div>
          )}

          <div className="form-field form-field-wide">
            <span className="meta-label">
              {isLoadingAiSettings
                ? 'VERIFICANDO CONFIGURAÇÃO…'
                : aiSettings.configured
                  ? aiSettings.unlocked
                    ? 'CHAVE CONFIGURADA E DESBLOQUEADA'
                    : 'CHAVE CONFIGURADA E BLOQUEADA'
                  : 'CHAVE AINDA NÃO CONFIGURADA'}
            </span>
            {!isLoadingAiSettings && (
              <span>Armazenamento: {aiStorageLabel(aiSettings.storage)}.</span>
            )}
          </div>

          {(aiSettingsError || aiSettingsMessage) && (
            <p
              className={`form-message${aiSettingsError ? ' is-error' : ' is-success'}`}
              role="status"
            >
              {aiSettingsError || aiSettingsMessage}
            </p>
          )}

          <div className="form-actions form-field-wide">
            <button
              className="primary-button"
              disabled={isSavingApiKey || aiSettings.storage === 'environment'}
              type="submit"
            >
              {isSavingApiKey
                ? 'Salvando…'
                : aiSettings.unlocked
                  ? 'Chave disponível nesta execução'
                  : aiSettings.configured
                    ? 'Desbloquear chave'
                    : 'Criptografar e salvar chave'}
            </button>
            {aiSettings.configured &&
              aiSettings.storage === 'encrypted_database' && (
                <>
                  {aiSettings.unlocked && (
                    <>
                      <button
                        className="text-button text-button-plain"
                        disabled={isSavingApiKey || isTestingAiConnection}
                        onClick={() => void handleOpenAiConnectionTest()}
                        type="button"
                      >
                        {isTestingAiConnection
                          ? 'Testando conexão…'
                          : 'Testar conexão'}
                      </button>
                      <button
                        className="text-button text-button-plain"
                        disabled={isSavingApiKey || isTestingAiConnection}
                        onClick={() => void handleApiKeyLock()}
                        type="button"
                      >
                        Bloquear cofre
                      </button>
                    </>
                  )}
                  <button
                    className="text-button text-button-plain danger-button"
                    disabled={isSavingApiKey}
                    onClick={() => void handleApiKeyRemoval()}
                    type="button"
                  >
                    Remover chave local
                  </button>
                </>
              )}
          </div>
        </form>
      </section>

      <section
        className="editorial-hero"
        id="inicio"
        aria-labelledby="page-title"
      >
        <div className="hero-copy">
          <p className="eyebrow">PLATAFORMA LOCAL DE VAGAS</p>
          <h1
            id="page-title"
            aria-label="Encontre oportunidades. Prepare-se para avançar."
          >
            Encontre oportunidades.
            <br />
            <em>Prepare-se para avançar.</em>
          </h1>
          <p className="lede">
            Um espaço simples para transformar sua busca de emprego em um
            processo que você consegue acompanhar.
          </p>
          <div className="hero-actions">
            <button
              className="primary-button"
              onClick={openProfileForm}
              type="button"
            >
              Configurar meu perfil
            </button>
            <a className="text-button" href="#como-funciona">
              Ver como funciona <span aria-hidden="true">↗</span>
            </a>
          </div>
          <p className="privacy-note">
            <span className="status-dot" aria-hidden="true" />
            Dados ficam neste computador.
          </p>
        </div>

        <aside
          className="workspace-card"
          id="perfil"
          aria-labelledby="workspace-title"
        >
          <div className="card-topline">
            <span className="meta-label">01 · SEU ESPAÇO DE BUSCA</span>
            <span className="card-status">{profileStatus}</span>
          </div>
          <div className="card-body">
            <p className="card-kicker">PRIMEIRO PASSO</p>
            <h2 id="workspace-title">
              {profile
                ? 'Seu perfil está pronto para buscar oportunidades.'
                : 'Seu perfil ainda não foi configurado.'}
            </h2>
            <p>
              {profile
                ? `Versão ${profile.version_number} está salva neste computador.`
                : 'Comece dizendo que tipo de oportunidade faz sentido para você. O restante do espaço se adapta a essas escolhas.'}
            </p>
            <div
              className="progress-line"
              aria-label={profile ? 'Perfil configurado' : 'Etapa 1 de 3'}
            >
              <span
                className={`progress-fill${profile ? ' profile-ready' : ''}`}
              />
            </div>
            <div className="progress-caption">
              <span>Perfil</span>
              <span>{profile ? 'configurado' : '1 de 3 etapas'}</span>
            </div>
          </div>
          <div className="card-footer">
            <span className="mono-note">SEM CONTA · SEM NUVEM</span>
            <button
              className="card-link"
              onClick={openProfileForm}
              type="button"
            >
              {profile ? 'Editar' : 'Começar'} <span aria-hidden="true">→</span>
            </button>
          </div>
        </aside>
      </section>

      {isFormOpen && (
        <section
          className="profile-form-section"
          aria-labelledby="profile-form-title"
        >
          <div className="profile-form-intro">
            <p className="eyebrow">CONFIGURAÇÃO DO PERFIL</p>
            <h2 id="profile-form-title">Configure seu perfil</h2>
            <p>
              Esses critérios orientam a busca e ficam somente no banco local do
              Job Finder.
            </p>
          </div>

          <form className="profile-form" onSubmit={handleSubmit}>
            <div className="form-field form-field-wide">
              <label htmlFor="target-roles">Cargos desejados</label>
              <input
                id="target-roles"
                onChange={(event) => handleFormChange('targetRoles', event)}
                placeholder="Ex.: Backend Engineer, Python Developer"
                value={formState.targetRoles}
              />
              <span>Separe mais de um cargo por vírgula.</span>
            </div>

            <div className="form-field form-field-wide">
              <label htmlFor="skills">Competências</label>
              <textarea
                id="skills"
                onChange={(event) => handleFormChange('skills', event)}
                placeholder="Ex.: Python, FastAPI, SQL"
                rows={3}
                value={formState.skills}
              />
              <span>Use palavras-chave que aparecem nas vagas.</span>
            </div>

            <fieldset className="form-field form-field-wide">
              <legend>Modalidades de trabalho</legend>
              <div className="checkbox-grid">
                {(
                  [
                    ['remote', 'Remoto'],
                    ['hybrid', 'Híbrido'],
                    ['on_site', 'Presencial'],
                  ] as const
                ).map(([value, label]) => (
                  <label className="checkbox-label" key={value}>
                    <input
                      checked={formState.workModels.includes(value)}
                      onChange={() => toggleWorkModel(value)}
                      type="checkbox"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="form-field">
              <label htmlFor="countries">Países permitidos</label>
              <input
                id="countries"
                onChange={(event) => handleFormChange('countries', event)}
                placeholder="Ex.: Brasil, Portugal"
                value={formState.countries}
              />
              <span>Filtro obrigatório; deixe vazio para aceitar todos.</span>
            </div>

            <fieldset className="form-field">
              <legend>Tipos de contrato</legend>
              <div className="checkbox-grid">
                {(
                  [
                    ['full_time', 'Tempo integral'],
                    ['part_time', 'Meio período'],
                    ['contract', 'Contrato'],
                    ['temporary', 'Temporário'],
                    ['internship', 'Estágio'],
                  ] as const
                ).map(([value, label]) => (
                  <label className="checkbox-label" key={value}>
                    <input
                      checked={formState.contractTypes.includes(value)}
                      onChange={() => {
                        setFormState((current) => ({
                          ...current,
                          contractTypes: current.contractTypes.includes(value)
                            ? current.contractTypes.filter(
                                (item) => item !== value,
                              )
                            : [...current.contractTypes, value],
                        }));
                        setFormError(null);
                      }}
                      type="checkbox"
                    />
                    {label}
                  </label>
                ))}
              </div>
              <span>Vazio significa aceitar qualquer tipo.</span>
            </fieldset>

            <div className="form-field">
              <label htmlFor="locations">Localizações preferidas</label>
              <input
                id="locations"
                onChange={(event) => handleFormChange('locations', event)}
                placeholder="Ex.: Brasil, São Paulo"
                value={formState.locations}
              />
            </div>

            <div className="form-field">
              <label htmlFor="excluded-keywords">Palavras a evitar</label>
              <input
                id="excluded-keywords"
                onChange={(event) =>
                  handleFormChange('excludedKeywords', event)
                }
                placeholder="Ex.: estágio, presencial"
                value={formState.excludedKeywords}
              />
            </div>

            <div className="form-field">
              <label htmlFor="language-code">Idioma principal</label>
              <input
                id="language-code"
                maxLength={5}
                onChange={(event) => handleFormChange('languageCode', event)}
                placeholder="Ex.: en"
                value={formState.languageCode}
              />
            </div>

            <div className="form-field">
              <label htmlFor="language-level">Nível mínimo</label>
              <select
                id="language-level"
                onChange={(event) => handleFormChange('languageLevel', event)}
                value={formState.languageLevel}
              >
                <option value="basic">Básico</option>
                <option value="intermediate">Intermediário</option>
                <option value="professional">Profissional</option>
                <option value="native">Nativo</option>
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="minimum-monthly">Pretensão mínima mensal</label>
              <input
                id="minimum-monthly"
                min="0"
                onChange={(event) => handleFormChange('minimumMonthly', event)}
                placeholder="Opcional"
                type="number"
                value={formState.minimumMonthly}
              />
            </div>

            <div className="form-field">
              <label htmlFor="maximum-monthly">Pretensão máxima mensal</label>
              <input
                id="maximum-monthly"
                min="0"
                onChange={(event) => handleFormChange('maximumMonthly', event)}
                placeholder="Opcional"
                type="number"
                value={formState.maximumMonthly}
              />
            </div>

            <div className="form-field">
              <label htmlFor="currency">Moeda</label>
              <select
                id="currency"
                onChange={(event) => handleFormChange('currency', event)}
                value={formState.currency}
              >
                <option value="BRL">BRL · Real</option>
                <option value="USD">USD · Dólar</option>
                <option value="EUR">EUR · Euro</option>
              </select>
            </div>

            <div className="weight-note form-field-wide">
              <span className="meta-label">PESOS INICIAIS DA ANÁLISE</span>
              <span>Competências 40% · Experiência 35% · Localização 25%</span>
            </div>

            <div className="redaction-preview form-field-wide">
              <div className="redaction-heading">
                <div>
                  <label htmlFor="ai-preview-input">
                    Texto para análise da IA
                  </label>
                  <span>
                    Veja exatamente o que poderá ser enviado depois da redação.
                  </span>
                </div>
                <button
                  className="header-action"
                  disabled={isRedacting}
                  onClick={handleRedactionPreview}
                  type="button"
                >
                  {isRedacting ? 'Redigindo…' : 'Gerar prévia segura'}
                </button>
              </div>
              <textarea
                id="ai-preview-input"
                onChange={(event) => {
                  setPreviewText(event.target.value);
                  setRedactionPreview(null);
                  setRedactionError(null);
                }}
                placeholder="Cole aqui um trecho de currículo ou descrição de vaga..."
                rows={4}
                value={previewText}
              />
              {redactionError && (
                <p className="form-message is-error" role="status">
                  {redactionError}
                </p>
              )}
              {redactionPreview && (
                <div className="redaction-result">
                  <span className="meta-label">PRÉVIA SEGURA PARA A IA</span>
                  <output aria-label="Prévia segura para a IA">
                    {redactionPreview.redacted_text}
                  </output>
                  <div className="redaction-counts">
                    {redactionPreview.replacements.map((replacement) => (
                      <span key={replacement.kind}>
                        {replacement.count} {replacementLabel(replacement.kind)}{' '}
                        removido
                        {replacement.count > 1 ? 's' : ''}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {(formError || loadError || saveMessage) && (
              <p
                className={`form-message${formError || loadError ? ' is-error' : ' is-success'}`}
                role="status"
              >
                {formError || loadError || saveMessage}
              </p>
            )}

            <div className="form-actions form-field-wide">
              <button
                className="primary-button"
                disabled={isSaving}
                type="submit"
              >
                {isSaving ? 'Salvando…' : 'Salvar perfil'}
              </button>
              <button
                className="text-button text-button-plain"
                onClick={() => setIsFormOpen(false)}
                type="button"
              >
                Cancelar
              </button>
            </div>
          </form>
        </section>
      )}

      {profile && profileHistory.length > 0 && (
        <section
          className="history-section"
          id="historico"
          aria-labelledby="history-title"
        >
          <div className="history-intro">
            <p className="eyebrow">HISTÓRICO DO PERFIL</p>
            <h2 id="history-title">
              Cada versão preserva o contexto da busca.
            </h2>
            <p>
              Editar o perfil cria uma nova versão. As anteriores continuam
              disponíveis para entender quando seus critérios mudaram.
            </p>
          </div>

          <ol className="history-list">
            {[...profileHistory]
              .sort((left, right) => right.version_number - left.version_number)
              .map((version) => {
                const isActive =
                  version.version_number === profile.version_number;
                return (
                  <li
                    className={`history-row${isActive ? ' is-active' : ''}`}
                    key={version.version_number}
                  >
                    <div className="history-version">
                      <span>Versão {version.version_number}</span>
                      {isActive && <strong>Ativa</strong>}
                    </div>
                    <div className="history-content">
                      <h3>{version.criteria.target_roles.join(' · ')}</h3>
                      <p>
                        {version.criteria.skills.length > 0
                          ? version.criteria.skills.join(', ')
                          : 'Sem competências adicionais'}
                      </p>
                    </div>
                    <time dateTime={version.created_at}>
                      {formatVersionDate(version.created_at)}
                    </time>
                  </li>
                );
              })}
          </ol>
        </section>
      )}

      <section
        className="agenda-section"
        id="agenda"
        aria-labelledby="agenda-title"
      >
        <div className="agenda-intro">
          <p className="eyebrow">PRÓXIMOS PASSOS</p>
          <h2 id="agenda-title">Agenda do processo seletivo</h2>
          <p>
            Entrevistas, desafios e prazos ficam agrupados por período para você
            saber o que exige atenção agora.
          </p>
        </div>

        <div className="agenda-workspace">
          {isLoadingAgenda && (
            <p className="agenda-feedback" role="status">
              Carregando agenda…
            </p>
          )}
          {!isLoadingAgenda && agendaError && (
            <p className="agenda-feedback is-error" role="status">
              {agendaError}
            </p>
          )}
          {!isLoadingAgenda && !agendaError && agendaEvents.length === 0 && (
            <div className="agenda-empty">
              <span className="meta-label">AGENDA LIVRE</span>
              <p>
                Registre uma entrevista, desafio ou prazo para acompanhar aqui.
              </p>
            </div>
          )}
          {!isLoadingAgenda && !agendaError && agendaEvents.length > 0 && (
            <div className="agenda-groups">
              <div className="agenda-group">
                <div className="agenda-group-heading">
                  <h3>Próximos</h3>
                  <span>{agendaUpcoming.length}</span>
                </div>
                {agendaUpcoming.length === 0 ? (
                  <p className="agenda-group-empty">Nenhum evento próximo.</p>
                ) : (
                  <ul className="agenda-list">
                    {agendaUpcoming.map((event) => (
                      <li className="agenda-item" key={event.id}>
                        <div>
                          <span className="agenda-status is-upcoming">
                            PRÓXIMO
                          </span>
                          <h4>{event.title}</h4>
                          <p>
                            {event.kind} · candidatura #{event.application_id}
                          </p>
                        </div>
                        <time dateTime={event.starts_at}>
                          {formatAgendaDate(
                            event.starts_at,
                            event.timezone_name,
                          )}
                        </time>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="agenda-group">
                <div className="agenda-group-heading">
                  <h3>Vencidos</h3>
                  <span>{agendaOverdue.length}</span>
                </div>
                {agendaOverdue.length === 0 ? (
                  <p className="agenda-group-empty">Nenhum prazo vencido.</p>
                ) : (
                  <ul className="agenda-list">
                    {agendaOverdue.map((event) => (
                      <li className="agenda-item is-overdue" key={event.id}>
                        <div>
                          <span className="agenda-status is-overdue">
                            VENCIDO
                          </span>
                          <h4>{event.title}</h4>
                          <p>
                            {event.kind} · candidatura #{event.application_id}
                          </p>
                        </div>
                        <time dateTime={event.starts_at}>
                          {formatAgendaDate(
                            event.starts_at,
                            event.timezone_name,
                          )}
                        </time>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      </section>

      <section
        className="trash-section"
        id="lixeira"
        aria-labelledby="trash-title"
      >
        <div className="trash-intro">
          <p className="eyebrow">RETENÇÃO LOCAL</p>
          <h2 id="trash-title">Lixeira recuperável</h2>
          <p>
            Vagas removidas ficam disponíveis até a data de retenção. Restaurar
            mantém o histórico; excluir definitivamente exige confirmação.
          </p>
        </div>

        <div className="trash-workspace">
          {isLoadingTrash && (
            <p className="trash-feedback" role="status">
              Carregando lixeira…
            </p>
          )}
          {!isLoadingTrash && trashError && (
            <p className="trash-feedback is-error" role="status">
              {trashError}
            </p>
          )}
          {!isLoadingTrash && !trashError && trashJobs.length === 0 && (
            <div className="trash-empty">
              <span className="meta-label">LIXEIRA VAZIA</span>
              <p>
                Vagas removidas aparecerão aqui enquanto puderem ser
                restauradas.
              </p>
            </div>
          )}
          {!isLoadingTrash && trashJobs.length > 0 && (
            <ul className="trash-list">
              {trashJobs.map((job) => (
                <li className="trash-item" key={job.id}>
                  <div>
                    <span className="job-status">REMOVIDA</span>
                    <h3>{job.title}</h3>
                    <p>{job.company}</p>
                    <span className="mono-note">
                      Expira em {formatVersionDate(job.purge_after)}
                    </span>
                  </div>
                  <div className="trash-actions">
                    <button
                      className="card-link"
                      onClick={() => void restoreTrashJob(job.id)}
                      type="button"
                    >
                      Restaurar vaga
                    </button>
                    <button
                      className="text-button text-button-plain danger-button"
                      onClick={() => void permanentlyDeleteTrashJob(job.id)}
                      type="button"
                    >
                      Excluir definitivamente
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section
        className="dashboard-section"
        id="dashboard"
        aria-labelledby="dashboard-title"
      >
        <div className="dashboard-intro">
          <p className="eyebrow">PAINEL OPERACIONAL</p>
          <h2 id="dashboard-title">O movimento da sua busca</h2>
          <p>
            Métricas locais, com denominadores visíveis e crédito de fonte
            definido.
          </p>
        </div>
        <div className="dashboard-workspace">
          <div className="dashboard-toolbar">
            <label htmlFor="dashboard-period">Período do painel</label>
            <select
              id="dashboard-period"
              onChange={(event) => setDashboardDays(event.target.value)}
              value={dashboardDays}
            >
              <option value="30">Últimos 30 dias</option>
              <option value="90">Últimos 90 dias</option>
              <option value="365">Último ano</option>
            </select>
          </div>
          {isLoadingDashboard && (
            <p className="dashboard-feedback" role="status">
              Calculando métricas…
            </p>
          )}
          {!isLoadingDashboard && dashboardError && (
            <p className="dashboard-feedback is-error" role="status">
              {dashboardError}
            </p>
          )}
          {!isLoadingDashboard && !dashboardError && dashboard && (
            <>
              <div className="dashboard-cards" aria-label="Resumo do período">
                {(
                  [
                    ['jobs_found', 'Vagas encontradas'],
                    ['applications', 'Candidaturas'],
                    ['interviews', 'Entrevistas'],
                    ['offers', 'Ofertas'],
                    ['hired', 'Contratações'],
                    ['active_pipeline', 'Pipeline ativo'],
                  ] as [keyof DashboardSummary['cards'], string][]
                ).map(([key, label]) => (
                  <article className="dashboard-card" key={key}>
                    <span className="meta-label">{label}</span>
                    <strong>{dashboard.cards[key]}</strong>
                  </article>
                ))}
              </div>
              <div className="dashboard-grid">
                <section
                  className="dashboard-panel"
                  aria-labelledby="dashboard-funnel-title"
                >
                  <div className="dashboard-panel-heading">
                    <h3 id="dashboard-funnel-title">Funil de conversão</h3>
                    <span className="mono-note">denominador visível</span>
                  </div>
                  <ol className="dashboard-funnel">
                    {dashboard.funnel.map((stage) => (
                      <li key={stage.key}>
                        <div>
                          <span>{stage.label}</span>
                          <strong>{stage.count}</strong>
                        </div>
                        <progress
                          aria-label={`${stage.label}: ${stage.count} de ${stage.denominator}`}
                          max={stage.denominator || 1}
                          value={stage.count}
                        />
                        <small>
                          {stage.conversion_percent == null
                            ? 'sem base'
                            : `${stage.conversion_percent}% de ${stage.denominator}`}
                        </small>
                      </li>
                    ))}
                  </ol>
                </section>
                <section
                  className="dashboard-panel"
                  aria-labelledby="dashboard-agenda-title"
                >
                  <div className="dashboard-panel-heading">
                    <h3 id="dashboard-agenda-title">Agenda</h3>
                    <a className="card-link" href="#agenda">
                      Abrir agenda
                    </a>
                  </div>
                  <div className="dashboard-agenda-summary">
                    <strong>{dashboard.agenda.upcoming}</strong>
                    <span>próximos</span>
                    <strong
                      className={
                        dashboard.agenda.overdue > 0 ? 'is-warning' : ''
                      }
                    >
                      {dashboard.agenda.overdue}
                    </strong>
                    <span>atrasados</span>
                  </div>
                </section>
              </div>
              <div className="dashboard-grid">
                <section
                  className="dashboard-panel"
                  aria-labelledby="dashboard-series-title"
                >
                  <div className="dashboard-panel-heading">
                    <h3 id="dashboard-series-title">Evolução semanal</h3>
                    <span className="mono-note">
                      vagas · candidaturas · entrevistas
                    </span>
                  </div>
                  <div className="dashboard-table-wrap">
                    <table>
                      <caption className="visually-hidden">
                        Evolução semanal da busca
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Semana</th>
                          <th scope="col">Vagas</th>
                          <th scope="col">Candidaturas</th>
                          <th scope="col">Entrevistas</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dashboard.series.map((point) => (
                          <tr key={point.period_start}>
                            <th scope="row">{point.period_start}</th>
                            <td>{point.jobs}</td>
                            <td>{point.applications}</td>
                            <td>{point.interviews}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
                <section
                  className="dashboard-panel"
                  aria-labelledby="dashboard-sources-title"
                >
                  <div className="dashboard-panel-heading">
                    <h3 id="dashboard-sources-title">Desempenho por fonte</h3>
                    <span className="mono-note">
                      crédito na primeira origem
                    </span>
                  </div>
                  <div className="dashboard-table-wrap">
                    <table>
                      <caption className="visually-hidden">
                        Desempenho por fonte
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Fonte</th>
                          <th scope="col">Vagas</th>
                          <th scope="col">Aplicação</th>
                          <th scope="col">Erros</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dashboard.sources.map((source) => (
                          <tr key={source.source_key}>
                            <th scope="row">{source.source_key}</th>
                            <td>{source.jobs}</td>
                            <td>
                              {source.application_rate_percent == null
                                ? '—'
                                : `${source.application_rate_percent}%`}
                            </td>
                            <td>{source.errors}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>
            </>
          )}
        </div>
      </section>

      <section
        className="pipeline-section"
        id="pipeline"
        aria-labelledby="pipeline-title"
      >
        <div className="pipeline-intro">
          <p className="eyebrow">ACOMPANHAMENTO</p>
          <h2 id="pipeline-title">Pipeline de candidaturas</h2>
          <p>
            Cada movimento fica registrado no histórico local. Use o teclado
            para escolher a próxima fase e confirmar a mudança.
          </p>
        </div>

        <div className="pipeline-workspace">
          {isLoadingApplications && (
            <p className="pipeline-feedback" role="status">
              Carregando candidaturas…
            </p>
          )}
          {!isLoadingApplications && applicationsError && (
            <p className="pipeline-feedback is-error" role="status">
              {applicationsError}
            </p>
          )}
          {!isLoadingApplications &&
            !applicationsError &&
            pipelineEntries.length === 0 && (
              <div className="pipeline-empty">
                <span className="meta-label">NENHUMA CANDIDATURA</span>
                <p>
                  Crie uma candidatura a partir de uma vaga para acompanhar as
                  fases neste quadro.
                </p>
              </div>
            )}
          {!isLoadingApplications && pipelineEntries.length > 0 && (
            <div className="pipeline-board">
              {pipelineStages.map((stage) => {
                const stageEntries = pipelineEntries.filter(
                  ({ application }) =>
                    application.current_status === stage.value,
                );
                return (
                  <section
                    className="pipeline-column"
                    key={stage.value}
                    aria-labelledby={`pipeline-${stage.value}`}
                  >
                    <div className="pipeline-column-heading">
                      <h3 id={`pipeline-${stage.value}`}>{stage.label}</h3>
                      <span>{stageEntries.length}</span>
                    </div>
                    <ul className="pipeline-card-list">
                      {stageEntries.map(({ application, job }) => (
                        <li className="pipeline-card" key={application.id}>
                          <span className="job-status">
                            {pipelineStatusLabel(application.current_status)}
                          </span>
                          <h4>{job.title}</h4>
                          <p>{job.company}</p>
                          <label htmlFor={`pipeline-target-${application.id}`}>
                            Próxima fase para {job.title}
                          </label>
                          <select
                            id={`pipeline-target-${application.id}`}
                            onChange={(event) =>
                              setPipelineTargets((current) => ({
                                ...current,
                                [application.id]: event.target
                                  .value as ApplicationStatus,
                              }))
                            }
                            value={
                              pipelineTargets[application.id] ??
                              application.current_status
                            }
                          >
                            {pipelineStages.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                          <button
                            className="card-link pipeline-move-button"
                            disabled={pipelineActionId === application.id}
                            onClick={() =>
                              void moveApplication(application, job)
                            }
                            type="button"
                          >
                            {pipelineActionId === application.id
                              ? 'Movendo…'
                              : 'Mover candidatura'}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </section>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <section className="jobs-section" id="vagas" aria-labelledby="jobs-title">
        <div className="jobs-intro">
          <p className="eyebrow">CAIXA DE ENTRADA</p>
          <h2 id="jobs-title">Caixa de entrada de vagas</h2>
          <p>
            Revise oportunidades encontradas, mantenha a origem registrada e
            escolha o próximo passo sem sair do computador.
          </p>
        </div>

        <div className="jobs-workspace">
          <div className="jobs-toolbar">
            <div className="job-search-field">
              <label htmlFor="job-search">Buscar na caixa de entrada</label>
              <input
                id="job-search"
                onChange={(event) => setJobSearch(event.target.value)}
                placeholder="Cargo, empresa ou local"
                value={jobSearch}
              />
            </div>
            <button
              className="header-action"
              onClick={openJobForm}
              type="button"
            >
              Adicionar vaga
            </button>
          </div>
          <div className="saved-filter-toolbar">
            <label htmlFor="saved-filter-select">Filtro salvo</label>
            <select
              id="saved-filter-select"
              onChange={(event) => applySavedFilter(event.target.value)}
              value={selectedSavedFilter}
            >
              <option value="">Nenhum filtro salvo</option>
              {savedFilters.map((filter) => (
                <option key={filter.id} value={filter.id}>
                  {filter.name}
                </option>
              ))}
            </select>
            <label className="saved-filter-name" htmlFor="saved-filter-name">
              Nome
              <input
                id="saved-filter-name"
                onChange={(event) => setSavedFilterName(event.target.value)}
                placeholder="ex.: Backend remoto"
                value={savedFilterName}
              />
            </label>
            <button
              className="card-link"
              onClick={() => void saveCurrentFilter()}
              type="button"
            >
              Salvar filtro atual
            </button>
          </div>
          {savedFilterMessage && (
            <p className="form-message" role="status">
              {savedFilterMessage}
            </p>
          )}

          {isLoadingJobDetail && (
            <p className="jobs-feedback" role="status">
              Carregando detalhe…
            </p>
          )}
          {jobDetailError && (
            <p className="jobs-feedback is-error" role="status">
              {jobDetailError}
            </p>
          )}
          {selectedJob && !isLoadingJobDetail && (
            <article className="job-detail" aria-labelledby="job-detail-title">
              <div className="job-detail-topline">
                <span className="meta-label">DETALHE DA VAGA</span>
                <button
                  className="text-button text-button-plain"
                  onClick={() => setSelectedJob(null)}
                  type="button"
                >
                  Fechar detalhe
                </button>
              </div>
              <span className="job-status">{selectedJob.status_label}</span>
              <h3 id="job-detail-title">Detalhe da vaga</h3>
              <h4>{selectedJob.title}</h4>
              <p className="job-detail-company">
                {selectedJob.company}
                {selectedJob.location ? ` · ${selectedJob.location}` : ''}
              </p>
              <div className="job-analysis-actions">
                <button
                  className="primary-button"
                  disabled={isAnalyzingJob}
                  onClick={() => void analyzeSelectedJobs([selectedJob.id])}
                  type="button"
                >
                  {isAnalyzingJob ? 'Analisando…' : 'Analisar esta vaga com IA'}
                </button>
                {jobAnalyses[selectedJob.id] && (
                  <span className="mono-note">
                    Versão {jobAnalyses[selectedJob.id].analysis_version} ·{' '}
                    {jobAnalyses[selectedJob.id].usage.fallback
                      ? 'triagem local limitada'
                      : `${jobAnalyses[selectedJob.id].usage.estimated_cost_usd == null ? 'custo indisponível' : `US$ ${jobAnalyses[selectedJob.id].usage.estimated_cost_usd!.toFixed(4)}`}`}
                  </span>
                )}
              </div>
              {jobAnalyses[selectedJob.id] && (
                <div className="job-analysis-summary" role="status">
                  <strong>
                    Aderência: {jobAnalyses[selectedJob.id].fit.score}/100
                  </strong>
                  <p>
                    {jobAnalyses[selectedJob.id].analysis.assessment.summary}
                  </p>
                  {jobAnalyses[selectedJob.id].analysis.assessment.warnings
                    .length > 0 && (
                    <p className="mono-note">
                      {jobAnalyses[
                        selectedJob.id
                      ].analysis.assessment.warnings.join(' · ')}
                    </p>
                  )}
                </div>
              )}
              <div className="job-detail-grid">
                <div>
                  <span className="meta-label">ORIGENS</span>
                  <ul className="job-origin-list">
                    {selectedJob.origins.map((origin) => (
                      <li key={origin.id}>
                        <span>{origin.source}</span>
                        {origin.url && (
                          <a href={origin.url} rel="noreferrer" target="_blank">
                            Abrir URL
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <span className="meta-label">CONTEÚDO VERSIONADO</span>
                  <ol className="job-content-history">
                    {[...selectedJob.content_versions]
                      .sort(
                        (left, right) =>
                          right.version_number - left.version_number,
                      )
                      .map((version) => (
                        <li key={version.id}>
                          <span>Versão {version.version_number}</span>
                          <pre className="job-detail-content">
                            {version.raw_content}
                          </pre>
                        </li>
                      ))}
                  </ol>
                </div>
              </div>
            </article>
          )}

          {isJobFormOpen && (
            <form className="job-form" onSubmit={handleManualJobSubmit}>
              <div className="form-field">
                <label htmlFor="manual-job-url">URL canônica</label>
                <input
                  id="manual-job-url"
                  onChange={(event) =>
                    setManualJobForm((current) => ({
                      ...current,
                      canonicalUrl: event.target.value,
                    }))
                  }
                  type="url"
                  value={manualJobForm.canonicalUrl}
                />
              </div>
              <div className="form-field">
                <label htmlFor="manual-job-title">Título da vaga</label>
                <input
                  id="manual-job-title"
                  onChange={(event) =>
                    setManualJobForm((current) => ({
                      ...current,
                      title: event.target.value,
                    }))
                  }
                  value={manualJobForm.title}
                />
              </div>
              <div className="form-field">
                <label htmlFor="manual-job-company">Empresa</label>
                <input
                  id="manual-job-company"
                  onChange={(event) =>
                    setManualJobForm((current) => ({
                      ...current,
                      company: event.target.value,
                    }))
                  }
                  value={manualJobForm.company}
                />
              </div>
              <div className="form-field">
                <label htmlFor="manual-job-location">Localização</label>
                <input
                  id="manual-job-location"
                  onChange={(event) =>
                    setManualJobForm((current) => ({
                      ...current,
                      location: event.target.value,
                    }))
                  }
                  placeholder="Opcional"
                  value={manualJobForm.location}
                />
              </div>
              <div className="form-field form-field-wide">
                <label htmlFor="manual-job-content">Conteúdo da vaga</label>
                <textarea
                  id="manual-job-content"
                  onChange={(event) =>
                    setManualJobForm((current) => ({
                      ...current,
                      content: event.target.value,
                    }))
                  }
                  rows={5}
                  value={manualJobForm.content}
                />
              </div>
              {(jobFormError || jobMessage) && (
                <p
                  className={`form-message${jobFormError ? ' is-error' : ' is-success'}`}
                  role="status"
                >
                  {jobFormError || jobMessage}
                </p>
              )}
              <div className="form-actions form-field-wide">
                <button
                  className="primary-button"
                  disabled={isSavingJob}
                  type="submit"
                >
                  {isSavingJob ? 'Salvando…' : 'Salvar vaga'}
                </button>
                <button
                  className="text-button text-button-plain"
                  onClick={() => setIsJobFormOpen(false)}
                  type="button"
                >
                  Cancelar
                </button>
              </div>
            </form>
          )}

          {jobMessage && !isJobFormOpen && (
            <p className="form-message is-success" role="status">
              {jobMessage}
            </p>
          )}

          {isLoadingJobs && (
            <p className="jobs-feedback" role="status">
              Carregando vagas…
            </p>
          )}
          {!isLoadingJobs && jobsError && (
            <p className="jobs-feedback is-error" role="status">
              {jobsError}
            </p>
          )}
          {!isLoadingJobs && !jobsError && jobs.length === 0 && (
            <div className="jobs-empty">
              <span className="meta-label">NENHUMA VAGA SALVA</span>
              <p>Adicione uma vaga manualmente para começar sua revisão.</p>
              <button
                className="text-button"
                onClick={openJobForm}
                type="button"
              >
                Adicionar primeira vaga <span aria-hidden="true">→</span>
              </button>
            </div>
          )}
          {!isLoadingJobs &&
            !jobsError &&
            jobs.length > 0 &&
            visibleJobs.length === 0 && (
              <p className="jobs-feedback" role="status">
                Nenhuma vaga corresponde à busca.
              </p>
            )}
          {!isLoadingJobs && !jobsError && visibleJobs.length > 0 && (
            <>
              <div className="job-bulk-actions">
                <span className="mono-note">
                  {selectedJobIds.length} selecionada(s)
                </span>
                <button
                  className="header-action"
                  disabled={isAnalyzingJob || selectedJobIds.length === 0}
                  onClick={() => void analyzeSelectedJobs(selectedJobIds)}
                  type="button"
                >
                  Analisar selecionadas
                </button>
              </div>
              {analysisMessage && (
                <p className="form-message is-success" role="status">
                  {analysisMessage}
                </p>
              )}
              {analysisError && (
                <p className="form-message is-error" role="status">
                  {analysisError}
                </p>
              )}
              <ul className="job-list">
                {visibleJobs.map((job) => {
                  const analysis = jobAnalyses[job.id];
                  return (
                    <li className="job-row" key={job.id}>
                      <div className="job-row-content">
                        <label className="job-select-control">
                          <input
                            aria-label={`Selecionar ${job.title}`}
                            checked={selectedJobIds.includes(job.id)}
                            onChange={(event) =>
                              setSelectedJobIds((current) =>
                                event.target.checked
                                  ? [...current, job.id]
                                  : current.filter((id) => id !== job.id),
                              )
                            }
                            type="checkbox"
                          />
                        </label>
                        <div className="job-row-main">
                          <span className="job-status">{job.status_label}</span>
                          <h3>{job.title}</h3>
                          <p>
                            {job.company}
                            {job.location ? ` · ${job.location}` : ''}
                          </p>
                        </div>
                        <div className="job-row-meta">
                          <span className="mono-note">
                            {job.origin_count} origem
                            {job.origin_count === 1 ? '' : 'ns'}
                          </span>
                          {job.canonical_url && (
                            <a
                              className="card-link"
                              href={job.canonical_url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              Abrir origem <span aria-hidden="true">↗</span>
                            </a>
                          )}
                          <button
                            className="card-link"
                            onClick={() => void openJobDetail(job.id)}
                            type="button"
                          >
                            Ver detalhes
                          </button>
                        </div>
                      </div>
                      {analysis && (
                        <section
                          aria-label={`Análise concluída: ${job.title}`}
                          className="job-row-analysis"
                          role="region"
                        >
                          <div className="job-row-analysis-heading">
                            <span className="meta-label">
                              ANÁLISE CONCLUÍDA
                            </span>
                            <span className="mono-note">
                              Versão {analysis.analysis_version}
                            </span>
                          </div>
                          <div className="job-row-analysis-identity">
                            <strong>{job.title}</strong>
                            <span>{job.company}</span>
                          </div>
                          <div className="job-row-analysis-score">
                            <strong>Aderência {analysis.fit.score}/100</strong>
                            <span>
                              Confiança{' '}
                              {analysis.analysis.assessment.confidence}%
                            </span>
                          </div>
                          <p>{analysis.analysis.assessment.summary}</p>
                          <button
                            className="card-link"
                            onClick={() => void openJobDetail(job.id)}
                            type="button"
                          >
                            Abrir análise completa de {job.title}
                          </button>
                        </section>
                      )}
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>
      </section>

      <section
        className="preferences-section"
        id="preferencias"
        aria-labelledby="preferences-title"
      >
        <div className="preferences-intro">
          <p className="eyebrow">PREFERÊNCIAS LOCAIS</p>
          <h2 id="preferences-title">Preferências gerais</h2>
          <p>
            Elas orientam idioma, moeda, datas e retenção sem enviar dados para
            a nuvem.
          </p>
        </div>

        <form className="preferences-form" onSubmit={handlePreferencesSubmit}>
          <div className="form-field">
            <label htmlFor="preference-locale">Idioma da interface</label>
            <select
              id="preference-locale"
              onChange={(event) => {
                setPreferences((current) => ({
                  ...current,
                  locale: event.target.value as Preferences['locale'],
                }));
                setPreferencesMessage(null);
              }}
              value={preferences.locale}
            >
              <option value="pt-BR">Português (Brasil)</option>
              <option value="en-US">English (United States)</option>
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="preference-currency">Moeda padrão</label>
            <select
              id="preference-currency"
              onChange={(event) => {
                setPreferences((current) => ({
                  ...current,
                  currency: event.target.value,
                }));
                setPreferencesMessage(null);
              }}
              value={preferences.currency}
            >
              <option value="BRL">BRL · Real</option>
              <option value="USD">USD · Dólar</option>
              <option value="EUR">EUR · Euro</option>
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="preference-timezone">Fuso horário</label>
            <select
              id="preference-timezone"
              onChange={(event) => {
                setPreferences((current) => ({
                  ...current,
                  timezone: event.target.value,
                }));
                setPreferencesMessage(null);
              }}
              value={preferences.timezone}
            >
              <option value="America/Sao_Paulo">America/Sao_Paulo</option>
              <option value="America/New_York">America/New_York</option>
              <option value="Europe/Lisbon">Europe/Lisbon</option>
              <option value="UTC">UTC</option>
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="preference-retention">Retenção local (dias)</label>
            <input
              id="preference-retention"
              max="3650"
              min="30"
              onChange={(event) => {
                setPreferences((current) => ({
                  ...current,
                  retention_days: Number(event.target.value),
                }));
                setPreferencesMessage(null);
              }}
              type="number"
              value={preferences.retention_days}
            />
          </div>

          {(preferencesError || preferencesMessage) && (
            <p
              className={`form-message${preferencesError ? ' is-error' : ' is-success'}`}
              role="status"
            >
              {preferencesError || preferencesMessage}
            </p>
          )}

          <div className="form-actions form-field-wide">
            <button
              className="primary-button"
              disabled={isSavingPreferences}
              type="submit"
            >
              {isSavingPreferences ? 'Salvando…' : 'Salvar preferências'}
            </button>
          </div>
        </form>
      </section>

      <section
        className="process-section"
        id="como-funciona"
        aria-labelledby="process-title"
      >
        <div className="section-heading">
          <p className="eyebrow">COMO FUNCIONA</p>
          <h2 id="process-title">
            Uma busca mais clara, do primeiro anúncio à próxima conversa.
          </h2>
        </div>

        <ol className="step-list" id="fluxo">
          {productSteps.map((step) => (
            <li className="step-row" key={step.number}>
              <span className="step-number">{step.number}</span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
              <span className="step-arrow" aria-hidden="true">
                ↗
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section className="closing-cta" aria-labelledby="closing-title">
        <div>
          <p className="eyebrow">PRÓXIMA ETAPA</p>
          <h2 id="closing-title">
            Sua próxima oportunidade começa com contexto.
          </h2>
        </div>
        <button
          className="inverse-button"
          onClick={openProfileForm}
          type="button"
        >
          Começar agora <span aria-hidden="true">↗</span>
        </button>
      </section>

      <footer className="site-footer">
        <span>JOB FINDER · LOCAL</span>
        <span>v0.1 · DADOS LOCAIS</span>
      </footer>
    </main>
  );
}

export default App;
