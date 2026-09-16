import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '../ui/primitives';
import type { VaultSession } from './useVaultSession';
import './vault.css';

function VaultDialog({ vault }: { vault: VaultSession }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const passwordInput = useRef<HTMLInputElement>(null);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [validation, setValidation] = useState<string | null>(null);
  const configured = vault.status?.configured ?? true;
  const unlocked = vault.status?.unlocked ?? false;

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const node = dialog.current;
    if (node?.showModal) node.showModal();
    else node?.setAttribute('open', '');
    (
      passwordInput.current ?? node?.querySelector<HTMLElement>('button')
    )?.focus();
    return () => {
      if (node?.close) node.close();
      if (previous?.isConnected) previous.focus();
    };
  }, []);

  const error = validation ?? vault.error;
  return createPortal(
    <dialog
      aria-labelledby="vault-title"
      aria-describedby="vault-description"
      aria-modal="true"
      className="vault-dialog"
      ref={dialog}
      onCancel={(event) => {
        event.preventDefault();
        vault.close();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) vault.close();
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          vault.close();
        }
        if (event.key === 'Tab') {
          const focusable = dialog.current?.querySelectorAll<HTMLElement>(
            'button:not(:disabled), input:not(:disabled), a[href]',
          );
          if (!focusable?.length) return;
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }
      }}
    >
      <div className="vault-dialog-body">
        <p className="eyebrow">SEGURANÇA LOCAL</p>
        <h2 id="vault-title">
          {unlocked
            ? 'Seu cofre está aberto.'
            : configured
              ? 'Desbloqueie seu cofre.'
              : 'Uma senha para suas integrações.'}
        </h2>
        <p id="vault-description">
          {unlocked
            ? 'OpenAI e providers cadastrados estão disponíveis nesta execução. Bloquear remove da memória as credenciais e a senha da sessão.'
            : 'Esta não é uma conta ou login. A senha libera as chaves OpenAI e dos providers neste computador, até você bloquear ou fechar o serviço local.'}
        </p>
        {!vault.status ? (
          <Button loading={vault.loading} onClick={() => void vault.refresh()}>
            Tentar novamente
          </Button>
        ) : unlocked ? (
          <Button
            loading={vault.busy}
            loadingLabel="Bloqueando…"
            onClick={() => void vault.lock()}
          >
            Bloquear cofre
          </Button>
        ) : (
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (password.length < 12) {
                setValidation(
                  'Use pelo menos 12 caracteres na senha do cofre.',
                );
                return;
              }
              if (!configured && password !== confirmation) {
                setValidation('A confirmação da senha do cofre não confere.');
                return;
              }
              setValidation(null);
              await vault.submit(password);
              setPassword('');
              setConfirmation('');
              passwordInput.current?.focus();
            }}
          >
            <label htmlFor="vault-password">
              {configured
                ? 'Senha do cofre'
                : 'Crie uma senha para o cofre local'}
            </label>
            <input
              id="vault-password"
              ref={passwordInput}
              type="password"
              required
              minLength={12}
              autoComplete={configured ? 'current-password' : 'new-password'}
              disabled={vault.busy}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? 'vault-error' : 'vault-password-help'}
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setValidation(null);
              }}
            />
            <small id="vault-password-help">
              Pelo menos 12 caracteres. A senha não é gravada em disco nem no
              navegador.
            </small>
            {!configured && (
              <>
                <label htmlFor="vault-confirmation">
                  Confirme a senha do cofre local
                </label>
                <input
                  id="vault-confirmation"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  disabled={vault.busy}
                  value={confirmation}
                  onChange={(event) => {
                    setConfirmation(event.target.value);
                    setValidation(null);
                  }}
                />
              </>
            )}
            <Button
              type="submit"
              loading={vault.busy}
              loadingLabel="Abrindo cofre…"
            >
              {configured ? 'Desbloquear cofre' : 'Criar cofre'}
            </Button>
          </form>
        )}
        {error && (
          <p className="vault-error" id="vault-error" role="alert">
            {error}
          </p>
        )}
        <Button variant="ghost" disabled={vault.busy} onClick={vault.close}>
          Fechar
        </Button>
        <p className="vault-dialog-note">
          As vagas, o perfil e as candidaturas continuam acessíveis com o cofre
          bloqueado. Chaves configuradas por variável de ambiente não são
          controladas pelo cofre.
        </p>
      </div>
    </dialog>,
    document.body,
  );
}

export function VaultControls({ vault }: { vault: VaultSession }) {
  const label = vault.loading
    ? 'Verificando cofre…'
    : !vault.status
      ? 'Cofre indisponível'
      : !vault.status.configured
        ? 'Configurar cofre'
        : vault.status.unlocked
          ? 'Cofre desbloqueado'
          : 'Cofre bloqueado';
  return (
    <>
      <Button
        className="vault-trigger"
        variant="secondary"
        size="small"
        aria-haspopup="dialog"
        disabled={vault.loading}
        onClick={vault.open}
      >
        {label}
      </Button>
      {vault.isOpen && <VaultDialog vault={vault} />}
    </>
  );
}
