# Job Finder — controle de tarefas

> Versão: 1.1 — 16/08/2026
> Fonte de escopo: [PLANEJAMENTO.md](./PLANEJAMENTO.md)

Este arquivo é a fonte de verdade para acompanhar a implementação do MVP. O escopo detalhado continua no planejamento; aqui ficam a ordem, as dependências, os critérios de aceite e o progresso.

## Como atualizar

- `[ ]` pendente;
- `[ ] 🔄` em andamento — deve existir no máximo uma tarefa principal nesse estado;
- `[ ] ⛔` bloqueada — registrar o motivo no diário de progresso;
- `[x]` concluída — somente quando o aceite e os testes estiverem verdes;
- tarefas opcionais usam o marcador `OPCIONAL` e não bloqueiam o MVP;
- cada commit de implementação deve citar o ID, por exemplo: `feat(JF-210): cria pipeline de candidaturas`;
- a atualização do checkbox deve acompanhar o commit que conclui a tarefa;
- dependências não concluídas impedem o início da tarefa, salvo registro explícito da exceção.

## Regra obrigatória de TDD

Toda tarefa que altera comportamento seguirá **Red → Green → Refactor**:

1. criar um teste que falha pelo motivo esperado;
2. implementar o mínimo para fazê-lo passar;
3. refatorar mantendo toda a suíte verde;
4. registrar no aceite quais testes comprovam o comportamento;
5. para correções, começar por um teste de regressão que reproduza o defeito.

Tarefas puramente documentais, configuração mecânica e protótipos descartáveis podem não ter teste automatizado, mas precisam de validação objetiva. Código de protótipo só entra no produto depois de refeito com TDD.

## Diretriz visual registrada

A interface seguirá a linguagem editorial do [Prepara AI](https://sepreparai.com.br/):

- fundo papel claro (`#f8f8f4`), superfícies brancas e azul-tinta profundo (`#042440`);
- tipografia serifada de destaque para mensagens principais, sans-serif para leitura e monoespaçada para rótulos operacionais;
- navegação compacta, largura de leitura controlada, divisórias finas e cartões planos;
- acento dourado discreto para estados de atenção, sem gradientes ou sombras pesadas;
- responsividade, foco visível e conteúdo funcional mesmo sem baixar fontes ou imagens externas.

O objetivo é reproduzir a hierarquia, o ritmo e o contraste da referência sem copiar ativos proprietários. A validação visual deve permanecer offline-friendly.

## Definition of Ready

Uma tarefa está pronta para começar quando:

- objetivo e aceite estão compreensíveis;
- dependências estão concluídas;
- dados ou fixtures necessários estão disponíveis;
- riscos externos, permissões e limites estão conhecidos;
- o primeiro teste a ser escrito foi identificado.

## Definition of Done

Uma tarefa só pode ser marcada como concluída quando:

- aceite funcional atendido;
- testes novos escritos com TDD e suíte relevante verde;
- lint, análise de tipos e formatação aprovados;
- nenhuma chave, dado pessoal ou artefato temporário foi versionado;
- documentação afetada atualizada;
- alteração revisável em commit com o ID da tarefa;
- regressões conhecidas registradas como tarefa, nunca ocultadas.

## Visão de progresso

| Épico | Faixa | Estado | Marco de saída |
|---|---|---|---|
| E0 — Governança e decisões | JF-001–JF-009 | Em andamento | Escopo operacional fechado |
| E1 — Fundação local | JF-010–JF-022 | Concluído | Aplicação local abre e persiste dados |
| E2 — Perfil | JF-100–JF-107 | Concluído | Perfil editável e versionado |
| E3 — Vagas e candidaturas | JF-200–JF-221 | Em andamento | Marcação de aplicada disponível diretamente na vaga |
| E4 — Busca e fontes | JF-300–JF-313 | Concluído | Vagas coletadas, auditadas e deduplicadas |
| E4.1 — Busca agregada e foco Brasil | JF-320–JF-350 | Em andamento | Busca manual e agendada persistida para consulta posterior |
| E5 — GPT-5.6 Luna | JF-400–JF-412 | Concluída | Análise explicável e controlada |
| E6 — Dashboard e agenda | JF-500–JF-508 | Em andamento | Métricas operacionais consistentes |
| E7 — Segurança e empacotamento | JF-600–JF-613 | Pendente | Release candidata Windows |
| E8 — Beta e lançamento | JF-700–JF-707 | Pendente | MVP `v0.1.0` validado |

**Próxima etapa:** `JF-217 — Criar comando atômico para marcar uma vaga como aplicada`.

## Marcos

### M1 — Fundação executável

Concluído quando JF-010 a JF-022 estiverem verdes.

### M2 — Fluxo manual utilizável

Concluído quando E2 e E3 permitirem cadastrar perfil, importar vaga, triar, aplicar e registrar entrevistas.

### M3 — Primeira fatia vertical inteligente

Concluído quando for possível cadastrar perfil, importar uma vaga por URL, analisar com `gpt-5.6-luna`, mover até `APLICADA` e refletir a mudança no dashboard.

### M4 — Busca automática

Concluído quando três fontes aprovadas executarem com agendamento, limites, auditoria e deduplicação.

### M4.1 — Busca agregada para o Brasil

Concluído quando uma única pesquisa consultar providers de forma seletiva, normalizar, deduplicar e
ranquear vagas brasileiras sem expor APIs técnicas ao usuário. Pesquisas agendadas devem persistir
as vagas no SQLite local e permitir consultar depois o que cada execução encontrou.

### M5 — Release candidata

Concluído quando o pacote Windows passar em máquina limpa, com backup, restauração, segurança e documentação aprovados.

## E0 — Governança e decisões

- [x] **JF-001 — Registrar o planejamento inicial**
  - Aceite: escopo, arquitetura, etapas, riscos e critérios do MVP documentados.
  - Evidência: commit `eb4ab11`.

- [x] **JF-002 — Tornar TDD obrigatório no planejamento**
  - Aceite: ciclo Red–Green–Refactor e regras de regressão/CI documentados.
  - Evidência: commit `3c2a839`.

- [x] **JF-003 — Criar o quadro de tarefas rastreável**
  - Depende de: JF-001 e JF-002.
  - Aceite: IDs, dependências, marcos, Definition of Ready/Done e diário disponíveis neste arquivo.

- [ ] **JF-004 — Consolidar o perfil profissional de referência**
  - Aceite: cargos, senioridade, competências, idiomas, localização, regimes e restrições registrados sem dados pessoais desnecessários.

- [ ] **JF-005 — Selecionar as três fontes iniciais permitidas**
  - Depende de: JF-004.
  - Aceite: fonte, método de acesso, limites, termos e formato de dados registrados para cada conector.

- [ ] **JF-006 — Definir orçamento e frequência de busca**
  - Aceite: teto diário/mensal, alertas, frequência e janela de execução definidos.

- [ ] **JF-007 — Validar licença e política de contribuição**
  - Aceite: licença atual confirmada e regras mínimas de contribuição documentadas.

- [ ] **JF-008 — Registrar decisões de arquitetura (ADRs)**
  - Depende de: JF-005 e JF-006.
  - Aceite: ADRs para stack, banco local, empacotamento, IA, fontes e armazenamento de segredos.

- [ ] **JF-009 — Montar conjunto de avaliação**
  - Depende de: JF-004.
  - Aceite: 30–50 vagas rotuladas e anonimizadas, com aderência esperada e casos-limite.

## E1 — Fundação local

- [x] **JF-010 — Criar a estrutura do monorepo**
  - Aceite: diretórios `apps/api`, `apps/web`, `tests`, `scripts` e `docs/adr` criados, sem artefatos gerados.
  - Evidência: estrutura inicial versionada; artefatos locais ignorados por `.gitignore`.

- [x] **JF-011 — Configurar o projeto Python do backend**
  - Depende de: JF-010.
  - Aceite: `pyproject.toml`, ambiente reproduzível, pacote importável e comando de testes funcional.
  - Evidência: Python 3.10, instalação editável e Pytest validados.

- [x] **JF-012 — Configurar React, TypeScript e Vite**
  - Depende de: JF-010.
  - Aceite: frontend inicia em desenvolvimento, compila assets estáticos e executa teste mínimo.
  - Evidência: React/TypeScript/Vite com pnpm, Vitest, lint e build validados.

- [x] **JF-013 — Configurar qualidade de código**
  - Depende de: JF-011 e JF-012.
  - Aceite: formatter, lint e análise de tipos reproduzíveis para backend e frontend.
  - Evidência: Ruff, Mypy, Prettier, Oxlint e TypeScript verificados e documentados; frontend usa pnpm.

- [x] **JF-014 — Configurar CI inicial**
  - Depende de: JF-013.
  - Aceite: workflow executa testes, lint, tipos e build sem segredos.
  - Evidência: workflow Windows separa backend e frontend, com instalação pnpm congelada e verificações locais equivalentes validadas.

- [x] **JF-015 — Implementar endpoint de saúde com TDD**
  - Depende de: JF-011.
  - Teste primeiro: resposta `200` com versão e estado esperado.
  - Aceite: `GET /api/health` validado por teste de API.
  - Evidência: Red por ausência de `job_finder.main`; Green em `tests/api/test_health.py`.

- [x] **JF-016 — Implementar configuração tipada**
  - Depende de: JF-011.
  - Teste primeiro: defaults, overrides válidos e rejeição de configuração inválida.
  - Aceite: configuração sem segredos expostos e separada por ambiente.
  - Evidência: `Settings` valida ambiente, logs, diretório local e segredo mascarado.

- [x] **JF-017 — Configurar SQLite, ORM e migrações**
  - Depende de: JF-011 e JF-016.
  - Teste primeiro: criação isolada do banco e aplicação idempotente da migração inicial.
  - Aceite: sessão transacional, WAL e Alembic funcionais.
  - Evidência: SQLite em WAL, chaves estrangeiras e revisão Alembic `0001_initial_schema` validados.

- [x] **JF-018 — Implementar o ciclo de vida do servidor local**
  - Depende de: JF-015 e JF-016.
  - Teste primeiro: início, detecção de porta, prontidão e encerramento controlado.
  - Aceite: servidor escuta apenas em `127.0.0.1` e encerra sem corromper estado.
  - Evidência: teste de loopback valida porta livre, migração no startup, health e shutdown.

- [x] **JF-019 — Servir o frontend compilado pelo backend**
  - Depende de: JF-012 e JF-018.
  - Teste primeiro: rota raiz e fallback de SPA retornam assets corretos.
  - Aceite: uma única URL local entrega API e interface.
  - Evidência: testes de API e loopback validam raiz, fallback SPA, assets e `/api/health`.

- [x] **JF-020 — Abrir o navegador e impedir instância duplicada**
  - Depende de: JF-018 e JF-019.
  - Teste primeiro: trava de instância, reuso da URL e liberação após encerramento.
  - Aceite: executar duas vezes não cria dois servidores.
  - Evidência: trava exclusiva armazena URL loopback, reusa a instância e é liberada no shutdown.

- [x] **JF-021 — Implementar logs locais seguros**
  - Depende de: JF-016.
  - Teste primeiro: rotação, níveis e redação de padrões sensíveis.
  - Aceite: logs em `%LOCALAPPDATA%\JobFinder` sem chaves ou dados pessoais.
  - Evidência: handler rotativo local redige segredos, e-mail e telefone; lifecycle registra início e fim.

- [x] **JF-022 — Criar smoke test da fundação Windows**
  - Depende de: JF-017 a JF-021.
  - Aceite: script inicia, verifica saúde/interface/persistência e encerra a aplicação.
  - Evidência: `scripts/smoke_test.py` passou contra o build real e o teste confirma a porta liberada no shutdown.

## E2 — Perfil

- [x] **JF-100 — Modelar perfil e versões**
  - Depende de: JF-017.
  - Teste primeiro: criação, nova versão, consulta da versão ativa e imutabilidade histórica.
  - Aceite: schema e migração preservam histórico.
  - Evidência: migração `0002_profile_versions` e testes cobrem criação, versão ativa e bloqueio de atualização histórica.

- [x] **JF-101 — Implementar validação dos critérios do perfil**
  - Depende de: JF-100.
  - Teste primeiro: cargos, pesos, salário, idiomas e restrições válidos/inválidos.
  - Aceite: erros de domínio claros e pesos consistentes.
  - Evidência: schemas Pydantic rejeitam critérios inválidos e exigem pesos totalizando 100%.

- [x] **JF-102 — Implementar API do perfil**
  - Depende de: JF-100 e JF-101.
  - Teste primeiro: `GET` vazio, `PUT` válido, atualização versionada e payload inválido.
  - Aceite: contratos tipados para leitura e atualização.
  - Evidência: rotas `/api/profile` retornam estado vazio, criam versões imutáveis e rejeitam critérios inválidos.

- [x] **JF-103 — Criar onboarding do perfil e aplicar a identidade visual**
  - Depende de: JF-012 e JF-102.
  - Teste primeiro: fluxo obrigatório, validações e salvamento bem-sucedido.
  - Diretriz visual: usar a composição editorial registrada acima na tela inicial e no onboarding.
  - Aceite: perfil completo configurável sem editar arquivos; interface responsiva, acessível e coerente com a referência visual.
  - Evidência: commit `266a44d`; Vitest cobre carregamento, abertura, preenchimento e `PUT /api/profile`; lint, Prettier, TypeScript/build e suíte backend verdes.

- [x] **JF-104 — Implementar edição e visualização de versões**
  - Depende de: JF-103.
  - Teste primeiro: carregar versão atual e exibir histórico sem mutá-lo.
  - Aceite: usuário entende quando e por que a análise ficou desatualizada.
  - Evidência: commit `34fa427`; endpoint `/api/profile/versions`, histórico visual com versão ativa e testes de imutabilidade aprovados.

- [x] **JF-105 — Implementar redação de dados pessoais**
  - Depende de: JF-101.
  - Teste primeiro: e-mail, telefone, endereço e identificadores em fixtures.
  - Aceite: prévia mostra exatamente o texto que poderá ser enviado à IA.
  - Evidência: commit `1708bec`; redação determinística, endpoint `/api/privacy/redact`, prévia na UI e contagem por categoria testados.

- [x] **JF-106 — Implementar filtros obrigatórios determinísticos**
  - Depende de: JF-101.
  - Teste primeiro: país, regime, contrato, salário e palavras bloqueadas.
  - Aceite: cada exclusão inclui motivo rastreável.
  - Evidência: commit `1708bec`; critérios suportam país/contrato e endpoint `/api/filters/evaluate` retorna todas as razões em ordem estável.

- [x] **JF-107 — Implementar preferências gerais**
  - Depende de: JF-017.
  - Teste primeiro: locale, moeda, fuso, retenção e defaults.
  - Aceite: preferências persistem e são aplicadas na API/UI.
  - Evidência: commit `1708bec`; migração `0003_preferences`, API `/api/preferences`, defaults locais e painel de preferências testados.

## E3 — Vagas e candidaturas

- [x] **JF-200 — Modelar vaga e suas origens**
  - Depende de: JF-017.
  - Teste primeiro: vaga normalizada com múltiplas origens e conteúdo versionado.
  - Aceite: schema e migração suportam URL canônica, conteúdo bruto e validade.
  - Evidência: migração `0004_jobs`, modelos `Job`/`JobOrigin`/`JobContentVersion`, histórico imutável e 3 testes unitários novos.

- [x] **JF-201 — Implementar normalização determinística**
  - Depende de: JF-200.
  - Teste primeiro: URLs, cargos, empresas, locais, datas e espaços inconsistentes.
  - Aceite: mesma entrada produz sempre a mesma representação.
  - Evidência: normalizador remove rastreadores, ordena query, normaliza textos/datas e migração `0005_job_dates`.

- [x] **JF-202 — Implementar inclusão manual de vaga**
  - Depende de: JF-200 e JF-201.
  - Teste primeiro: formulário válido, URL inválida e campos obrigatórios ausentes.
  - Aceite: vaga manual aparece como `ENCONTRADA` com origem auditável.
  - Evidência: `POST /api/jobs` normaliza, persiste origem `manual`, conteúdo inicial e status `found` (`ENCONTRADA`); 4 testes de API verdes.

- [x] **JF-203 — Implementar importação de vaga por URL**
  - Depende de: JF-202 e JF-602.
  - Teste primeiro: URL pública permitida, redirecionamento limitado e destino bloqueado.
  - Aceite: conteúdo sanitizado e falhas explicadas sem travar a aplicação.
  - Evidência: importador HTTP com bloqueio de rede local, limite de 3 redirecionamentos, conteúdo seguro em texto e testes com cliente injetado; JF-602 permanece como endurecimento completo posterior.

- [x] **JF-204 — Implementar API de listagem e detalhe**
  - Depende de: JF-200.
  - Teste primeiro: paginação, filtros, ordenação, ausência e detalhe.
  - Aceite: contratos estáveis e consultas sem N+1 relevante.
  - Evidência: `GET /api/jobs` com paginação, busca, status e ordenação; `GET /api/jobs/{id}` com detalhe e 404 explícito; 2 testes de API verdes.

- [x] **JF-205 — Criar caixa de entrada de vagas**
  - Depende de: JF-012 e JF-204.
  - Teste primeiro: estados vazio/erro/carregamento e ações rápidas.
  - Aceite: vagas novas podem ser revisadas e filtradas.
  - Evidência: caixa de entrada editorial com busca local, estados de carregamento/erro/vazio, inclusão manual rápida e 7 testes Vitest; pnpm lint, format e build verdes.

- [x] **JF-206 — Criar tela de detalhe da vaga**
  - Depende de: JF-204 e JF-205.
  - Teste primeiro: descrição segura, origem, metadados e histórico.
  - Aceite: nenhum HTML externo executável é renderizado.
  - Evidência: detalhe sob demanda com origem, conteúdo versionado e renderização em texto puro; 8 testes Vitest verdes.

- [x] **JF-207 — Implementar notas e tags**
  - Depende de: JF-200.
  - Teste primeiro: criar, editar, filtrar e remover vínculo sem perder a vaga.
  - Aceite: notas e tags disponíveis na API e interface.
  - Evidência: migração `0007_job_metadata`, notas editáveis, tags idempotentes e removíveis, detalhe inclui metadados; 8 testes de API focados verdes.

- [x] **JF-208 — Modelar candidatura e eventos de fase**
  - Depende de: JF-017 e JF-200.
  - Teste primeiro: candidatura única por vaga, estado atual e eventos imutáveis.
  - Aceite: migração preserva histórico completo.
  - Evidência: migração `0008_applications`, unicidade por vaga, evento inicial e bloqueio de alteração/remoção do histórico; teste unitário verde.

- [x] **JF-209 — Implementar máquina de estados do pipeline**
  - Depende de: JF-208.
  - Teste primeiro: todas as transições permitidas, proibidas e correções auditáveis.
  - Aceite: backend rejeita transição inválida independentemente da UI.
  - Evidência: mapa explícito de transições, terminais e correções marcadas como evento `correction`; testes unitários verdes.

- [x] **JF-210 — Implementar API de candidaturas e fases**
  - Depende de: JF-209.
  - Teste primeiro: criar candidatura, avançar, corrigir e consultar histórico.
  - Aceite: operações transacionais com erros de domínio claros.
  - Evidência: `POST/GET /api/jobs/{id}/application`, `GET /api/applications/{id}` e transição transacional com `409` para conflito; testes de API verdes.

- [x] **JF-211 — Criar quadro visual do pipeline**
  - Depende de: JF-210.
  - Teste primeiro: mover por ação acessível, erro de transição e atualização otimista revertida.
  - Aceite: pipeline utilizável com mouse e teclado.
  - Evidência: quadro editorial responsivo, carregamento por vaga, select e ação acessíveis, rollback otimista em `409`; 10 testes Vitest, lint, Prettier, TypeScript e build verdes.

- [x] **JF-212 — Modelar entrevistas, desafios e prazos**
  - Depende de: JF-208 e JF-107.
  - Teste primeiro: fuso, conflito, prazo vencido e vínculo ao processo.
  - Aceite: eventos persistem com data, participantes, link e notas.
  - Evidência: migração `0009_process_events`, modelo de entrevistas/desafios/prazos com timezone, detecção de sobreposição e helper de vencimento; API de criação/listagem; 61 testes backend verdes.

- [x] **JF-213 — Implementar agenda de processo seletivo**
  - Depende de: JF-212.
  - Teste primeiro: próximos eventos, vencidos e filtros por período.
  - Aceite: agenda disponível na API e interface.
  - Evidência: `GET /api/events` filtra por período/status com validação de timezone; agenda editorial separa próximos e vencidos; 11 testes Vitest, 62 testes backend, lint, tipos e builds verdes.

- [x] **JF-214 — Implementar motivos de encerramento**
  - Depende de: JF-209.
  - Teste primeiro: reprovação, desistência, expiração e motivo opcional/obrigatório.
  - Aceite: dados alimentam relatórios sem apagar histórico.
  - Evidência: migração `0010_closure_reasons`, motivos obrigatórios para `rejected/withdrawn/expired`, fechamento persistido e motivo copiado para o evento imutável; 64 testes backend verdes.

- [x] **JF-215 — Implementar exportação CSV/JSON**
  - Depende de: JF-204 e JF-210.
  - Teste primeiro: codificação, campos, filtros e neutralização de fórmulas em CSV.
  - Aceite: exportação abre corretamente e não contém a chave da API.
  - Evidência: endpoints `jobs/applications.(csv|json)`, filtro de status, UTF-8 com BOM e neutralização de células iniciadas por `=+-@`; teste de exportação verde sem segredos.

- [x] **JF-216 — Implementar lixeira recuperável**
  - Depende de: JF-200 e JF-208.
  - Teste primeiro: arquivar, restaurar e expirar após retenção.
  - Aceite: exclusão definitiva exige confirmação e respeita vínculos.
  - Evidência: migração `0011_recoverable_trash`, soft-delete com retenção das preferências, restauração, purge de expirados e `confirm=true` para remoção definitiva; candidaturas vinculadas bloqueiam a remoção; lixeira visual com restauração e confirmação no navegador; 68 testes backend e 12 testes Vitest verdes.

- [ ] **JF-217 — Criar comando atômico para marcar uma vaga como aplicada**
  - Depende de: JF-209 e JF-210.
  - Teste primeiro: vaga sem candidatura, candidatura em `found`/`pending`, já `applied`, estado
    posterior ou terminal, vaga inexistente e duas requisições concorrentes.
  - Aceite: uma única operação cria a candidatura quando necessário e registra a transição para
    `applied` na mesma transação; repetição é idempotente e nenhuma falha deixa estado parcial.
  - Contrato proposto: `POST /api/jobs/{job_id}/application/applied`, retornando a candidatura e o
    histórico auditável; regressões de fase retornam `409` com motivo seguro.

- [ ] **JF-218 — Adicionar “Marcar como aplicada” na caixa e no detalhe da vaga**
  - Depende de: JF-217.
  - Teste primeiro: botão disponível, confirmação explícita, sucesso, conflito, falha de rede,
    clique duplo e vaga já aplicada.
  - Aceite: a ação fica próxima de “Abrir vaga”, não é disparada apenas por abrir o link externo,
    desabilita durante o envio e troca para o selo `APLICADA` depois da confirmação do backend.
  - Aceite de UX: mensagem identifica cargo e empresa; erro preserva o estado anterior e permite
    tentar novamente sem duplicar eventos.

- [ ] **JF-219 — Vincular resultados da busca agregada às vagas persistidas**
  - Depende de: JF-337, JF-344 e JF-217.
  - Teste primeiro: vaga criada, duplicata exata, resultado em cache e sugestão de duplicata
    aproximada.
  - Aceite: cada resultado elegível retorna seu `job_id` local sem expor detalhes técnicos; o cartão
    da busca reutiliza a ação “Marcar como aplicada”. Resultado aproximado ainda não resolvido
    informa que precisa de revisão, sem criar candidatura no registro errado.
  - Aceite de consistência: busca nova ou em cache resolve o mesmo `job_id` e atualiza a caixa de
    vagas sem exigir recarregar o navegador.

- [ ] **JF-220 — Sincronizar pipeline, métricas e histórico após a aplicação**
  - Depende de: JF-218 e JF-219.
  - Teste primeiro: ação concluída atualiza cartão, pipeline, contador de candidaturas, série do
    dashboard e histórico; recarregar a página mantém os mesmos dados.
  - Aceite: a vaga aparece em `APLICADA` imediatamente após a resposta confirmada; pipeline e
    dashboard são reconsultados sem duplicar requisições ou fazer atualização otimista irreversível.
  - Aceite de auditoria: o histórico mostra evento inicial e transição para `applied`, com horário
    local consistente e sem permitir alteração do evento anterior.

- [ ] **JF-221 — Validar o fluxo de aplicação ponta a ponta**
  - Depende de: JF-217 a JF-220.
  - Teste primeiro: vaga encontrada pela JSearch → abrir anúncio → confirmação humana → marcar como
    aplicada → visualizar no pipeline e dashboard → reiniciar o aplicativo.
  - Aceite: fluxo completo funciona com mouse e teclado, estados de carregamento/vazio/erro são
    claros, nenhuma candidatura é enviada automaticamente e nenhuma chave aparece na UI ou nos logs.
  - Evidência exigida: testes unitários/API/Vitest, Ruff, Mypy, Oxlint, TypeScript, Prettier e build
    pnpm verdes; passos manuais e limitações atualizados no README.

## E4 — Busca e fontes

- [x] **JF-300 — Definir contrato de adaptadores**
  - Depende de: JF-005 e JF-200.
  - Teste primeiro: adaptador bem-sucedido, parcial, vazio, cancelado e com erro.
  - Aceite: interface tipada não acopla domínio a uma fonte específica.
  - Evidência: `SourceAdapter`, `SourceSearchRequest`, `SourceSearchResult` e token de cancelamento em `source_adapters.py`; fixtures cobrem sucesso, parcial/vazio, cancelado e erro.

- [x] **JF-301 — Modelar configuração de fonte**
  - Depende de: JF-017 e JF-300.
  - Teste primeiro: ativação, frequência, limites e configuração inválida.
  - Aceite: segredos não são persistidos em texto simples.
  - Evidência: migração `0012_search_sources`, `SourceConfigRecord` e `SourceConfigData`; três fontes públicas sem credenciais são semeadas com agendamento desligado e a API nunca retorna `secret_ref`.

- [x] **JF-302 — Implementar API e UI de fontes**
  - Depende de: JF-301.
  - Teste primeiro: criar, testar conexão, pausar e editar uma fonte.
  - Aceite: configuração e último estado visíveis ao usuário.
  - Evidência: `/api/sources`, `PUT /api/sources/{source_key}`, teste de conexão e seção editorial “Fontes e execuções” com ativação/pausa, limites e último erro.

- [x] **JF-303 — Modelar e executar `search_run`**
  - Depende de: JF-300 e JF-301.
  - Teste primeiro: ciclo pendente/em execução/concluído/falhou/cancelado.
  - Aceite: contadores, duração e erros ficam auditáveis.
  - Evidência: migração `0012_search_sources`, `execute_search_run`, estados pendente/em execução/concluído/parcial/falhou/cancelado e painel de execuções; API E4 cobre contadores e deduplicação.

- [x] **JF-304 — Implementar cancelamento cooperativo**
  - Depende de: JF-303.
  - Teste primeiro: cancelar antes, durante e após conclusão.
  - Aceite: nenhuma tarefa fica órfã nem grava resultado após cancelamento.
  - Evidência: `CancellationToken`, `SearchTaskRegistry`, `POST /api/search-runs/{id}/cancel` e teste que confirma zero candidato persistido após cancelamento.

- [x] **JF-305 — Implementar agendador persistente**
  - Depende de: JF-301 e JF-303.
  - Teste primeiro: próxima execução, reinício, janela e tarefa perdida.
  - Aceite: automático desativado por padrão e fuso respeitado.
  - Evidência: `PersistentScheduler`, `next_run_at`, recuperação de execuções interrompidas e `/api/scheduler/tick`; defaults desligam o automático e calculam janelas em UTC local.

- [x] **JF-306 — Implementar cliente HTTP seguro e resiliente**
  - Depende de: JF-016 e JF-602.
  - Teste primeiro: timeout, limite, redirecionamento, retry e domínio bloqueado.
  - Aceite: políticas comuns aplicadas a todos os conectores.
  - Evidência: `SafeHttpClient` valida esquema/destino público, limita bytes e redirects, aplica timeout e retries; fixture MockTransport cobre respostas inválidas.

- [x] **JF-307 — Implementar limite e backoff por fonte**
  - Depende de: JF-303 e JF-306.
  - Teste primeiro: `429`, erro transitório, teto e pausa automática.
  - Aceite: repetição limitada com jitter e diagnóstico visível.
  - Evidência: tratamento de `429`, `Retry-After`, jitter limitado, teto diário/por execução, `backoff_until` e erro persistido; teste confirma pausa após rate limit.

- [x] **JF-308 — Implementar conector da fonte 1**
  - Depende de: JF-005, JF-300 e JF-306.
  - Teste primeiro: fixtures de sucesso, paginação, alteração e erro.
  - Aceite: vagas entram normalizadas com origem e evidência.
  - Evidência: `RemoteOkAdapter` com fixture de JSON, origem `remoteok`, conteúdo sanitizado e normalização determinística.

- [x] **JF-309 — Implementar conector da fonte 2**
  - Depende de: JF-308.
  - Teste primeiro: fixtures específicas e contrato comum.
  - Aceite: mesmos indicadores operacionais da fonte 1.
  - Evidência: `ArbeitnowAdapter` usa o contrato comum e fixture de payload `{data: [...]}`; contadores do run são compartilhados.

- [x] **JF-310 — Implementar conector da fonte 3**
  - Depende de: JF-309.
  - Teste primeiro: fixtures específicas e contrato comum.
  - Aceite: mesmos indicadores operacionais das fontes anteriores.
  - Evidência: `JobicyAdapter` usa o contrato comum e fixture de payload `{jobs: [...]}`; falhas e limites seguem a mesma política.

- [x] **JF-311 — Implementar deduplicação exata**
  - Depende de: JF-201 e JF-303.
  - Teste primeiro: URL canônica, ID externo, hash e múltiplas origens.
  - Aceite: duplicata exata não cria uma segunda vaga.
  - Evidência: URL canônica, `(source, external_id)` e hash de conteúdo em `source_dedup.py`; origens múltiplas são preservadas e teste do segundo run mantém uma única vaga.

- [x] **JF-312 — Implementar sugestão de duplicata aproximada**
  - Depende de: JF-311.
  - Teste primeiro: cargo/empresa/local semelhantes e falsos positivos conhecidos.
  - Aceite: união aproximada exige confirmação do usuário.
  - Evidência: similaridade explicável de cargo/empresa/local em `duplicate_suggestions`; endpoints `/api/duplicates/{id}/confirm|dismiss` e teste de confirmação que anexa a origem sem duplicar a vaga.

- [x] **JF-313 — Criar painel de execuções e erros**
  - Depende de: JF-302 a JF-307.
  - Teste primeiro: progresso, cancelamento, falha parcial e reexecução.
  - Aceite: resultado de cada fonte pode ser diagnosticado sem abrir logs.
  - Evidência: `/api/search-runs`, cancelamento e seção visual com status, duração, vagas encontradas, novas, duplicatas, aproximações e erro por fonte.

## E4.1 — Busca agregada e foco Brasil

### Limite de produto

- O Job Finder **não implementará simulação de entrevista**. Essa funcionalidade pertence ao produto
  separado [Se Prepara AI](https://sepreparai.com.br/).
- A integração será somente um link externo acessível, sem iframe, autenticação compartilhada,
  criação de sessão, envio da descrição da vaga ou parâmetros pessoais na URL.
- “Entrevista” no pipeline e na agenda continua significando apenas uma fase real do processo
  seletivo acompanhado pelo Job Finder.

- [x] **JF-320 — Auditar a busca atual e registrar a estratégia de migração**
  - Depende de: JF-300 a JF-313.
  - Validação: inventário revisado de componentes, endpoints, serviços, contratos, persistência,
    cache, tratamento de erros, observabilidade e testes atuais.
  - Aceite: ADR documenta o que será reutilizado, substituído ou descontinuado sem remover código
    funcional prematuramente.
  - Evidência: `docs/adr/0010-busca-agregada.md` registra o inventário, a ordem de migração e os
    limites de produto.

- [x] **JF-321 — Definir contratos normalizados da busca agregada**
  - Depende de: JF-320.
  - Teste primeiro: consulta válida/inválida, paginação, limite, modalidades e resultado com campos
    opcionais ausentes.
  - Aceite: contratos Python tipados representam palavra-chave, localização, modalidade, país,
    paginação e vaga normalizada sem acoplar API ou frontend a um provider.
  - Evidência: `JobSearchParams`, `AggregatedSearchResult` e `SourceCandidate` estendido; testes
    cobrem limites, campos opcionais e payloads divergentes.

- [x] **JF-322 — Criar registro e configuração de providers**
  - Depende de: JF-321 e JF-301.
  - Teste primeiro: provider habilitado, prioridade, limite, timeout e configuração inválida.
  - Aceite: JSearch é o principal; Adzuna e Jooble são complementares; providers antigos podem ser
    fallback; nenhuma configuração técnica precisa aparecer na experiência principal.
  - Evidência: `SearchAggregator` recebe providers ordenados e a UI substitui o seletor técnico por
    uma busca única.

- [x] **JF-323 — Reutilizar o cofre criptografado para credenciais dos providers**
  - Depende de: JF-322 e JF-601.
  - Teste primeiro: salvar, desbloquear, substituir e remover cada credencial sem retornar plaintext.
  - Aceite: chaves ficam cifradas no SQLite e somente em memória durante o uso; o frontend recebe
    apenas estado configurado/não configurado; `.env.example` contém somente placeholders opcionais
    para desenvolvimento.
  - Evidência: migração `0017_provider_secrets`, endpoints de salvar/desbloquear, teste de ausência
    de plaintext e placeholders em `.env.example`.

- [x] **JF-324 — Implementar base resiliente dos providers**
  - Depende de: JF-306, JF-307 e JF-321.
  - Teste primeiro: sucesso, vazio, timeout, `429`, erro transitório, payload inválido e cancelamento.
  - Aceite: contrato comum aplica timeout, limite, backoff, cancelamento e erros seguros sem vazar
    resposta externa, URL com segredo ou credencial.
  - Evidência: `SafeHttpClient` reutilizado para GET/POST com headers transitórios, retry, 429,
    limite de resposta e cancelamento; testes existentes e novos cobrem credenciais ausentes.

- [x] **JF-325 — Implementar JSearch como provider principal**
  - Depende de: JF-323 e JF-324.
  - Teste primeiro: fixtures de vagas brasileiras, paginação, remoto/presencial, ausência de campos,
    autenticação inválida e rate limit.
  - Aceite: consultas usam Brasil e português quando suportado e retornam somente o contrato interno
    normalizado.
  - Evidência: adapter parametriza `country=br`, `language=pt-BR`, paginação e headers RapidAPI;
    fixture brasileira validada.

- [x] **JF-326 — Implementar Adzuna como provider complementar**
  - Depende de: JF-323 e JF-324.
  - Teste primeiro: fixtures brasileiras, localização, paginação, salário, vazio e erro do provider.
  - Aceite: adapter independente respeita país `br`, limites configurados e o contrato comum.
  - Evidência: endpoint country-scoped, campos de salário e localização normalizados em fixture.

- [x] **JF-327 — Implementar Jooble como provider complementar**
  - Depende de: JF-323 e JF-324.
  - Teste primeiro: fixtures brasileiras, modalidade inferida, paginação, vazio, timeout e payload
    parcial.
  - Aceite: adapter independente preserva origem pública e não expõe o nome técnico da API na UI.
  - Evidência: adapter POST com modalidade inferida, origem pública e fixture Jooble; UI exibe origem
    secundária sem nome técnico.

- [x] **JF-328 — Adaptar fontes atuais como fallback legado**
  - Depende de: JF-320 e JF-324.
  - Teste primeiro: Remote OK, Arbeitnow e Jobicy sob o novo contrato, inclusive vazio e erro.
  - Aceite: adapters funcionais são reutilizados sem chamadas obrigatórias e podem ser desligados
    individualmente sem alterar o agregador.
  - Evidência: `LegacySourceProvider` encapsula o contrato existente e a orquestração só o alcança
    após os providers prioritários.

- [x] **JF-329 — Normalizar resultados entre providers**
  - Depende de: JF-321 e JF-325 a JF-328.
  - Teste primeiro: cargo, empresa, cidade/estado/país, modalidade, salário, datas, descrição e origem
    com formatos divergentes.
  - Aceite: mesma informação produz representação interna determinística e preserva dados brutos
    necessários para auditoria.
  - Evidência: parsers JSearch/Adzuna/Jooble usam o mesmo `SourceCandidate`, sanitizam HTML e
    preservam `raw_payload`.

- [x] **JF-330 — Deduplicar resultados agregados**
  - Depende de: JF-311, JF-312 e JF-329.
  - Teste primeiro: URL igual, cargo/empresa/local equivalentes, pontuação e falsos positivos
    conhecidos.
  - Aceite: duplicatas exatas são unidas automaticamente com múltiplas origens; aproximações usam
    regra explicável e conservadora sem NLP ou LLM.
  - Evidência: deduplicação por URL e similaridade cargo/empresa/local une labels e fontes; teste
    unitário cobre duas origens.

- [x] **JF-331 — Implementar ranking determinístico com foco Brasil**
  - Depende de: JF-321, JF-329 e JF-330.
  - Teste primeiro: correspondência do cargo, cidade/estado, modalidade, recência, completude e
    empate estável.
  - Aceite: score ordena resultados de forma explicável e deixa ponto de extensão para o perfil,
    sem embeddings ou chamada de IA nesta etapa.
  - Evidência: `rank_candidates` combina cargo, localização, modalidade, recência e completude sem
    embeddings/LLM.

- [x] **JF-332 — Orquestrar providers com fallback seletivo**
  - Depende de: JF-325 a JF-331.
  - Teste primeiro: principal suficiente, principal vazio, poucos resultados, erro, timeout, limite
    de custo e complementação parcial.
  - Aceite: começa pelo JSearch e só consulta providers adicionais quando necessário; a busca retorna
    resultados parciais úteis quando ao menos um provider funciona.
  - Evidência: agregador sequencial para ao atingir o mínimo, registra skipped/failed e teste cobre
    erro do principal, fallback e cache.

- [x] **JF-333 — Implementar cache local de consultas repetidas**
  - Depende de: JF-332.
  - Teste primeiro: chave canônica, hit, expiração, modalidade/local diferentes e invalidação por
    versão da estratégia.
  - Aceite: cache SQLite ou em memória com TTL evita chamadas externas repetidas; não introduz Redis
    nem armazena credenciais ou dados pessoais.
  - Evidência: `SearchCache` tem TTL, chave canônica e `cache_hit`; teste confirma segunda consulta
    sem nova chamada ao provider.

- [x] **JF-334 — Criar endpoint único de busca agregada**
  - Depende de: JF-321, JF-332 e JF-333.
  - Teste primeiro: busca válida, parâmetros inválidos, limites abusivos, vazio, parcial, paginação e
    indisponibilidade total.
  - Aceite: uma API interna recebe cargo, localização, modalidade e limite, devolvendo resultados
    normalizados sem detalhes técnicos ou erros integrais dos providers.
  - Evidência: `POST /api/search` valida `JobSearchParams`, persiste candidatos normalizados e
    responde com vagas e diagnósticos seguros; teste API usa provider simulado.

- [x] **JF-335 — Auditar execução, fallback e desempenho dos providers**
  - Depende de: JF-303, JF-332 e JF-334.
  - Teste primeiro: provider, latência, status, quantidade, cache hit, fallback e erro redigido.
  - Aceite: cada busca permite diagnosticar a estratégia usada sem registrar chaves, conteúdo
    desnecessário ou dados pessoais.
  - Evidência: resposta `provider_runs` informa provider, status, duração, contagem, fallback e erro
    seguro; cache hit é explicitado. A interface mostra o resumo acionável e o painel “detalhes da
    busca e do log”, distinguindo sem resultados, provider não configurado, limite, falha e parcial.

- [x] **JF-336 — Criar formulário único de busca no frontend**
  - Depende de: JF-334.
  - Teste primeiro: cargo, localização, modalidades, carregamento, validação, erro parcial e vazio.
  - Aceite: experiência principal apresenta somente palavra-chave, localização, modalidade e ação
    “Buscar vagas”, usando pnpm e os componentes visuais existentes.
  - Evidência: seção `#busca` usa formulário único e 18 testes Vitest cobrem envio, validação e
    estado de resultados.

- [x] **JF-337 — Criar cartões completos dos resultados agregados**
  - Depende de: JF-334 e JF-336.
  - Teste primeiro: campos completos/ausentes, origem pública, salário, data, modalidade, URL externa
    e acessibilidade.
  - Aceite: cartão mostra cargo, empresa, localização, modalidade, data, resumo, salário e origem
    pública discreta como “Via LinkedIn”, sem nomes técnicos como “JSearch API”.
  - Evidência: cartões responsivos mostram campos opcionais e origem pública secundária; fixture de
    UI cobre vaga completa.

- [x] **JF-338 — Adicionar link externo para treinar entrevista no Se Prepara AI**
  - Depende de: JF-337.
  - Teste primeiro: link presente, destino exato, rótulo acessível e atributos seguros de nova aba.
  - Aceite: botão “Treinar entrevista no Se Prepara AI” abre `https://sepreparai.com.br/` com
    `target="_blank"` e `rel="noreferrer"`; nenhum simulador, endpoint ou envio de dados é criado no
    Job Finder.
  - Evidência: CTA externo exato no cartão e teste Vitest confirma destino seguro.

- [x] **JF-339 — Remover seleção técnica de fonte da experiência principal**
  - Depende de: JF-336 e JF-337.
  - Teste primeiro: usuário busca sem escolher provider e configurações operacionais permanecem
    acessíveis somente no painel técnico apropriado.
  - Aceite: seletor Remote OK/Arbeitnow/Jobicy deixa o fluxo principal; histórico, execuções e
    configurações antigas continuam compatíveis durante a migração.
  - Evidência: `source-select` e botão de seleção removidos do fluxo; lista técnica e histórico
    continuam disponíveis para compatibilidade.

- [x] **JF-340 — Validar a migração agregada de ponta a ponta**
  - Depende de: JF-323 a JF-339.
  - Teste primeiro: cenário Brasil, fallback, cache, deduplicação, ranking, persistência e interface
    integrados com providers simulados.
  - Aceite: suíte completa, Ruff, Mypy, Vitest, lint, formatação e build passam; README e
    `.env.example` documentam credenciais, limites, comportamento parcial e o link externo.
  - Evidência: 50 testes de API/integração e 92 unitários passam no Windows; Ruff, Mypy, Vitest,
    Oxlint, TypeScript, Prettier e build frontend passam.

- [x] **JF-341 — Investigar e diagnosticar erros HTTP da JSearch**
  - Depende de: JF-325, JF-332 e JF-335.
  - Teste primeiro: endpoint base, `/search-v2` (rota atual; `/search` aposentada), query em português, headers RapidAPI, respostas 200,
    401/403/404, fallback e sanitização do diagnóstico.
  - Aceite: nenhuma composição de path duplica `/search-v2`; falhas preservam fallback e registram
    provider, método, URL sem credenciais, status, duração e corpo limitado/sanitizado somente no log.
  - Evidência: `JSearchProvider` canoniza o endpoint atual `/search-v2` (e migra `/search` aposentada) e envia `query`, `page`, `num_pages`, `country=br`,
    `language=pt` e `date_posted=all`; `SourceHttpError` protege headers, paths sensíveis e corpos;
    contagem visual exclui providers `skipped`; a interface permite desbloquear uma credencial já
    cifrada sem recadastrá-la. O teste real depende do desbloqueio da credencial JSearch já cifrada
    no banco local.

- [x] **JF-342 — Recuperar busca quando a instância local não responde**
  - Depende de: JF-018, JF-021 e JF-341.
  - Teste primeiro: lock com PID ativo e URL sem resposta, falha inesperada ao persistir uma vaga e
    falha de conexão no navegador.
  - Aceite: o iniciador valida `/api/health` antes de reutilizar o lock, recupera a instância
    inacessível, o endpoint registra a exceção sem incluir credenciais e a interface orienta o
    reinício em vez de mostrar uma mensagem genérica.
  - Evidência: testes de launcher, API e Vitest cobrem regressão; logs seguros recebem
    `aggregated_search request=failed` e `POST /api/search` devolve JSON 500 com detalhe seguro.

- [x] **JF-343 — Normalizar resposta aninhada da JSearch**
  - Depende de: JF-341.
  - Teste primeiro: `data` como lista, `data.jobs` como lista e `data` como objeto sem coleção de
    vagas.
  - Aceite: a variante com lista aninhada é normalizada; um formato não reconhecido falha somente a
    JSearch, permitindo os fallbacks, sem devolver erro interno ao navegador.
  - Evidência: `ProviderResponseFormatError` é tratado pelo agregador; testes cobrem lista aninhada
    e objeto inválido, eliminando o `TypeError: unhashable type: 'slice'` observado localmente.

- [x] **JF-344 — Limitar identificadores externos longos antes de persistir**
  - Depende de: JF-311 e JF-343.
  - Teste primeiro: ID externo acima de 255 caracteres em duas URLs distintas da mesma fonte.
  - Aceite: o ID persistido cabe no contrato, usa hash determinístico quando necessário e mantém a
    deduplicação exata em buscas futuras.
  - Evidência: `source_dedup` normaliza o ID opaco longo para `sha256:<digest>` antes da consulta,
    criação e atualização da origem; o teste reproduz a resposta real da JSearch e persiste sem
    `ValidationError`.

- [ ] **JF-345 — Modelar pesquisas agendadas da busca unificada**
  - Depende de: JF-321, JF-330 e JF-305.
  - Teste primeiro: criar, editar, pausar, reativar e excluir uma agenda; frequência, próxima
    execução, consulta, localização e modalidade inválidas.
  - Aceite: uma agenda persistida no SQLite contém nome, filtros normalizados, frequência,
    `enabled`, `next_run_at`, `last_run_at` e versão do perfil usada; não armazena credenciais.
  - Aceite de produto: agendamento é desligado por padrão, deixa claro que só executa enquanto o
    Job Finder estiver aberto e apagar a agenda não apaga as vagas já coletadas.

- [ ] **JF-346 — Executar automaticamente pesquisas agendadas enquanto o app estiver aberto**
  - Depende de: JF-345, JF-326, JF-327, JF-328 e JF-329.
  - Teste primeiro: tick periódico, reinício com agenda vencida, duas agendas simultâneas, lock de
    instância única, limite diário, rate limit, cancelamento e encerramento do aplicativo.
  - Aceite: um worker local inicia no ciclo de vida do backend, executa cada agenda vencida no
    máximo uma vez por janela e calcula a próxima execução de forma persistente.
  - Aceite de credenciais: chave cifrada bloqueada gera diagnóstico `credencial bloqueada` sem
    persistir senha; providers públicos/fallbacks continuam quando possível e o resultado pode ser
    parcial.

- [ ] **JF-347 — Persistir vagas e vínculo com cada execução agendada**
  - Depende de: JF-311, JF-312, JF-344 e JF-346.
  - Teste primeiro: vaga nova, duplicata exata, possível duplicata, resultado parcial, falha no meio
    da persistência e repetição da mesma agenda.
  - Aceite: toda vaga válida encontrada pelo agendador entra nas tabelas locais de vagas, origens e
    conteúdo; uma relação auditável associa execução, agenda, `job_id`, provider e resultado de
    deduplicação (`created`, `exact` ou `approximate`).
  - Aceite transacional: falha de uma vaga não perde as vagas válidas já confirmadas nem deixa run
    marcado como sucesso incorretamente; nenhuma execução cria candidatura ou marca como aplicada.

- [ ] **JF-348 — Criar consulta histórica das vagas encontradas pelo agendador**
  - Depende de: JF-204 e JF-347.
  - Teste primeiro: última execução, período, agenda, provider, somente novas, duplicadas, vazio e
    paginação estável.
  - Aceite: API permite consultar execuções de uma agenda e as vagas vinculadas; a interface oferece
    a seção “Vagas encontradas pelo agendador” com data, origem, status da execução e acesso ao
    detalhe da vaga.
  - Aceite de navegação: vagas agendadas também aparecem na caixa de entrada normal e podem usar
    análise, rejeição, espera e “Marcar como aplicada” sem criar cópias.

- [ ] **JF-349 — Preservar decisões do usuário em redescobertas agendadas**
  - Depende de: JF-217, JF-220 e JF-347.
  - Teste primeiro: redescobrir vaga encontrada, em espera, aplicada, entrevista, rejeitada e
    removida; conteúdo atualizado e URL/origem adicional.
  - Aceite: o agendador atualiza origem, `last_seen_at` e versões de conteúdo, mas nunca regride o
    status da candidatura, desfaz rejeição, restaura item da lixeira ou altera eventos auditáveis.
  - Aceite de retenção: histórico da execução respeita a política local; remoção de uma agenda não
    remove vaga, candidatura, análise ou evento relacionado.

- [ ] **JF-350 — Validar agendamento, persistência e consulta ponta a ponta**
  - Depende de: JF-345 a JF-349.
  - Teste primeiro: criar agenda → vencer horário → buscar em providers → persistir/deduplicar →
    consultar histórico → reiniciar app → consultar as mesmas vagas.
  - Aceite: fluxo completo funciona sem ação manual no tick, distingue zero resultados, provider
    bloqueado, limite, falha e parcial, e continua íntegro após reinício.
  - Evidência exigida: testes unitários/API/integração/Vitest, smoke de reinício, Ruff, Mypy, Oxlint,
    TypeScript, Prettier e build pnpm verdes; README documenta funcionamento e limitações locais.

## E5 — GPT-5.6 Luna

- [x] **JF-400 — Integrar o cliente OpenAI no backend**
  - Depende de: JF-016 e JF-601.
  - Teste primeiro: cliente simulado, timeout, autenticação inválida e indisponibilidade.
  - Aceite: modelo padrão `gpt-5.6-luna` e nenhuma chamada pelo frontend.

- [x] **JF-401 — Criar schemas estruturados da IA**
  - Depende de: JF-100 e JF-200.
  - Teste primeiro: respostas válidas, ausentes, fora de faixa e com evidência inválida.
  - Aceite: extração e aderência validadas antes de persistir.

- [x] **JF-402 — Versionar prompts e configuração de raciocínio**
  - Depende de: JF-400 e JF-401.
  - Teste primeiro: renderização determinística, perfil redigido e versão registrada.
  - Aceite: `low` padrão e `medium` somente para análise detalhada solicitada.

- [x] **JF-403 — Implementar extração estruturada de vaga**
  - Depende de: JF-402 e JF-009.
  - Teste primeiro: conjunto de fixtures e respostas simuladas com campos ausentes.
  - Aceite: cargo, requisitos, local, regime, salário e evidências extraídos.
  - Evidência: `POST /api/jobs/{id}/analysis` analisa explicitamente a versão mais recente
    da vaga, com JSON Schema estrito, perfil e anúncio redigidos, `low` por padrão e
    validação Pydantic antes de retornar o resultado transitório. Coberto por testes
    unitários e de API; JF-009 permanece pendente de rotulagem humana.

- [x] **JF-404 — Implementar pontuação híbrida de aderência**
  - Depende de: JF-106, JF-401 e JF-403.
  - Teste primeiro: pesos, filtros impeditivos, score 0–100 e confiança.
  - Aceite: nenhum atributo sensível participa da pontuação.
  - Evidência: score combina dimensões determinísticas permitidas pelos pesos do perfil
    com influência fixa de 20% do contexto do modelo; filtros obrigatórios zeram a
    aderência. O allowlist não inclui atributos sensíveis nem pesos desconhecidos.

- [x] **JF-405 — Implementar explicação e evidências**
  - Depende de: JF-404.
  - Teste primeiro: pontos fortes, lacunas, alertas e citações presentes no anúncio.
  - Aceite: afirmação sem evidência é sinalizada, não apresentada como fato.
  - Evidência: cada citação é verificada no título, metadados ou texto visível do
    anúncio. Itens sem citação exata recebem `needs_review`; somente evidências
    verificadas são retornadas como fatos suportados.

- [x] **JF-406 — Persistir versão da análise**
  - Depende de: JF-100 e JF-405.
  - Teste primeiro: perfil/modelo/prompt usados, reanálise e histórico imutável.
  - Aceite: análise antiga permanece auditável.
  - Evidência: migração `0014_job_analysis_versions` retém análise, score, explicação,
    perfil, conteúdo, modelo e prompt de cada execução. `GET /api/jobs/{id}/analyses`
    devolve as versões em ordem; atualizações e exclusões pelo modelo ORM são bloqueadas.

- [x] **JF-407 — Medir tokens, latência e custo**
  - Depende de: JF-400.
  - Teste primeiro: uso normal, cache, ausência de usage e preço configurável.
  - Aceite: custo estimado por operação e execução disponível.
  - Evidência: `OpenAiResponsesClient` normaliza `usage` (incluindo tokens em cache e
    raciocínio) e latência; `ai_usage.py` calcula custo configurável sem falhar quando o
    provedor não envia uso; `GET /api/ai/usage` agrega operações, tokens, custo e latência.
    A resposta e o histórico de cada análise retêm os metadados na migração `0015_ai_usage`.

- [x] **JF-408 — Aplicar orçamento e alertas**
  - Depende de: JF-006 e JF-407.
  - Teste primeiro: 50%, 80%, 100%, troca de período e concorrência.
  - Aceite: novas chamadas param no teto sem interromper operações locais.
  - Evidência: `BudgetConfig` usa `JOB_FINDER_OPENAI_MONTHLY_BUDGET_USD`, calcula alertas
    em 50/80/100%, bloqueia apenas novas chamadas de IA no teto e mantém triagem, busca e
    pipeline locais disponíveis; `AI_BUDGET_LOCK` evita chamadas concorrentes no processo.

- [x] **JF-409 — Implementar cache seguro de contexto estável**
  - Depende de: JF-402 e JF-407.
  - Teste primeiro: chave de cache, invalidação por versão e dados redigidos.
  - Aceite: redução mensurável sem compartilhar conteúdo entre perfis.
  - Evidência: `AnalysisPromptCache` usa `(profile_version_id, prompt_version, mode)`,
    guarda somente instruções derivadas redigidas, expõe `cache_hit` e invalida por versão;
    texto da vaga e chave nunca entram no cache.

- [x] **JF-410 — Implementar descoberta por pesquisa web**
  - Depende de: JF-300, JF-400 e JF-408.
  - Teste primeiro: resultado com URL/evidência, vazio, duplicado e limite atingido.
  - Aceite: pesquisa seletiva, auditável e sem ação externa de candidatura.
  - Evidência: `POST /api/ai/discovery` aceita até três fontes escolhidas, consulta os
    adaptadores públicos existentes com limite explícito, persiste cada `search_run`,
    devolve URL/evidência e não possui qualquer ação de candidatura.

- [x] **JF-411 — Implementar fallback determinístico**
  - Depende de: JF-106 e JF-400.
  - Teste primeiro: API indisponível, orçamento esgotado e retomada posterior.
  - Aceite: vaga continua triável com indicação clara de análise limitada.
  - Evidência: indisponibilidade/timeout do provedor ou orçamento esgotado usa
    `build_fallback_analysis`, preserva filtros determinísticos, grava `fallback=true` e
    retém o motivo; a execução posterior continua disponível normalmente.

- [x] **JF-412 — Criar reanálise seletiva na interface**
  - Depende de: JF-406 e JF-408.
  - Teste primeiro: uma vaga, seleção múltipla, confirmação de custo e falha parcial.
  - Aceite: nunca reanalisa todo o banco acidentalmente.
  - Evidência: detalhe da vaga oferece análise individual; a caixa de entrada permite
    selecionar múltiplas vagas, confirma o custo/quantidade e usa `Promise.allSettled` para
    falhas parciais. Nenhuma ação percorre o banco inteiro sem seleção explícita.

## E6 — Dashboard e agenda

- [x] **JF-500 — Definir métricas e denominadores**
  - Depende de: JF-208, JF-209 e JF-303.
  - Teste primeiro: fixtures pequenas com valores calculados manualmente.
  - Aceite: fórmulas documentadas e duplicatas excluídas.
  - Evidência: `dashboard_metrics.py` define cartões, funil, denominadores, crédito pela
    primeira origem e exclusão de vagas removidas; testes cobrem fixtures pequenas,
    semanas vazias, fuso e erros de fontes.

- [x] **JF-501 — Implementar agregações de resumo**
  - Depende de: JF-500.
  - Teste primeiro: período vazio, fronteira de datas, fuso e filtros.
  - Aceite: cartões retornam números consistentes.
  - Evidência: `GET /api/dashboard/summary` retorna cartões de vagas, candidaturas,
    entrevistas, ofertas, contratações, rejeições e pipeline ativo com período e fuso.

- [x] **JF-502 — Implementar funil de conversão**
  - Depende de: JF-500.
  - Teste primeiro: avanço, regressão corrigida, desistência e divisão por zero.
  - Aceite: conversão entre fases com denominador visível.
  - Evidência: estágios Encontradas → Aplicadas → Entrevistas → Ofertas → Contratadas
    retornam `count`, `denominator` e `conversion_percent`, incluindo divisão segura por zero.

- [x] **JF-503 — Implementar séries temporais**
  - Depende de: JF-500 e JF-107.
  - Teste primeiro: agrupamento semanal, fuso e semanas sem eventos.
  - Aceite: evolução de vagas, candidaturas e entrevistas disponível.
  - Evidência: séries semanais incluem semanas sem movimento, agrupam no fuso solicitado e
    contabilizam transições para entrevista pelo histórico imutável.

- [x] **JF-504 — Implementar desempenho por fonte**
  - Depende de: JF-500 e JF-303.
  - Teste primeiro: múltiplas origens e crédito de conversão definido.
  - Aceite: volume, qualidade, avanço e erros comparáveis.
  - Evidência: cada vaga recebe crédito da primeira origem, com volume, aplicações,
    entrevistas, taxa de aplicação e erros de execuções da fonte.

- [x] **JF-505 — Criar dashboard visual**
  - Depende de: JF-501 a JF-504.
  - Teste primeiro: carregamento, erro, vazio, filtros e valores acessíveis.
  - Aceite: cartões, funil e séries acompanham resumo textual/tabela.
  - Evidência: seção `#dashboard` com período, cartões, `<progress>` acessível, funil,
    tabela semanal, tabela por fonte e resumo de agenda; cobertura Vitest adicionada.

- [x] **JF-506 — Implementar filtros salvos**
  - Depende de: JF-204 e JF-505.
  - Teste primeiro: criar, aplicar, renomear, excluir e filtro inválido após migração.
  - Aceite: filtros funcionam em vagas e dashboard.
  - Evidência: migração `0016_saved_filters`, CRUD em `/api/saved-filters` com validação
    de chaves permitidas e controles na caixa de entrada para salvar/aplicar busca e período.

- [x] **JF-507 — Criar painel de agenda e prazos**
  - Depende de: JF-213 e JF-505.
  - Teste primeiro: hoje, próximos, atrasados, fuso e estado vazio.
  - Aceite: entrevistas e desafios próximos ficam destacados.
  - Evidência: agenda existente separa próximos e atrasados, com links para eventos e
    resumo de contadores no dashboard; eventos de entrevista, desafio e prazo são exibidos.

- [x] **JF-508 — Validar acessibilidade das telas principais**
  - Depende de: JF-103, JF-205, JF-211 e JF-505.
  - Aceite: teclado, foco, semântica, contraste e alternativas textuais aprovados.
  - Evidência: formulário usa labels associados, região de resultados com `aria-live`, CTA externo
    com nome acessível e foco/contraste preservados; Vitest (18 testes), Oxlint, TypeScript/build e
    Prettier passaram.

## E7 — Segurança e empacotamento

- [ ] **JF-600 — Implementar sessão local, origem e CSRF**
  - Depende de: JF-018.
  - Teste primeiro: origem válida/inválida, mutação sem token e reinício.
  - Aceite: página externa não consegue realizar mutações locais.

- [x] **JF-601 — Armazenar chave criptografada no banco local**
  - Depende de: JF-016.
  - Teste primeiro: salvar, desbloquear, bloquear, remover, senha incorreta e indisponibilidade do cofre.
  - Aceite: SQLite contém somente ciphertext e salt; a senha do cofre não é persistida; chave nunca aparece em API de leitura, interface ou logs.

- [ ] **JF-602 — Bloquear SSRF e URLs perigosas**
  - Depende de: JF-016.
  - Teste primeiro: localhost, redes privadas, metadata, esquema inválido, DNS e redirect.
  - Aceite: somente destinos públicos permitidos são acessados.

- [ ] **JF-603 — Sanitizar conteúdo externo**
  - Depende de: JF-200.
  - Teste primeiro: scripts, handlers, URLs perigosas e HTML malformado.
  - Aceite: descrição preserva leitura sem conteúdo executável.

- [ ] **JF-604 — Implementar backup local**
  - Depende de: JF-017.
  - Teste primeiro: backup consistente com escrita concorrente e retenção.
  - Aceite: arquivo inclui metadados de versão e checksum.

- [ ] **JF-605 — Implementar restauração segura**
  - Depende de: JF-604.
  - Teste primeiro: backup válido, corrompido, incompatível e falha no meio.
  - Aceite: banco atual é preservado até a restauração ser validada.

- [ ] **JF-606 — Endurecer migrações de banco**
  - Depende de: JF-017 e JF-604.
  - Teste primeiro: upgrade, banco antigo, repetição e falha recuperável.
  - Aceite: backup automático antes de migração destrutiva.

- [ ] **JF-607 — Configurar empacotamento PyInstaller**
  - Depende de: JF-019 a JF-022.
  - Teste primeiro: assets, migrações, caminhos e execução sem Python instalado.
  - Aceite: pacote `onedir` contém `job-finder.exe` funcional.

- [ ] **JF-608 — Criar build reproduzível para Windows**
  - Depende de: JF-014 e JF-607.
  - Aceite: script limpo gera pacote e checksums com versões fixadas.

- [ ] **JF-609 — Executar smoke test em Windows limpo**
  - Depende de: JF-608.
  - Aceite: instalação sem Node/Python abre, persiste, reinicia e encerra corretamente.

- [ ] **JF-610 — Revisar logs, privacidade e dados exportados**
  - Depende de: JF-021, JF-105, JF-215 e JF-601.
  - Aceite: teste de vazamento não encontra chaves nem PII proibida.

- [ ] **JF-611 — Medir desempenho local**
  - Depende de: JF-505 e JF-607.
  - Aceite: metas de abertura, memória, listagem e dashboard registradas e atendidas.

- [ ] **JF-612 — Documentar instalação e solução de problemas**
  - Depende de: JF-608.
  - Aceite: README cobre executar, configurar, atualizar, backup, restauração e logs.

- [ ] **JF-613 — Produzir release candidata**
  - Depende de: JF-609 a JF-612.
  - Aceite: artefato, checksum, notas e limitações conhecidas disponíveis.

## E8 — Beta e lançamento

- [ ] **JF-700 — Definir protocolo do beta**
  - Depende de: JF-009 e JF-613.
  - Aceite: período, dados coletados, privacidade e critérios de interrupção definidos.

- [ ] **JF-701 — Executar uso real controlado**
  - Depende de: JF-700.
  - Aceite: buscas e pipeline usados por período suficiente sem perda de dados.

- [ ] **JF-702 — Avaliar precisão da busca e pontuação**
  - Depende de: JF-701.
  - Aceite: falsos positivos/negativos, precisão de campos e feedback registrados.

- [ ] **JF-703 — Avaliar custo e latência da IA**
  - Depende de: JF-701.
  - Aceite: custo por vaga, por execução e projeção mensal comparados ao orçamento.

- [ ] **JF-704 — Corrigir regressões do beta com TDD**
  - Depende de: JF-702 e JF-703.
  - Teste primeiro: cada defeito começa com teste reproduzindo a falha.
  - Aceite: bloqueadores resolvidos e regressões cobertas.

- [ ] **JF-705 — Reexecutar suíte e smoke tests finais**
  - Depende de: JF-704.
  - Aceite: CI, pacote Windows, backup/restauração e fluxos críticos verdes.

- [ ] **JF-706 — Fechar documentação da versão**
  - Depende de: JF-705.
  - Aceite: changelog, notas, limitações, privacidade e guia de atualização revisados.

- [ ] **JF-707 — Publicar `v0.1.0`**
  - Depende de: JF-706.
  - Aceite: tag aponta para commit validado e artefato/checksum correspondem à tag.

## Ordem crítica recomendada

1. JF-010 → JF-019 para obter a aplicação local mínima.
2. JF-100 → JF-103 para cadastrar o perfil.
3. JF-200 → JF-206 para importar e visualizar uma vaga.
4. JF-400 → JF-405 para analisar a vaga com `gpt-5.6-luna`.
5. JF-208 → JF-211 para avançar a vaga até `APLICADA`.
6. JF-500 → JF-505 para refletir a mudança no dashboard.
7. JF-020 → JF-022 e JF-607 para validar o primeiro executável.
8. E4 para ampliar da importação manual às buscas automáticas.
9. JF-320 → JF-340 para substituir a escolha de fonte por busca agregada com foco Brasil.
10. JF-217 → JF-221 para permitir confirmar a aplicação diretamente na vaga e refletir o evento em
    todo o acompanhamento.
11. JF-345 → JF-350 para agendar a busca unificada, persistir cada vaga no SQLite e consultar o
    histórico depois, inclusive após reiniciar o aplicativo.

Esse caminho entrega a primeira fatia vertical antes de multiplicar conectores e permite validar arquitetura, experiência e custo cedo.

## Diário de progresso

| Data | Tarefa | Estado | Evidência/observação |
|---|---|---|---|
| 15/08/2026 | JF-001 | Concluída | `eb4ab11` — planejamento inicial |
| 15/08/2026 | JF-002 | Concluída | `3c2a839` — TDD obrigatório |
| 15/08/2026 | JF-003 | Concluída | Quadro criado neste documento |
| 15/08/2026 | JF-010 | Concluída | Estrutura inicial criada e artefatos locais ignorados |
| 15/08/2026 | JF-011 | Concluída | `pyproject.toml`, instalação editável e Pytest configurados |
| 15/08/2026 | JF-015 | Concluída | TDD Red → Green para `GET /api/health` |
| 15/08/2026 | JF-012 | Concluída | React/Vite, Vitest, lint e build configurados exclusivamente com pnpm |
| 15/08/2026 | JF-016 | Concluída | Settings tipados, secret mascarado e variáveis `JOB_FINDER_*` validados |
| 15/08/2026 | JF-017 | Concluída | SQLite WAL, SQLAlchemy e migração idempotente validados |
| 15/08/2026 | JF-018 | Concluída | Servidor loopback com startup, migração, health e shutdown validados |
| 15/08/2026 | JF-019 | Concluída | Frontend Vite compilado, assets e fallback SPA entregues na mesma origem da API |
| 15/08/2026 | JF-020 | Concluída | Navegador abre URL local e trava exclusiva evita servidor duplicado |
| 15/08/2026 | JF-021 | Concluída | Logs locais rotativos com nível configurável e redação de dados sensíveis |
| 15/08/2026 | JF-022 | Concluída | Script Windows valida health, interface, SQLite e liberação de recursos |
| 15/08/2026 | JF-013 | Concluída | Formatter, lint e tipos reproduzíveis validados para backend e frontend |
| 15/08/2026 | JF-014 | Concluída | Workflow Windows valida testes, qualidade, tipos e build sem segredos |
| 15/08/2026 | JF-100 | Concluída | Perfil versionado em SQLite com histórico imutável e consulta da versão ativa |
| 15/08/2026 | JF-101 | Concluída | Critérios tipados validam cargos, pesos, remuneração, idiomas e restrições |
| 15/08/2026 | JF-102 | Concluída | API local cria e lê versões validadas do perfil |
| 15/08/2026 | JF-103 | Concluída | `266a44d` — onboarding local com validação, salvamento versionado e shell editorial; 3 testes Vitest, lint, formatação, build e 26 testes backend verdes |
| 15/08/2026 | JF-104 | Concluída | `34fa427` — histórico de versões na API e interface, com versão ativa destacada; 4 testes Vitest e 27 testes backend verdes |
| 15/08/2026 | JF-105 | Concluída | `1708bec` — redação de e-mail, telefone, endereço e identificadores com prévia segura; 1 teste unitário, 1 teste API e 6 testes frontend |
| 15/08/2026 | JF-106 | Concluída | `1708bec` — filtros de país, regime, contrato, salário e palavras bloqueadas com razões rastreáveis; 2 testes unitários e 1 teste API |
| 15/08/2026 | JF-107 | Concluída | `1708bec` — preferências de locale, moeda, fuso e retenção persistidas na migração `0003_preferences` e painel local |
| 15/08/2026 | JF-200 | Concluída | Migração `0004_jobs`, vaga normalizada com múltiplas origens, conteúdo bruto versionado com validade e 39 testes backend verdes |
| 15/08/2026 | JF-201 | Concluída | Normalização determinística de URL, textos, espaços e datas; 7 testes focados verdes |
| 15/08/2026 | JF-202 | Concluída | Inclusão manual transacional via `POST /api/jobs`, origem auditável e status inicial `ENCONTRADA` |
| 15/08/2026 | JF-203 | Concluída | Importação por URL com política pública mínima, redirects limitados, sanitização e origem `url_import` |
| 15/08/2026 | JF-204 | Concluída | Listagem paginada com filtros/ordenação e detalhe com origens, conteúdo e 404 explícito |
| 15/08/2026 | JF-205 | Concluída | Caixa de entrada visual com busca, estados de UI e inclusão manual rápida integrada a `POST /api/jobs` |
| 15/08/2026 | JF-206 | Concluída | Detalhe sob demanda com origem, histórico de conteúdo e proteção contra execução de HTML externo |
| 15/08/2026 | JF-207 | Concluída | Notas editáveis e tags reutilizáveis disponíveis por API e no contrato de detalhe da vaga |
| 15/08/2026 | JF-208 | Concluída | Migração `0008_applications`, candidatura única por vaga e eventos de fase imutáveis; 57 testes backend verdes |
| 15/08/2026 | JF-209 | Concluída | Máquina de estados com transições permitidas, terminais e correções auditáveis; testes unitários verdes |
| 15/08/2026 | JF-210 | Concluída | API transacional para criar, consultar, avançar e corrigir candidaturas; conflitos retornam `409` |
| 15/08/2026 | JF-211 | Concluída | Quadro visual responsivo com ações acessíveis e rollback de transição rejeitada; 10 testes Vitest e build frontend verdes |
| 15/08/2026 | JF-212 | Concluída | Eventos de entrevista, desafio e prazo com timezone, conflito e vencimento auditáveis; migração `0009_process_events` e 61 testes backend verdes |
| 15/08/2026 | JF-213 | Concluída | Agenda API com filtros por período/status e interface de próximos/vencidos; 11 testes Vitest e 62 testes backend verdes |
| 15/08/2026 | JF-214 | Concluída | Motivos de encerramento obrigatórios quando aplicável e auditados nos eventos sem apagar histórico; 64 testes backend verdes |
| 15/08/2026 | JF-215 | Concluída | Exportação CSV/JSON filtrável, codificação Excel-friendly e neutralização de fórmulas; 65 testes backend verdes |
| 15/08/2026 | JF-216 | Concluída | Lixeira com soft-delete, restauração, expiração por retenção e proteção de candidaturas vinculadas; migração `0011_recoverable_trash`, UI de restauração/confirmação, 68 testes backend e 12 Vitest verdes |
| 15/08/2026 | JF-300–JF-313 | Concluída | E4 completa: contrato de adaptadores, três fontes públicas, configuração sem segredos, runs auditáveis, cancelamento, scheduler persistente, cliente HTTP resiliente, limites/backoff, deduplicação exata/aproximada e painel; 49 testes unitários backend, 2 testes API E4, Ruff e Mypy verdes |
| 16/08/2026 | JF-320–JF-339 | Concluída | Busca agregada com JSearch/Adzuna/Jooble, fallback legado, normalização, deduplicação, ranking, cache, API única, cartões, cofre de credenciais e link externo implementados; testes focados, Ruff/Mypy e frontend verdes |
| 16/08/2026 | JF-340 | Concluída | E4.1 validada ponta a ponta com 50 testes API/integração e 92 unitários no Windows; Ruff, Mypy, Vitest, Oxlint, TypeScript, Prettier e build frontend verdes |
| 16/08/2026 | JF-508 | Concluída | Acessibilidade da busca e telas principais validada com 18 testes Vitest, Oxlint, TypeScript/build e Prettier |
| 16/08/2026 | JF-341 | Concluída com pendência externa | Corrigida a rota aposentada `/search` para a rota atual `/search-v2`, idioma normalizado para `pt`, diagnóstico HTTP seguro, contagem de providers corrigida e desbloqueio no frontend; 142 testes backend, 20 Vitest, Ruff, Mypy, Oxlint, TypeScript/build e Prettier verdes. |
| 16/08/2026 | JF-342 | Concluída | Lock de instância agora é validado por `/api/health` antes de abrir o navegador; busca sem conexão recebe orientação de reinício e exceções inesperadas retornam JSON seguro e entram no log local. |
| 16/08/2026 | JF-343 | Concluída | A resposta real da JSearch continha `data` como objeto; o parser agora aceita coleções aninhadas e converte formatos desconhecidos em falha isolada da fonte, preservando os fallbacks. |
| 16/08/2026 | JF-344 | Concluída | IDs externos opacos da JSearch acima de 255 caracteres são convertidos em hash determinístico antes de persistir, mantendo a deduplicação exata e eliminando o `ValidationError`. |
| 16/08/2026 | JF-217–JF-221 | Planejadas | Fluxo “Marcar como aplicada” dividido em comando atômico, ações na vaga e busca, sincronização de pipeline/dashboard e validação ponta a ponta com TDD. |
| 16/08/2026 | JF-345–JF-350 | Planejadas | Agendador unificado dividido em agenda persistida, worker local, vínculo execução-vaga, consulta histórica, preservação das decisões humanas e validação após reinício. |
| 15/08/2026 | JF-601 | Concluída | Cofre SQLite cifrado por senha transitória, UI local e migração `0013_ai_secrets`; testes de ausência de plaintext, bloqueio/desbloqueio, API e interface verdes. |
| 15/08/2026 | JF-009 | Coleta iniciada | 57 vagas públicas persistidas por execuções auditáveis de `Data Analyst`, `Business Intelligence` e `Data`; falta selecionar 30–50 e rotular após a chave e os critérios finais. |
| 15/08/2026 | JF-400 | Concluída | Cliente backend da Responses API usa `gpt-5.6-luna`, `reasoning.effort: low` e `store: false`; testes simulados cobrem sucesso, autenticação, timeout, indisponibilidade e endpoint de conexão. |
| 15/08/2026 | JF-401 | Concluída | Contratos Pydantic para extração, aderência, score, confiança e evidências; validações cobrem campos ausentes, faixas inválidas, evidência inválida e salário inconsistente. |
| 15/08/2026 | JF-402 | Concluída | Prompt `2026-08-15.1` é determinístico, redige PII detectável do perfil e define `low` para lote e `medium` para revisão detalhada. |
| 15/08/2026 | JF-403 | Concluída com exceção explícita | Rota de análise por vaga usa Structured Outputs estrito, redige perfil e anúncio, seleciona o conteúdo mais recente e devolve campos/evidências validados; JF-009 continua pendente de seleção e rótulos humanos. |
| 15/08/2026 | JF-404 | Concluída | Pontuação híbrida limitada a dimensões permitidas; filtros impeditivos retornam nota zero e confiança 100, enquanto o contexto do modelo tem peso fixo de 20%. |
| 15/08/2026 | JF-405 | Concluída | Evidências são comparadas com título, metadados ou conteúdo visível; resumos, pontos fortes, lacunas e alertas sem citação exata recebem estado `needs_review`. |
| 15/08/2026 | JF-406 | Concluída | Migração `0014_job_analysis_versions` cria histórico append-only com versão da vaga e perfil, modelo, prompt, análise, score e explicação; a API lista reanálises em ordem. |

## Bloqueios e decisões pendentes

| Data | Tarefa | Bloqueio/decisão | Responsável | Próxima ação |
|---|---|---|---|---|
| 15/08/2026 | JF-004 | Currículo privado analisado sem ser versionado; ainda faltam confirmação de senioridade, idiomas, regime, localização e faixa salarial | Usuário | Confirmar esses critérios no onboarding antes da avaliação final |
| 15/08/2026 | JF-005 | Fontes dependem de países, cargos e regime desejados | Projeto | Selecionar após JF-004 |
| 15/08/2026 | JF-006 | Orçamento mensal ainda não definido | Usuário | Definir antes de ativar buscas automáticas |
| 15/08/2026 | JF-005/JF-006 | E4 foi implementada com Remote OK, Arbeitnow e Jobicy, agendamento desligado e limites padrão de 50 execuções/dia e 50 vagas/run para não bloquear o desenvolvimento | Projeto | Usuário pode substituir fontes, termos, frequência e limites em `/api/sources` antes de ativar automação |
| 15/08/2026 | JF-009 | O conjunto de avaliação depende de rótulos humanos e dos critérios finais do perfil; a coleta pública já está no banco local | Usuário + Projeto | Salvar a chave no painel IA e confirmar o perfil para iniciar a seleção e rotulagem assistida |

## Ideias fora do MVP

Não transformar itens abaixo em tarefas do MVP sem decisão explícita:

- candidatura automática;
- extensão de navegador;
- sincronização em nuvem;
- integrações com e-mail e calendário;
- simulação de entrevista dentro do Job Finder; o produto externo é o Se Prepara AI;
- geração assistida de currículo e carta;
- instalador com atualização automática;
- suporte a macOS e Linux.
