import type { ReactNode } from 'react';
import type { AppPath } from '../routes';

type RoutePageProps = {
  children: ReactNode;
  pathname: AppPath;
};

type RouteBoundaryProps = RoutePageProps & {
  routes: readonly AppPath[];
};

function RouteBoundary({ children, pathname, routes }: RouteBoundaryProps) {
  return routes.includes(pathname) ? children : null;
}

function SingleRoutePage({
  children,
  pathname,
  route,
}: RoutePageProps & { route: AppPath }) {
  return (
    <RouteBoundary pathname={pathname} routes={[route]}>
      {children}
    </RouteBoundary>
  );
}

export function HomePage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/" />;
}

export function SearchPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/busca" />;
}

export function JobsPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/vagas" />;
}

export function ApplicationsPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/candidaturas" />;
}

export function AgendaPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/agenda" />;
}

export function InsightsPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/insights" />;
}

export function DashboardPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/painel" />;
}

export function ProfilePage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/perfil" />;
}

export function SettingsPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/configuracoes" />;
}

export function SourcesPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/configuracoes/fontes" />;
}

export function PreferencesPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/configuracoes/preferencias" />;
}

export function HistoryPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/configuracoes/historico" />;
}

export function TrashPage(props: RoutePageProps) {
  return <SingleRoutePage {...props} route="/configuracoes/lixeira" />;
}

const sourceWorkspaceRoutes: readonly AppPath[] = ['/configuracoes/historico'];

export function SourceWorkspacePage({ children, pathname }: RoutePageProps) {
  return (
    <RouteBoundary pathname={pathname} routes={sourceWorkspaceRoutes}>
      {children}
    </RouteBoundary>
  );
}
