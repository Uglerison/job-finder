import { useEffect, useRef, type ReactNode } from 'react';
import { EmptyState } from '../../components/ui/primitives';
import './jobs.css';

export function JobsSplit({
  children,
  detail,
  selectedId,
}: {
  children: ReactNode;
  detail: ReactNode;
  selectedId: number | null;
}) {
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (selectedId !== null) {
      panel.current?.focus({ preventScroll: true });
      if (window.matchMedia?.('(max-width: 60rem)').matches)
        panel.current?.scrollIntoView?.({
          block: 'start',
          behavior: 'instant',
        });
    }
  }, [selectedId]);
  return (
    <div className="jobs-split">
      <section className="jobs-inbox" aria-label="Oportunidades salvas">
        {children}
      </section>
      <section
        className="jobs-review"
        aria-label="Revisão da vaga"
        tabIndex={-1}
        ref={panel}
      >
        {detail}
        {selectedId === null && (
          <EmptyState
            title="Selecione uma vaga"
            description="Abra os detalhes para ler o anúncio, conferir a análise e registrar sua candidatura."
          />
        )}
      </section>
    </div>
  );
}
