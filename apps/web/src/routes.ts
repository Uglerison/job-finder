export type AppPath =
  | '/'
  | '/busca'
  | '/vagas'
  | '/candidaturas'
  | '/agenda'
  | '/insights'
  | '/painel'
  | '/perfil'
  | '/configuracoes'
  | '/configuracoes/fontes'
  | '/configuracoes/preferencias'
  | '/configuracoes/historico'
  | '/configuracoes/lixeira';

const supportedPaths: AppPath[] = [
  '/',
  '/busca',
  '/vagas',
  '/candidaturas',
  '/agenda',
  '/insights',
  '/painel',
  '/perfil',
  '/configuracoes',
  '/configuracoes/fontes',
  '/configuracoes/preferencias',
  '/configuracoes/historico',
  '/configuracoes/lixeira',
];

export function normalizePath(pathname: string): AppPath {
  const path = pathname.replace(/\/+$/, '') || '/';
  return supportedPaths.includes(path as AppPath) ? (path as AppPath) : '/';
}
