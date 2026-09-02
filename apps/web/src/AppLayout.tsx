import type { ReactNode } from 'react';
import { AppNavigation } from './AppNavigation';
import type { AppPath } from './routes';

type AppLayoutProps = {
  children: ReactNode;
  onNavigate: (path: AppPath) => void;
  pathname: AppPath;
};

export function AppLayout({ children, onNavigate, pathname }: AppLayoutProps) {
  return (
    <AppNavigation onNavigate={onNavigate} pathname={pathname}>
      {children}
    </AppNavigation>
  );
}
