import { useState, type ReactNode } from 'react';
import {
  Badge,
  Button,
  Card,
  Notice,
  PageHeader,
} from '../../components/ui/primitives';
import './settings.css';
export type ProviderKey = 'jsearch' | 'adzuna' | 'jooble';
export type ProviderCredentialStatus = {
  provider: ProviderKey;
  configured: boolean;
  unlocked: boolean;
  storage: 'encrypted_database' | 'environment' | 'not_configured';
};
const providers: { key: ProviderKey; name: string; description: string }[] = [
  {
    key: 'jsearch',
    name: 'JSearch',
    description: 'Busca de vagas pela integração RapidAPI.',
  },
  {
    key: 'adzuna',
    name: 'Adzuna',
    description: 'Usa o app ID e a app key da sua conta.',
  },
  {
    key: 'jooble',
    name: 'Jooble',
    description: 'Busca de vagas com a chave da sua conta Jooble.',
  },
];
type Props = {
  statuses: ProviderCredentialStatus[];
  loading: boolean;
  error: boolean;
  vaultUnlocked: boolean;
  onVault: () => void;
  editor: ReactNode;
  editing: ProviderKey | null;
  onEdit: (provider: ProviderKey | null) => void;
  onTest: (provider: ProviderKey) => Promise<string>;
  onRemove: (provider: ProviderKey) => Promise<string>;
  ai: ReactNode;
  aiState: string;
  publicSources: ReactNode;
};
export function SourcesWorkspace({
  statuses,
  loading,
  error,
  vaultUnlocked,
  onVault,
  editor,
  editing,
  onEdit,
  onTest,
  onRemove,
  ai,
  aiState,
  publicSources,
}: Props) {
  const [pending, setPending] = useState<{
    key: ProviderKey;
    operation: 'test' | 'remove';
  } | null>(null);
  const [busy, setBusy] = useState<ProviderKey | null>(null);
  const [messages, setMessages] = useState<
    Record<string, { text: string; error: boolean }>
  >({});
  const execute = async (key: ProviderKey, operation: 'test' | 'remove') => {
    setBusy(key);
    setPending(null);
    setMessages((current) => ({
      ...current,
      [key]: { text: '', error: false },
    }));
    try {
      const text = await (operation === 'test' ? onTest(key) : onRemove(key));
      setMessages((current) => ({ ...current, [key]: { text, error: false } }));
    } catch (failure) {
      setMessages((current) => ({
        ...current,
        [key]: {
          text:
            failure instanceof Error
              ? failure.message
              : 'A ação não foi concluída.',
          error: true,
        },
      }));
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="workspace-page settings-page sources-settings">
      <PageHeader
        eyebrow="CONFIGURAÇÕES"
        title="Fontes e integrações"
        description="Gerencie as conexões usadas para buscar e analisar vagas."
      />
      <div className="settings-vault-row">
        <p>
          O cofre global libera todas as chaves locais de uma vez. A senha é
          solicitada somente no diálogo.
        </p>
        <Button variant="secondary" onClick={onVault}>
          Gerenciar cofre
        </Button>
      </div>
      <section aria-label="Integrações de busca" className="provider-cards">
        <h2>Integrações de busca</h2>
        {providers.map((provider) => {
          const status = statuses.find(
            (item) => item.provider === provider.key,
          );
          const configured = Boolean(status?.configured);
          const environment = status?.storage === 'environment';
          const locked = configured && !environment && !vaultUnlocked;
          const state = loading
            ? 'Verificando…'
            : error
              ? 'Estado indisponível'
              : !configured
                ? 'Não configurado'
                : locked
                  ? 'Cofre bloqueado'
                  : 'Disponível';
          return (
            <Card
              aria-label={provider.name}
              className="provider-card"
              key={provider.key}
            >
              <div className="provider-card-top">
                <div>
                  <h3>{provider.name}</h3>
                  <p>{provider.description}</p>
                </div>
                <Badge
                  tone={
                    state === 'Disponível'
                      ? 'success'
                      : locked || error
                        ? 'warning'
                        : 'neutral'
                  }
                >
                  {state}
                </Badge>
              </div>
              <div className="provider-card-actions">
                {environment ? (
                  <span>Configurada pelo ambiente</span>
                ) : (
                  <Button
                    variant="secondary"
                    disabled={loading || error || busy !== null}
                    onClick={() => {
                      setPending(null);
                      onEdit(editing === provider.key ? null : provider.key);
                    }}
                  >
                    {configured
                      ? 'Atualizar credencial'
                      : 'Cadastrar credencial'}
                  </Button>
                )}
                {locked && (
                  <Button variant="secondary" onClick={onVault}>
                    Desbloquear cofre
                  </Button>
                )}
                {configured && (
                  <Button
                    variant="ghost"
                    disabled={loading || error || busy !== null}
                    onClick={() =>
                      setPending({ key: provider.key, operation: 'test' })
                    }
                  >
                    {busy === provider.key ? 'Aguarde…' : 'Testar conexão'}
                  </Button>
                )}
                {configured && !environment && (
                  <Button
                    variant="ghost"
                    disabled={loading || error || busy !== null}
                    onClick={() =>
                      setPending({ key: provider.key, operation: 'remove' })
                    }
                  >
                    Remover credencial
                  </Button>
                )}
              </div>
              {editing === provider.key && !environment && (
                <div className="provider-editor">
                  {editor}
                  <Button
                    variant="ghost"
                    disabled={busy !== null}
                    onClick={() => onEdit(null)}
                  >
                    Fechar edição
                  </Button>
                </div>
              )}
              {pending?.key === provider.key && (
                <div className="provider-confirm">
                  <p>
                    {pending.operation === 'test'
                      ? 'O teste faz uma consulta à fonte e pode consumir sua cota. Nenhuma vaga será salva.'
                      : 'A chave local desta integração será removida. Vagas e candidaturas serão mantidas.'}
                  </p>
                  <Button
                    variant={
                      pending.operation === 'remove' ? 'danger' : 'secondary'
                    }
                    onClick={() =>
                      void execute(provider.key, pending.operation)
                    }
                  >
                    {pending.operation === 'test'
                      ? 'Confirmar teste de '
                      : 'Confirmar remoção de '}
                    {provider.name}
                  </Button>
                  <Button variant="ghost" onClick={() => setPending(null)}>
                    Cancelar
                  </Button>
                </div>
              )}
              {messages[provider.key]?.text && (
                <Notice
                  tone={messages[provider.key].error ? 'error' : 'success'}
                >
                  {messages[provider.key].text}
                </Notice>
              )}
            </Card>
          );
        })}
      </section>
      <Card className="openai-settings" aria-label="OpenAI">
        <div className="provider-card-top">
          <h2>OpenAI · análise de vagas</h2>
          <Badge>{aiState}</Badge>
        </div>
        <p>A análise por IA é opcional e exige confirmação em cada execução.</p>
        <details>
          <summary>Configurar OpenAI</summary>
          {ai}
        </details>
      </Card>
      <section className="public-source-settings" aria-label="Fontes públicas">
        <h2>Fontes públicas</h2>
        <p>
          Estas fontes não exigem API key. Ative apenas as que deseja consultar.
        </p>
        {publicSources}
      </section>
    </div>
  );
}
