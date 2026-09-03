import { Badge } from '../../components/ui/primitives';
type AnalysisUsage = {
  estimated_cost_usd: number | null;
  fallback: boolean;
  fallback_reason: string | null;
  input_tokens: number | null;
  latency_ms: number;
  metered: boolean;
  output_tokens: number | null;
};

export type JobAnalysisResponse = {
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

export function JobAnalysisPanel({
  title,
  analysis,
}: {
  title: string;
  analysis: JobAnalysisResponse;
}) {
  const assessment = analysis.analysis.assessment;
  return (
    <section className="job-analysis-panel" aria-label={`Análise de ${title}`}>
      <div className="job-analysis-panel-heading">
        <h3>Análise de {title}</h3>
        <Badge tone="success">Concluída</Badge>
      </div>
      <p>
        <strong>Aderência: {analysis.fit.score}/100</strong> · Confiança{' '}
        {assessment.confidence}%
      </p>
      <p>{assessment.summary}</p>
      <div className="job-analysis-findings">
        <div>
          <h4>Pontos fortes</h4>
          {assessment.strengths?.length ? (
            <ul>
              {assessment.strengths.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          ) : (
            <p>Nenhum ponto forte identificado.</p>
          )}
        </div>
        <div>
          <h4>Lacunas a avaliar</h4>
          {assessment.gaps?.length ? (
            <ul>
              {assessment.gaps.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          ) : (
            <p>Nenhuma lacuna identificada.</p>
          )}
        </div>
      </div>
      {assessment.warnings?.length > 0 && (
        <p className="job-analysis-warning">
          {assessment.warnings.join(' · ')}
        </p>
      )}
      <details>
        <summary>Evidências e informações da análise</summary>
        {analysis.explanation?.supported_evidence?.map((item, index) => (
          <blockquote key={index}>
            <strong>{item.claim}</strong>
            <p>{item.quote}</p>
          </blockquote>
        ))}
        <p>
          Versão {analysis.analysis_version} ·{' '}
          {analysis.usage.fallback ? 'Triagem local limitada' : analysis.model}{' '}
          ·{' '}
          {analysis.usage.estimated_cost_usd == null
            ? 'Custo indisponível'
            : `US$ ${analysis.usage.estimated_cost_usd.toFixed(4)}`}
        </p>
      </details>
    </section>
  );
}
