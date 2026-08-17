import { useEffect, useState, type ReactNode } from 'react';
import type { AppPath } from './routes';

type InternalLinkProps = {
  active?: boolean;
  children: ReactNode;
  onNavigate: (path: AppPath) => void;
  path: AppPath;
};

function InternalLink({
  active = false,
  children,
  onNavigate,
  path,
}: InternalLinkProps) {
  return (
    <a
      aria-current={active ? 'page' : undefined}
      className={active ? 'is-active' : undefined}
      href={path}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(path);
      }}
    >
      {children}
    </a>
  );
}

type AppNavigationProps = {
  children: ReactNode;
  onNavigate: (path: AppPath) => void;
  onOpenProfile: () => void;
  pathname: AppPath;
};

export function AppNavigation({
  children,
  onNavigate,
  onOpenProfile,
  pathname,
}: AppNavigationProps) {
  const configPath = pathname.startsWith('/configuracoes');
  const [isConfigMenuOpen, setIsConfigMenuOpen] = useState(configPath);

  useEffect(() => {
    setIsConfigMenuOpen(configPath);
  }, [configPath]);

  return (
    <div className="paper-app">
      <header className="site-header" role="banner">
        <div className="header-inner">
          <InternalLink
            active={pathname === '/'}
            onNavigate={onNavigate}
            path="/"
          >
            <span className="brand" aria-label="Job Finder, início">
              <span className="brand-mark" aria-hidden="true" />
              <span className="brand-name">Job Finder</span>
            </span>
          </InternalLink>

          <nav aria-label="Navegação principal" className="primary-nav">
            <div className="nav-row">
              <span className="nav-group-label">Principal</span>
              <InternalLink
                active={pathname === '/'}
                onNavigate={onNavigate}
                path="/"
              >
                Início
              </InternalLink>
              <InternalLink
                active={pathname === '/busca'}
                onNavigate={onNavigate}
                path="/busca"
              >
                Buscar vagas
              </InternalLink>
              <InternalLink
                active={pathname === '/vagas'}
                onNavigate={onNavigate}
                path="/vagas"
              >
                Minhas vagas
              </InternalLink>
              <InternalLink
                active={pathname === '/candidaturas'}
                onNavigate={onNavigate}
                path="/candidaturas"
              >
                Candidaturas
              </InternalLink>
            </div>
            <div className="nav-row">
              <span className="nav-group-label">Acompanhar</span>
              <InternalLink
                active={pathname === '/agenda'}
                onNavigate={onNavigate}
                path="/agenda"
              >
                Agenda
              </InternalLink>
              <InternalLink
                active={pathname === '/insights'}
                onNavigate={onNavigate}
                path="/insights"
              >
                Insights
              </InternalLink>
              <InternalLink
                active={pathname === '/painel'}
                onNavigate={onNavigate}
                path="/painel"
              >
                Painel
              </InternalLink>
            </div>
          </nav>

          <details
            className="config-menu"
            onToggle={(event) => setIsConfigMenuOpen(event.currentTarget.open)}
            open={isConfigMenuOpen}
          >
            <summary aria-label="Abrir configurações">Configurações</summary>
            <div className="config-menu-list">
              <InternalLink
                active={pathname === '/configuracoes'}
                onNavigate={onNavigate}
                path="/configuracoes"
              >
                Visão geral
              </InternalLink>
              <InternalLink
                active={pathname === '/perfil'}
                onNavigate={onNavigate}
                path="/perfil"
              >
                Perfil
              </InternalLink>
              <InternalLink
                active={pathname === '/configuracoes/fontes'}
                onNavigate={onNavigate}
                path="/configuracoes/fontes"
              >
                Fontes e integrações
              </InternalLink>
              <InternalLink
                active={pathname === '/configuracoes/preferencias'}
                onNavigate={onNavigate}
                path="/configuracoes/preferencias"
              >
                Preferências
              </InternalLink>
              <InternalLink
                active={pathname === '/configuracoes/historico'}
                onNavigate={onNavigate}
                path="/configuracoes/historico"
              >
                Histórico técnico
              </InternalLink>
              <InternalLink
                active={pathname === '/configuracoes/lixeira'}
                onNavigate={onNavigate}
                path="/configuracoes/lixeira"
              >
                Lixeira
              </InternalLink>
            </div>
          </details>

          <div className="header-meta">
            <span className="meta-label">LOCAL · PRIVADO</span>
            <button
              className="header-action"
              onClick={onOpenProfile}
              type="button"
            >
              Abrir perfil
            </button>
          </div>
        </div>
      </header>

      <main className="route-page">{children}</main>

      <footer className="site-footer">
        <span>JOB FINDER · LOCAL</span>
        <span>v0.1 · DADOS LOCAIS</span>
      </footer>
    </div>
  );
}
