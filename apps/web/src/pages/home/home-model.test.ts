import { describe, expect, it } from 'vitest';
import { buildHomeSummary, type HomeState } from './home-model';

const readyState: HomeState = {
  profile: {
    version_number: 1,
    criteria: { target_roles: ['Analista de Dados'] },
  },
  jobs: [],
  applications: [],
  events: [],
  sources: [{ enabled: true }],
  providers: [],
  vault: { configured: false, unlocked: false },
  vaultLoading: false,
  loading: {},
  errors: {},
};
const now = Date.parse('2026-09-02T12:00:00Z');
const job = {
  id: 1,
  title: 'Analista de Dados',
  company: 'Empresa',
  status: 'found',
  created_at: '2026-09-01T12:00:00Z',
};

describe('próxima ação do início', () => {
  it('orienta um novo usuário a salvar o perfil', () => {
    expect(
      buildHomeSummary({ ...readyState, profile: null }, now).action,
    ).toMatchObject({ label: 'Configurar meu perfil', target: '/perfil' });
  });
  it('oferece busca para quem já tem perfil e fontes públicas, mesmo sem cofre', () => {
    expect(buildHomeSummary(readyState, now).action.target).toBe('/busca');
  });
  it('pede desbloqueio único quando há credenciais privadas bloqueadas', () => {
    const summary = buildHomeSummary(
      {
        ...readyState,
        vault: { configured: true, unlocked: false },
        providers: [
          { configured: true, unlocked: false, storage: 'encrypted_database' },
        ],
      },
      now,
    );
    expect(summary.action).toMatchObject({
      target: 'vault',
      label: 'Desbloquear cofre',
    });
  });
  it('não exige cofre para uma chave de ambiente ou só pela configuração da OpenAI', () => {
    expect(
      buildHomeSummary(
        {
          ...readyState,
          sources: [],
          vault: { configured: true, unlocked: false },
          providers: [
            { configured: true, unlocked: true, storage: 'environment' },
          ],
        },
        now,
      ).action.target,
    ).toBe('/busca');
  });
  it('indica fontes quando nenhuma está habilitada', () => {
    expect(
      buildHomeSummary({ ...readyState, sources: [{ enabled: false }] }, now)
        .action.target,
    ).toBe('/configuracoes/fontes');
  });
  it('prioriza vagas salvas sobre desbloqueio e candidaturas, usando a fase atual', () => {
    const summary = buildHomeSummary(
      {
        ...readyState,
        jobs: [job, { ...job, id: 2 }, { ...job, id: 3 }],
        applications: [
          {
            id: 1,
            job_id: 1,
            current_status: 'applied',
            updated_at: '2026-09-02T10:00:00Z',
          },
          {
            id: 3,
            job_id: 3,
            current_status: 'rejected',
            updated_at: '2026-09-02T10:00:00Z',
          },
        ],
        vault: { configured: true, unlocked: false },
      },
      now,
    );
    expect(summary.action.target).toBe('/vagas');
    expect(summary.metrics).toMatchObject({ review: 1, active: 1 });
  });
  it('leva candidaturas em andamento ao pipeline e não conta resultados encerrados', () => {
    const applications = [
      'applied',
      'interview',
      'offer',
      'hired',
      'rejected',
      'withdrawn',
      'expired',
      'pending',
      'found',
    ].map((current_status, id) => ({
      id,
      job_id: id,
      current_status,
      updated_at: '2026-09-01T12:00:00Z',
    }));
    const summary = buildHomeSummary({ ...readyState, applications }, now);
    expect(summary.action.target).toBe('/candidaturas');
    expect(summary.metrics.active).toBe(3);
  });
  it('usa a coleção completa sem limite de dez vagas', () => {
    expect(
      buildHomeSummary(
        {
          ...readyState,
          jobs: Array.from({ length: 37 }, (_, id) => ({ ...job, id })),
        },
        now,
      ).metrics.review,
    ).toBe(37);
  });
  it('distingue carregamento e erro de contagens vazias', () => {
    const loading = buildHomeSummary(
      { ...readyState, loading: { jobs: true } },
      now,
    );
    expect(loading.metrics.review).toBeNull();
    expect(loading.action.target).toBeNull();
    const failed = buildHomeSummary(
      { ...readyState, errors: { jobs: true } },
      now,
    );
    expect(failed.metrics.review).toBeNull();
    expect(failed.action.label).toBe('Verificar vagas');
  });
  it('não anuncia fonte disponível quando sua consulta falha', () => {
    expect(
      buildHomeSummary({ ...readyState, errors: { sources: true } }, now).action
        .label,
    ).toBe('Verificar fontes');
  });
  it('conta eventos futuros/em andamento e ignora cancelados, concluídos e datas inválidas', () => {
    const events = [
      { status: 'scheduled', starts_at: '2026-09-03T12:00:00Z', ends_at: null },
      {
        status: 'scheduled',
        starts_at: '2026-09-02T11:00:00Z',
        ends_at: '2026-09-02T13:00:00Z',
      },
      { status: 'cancelled', starts_at: '2026-09-03T12:00:00Z', ends_at: null },
      { status: 'completed', starts_at: '2026-09-03T12:00:00Z', ends_at: null },
      { status: 'scheduled', starts_at: 'inválida', ends_at: null },
      { status: 'scheduled', starts_at: '2026-09-01T12:00:00Z', ends_at: null },
    ];
    expect(
      buildHomeSummary({ ...readyState, events }, now).metrics.upcoming,
    ).toBe(2);
  });
  it('ordena atividade persistida, limita a cinco e não inventa datas', () => {
    const jobs = Array.from({ length: 8 }, (_, id) => ({
      ...job,
      id,
      created_at: `2026-08-${20 + id}T10:00:00Z`,
    }));
    const summary = buildHomeSummary(
      {
        ...readyState,
        jobs: [...jobs, { ...job, id: 90, created_at: 'inválida' }],
      },
      now,
    );
    expect(summary.activity).toHaveLength(5);
    expect(summary.activity[0]).toMatchObject({
      id: 'job-7',
      target: '/vagas',
    });
    expect(jobs[0].id).toBe(0);
  });
});
