import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  LoadingState,
  Notice,
  PageHeader,
} from './primitives';

describe('componentes-base da interface', () => {
  it('expõe estado de carregamento e bloqueia clique duplicado no botão', () => {
    render(
      <Button loading loadingLabel="Salvando alterações">
        Salvar
      </Button>,
    );

    const button = screen.getByRole('button', {
      name: 'Salvando alterações',
    });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
  });

  it('associa rótulo, ajuda e erro ao campo', () => {
    render(
      <Field
        error="Informe uma senha válida."
        hint="Use pelo menos 12 caracteres."
        htmlFor="vault-password-test"
        label="Senha do cofre"
      >
        <input id="vault-password-test" type="password" />
      </Field>,
    );

    const input = screen.getByLabelText('Senha do cofre');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby');
    expect(
      screen.getByText('Use pelo menos 12 caracteres.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Informe uma senha válida.',
    );
  });

  it('mantém cabeçalho, superfície e badge com semântica previsível', () => {
    render(
      <>
        <PageHeader
          actions={<Button variant="secondary">Nova busca</Button>}
          description="Revise oportunidades antes de aplicar."
          eyebrow="VAGAS"
          title="Oportunidades encontradas"
        />
        <Card aria-label="Resumo da vaga">
          <Badge tone="success">Compatível</Badge>
        </Card>
      </>,
    );

    expect(
      screen.getByRole('heading', { name: 'Oportunidades encontradas' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Nova busca' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Resumo da vaga')).toHaveClass('ui-card');
    expect(screen.getByText('Compatível')).toHaveClass('ui-badge--success');
  });

  it('diferencia avisos informativos de erros', () => {
    const { rerender } = render(
      <Notice title="Cofre bloqueado">Desbloqueie para continuar.</Notice>,
    );

    expect(screen.getByRole('status')).toHaveTextContent(
      'Desbloqueie para continuar.',
    );

    rerender(
      <Notice title="Falha na busca" tone="error">
        Tente novamente.
      </Notice>,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Tente novamente.');
  });

  it('oferece estados vazio e carregando com nomes acessíveis', () => {
    render(
      <>
        <EmptyState
          action={<Button>Buscar vagas</Button>}
          description="Execute uma busca para preencher esta área."
          title="Nenhuma vaga encontrada"
        />
        <LoadingState label="Carregando candidaturas" />
      </>,
    );

    expect(
      screen.getByRole('heading', { name: 'Nenhuma vaga encontrada' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Buscar vagas' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAccessibleName(
      'Carregando candidaturas',
    );
  });
});
