import type { ReactNode } from 'react';
import { AppNavigation } from './AppNavigation';
import type { AppPath } from './routes';

type AppLayoutProps = {
  children: ReactNode;
  onNavigate: (path: AppPath) => void;
  pathname: AppPath;
  vaultAction?: ReactNode;
};

export function AppLayout({
  children,
  onNavigate,
  pathname,
  vaultAction,
}: AppLayoutProps) {
  return (
    <AppNavigation
      onNavigate={onNavigate}
      pathname={pathname}
      vaultAction={vaultAction}
    >
      {children}
    </AppNavigation>
  );
}
