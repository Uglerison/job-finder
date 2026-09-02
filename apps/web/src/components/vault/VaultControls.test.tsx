import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { VaultControls } from './VaultControls';
import { useVaultSession } from './useVaultSession';

function setup(configured = true, rejectUnlock = false) {
  let unlocked = false;
  const action = vi.fn();
  const request = vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.endsWith('/unlock') && rejectUnlock) {
      return new Response(JSON.stringify({ detail: 'Senha incorreta.' }), {
        status: 409,
      });
    }
    if (url.endsWith('/unlock') || url.endsWith('/create')) {
      unlocked = true;
      configured = true;
    }
    if (url.endsWith('/lock')) unlocked = false;
    return new Response(JSON.stringify({ configured, unlocked }));
  });
  function Harness() {
    const vault = useVaultSession(request);
    return (
      <>
        <VaultControls vault={vault} />
        <button
          onClick={async () => {
            if (await vault.requireUnlocked()) action();
          }}
        >
          Ação protegida
        </button>
      </>
    );
  }
  render(<Harness />);
  return { request, action };
}

describe('cofre global', () => {
  it('desbloqueia uma vez, retoma a ação pendente e permite bloquear todas as chaves', async () => {
    const { request, action } = setup();
    await screen.findByRole('button', { name: 'Cofre bloqueado' });
    fireEvent.click(screen.getByRole('button', { name: 'Ação protegida' }));
    const password = await screen.findByLabelText('Senha do cofre');
    expect(password).toHaveFocus();
    fireEvent.change(password, { target: { value: 'senha local longa' } });
    fireEvent.submit(
      screen
        .getByRole('button', { name: 'Desbloquear cofre' })
        .closest('form')!,
    );
    await waitFor(() => expect(action).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(
      screen.queryByDisplayValue('senha local longa'),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Ação protegida' }));
    await waitFor(() => expect(action).toHaveBeenCalledTimes(2));
    expect(
      request.mock.calls.filter(([url]) => url === '/api/vault/unlock'),
    ).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: 'Cofre desbloqueado' }));
    fireEvent.click(
      await screen.findByRole('button', { name: 'Bloquear cofre' }),
    );
    await screen.findByRole('button', { name: 'Cofre bloqueado' });
  });

  it('fecha com Escape, devolve o foco e cancela a ação pendente', async () => {
    const { action } = setup();
    const trigger = await screen.findByRole('button', {
      name: 'Cofre bloqueado',
    });
    trigger.focus();
    fireEvent.click(trigger);
    const dialog = await screen.findByRole('dialog');
    fireEvent.keyDown(dialog, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(action).not.toHaveBeenCalled();
  });

  it('exige confirmação na criação e não revela nem mantém a senha no erro', async () => {
    const { request } = setup(false);
    fireEvent.click(
      await screen.findByRole('button', { name: 'Configurar cofre' }),
    );
    fireEvent.change(
      await screen.findByLabelText('Crie uma senha para o cofre local'),
      { target: { value: 'senha local longa' } },
    );
    fireEvent.change(screen.getByLabelText('Confirme a senha do cofre local'), {
      target: { value: 'confirmacao diferente' },
    });
    fireEvent.submit(
      screen.getByRole('button', { name: 'Criar cofre' }).closest('form')!,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('confirmação');
    expect(request.mock.calls.some(([url]) => url.endsWith('/create'))).toBe(
      false,
    );
  });

  it('mantém a ação bloqueada quando o serviço rejeita a senha', async () => {
    const { action } = setup(true, true);
    await screen.findByRole('button', { name: 'Cofre bloqueado' });
    fireEvent.click(screen.getByRole('button', { name: 'Ação protegida' }));
    fireEvent.change(await screen.findByLabelText('Senha do cofre'), {
      target: { value: 'senha invalida longa' },
    });
    fireEvent.submit(
      screen
        .getByRole('button', { name: 'Desbloquear cofre' })
        .closest('form')!,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Senha incorreta',
    );
    expect(action).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Senha do cofre')).toHaveValue('');
  });
});
