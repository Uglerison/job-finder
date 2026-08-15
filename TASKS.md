# Job Finder — controle de tarefas

> Versão: 1.0 — 15/08/2026
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
| E1 — Fundação local | JF-010–JF-022 | Em andamento | Aplicação local abre e persiste dados |
| E2 — Perfil | JF-100–JF-107 | Pendente | Perfil editável e versionado |
| E3 — Vagas e candidaturas | JF-200–JF-216 | Pendente | Fluxo manual completo |
| E4 — Busca e fontes | JF-300–JF-313 | Pendente | Vagas coletadas e deduplicadas |
| E5 — GPT-5.6 Luna | JF-400–JF-412 | Pendente | Análise explicável e controlada |
| E6 — Dashboard e agenda | JF-500–JF-508 | Pendente | Métricas operacionais consistentes |
| E7 — Segurança e empacotamento | JF-600–JF-613 | Pendente | Release candidata Windows |
| E8 — Beta e lançamento | JF-700–JF-707 | Pendente | MVP `v0.1.0` validado |

**Próxima tarefa pronta:** `JF-014 — Configurar CI inicial`.

## Marcos

### M1 — Fundação executável

Concluído quando JF-010 a JF-022 estiverem verdes.

### M2 — Fluxo manual utilizável

Concluído quando E2 e E3 permitirem cadastrar perfil, importar vaga, triar, aplicar e registrar entrevistas.

### M3 — Primeira fatia vertical inteligente

Concluído quando for possível cadastrar perfil, importar uma vaga por URL, analisar com `gpt-5.6-luna`, mover até `APLICADA` e refletir a mudança no dashboard.

### M4 — Busca automática

Concluído quando três fontes aprovadas executarem com agendamento, limites, auditoria e deduplicação.

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

- [ ] **JF-014 — Configurar CI inicial**
  - Depende de: JF-013.
  - Aceite: workflow executa testes, lint, tipos e build sem segredos.

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

- [ ] **JF-100 — Modelar perfil e versões**
  - Depende de: JF-017.
  - Teste primeiro: criação, nova versão, consulta da versão ativa e imutabilidade histórica.
  - Aceite: schema e migração preservam histórico.

- [ ] **JF-101 — Implementar validação dos critérios do perfil**
  - Depende de: JF-100.
  - Teste primeiro: cargos, pesos, salário, idiomas e restrições válidos/inválidos.
  - Aceite: erros de domínio claros e pesos consistentes.

- [ ] **JF-102 — Implementar API do perfil**
  - Depende de: JF-100 e JF-101.
  - Teste primeiro: `GET` vazio, `PUT` válido, atualização versionada e payload inválido.
  - Aceite: contratos tipados para leitura e atualização.

- [ ] **JF-103 — Criar onboarding do perfil**
  - Depende de: JF-012 e JF-102.
  - Teste primeiro: fluxo obrigatório, validações e salvamento bem-sucedido.
  - Aceite: perfil completo configurável sem editar arquivos.

- [ ] **JF-104 — Implementar edição e visualização de versões**
  - Depende de: JF-103.
  - Teste primeiro: carregar versão atual e exibir histórico sem mutá-lo.
  - Aceite: usuário entende quando e por que a análise ficou desatualizada.

- [ ] **JF-105 — Implementar redação de dados pessoais**
  - Depende de: JF-101.
  - Teste primeiro: e-mail, telefone, endereço e identificadores em fixtures.
  - Aceite: prévia mostra exatamente o texto que poderá ser enviado à IA.

- [ ] **JF-106 — Implementar filtros obrigatórios determinísticos**
  - Depende de: JF-101.
  - Teste primeiro: país, regime, contrato, salário e palavras bloqueadas.
  - Aceite: cada exclusão inclui motivo rastreável.

- [ ] **JF-107 — Implementar preferências gerais**
  - Depende de: JF-017.
  - Teste primeiro: locale, moeda, fuso, retenção e defaults.
  - Aceite: preferências persistem e são aplicadas na API/UI.

## E3 — Vagas e candidaturas

- [ ] **JF-200 — Modelar vaga e suas origens**
  - Depende de: JF-017.
  - Teste primeiro: vaga normalizada com múltiplas origens e conteúdo versionado.
  - Aceite: schema e migração suportam URL canônica, conteúdo bruto e validade.

- [ ] **JF-201 — Implementar normalização determinística**
  - Depende de: JF-200.
  - Teste primeiro: URLs, cargos, empresas, locais, datas e espaços inconsistentes.
  - Aceite: mesma entrada produz sempre a mesma representação.

- [ ] **JF-202 — Implementar inclusão manual de vaga**
  - Depende de: JF-200 e JF-201.
  - Teste primeiro: formulário válido, URL inválida e campos obrigatórios ausentes.
  - Aceite: vaga manual aparece como `ENCONTRADA` com origem auditável.

- [ ] **JF-203 — Implementar importação de vaga por URL**
  - Depende de: JF-202 e JF-602.
  - Teste primeiro: URL pública permitida, redirecionamento limitado e destino bloqueado.
  - Aceite: conteúdo sanitizado e falhas explicadas sem travar a aplicação.

- [ ] **JF-204 — Implementar API de listagem e detalhe**
  - Depende de: JF-200.
  - Teste primeiro: paginação, filtros, ordenação, ausência e detalhe.
  - Aceite: contratos estáveis e consultas sem N+1 relevante.

- [ ] **JF-205 — Criar caixa de entrada de vagas**
  - Depende de: JF-012 e JF-204.
  - Teste primeiro: estados vazio/erro/carregamento e ações rápidas.
  - Aceite: vagas novas podem ser revisadas e filtradas.

- [ ] **JF-206 — Criar tela de detalhe da vaga**
  - Depende de: JF-204 e JF-205.
  - Teste primeiro: descrição segura, origem, metadados e histórico.
  - Aceite: nenhum HTML externo executável é renderizado.

- [ ] **JF-207 — Implementar notas e tags**
  - Depende de: JF-200.
  - Teste primeiro: criar, editar, filtrar e remover vínculo sem perder a vaga.
  - Aceite: notas e tags disponíveis na API e interface.

- [ ] **JF-208 — Modelar candidatura e eventos de fase**
  - Depende de: JF-017 e JF-200.
  - Teste primeiro: candidatura única por vaga, estado atual e eventos imutáveis.
  - Aceite: migração preserva histórico completo.

- [ ] **JF-209 — Implementar máquina de estados do pipeline**
  - Depende de: JF-208.
  - Teste primeiro: todas as transições permitidas, proibidas e correções auditáveis.
  - Aceite: backend rejeita transição inválida independentemente da UI.

- [ ] **JF-210 — Implementar API de candidaturas e fases**
  - Depende de: JF-209.
  - Teste primeiro: criar candidatura, avançar, corrigir e consultar histórico.
  - Aceite: operações transacionais com erros de domínio claros.

- [ ] **JF-211 — Criar quadro visual do pipeline**
  - Depende de: JF-210.
  - Teste primeiro: mover por ação acessível, erro de transição e atualização otimista revertida.
  - Aceite: pipeline utilizável com mouse e teclado.

- [ ] **JF-212 — Modelar entrevistas, desafios e prazos**
  - Depende de: JF-208 e JF-107.
  - Teste primeiro: fuso, conflito, prazo vencido e vínculo ao processo.
  - Aceite: eventos persistem com data, participantes, link e notas.

- [ ] **JF-213 — Implementar agenda de processo seletivo**
  - Depende de: JF-212.
  - Teste primeiro: próximos eventos, vencidos e filtros por período.
  - Aceite: agenda disponível na API e interface.

- [ ] **JF-214 — Implementar motivos de encerramento**
  - Depende de: JF-209.
  - Teste primeiro: reprovação, desistência, expiração e motivo opcional/obrigatório.
  - Aceite: dados alimentam relatórios sem apagar histórico.

- [ ] **JF-215 — Implementar exportação CSV/JSON**
  - Depende de: JF-204 e JF-210.
  - Teste primeiro: codificação, campos, filtros e neutralização de fórmulas em CSV.
  - Aceite: exportação abre corretamente e não contém a chave da API.

- [ ] **JF-216 — Implementar lixeira recuperável**
  - Depende de: JF-200 e JF-208.
  - Teste primeiro: arquivar, restaurar e expirar após retenção.
  - Aceite: exclusão definitiva exige confirmação e respeita vínculos.

## E4 — Busca e fontes

- [ ] **JF-300 — Definir contrato de adaptadores**
  - Depende de: JF-005 e JF-200.
  - Teste primeiro: adaptador bem-sucedido, parcial, vazio, cancelado e com erro.
  - Aceite: interface tipada não acopla domínio a uma fonte específica.

- [ ] **JF-301 — Modelar configuração de fonte**
  - Depende de: JF-017 e JF-300.
  - Teste primeiro: ativação, frequência, limites e configuração inválida.
  - Aceite: segredos não são persistidos em texto simples.

- [ ] **JF-302 — Implementar API e UI de fontes**
  - Depende de: JF-301.
  - Teste primeiro: criar, testar conexão, pausar e editar uma fonte.
  - Aceite: configuração e último estado visíveis ao usuário.

- [ ] **JF-303 — Modelar e executar `search_run`**
  - Depende de: JF-300 e JF-301.
  - Teste primeiro: ciclo pendente/em execução/concluído/falhou/cancelado.
  - Aceite: contadores, duração e erros ficam auditáveis.

- [ ] **JF-304 — Implementar cancelamento cooperativo**
  - Depende de: JF-303.
  - Teste primeiro: cancelar antes, durante e após conclusão.
  - Aceite: nenhuma tarefa fica órfã nem grava resultado após cancelamento.

- [ ] **JF-305 — Implementar agendador persistente**
  - Depende de: JF-301 e JF-303.
  - Teste primeiro: próxima execução, reinício, janela e tarefa perdida.
  - Aceite: automático desativado por padrão e fuso respeitado.

- [ ] **JF-306 — Implementar cliente HTTP seguro e resiliente**
  - Depende de: JF-016 e JF-602.
  - Teste primeiro: timeout, limite, redirecionamento, retry e domínio bloqueado.
  - Aceite: políticas comuns aplicadas a todos os conectores.

- [ ] **JF-307 — Implementar limite e backoff por fonte**
  - Depende de: JF-303 e JF-306.
  - Teste primeiro: `429`, erro transitório, teto e pausa automática.
  - Aceite: repetição limitada com jitter e diagnóstico visível.

- [ ] **JF-308 — Implementar conector da fonte 1**
  - Depende de: JF-005, JF-300 e JF-306.
  - Teste primeiro: fixtures de sucesso, paginação, alteração e erro.
  - Aceite: vagas entram normalizadas com origem e evidência.

- [ ] **JF-309 — Implementar conector da fonte 2**
  - Depende de: JF-308.
  - Teste primeiro: fixtures específicas e contrato comum.
  - Aceite: mesmos indicadores operacionais da fonte 1.

- [ ] **JF-310 — Implementar conector da fonte 3**
  - Depende de: JF-309.
  - Teste primeiro: fixtures específicas e contrato comum.
  - Aceite: mesmos indicadores operacionais das fontes anteriores.

- [ ] **JF-311 — Implementar deduplicação exata**
  - Depende de: JF-201 e JF-303.
  - Teste primeiro: URL canônica, ID externo, hash e múltiplas origens.
  - Aceite: duplicata exata não cria uma segunda vaga.

- [ ] **JF-312 — Implementar sugestão de duplicata aproximada**
  - Depende de: JF-311.
  - Teste primeiro: cargo/empresa/local semelhantes e falsos positivos conhecidos.
  - Aceite: união aproximada exige confirmação do usuário.

- [ ] **JF-313 — Criar painel de execuções e erros**
  - Depende de: JF-302 a JF-307.
  - Teste primeiro: progresso, cancelamento, falha parcial e reexecução.
  - Aceite: resultado de cada fonte pode ser diagnosticado sem abrir logs.

## E5 — GPT-5.6 Luna

- [ ] **JF-400 — Integrar o cliente OpenAI no backend**
  - Depende de: JF-016 e JF-601.
  - Teste primeiro: cliente simulado, timeout, autenticação inválida e indisponibilidade.
  - Aceite: modelo padrão `gpt-5.6-luna` e nenhuma chamada pelo frontend.

- [ ] **JF-401 — Criar schemas estruturados da IA**
  - Depende de: JF-100 e JF-200.
  - Teste primeiro: respostas válidas, ausentes, fora de faixa e com evidência inválida.
  - Aceite: extração e aderência validadas antes de persistir.

- [ ] **JF-402 — Versionar prompts e configuração de raciocínio**
  - Depende de: JF-400 e JF-401.
  - Teste primeiro: renderização determinística, perfil redigido e versão registrada.
  - Aceite: `low` padrão e `medium` somente para análise detalhada solicitada.

- [ ] **JF-403 — Implementar extração estruturada de vaga**
  - Depende de: JF-402 e JF-009.
  - Teste primeiro: conjunto de fixtures e respostas simuladas com campos ausentes.
  - Aceite: cargo, requisitos, local, regime, salário e evidências extraídos.

- [ ] **JF-404 — Implementar pontuação híbrida de aderência**
  - Depende de: JF-106, JF-401 e JF-403.
  - Teste primeiro: pesos, filtros impeditivos, score 0–100 e confiança.
  - Aceite: nenhum atributo sensível participa da pontuação.

- [ ] **JF-405 — Implementar explicação e evidências**
  - Depende de: JF-404.
  - Teste primeiro: pontos fortes, lacunas, alertas e citações presentes no anúncio.
  - Aceite: afirmação sem evidência é sinalizada, não apresentada como fato.

- [ ] **JF-406 — Persistir versão da análise**
  - Depende de: JF-100 e JF-405.
  - Teste primeiro: perfil/modelo/prompt usados, reanálise e histórico imutável.
  - Aceite: análise antiga permanece auditável.

- [ ] **JF-407 — Medir tokens, latência e custo**
  - Depende de: JF-400.
  - Teste primeiro: uso normal, cache, ausência de usage e preço configurável.
  - Aceite: custo estimado por operação e execução disponível.

- [ ] **JF-408 — Aplicar orçamento e alertas**
  - Depende de: JF-006 e JF-407.
  - Teste primeiro: 50%, 80%, 100%, troca de período e concorrência.
  - Aceite: novas chamadas param no teto sem interromper operações locais.

- [ ] **JF-409 — Implementar cache seguro de contexto estável**
  - Depende de: JF-402 e JF-407.
  - Teste primeiro: chave de cache, invalidação por versão e dados redigidos.
  - Aceite: redução mensurável sem compartilhar conteúdo entre perfis.

- [ ] **JF-410 — Implementar descoberta por pesquisa web**
  - Depende de: JF-300, JF-400 e JF-408.
  - Teste primeiro: resultado com URL/evidência, vazio, duplicado e limite atingido.
  - Aceite: pesquisa seletiva, auditável e sem ação externa de candidatura.

- [ ] **JF-411 — Implementar fallback determinístico**
  - Depende de: JF-106 e JF-400.
  - Teste primeiro: API indisponível, orçamento esgotado e retomada posterior.
  - Aceite: vaga continua triável com indicação clara de análise limitada.

- [ ] **JF-412 — Criar reanálise seletiva na interface**
  - Depende de: JF-406 e JF-408.
  - Teste primeiro: uma vaga, seleção múltipla, confirmação de custo e falha parcial.
  - Aceite: nunca reanalisa todo o banco acidentalmente.

## E6 — Dashboard e agenda

- [ ] **JF-500 — Definir métricas e denominadores**
  - Depende de: JF-208, JF-209 e JF-303.
  - Teste primeiro: fixtures pequenas com valores calculados manualmente.
  - Aceite: fórmulas documentadas e duplicatas excluídas.

- [ ] **JF-501 — Implementar agregações de resumo**
  - Depende de: JF-500.
  - Teste primeiro: período vazio, fronteira de datas, fuso e filtros.
  - Aceite: cartões retornam números consistentes.

- [ ] **JF-502 — Implementar funil de conversão**
  - Depende de: JF-500.
  - Teste primeiro: avanço, regressão corrigida, desistência e divisão por zero.
  - Aceite: conversão entre fases com denominador visível.

- [ ] **JF-503 — Implementar séries temporais**
  - Depende de: JF-500 e JF-107.
  - Teste primeiro: agrupamento semanal, fuso e semanas sem eventos.
  - Aceite: evolução de vagas, candidaturas e entrevistas disponível.

- [ ] **JF-504 — Implementar desempenho por fonte**
  - Depende de: JF-500 e JF-303.
  - Teste primeiro: múltiplas origens e crédito de conversão definido.
  - Aceite: volume, qualidade, avanço e erros comparáveis.

- [ ] **JF-505 — Criar dashboard visual**
  - Depende de: JF-501 a JF-504.
  - Teste primeiro: carregamento, erro, vazio, filtros e valores acessíveis.
  - Aceite: cartões, funil e séries acompanham resumo textual/tabela.

- [ ] **JF-506 — Implementar filtros salvos**
  - Depende de: JF-204 e JF-505.
  - Teste primeiro: criar, aplicar, renomear, excluir e filtro inválido após migração.
  - Aceite: filtros funcionam em vagas e dashboard.

- [ ] **JF-507 — Criar painel de agenda e prazos**
  - Depende de: JF-213 e JF-505.
  - Teste primeiro: hoje, próximos, atrasados, fuso e estado vazio.
  - Aceite: entrevistas e desafios próximos ficam destacados.

- [ ] **JF-508 — Validar acessibilidade das telas principais**
  - Depende de: JF-103, JF-205, JF-211 e JF-505.
  - Aceite: teclado, foco, semântica, contraste e alternativas textuais aprovados.

## E7 — Segurança e empacotamento

- [ ] **JF-600 — Implementar sessão local, origem e CSRF**
  - Depende de: JF-018.
  - Teste primeiro: origem válida/inválida, mutação sem token e reinício.
  - Aceite: página externa não consegue realizar mutações locais.

- [ ] **JF-601 — Armazenar chave no Windows Credential Manager**
  - Depende de: JF-016.
  - Teste primeiro: salvar, recuperar, substituir, remover e keyring indisponível.
  - Aceite: chave nunca aparece no banco, frontend ou logs.

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

## Bloqueios e decisões pendentes

| Data | Tarefa | Bloqueio/decisão | Responsável | Próxima ação |
|---|---|---|---|---|
| 15/08/2026 | JF-004 | Falta consolidar o perfil profissional de referência | Usuário | Fornecer currículo ou preencher critérios no onboarding quando disponível |
| 15/08/2026 | JF-005 | Fontes dependem de países, cargos e regime desejados | Projeto | Selecionar após JF-004 |
| 15/08/2026 | JF-006 | Orçamento mensal ainda não definido | Usuário | Definir antes de ativar buscas automáticas |

## Ideias fora do MVP

Não transformar itens abaixo em tarefas do MVP sem decisão explícita:

- candidatura automática;
- extensão de navegador;
- sincronização em nuvem;
- integrações com e-mail e calendário;
- geração assistida de currículo e carta;
- instalador com atualização automática;
- suporte a macOS e Linux.
