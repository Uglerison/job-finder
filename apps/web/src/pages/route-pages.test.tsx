import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { JobsPage, SearchPage } from './route-pages';

describe('páginas de rota', () => {
  it('monta somente o domínio correspondente à URL ativa', () => {
    render(
      <>
        <SearchPage pathname="/vagas">
          <p>Busca ativa</p>
        </SearchPage>
        <JobsPage pathname="/vagas">
          <p>Vagas ativas</p>
        </JobsPage>
      </>,
    );

    expect(screen.queryByText('Busca ativa')).not.toBeInTheDocument();
    expect(screen.getByText('Vagas ativas')).toBeInTheDocument();
  });
});
