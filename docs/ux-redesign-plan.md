# Plano de redesenho de UX — Job Finder

## Objetivo

Fazer o Job Finder parecer um produto único, simples e previsível, seguindo a linguagem editorial do Se Prepara AI e priorizando a jornada:

**Desbloquear → Buscar → Avaliar → Aplicar → Acompanhar**

O redesenho não adicionará autenticação em nuvem. A senha existente continuará sendo apenas a senha do cofre local, usada para descriptografar as credenciais nesta execução do aplicativo.

## Diagnóstico atual

1. O cabeçalho combina marca, duas linhas de navegação, menu de configurações, estado local e ação de perfil. A hierarquia não deixa evidente qual é a próxima ação.
2. O acesso ao cofre está enterrado em `/configuracoes/fontes`, embora seja necessário antes de buscar em providers privados ou usar a análise da OpenAI.
3. A página de fontes mistura desbloqueio, cadastro de API keys, estado dos providers, fontes públicas e configuração da OpenAI em blocos distantes da mesma página.
4. A interface usa a paleta correta, mas mantém componentes e regras de CSS de fases diferentes. Há estilos duplicados e variações concorrentes de botão, formulário, card e cabeçalho.
5. `App.tsx` concentra estado, carregamento, handlers e renderização de todas as páginas. Essa estrutura dificulta manter consistência visual e testar cada jornada isoladamente.
6. Feedbacks importantes aparecem dentro das páginas e podem ficar longe da ação que os causou. Estados bloqueado, carregando, vazio, sucesso e erro não usam um padrão único.
7. No celular, a navegação depende de quebra e rolagem horizontal. Isso não oferece a mesma previsibilidade do menu compacto usado como referência.

## Princípios do redesenho

- Uma ação primária por contexto; ações destrutivas ou técnicas ficam em segundo plano.
- O usuário deve alcançar o cofre em um clique a partir de qualquer rota.
- O cofre deve ser chamado de **Cofre local**, não de login, para não sugerir conta ou autenticação remota.
- O estado `Bloqueado` ou `Desbloqueado` deve estar sempre visível no cabeçalho.
- A navegação principal representa tarefas; configurações e manutenção ficam em um menu utilitário.
- Papel `#f8f8f4`, tinta `#042440`, acento ocre `#a87413`, títulos editoriais, fios finos, baixa elevação e raios pequenos permanecem como base.
- Cards, campos, botões, badges, avisos, diálogos e estados vazios terão componentes únicos e reutilizáveis.
- Cada rota terá um cabeçalho de página, conteúdo principal e ações previsíveis; páginas não repetirão explicações extensas.
- Toda alteração de comportamento seguirá TDD e toda alteração visual terá validação objetiva em desktop e mobile.

## Arquitetura de informação proposta

### Cabeçalho global

- A marca leva ao início e elimina a necessidade de um link adicional “Início”.
- Navegação principal no desktop: **Buscar**, **Vagas**, **Candidaturas**, **Agenda** e **Painel**.
- **Insights** fica acessível pelo menu utilitário e por ações contextuais de análise nas vagas.
- À direita ficam:
  - botão persistente `Cofre bloqueado` ou `Cofre desbloqueado`;
  - menu de configurações/manutenção;
  - menu compacto no mobile.
- Em telas menores, os destinos entram em um menu hambúrguer; não haverá rolagem horizontal no cabeçalho.

### Cofre global

O botão do cabeçalho abre um diálogo acessível em qualquer rota.

**Cofre já configurado e bloqueado**

- campo de senha;
- mostrar/ocultar senha;
- envio por Enter;
- ação primária `Desbloquear cofre`;
- erro junto ao campo, sem apagar a senha por falha de rede;
- explicação curta de que a senha não sai do computador nem é persistida.

**Primeiro uso**

- criação e confirmação da senha;
- critérios visíveis antes do envio;
- depois da criação, direcionamento explícito para cadastrar uma integração.

**Cofre desbloqueado**

- confirmação do estado;
- resumo das credenciais disponíveis;
- ação secundária `Bloquear agora`.

Quando uma busca ou análise exigir credenciais bloqueadas, a ação abre o mesmo diálogo e, após o desbloqueio, permite retomar o fluxo. A senha não será repetida em cada formulário de provider.

### Páginas

| Rota | Foco após o redesenho |
|---|---|
| `/` | Próxima ação, estado do cofre, métricas essenciais e atividade recente |
| `/busca` | Formulário de busca, estado das fontes e resultado da execução atual |
| `/vagas` | Caixa de entrada, filtros, aderência/análise visível e ações de triagem |
| `/candidaturas` | Pipeline legível, mudança de fase e próximos passos |
| `/agenda` | Buscas automáticas e compromissos, separados por contexto |
| `/painel` | Métricas detalhadas e evolução do funil |
| `/insights` | Visão consolidada das análises, acessível também a partir das vagas |
| `/configuracoes/fontes` | Cards de providers, cadastro/remoção/teste de credenciais e fontes públicas |
| demais configurações | Preferências e manutenção, sem competir com a jornada principal |

## Componentes compartilhados previstos

- `AppShell` e `AppHeader`;
- `MobileNavigation` e `UtilityMenu`;
- `VaultTrigger`, `VaultDialog` e `VaultStatus`;
- `PageHeader` e `SectionHeader`;
- `Button`, `IconButton`, `Card`, `Badge`, `Field` e `SelectField`;
- `Notice`, `ToastRegion`, `EmptyState`, `LoadingState` e `ErrorState`;
- `ProviderCard`, `JobCard`, `ApplicationCard` e `MetricCard`.

Os componentes devem nascer a partir dos tokens já registrados, sem copiar assets proprietários do Se Prepara AI.

## Estratégia técnica

1. Extrair tokens e componentes-base antes de redesenhar páginas.
2. Decompor `App.tsx` em páginas e providers de estado, mantendo a persistência no backend/SQLite.
3. Substituir as condicionais de todas as páginas por uma camada de roteamento com componentes de rota independentes e layout compartilhado.
4. Implementar primeiro o novo shell e o cofre global, pois eles resolvem o maior bloqueio de navegação.
5. Migrar as páginas por jornada, preservando os endpoints existentes.
6. Remover CSS legado somente depois que cada página migrada tiver teste e validação visual.

## Validação e TDD

### Testes comportamentais obrigatórios

- o botão do cofre existe e é alcançável em todas as rotas;
- o estado bloqueado/desbloqueado muda após resposta confirmada do backend;
- uma senha desbloqueia OpenAI e todos os providers cadastrados;
- `Enter`, `Escape`, foco inicial e retorno de foco funcionam no diálogo;
- formulários de provider não pedem novamente a senha do cofre;
- uma ação que exige credencial bloqueada orienta o usuário e abre o diálogo correto;
- navegar entre rotas não perde filtros, vagas, candidaturas ou configurações persistidas;
- menu mobile abre, fecha, informa `aria-expanded` e não causa rolagem horizontal.

### Matriz visual mínima

| Largura | Cenários |
|---|---|
| 375 px | cabeçalho, menu, cofre, busca, vaga e pipeline |
| 768 px | navegação intermediária, formulários e listas |
| 1280 px | todas as rotas principais e configurações |

Em cada viewport serão verificados hierarquia, espaçamento, foco, contraste, ausência de overflow, estados vazios, carregamento, erro e conteúdo longo.

## Critérios de saída

- Cofre acessível em um clique em qualquer rota.
- Nenhuma senha duplicada nos formulários individuais de provider.
- Cabeçalho sem quebra ou rolagem horizontal nos viewports definidos.
- Rotas independentes e layout compartilhado preservados.
- Fluxo principal compreensível sem depender de texto técnico.
- Componentes visuais únicos, sem regras legadas concorrentes nas páginas migradas.
- Testes, lint, tipos, formatação e build com `pnpm` aprovados.
- README e executável atualizados somente depois da validação final.

## Fora de escopo

- conta de usuário, login remoto ou sincronização em nuvem;
- candidatura automática;
- simulação de entrevista dentro do Job Finder;
- alteração da criptografia ou persistência do cofre sem necessidade técnica descoberta durante a implementação;
- novas fontes de vagas durante o redesenho.
