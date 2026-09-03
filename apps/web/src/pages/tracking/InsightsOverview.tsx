import {
  Button,
  EmptyState,
  LoadingState,
  Notice,
  PageHeader,
} from '../../components/ui/primitives';
import type { JobAnalysisResponse } from '../jobs/JobAnalysisPanel';
import './tracking.css';
type Props = {
  jobs: { id: number; title: string; company: string }[];
  analyses: Record<number, JobAnalysisResponse>;
  loading: boolean;
  error: string | null;
  onOpen: (id: number) => void;
  onJobs: () => void;
  onSettings: () => void;
};
export function InsightsOverview({
  jobs,
  analyses,
  loading,
  error,
  onOpen,
  onJobs,
  onSettings,
}: Props) {
  const entries = jobs.filter((job) => analyses[job.id]);
  return (
    <div className="workspace-page tracking-page">
      <PageHeader
        eyebrow="ANÁLISES E DECISÕES"
        title="Insights das suas vagas"
        description="Consulte as análises salvas e confira o contexto antes de decidir."
      />
      <section aria-label="Análises disponíveis">
        {loading && <LoadingState label="Carregando análises salvas…" />}
        {error && <Notice tone="warning">{error}</Notice>}
        {!loading && !error && entries.length === 0 && (
          <EmptyState
            title="Nenhuma análise disponível"
            description="Escolha uma vaga e solicite uma análise. A IA só é acionada com sua confirmação."
            action={<Button onClick={onJobs}>Escolher uma vaga</Button>}
          />
        )}
        {entries.length > 0 && (
          <ul className="insights-analysis-list">
            {entries.map((job) => (
              <li key={job.id}>
                <div>
                  <h2>{job.title}</h2>
                  <p>{job.company}</p>
                  <p>{analyses[job.id].analysis.assessment.summary}</p>
                </div>
                <div>
                  <strong>Aderência {analyses[job.id].fit.score}/100</strong>
                  <Button variant="secondary" onClick={() => onOpen(job.id)}>
                    Ver análise de {job.title}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
      <Notice>
        A análise é uma referência, não uma garantia de aprovação. Confira o
        anúncio e possíveis lacunas.
      </Notice>
      <div className="tracking-secondary-actions">
        <Button variant="ghost" onClick={onJobs}>
          Abrir minhas vagas
        </Button>
        <Button variant="ghost" onClick={onSettings}>
          Configurar integrações
        </Button>
        <a href="https://sepreparai.com.br/" target="_blank" rel="noreferrer">
          Treinar entrevista no Se Prepara AI ↗
        </a>
      </div>
    </div>
  );
}
