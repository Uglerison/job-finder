import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';

import './App.css';

type WorkModel = 'remote' | 'hybrid' | 'on_site';
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

type ProfileFormState = {
  targetRoles: string;
  skills: string;
  workModels: WorkModel[];
  locations: string;
  excludedKeywords: string;
  languageCode: string;
  languageLevel: LanguageLevel;
  currency: string;
  minimumMonthly: string;
  maximumMonthly: string;
};

const defaultFormState: ProfileFormState = {
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
