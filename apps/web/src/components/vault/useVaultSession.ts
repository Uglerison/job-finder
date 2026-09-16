import { useCallback, useEffect, useRef, useState } from 'react';

type VaultStatus = { configured: boolean; unlocked: boolean };
type LocalRequest = (url: string, init?: RequestInit) => Promise<Response>;

async function statusFrom(response: Response): Promise<VaultStatus> {
  const payload = await response.json().catch(() => null);
  if (
    !response.ok ||
    typeof payload?.configured !== 'boolean' ||
    typeof payload?.unlocked !== 'boolean'
  ) {
    throw new Error(
      typeof payload?.detail === 'string'
        ? payload.detail
        : 'Não foi possível consultar o cofre local. Tente novamente.',
    );
  }
  return payload as VaultStatus;
}

export function useVaultSession(request: LocalRequest) {
  const [status, setStatus] = useState<VaultStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef<((unlocked: boolean) => void) | null>(null);
  const checking = useRef(false);
  const revision = useRef(0);

  const refresh = useCallback(async () => {
    const current = ++revision.current;
    try {
      const next = await statusFrom(await request('/api/vault'));
      if (current === revision.current) {
        setStatus(next);
        setError(null);
      }
      return next;
    } catch (failure) {
      if (current === revision.current) {
        setStatus(null);
        setError(
          failure instanceof Error
            ? failure.message
            : 'O cofre está indisponível.',
        );
      }
      return null;
    } finally {
      if (current === revision.current) setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void refresh();
    const onFocus = () => {
      void refresh();
    };
    window.addEventListener('focus', onFocus);
    return () => {
      revision.current += 1;
      window.removeEventListener('focus', onFocus);
      pending.current?.(false);
      pending.current = null;
    };
  }, [refresh]);

  const close = () => {
    if (busy) return;
    setIsOpen(false);
    setError(null);
    pending.current?.(false);
    pending.current = null;
  };

  const open = () => {
    setIsOpen(true);
    void refresh();
  };

  const requireUnlocked = async (): Promise<boolean> => {
    if (checking.current || pending.current || busy) return false;
    checking.current = true;
    const current = await refresh();
    checking.current = false;
    if (current?.unlocked) return true;
    setIsOpen(true);
    return new Promise<boolean>((resolve) => {
      pending.current = resolve;
    });
  };

  const mutate = async (
    operation: 'create' | 'unlock' | 'lock',
    password?: string,
  ) => {
    setBusy(true);
    setError(null);
    revision.current += 1;
    try {
      const next = await statusFrom(
        await request(`/api/vault/${operation}`, {
          method: 'POST',
          ...(password !== undefined
            ? {
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vault_password: password }),
              }
            : {}),
        }),
      );
      revision.current += 1;
      setStatus(next);
      setIsOpen(false);
      pending.current?.(next.unlocked);
      pending.current = null;
    } catch (failure) {
      // A rejected unlock locks the entire backend; don't keep a stale unlocked badge.
      const current = await refresh();
      setStatus(current);
      setError(
        failure instanceof Error
          ? failure.message
          : 'Não foi possível acessar o cofre.',
      );
    } finally {
      setBusy(false);
    }
  };

  return {
    status,
    loading,
    busy,
    isOpen,
    error,
    open,
    close,
    refresh,
    requireUnlocked,
    submit: (password: string) =>
      mutate(status?.configured ? 'unlock' : 'create', password),
    lock: () => mutate('lock'),
  };
}

export type VaultSession = ReturnType<typeof useVaultSession>;
