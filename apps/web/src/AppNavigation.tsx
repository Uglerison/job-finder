import { useEffect, useRef, useState, type ReactNode } from 'react';
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

const primaryRoutes: Array<{ label: string; path: AppPath }> = [
  { label: 'Buscar', path: '/busca' },
  { label: 'Vagas', path: '/vagas' },
  { label: 'Candidaturas', path: '/candidaturas' },
  { label: 'Agenda', path: '/agenda' },
  { label: 'Painel', path: '/painel' },
];

const utilityRoutes: Array<{ label: string; path: AppPath }> = [
  { label: 'Visão geral', path: '/configuracoes' },
  { label: 'Perfil profissional', path: '/perfil' },
  { label: 'Fontes e integrações', path: '/configuracoes/fontes' },
  { label: 'Preferências', path: '/configuracoes/preferencias' },
  { label: 'Histórico técnico', path: '/configuracoes/historico' },
  { label: 'Lixeira', path: '/configuracoes/lixeira' },
  { label: 'Insights', path: '/insights' },
];

type AppNavigationProps = {
  children: ReactNode;
  onNavigate: (path: AppPath) => void;
  pathname: AppPath;
  vaultAction?: ReactNode;
};

export function AppNavigation({
  children,
  onNavigate,
  pathname,
  vaultAction,
}: AppNavigationProps) {
  const navigationRef = useRef<HTMLDivElement>(null);
  const [isConfigMenuOpen, setIsConfigMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    setIsConfigMenuOpen(false);
    setIsMobileMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!isMobileMenuOpen) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!navigationRef.current?.contains(event.target as Node)) {
        setIsMobileMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMobileMenuOpen]);

  const handleNavigate = (path: AppPath) => {
    setIsConfigMenuOpen(false);
    setIsMobileMenuOpen(false);
    onNavigate(path);
  };

  return (
    <div className="paper-app">
      <header className="site-header" role="banner">
        <div className="header-inner" ref={navigationRef}>
          <InternalLink
            active={pathname === '/'}
            onNavigate={handleNavigate}
            path="/"
          >
            <span className="brand" aria-label="Job Finder, início">
              <span className="brand-mark" aria-hidden="true" />
              <span className="brand-name">Job Finder</span>
            </span>
          </InternalLink>

          <button
            aria-controls="site-navigation"
            aria-expanded={isMobileMenuOpen}
            aria-label={isMobileMenuOpen ? 'Fechar menu' : 'Abrir menu'}
            className="mobile-menu-trigger"
            onClick={() => setIsMobileMenuOpen((isOpen) => !isOpen)}
            type="button"
          >
            <span aria-hidden="true">{isMobileMenuOpen ? '×' : '☰'}</span>
          </button>

          <nav
            aria-label="Navegação principal"
            className={`primary-nav${isMobileMenuOpen ? ' is-open' : ''}`}
            id="site-navigation"
          >
            {primaryRoutes.map((route) => (
              <InternalLink
                active={pathname === route.path}
                key={route.path}
                onNavigate={handleNavigate}
                path={route.path}
              >
                {route.label}
              </InternalLink>
            ))}
          </nav>

          <div className="header-utilities">
            {vaultAction}
            <div className="config-menu">
              <button
                aria-expanded={isConfigMenuOpen}
                aria-haspopup="menu"
                className="config-menu-trigger"
                onClick={() => setIsConfigMenuOpen((isOpen) => !isOpen)}
                type="button"
              >
                Configurações
              </button>
              {isConfigMenuOpen && (
                <div
                  aria-label="Menu de configurações"
                  className="config-menu-list"
                  role="menu"
                >
                  {utilityRoutes.map((route) => (
                    <InternalLink
                      active={pathname === route.path}
                      key={route.path}
                      onNavigate={handleNavigate}
                      path={route.path}
                    >
                      {route.label}
                    </InternalLink>
                  ))}
                </div>
              )}
            </div>
            <span className="meta-label">LOCAL · PRIVADO</span>
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
