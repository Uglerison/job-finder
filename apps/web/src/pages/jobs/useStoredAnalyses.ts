import { useEffect, useState } from 'react';
import type { JobAnalysisResponse } from './JobAnalysisPanel';
type StoredAnalysis = Omit<JobAnalysisResponse, 'analysis_version'> & {
  version_number: number;
};
export function useStoredAnalyses(
  jobs: { id: number }[],
  ready: boolean,
  request: (url: string) => Promise<Response>,
) {
  const [analyses, setAnalyses] = useState<Record<number, JobAnalysisResponse>>(
    {},
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!ready) return;
    let active = true;
    setLoading(true);
    setError(null);
    const run = async () => {
      const saved: Record<number, JobAnalysisResponse> = {};
      let failed = false;
      // Limit local reads instead of firing one unbounded request per saved job.
      for (let offset = 0; offset < jobs.length; offset += 6) {
        if (!active) return;
        await Promise.all(
          jobs.slice(offset, offset + 6).map(async (job) => {
            try {
              const response = await request(`/api/jobs/${job.id}/analyses`);
              if (!response.ok) throw Error('history unavailable');
              const versions: StoredAnalysis[] = await response.json();
              if (!Array.isArray(versions)) return;
              const latest = versions.reduce<StoredAnalysis | null>(
                (best, item) =>
                  !best || item.version_number > best.version_number
                    ? item
                    : best,
                null,
              );
              if (latest)
                saved[job.id] = {
                  ...latest,
                  analysis_version: latest.version_number,
                };
            } catch {
              failed = true;
            }
          }),
        );
      }
      if (!active) return;
      setAnalyses((current) => {
        const next = { ...current };
        for (const [id, value] of Object.entries(saved))
          if (
            !next[Number(id)] ||
            next[Number(id)].analysis_version < value.analysis_version
          )
            next[Number(id)] = value;
        return next;
      });
      setError(
        failed ? 'Não foi possível carregar todas as análises salvas.' : null,
      );
      setLoading(false);
    };
    void run();
    return () => {
      active = false;
    };
  }, [jobs, ready, request]);
  return { analyses, setAnalyses, loading, error };
}
