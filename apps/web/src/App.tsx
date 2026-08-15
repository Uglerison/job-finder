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
  const [isLoadingJobDetail, setIsLoadingJobDetail] = useState(false);
  const [jobDetailError, setJobDetailError] = useState<string | null>(null);

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
          setJobs(Array.isArray(payload?.items) ? payload.items : []);
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

  const visibleJobs = jobs.filter((job) => {
    const query = jobSearch.trim().toLocaleLowerCase();
    if (!query) {
      return true;
    }
    return `${job.title} ${job.company} ${job.location ?? ''}`
      .toLocaleLowerCase()
      .includes(query);
  });

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
            <a href="#vagas">Vagas</a>
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
                      .sort((left, right) => right.version_number - left.version_number)
                      .map((version) => (
                        <li key={version.id}>
                          <span>Versão {version.version_number}</span>
                          <pre className="job-detail-content">{version.raw_content}</pre>
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
            <ul className="job-list">
              {visibleJobs.map((job) => (
                <li className="job-row" key={job.id}>
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
                </li>
              ))}
            </ul>
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
