import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';

describe('App', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockImplementation(
      (_input: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === 'PUT') {
          return Promise.resolve({
            json: async () => ({
              criteria: JSON.parse(init.body as string),
              profile_id: 1,
              version_number: 1,
            }),
            ok: true,
          });
        }

        return Promise.resolve({
          json: async () => null,
          ok: true,
        });
      },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it('apresenta a promessa principal do espaço local de vagas', () => {
    render(<App />);

    expect(
      screen.getByRole('heading', {
        name: 'Encontre oportunidades. Prepare-se para avançar.',
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('Job Finder')).toBeInTheDocument();
  });

  it('adota o shell editorial da referência visual', () => {
    render(<App />);

    expect(screen.getByRole('banner')).toHaveTextContent('Job Finder');
    expect(screen.getByText('PLATAFORMA LOCAL DE VAGAS')).toBeInTheDocument();
    expect(
      screen.getByText('Dados ficam neste computador.'),
    ).toBeInTheDocument();
    expect(document.querySelector('.paper-app')).not.toBeNull();
  });

  it('abre o onboarding e salva critérios válidos no perfil local', async () => {
    render(<App />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/profile'));
    fireEvent.click(
      screen.getByRole('button', { name: 'Configurar meu perfil' }),
    );

    expect(
      screen.getByRole('heading', { name: 'Configure seu perfil' }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Cargos desejados'), {
      target: { value: 'Backend Engineer' },
    });
    fireEvent.change(screen.getByLabelText('Competências'), {
      target: { value: 'Python, FastAPI' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Salvar perfil' }));

    await waitFor(() =>
      expect(screen.getByText('Perfil salvo localmente.')).toBeInTheDocument(),
    );

    const [, options] = fetchMock.mock.calls.at(-1) as [string, RequestInit];
    expect(options.method).toBe('PUT');
    expect(JSON.parse(options.body as string)).toMatchObject({
      skills: ['Python', 'FastAPI'],
      target_roles: ['Backend Engineer'],
      restrictions: { work_models: ['remote'] },
    });
  });
});
