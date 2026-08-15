# Job Finder — planejamento do produto e implementação

> Documento inicial de produto e arquitetura  
> Versão: 1.1 — 15/08/2026
> Execução-alvo: Windows, local, com abertura automática no navegador

## 1. Visão do produto

O **Job Finder** será uma aplicação local para encontrar vagas compatíveis com o perfil profissional do usuário e acompanhar todo o ciclo de candidatura em um único painel. O usuário executará `job-finder.exe`; o programa iniciará um servidor restrito ao computador (`127.0.0.1`), abrirá a interface no navegador padrão e armazenará os dados localmente.

O produto deverá:

- permitir cadastrar e ajustar o perfil profissional e os critérios de busca;
- procurar vagas na web por fontes configuráveis e permitidas;
- eliminar duplicatas e classificar a aderência de cada vaga ao perfil;
- explicar os pontos favoráveis, lacunas e possíveis impeditivos da vaga;
- permitir decidir entre rejeitar, manter em espera ou avançar com uma vaga;
- registrar candidatura, entrevistas, oferta, contratação, desistência e reprovação;
- mostrar métricas do funil, das fontes e da evolução das candidaturas;
- preservar controle humano: o MVP não enviará candidaturas nem mensagens automaticamente.

## 2. Objetivos e limites

### 2.1 Objetivos do MVP

1. Entregar um executável Windows que funcione sem Node.js ou Python instalados na máquina do usuário.
2. Centralizar vagas descobertas automaticamente e vagas adicionadas por URL.
3. Pontuar vagas de 0 a 100 segundo um perfil editável.
4. Manter histórico completo das mudanças de fase.
5. Disponibilizar dashboard e filtros úteis para a rotina diária.
6. Usar `gpt-5.6-luna` com orçamento, privacidade e observabilidade controláveis.
7. Exportar dados e criar backups locais restauráveis.

### 2.2 Fora do MVP

- candidatura automática em sites de terceiros;
- preenchimento automático de formulários com dados pessoais;
- envio automático de e-mails ou mensagens a recrutadores;
- coleta agressiva em páginas que proíbem automação;
- sincronização multiusuário ou hospedagem em nuvem;
- aplicativo móvel nativo;
- extensão de navegador.

Esses itens poderão ser avaliados depois do MVP, sempre com confirmação explícita antes de qualquer ação externa.

## 3. Perfil e critérios de aderência

O cadastro do perfil deverá conter:

- cargos desejados e cargos alternativos;
- senioridade;
- competências obrigatórias, desejáveis e competências que o usuário quer desenvolver;
- tecnologias ou tipos de atividade a evitar;
- localização, raio, fuso e preferência por remoto, híbrido ou presencial;
- tipos de contrato aceitos;
- faixa salarial mínima e moeda, quando aplicável;
- idiomas e níveis;
- disponibilidade para viagens ou mudança;
- segmentos e empresas preferidos ou bloqueados;
- palavras-chave positivas e negativas;
- texto do currículo, com opção de ocultar dados pessoais antes do envio à OpenAI.

O perfil será versionado. Cada análise guardará a versão usada para que uma mudança futura não altere silenciosamente o histórico.

### 3.1 Pontuação sugerida

Antes da IA, filtros obrigatórios eliminam incompatibilidades objetivas, como país não aceito, regime presencial inviável ou contrato proibido. Para vagas restantes, a primeira versão usará pesos configuráveis:

| Dimensão | Peso inicial |
|---|---:|
| Cargo e escopo | 30 |
| Competências | 30 |
| Senioridade | 15 |
| Localização e regime | 10 |
| Idioma | 5 |
| Remuneração | 5 |
| Atualidade da vaga | 5 |

A análise deverá retornar pontuação, confiança, resumo, evidências retiradas do anúncio, lacunas e alertas. Dados sensíveis — por exemplo idade, gênero, raça, religião, deficiência ou estado civil — não poderão participar da pontuação.

## 4. Fontes e estratégia de busca

A coleta será organizada em adaptadores independentes, cada um com limite de frequência, política de repetição e registro de origem.

Ordem recomendada:

1. APIs públicas, feeds RSS e páginas oficiais de empresas;
2. páginas públicas de sistemas de recrutamento (ATS) que permitam consulta, como conectores específicos para boards suportados;
3. pesquisa web da OpenAI para descoberta de URLs e vagas difíceis de encontrar por fonte estruturada;
4. inclusão manual por URL ou formulário;
5. importação CSV em uma fase posterior do MVP.

Cada conector deverá obedecer aos termos de uso da fonte, `robots.txt` quando aplicável, limites de requisição e legislação pertinente. Sites com autenticação, CAPTCHA ou proibição de automação não serão contornados. LinkedIn, Indeed e fontes semelhantes deverão ser tratados por integração oficial, importação manual ou link fornecido pelo usuário, não por scraping não autorizado.

### 4.1 Fluxo de coleta

1. O agendador dispara uma pesquisa manual ou recorrente.
2. Cada adaptador retorna candidatos brutos com URL e metadados de origem.
3. O sistema normaliza URL, empresa, cargo, local, descrição e data.
4. A deduplicação usa URL canônica, identificador externo, hash de conteúdo e similaridade de cargo/empresa/local.
5. Filtros determinísticos removem incompatibilidades óbvias.
6. O GPT extrai campos ausentes e avalia aderência usando saída estruturada.
7. Apenas vagas novas ou materialmente alteradas aparecem na caixa de entrada.
8. O sistema registra execução, erros, custo, quantidade encontrada e quantidade aproveitada.

### 4.2 Agendamento

- execução manual a qualquer momento;
- execução automática diária, desativada por padrão até o usuário configurar fontes e orçamento;
- janela de horário configurável;
- limite por fonte e limite global por execução;
- repetição com atraso exponencial para erros transitórios;
- pausa automática do conector após erros persistentes;
- botão para cancelar uma busca em andamento.

## 5. Funil de vagas e candidaturas

### 5.1 Estados

| Grupo | Estado | Significado |
|---|---|---|
| Triagem | `ENCONTRADA` | Nova vaga ainda não revisada |
| Triagem | `EM_ANALISE` | Revisão iniciada |
| Triagem | `EM_ESPERA` | Interessante, mas sem decisão imediata |
| Triagem | `REJEITADA_PELO_USUARIO` | Descartada antes da candidatura |
| Preparação | `PRONTA_PARA_APLICAR` | Decisão de candidatura tomada |
| Processo | `APLICADA` | Candidatura enviada manualmente |
| Processo | `TRIAGEM_RH` | Contato ou conversa inicial |
| Processo | `ENTREVISTA_RH` | Entrevista com recrutamento |
| Processo | `ENTREVISTA_TECNICA` | Entrevista técnica |
| Processo | `DESAFIO` | Teste ou case em andamento |
| Processo | `ENTREVISTA_FINAL` | Fase final |
| Resultado | `OFERTA` | Oferta recebida |
| Resultado | `CONTRATADA` | Processo concluído com aprovação |
| Resultado | `REPROVADA_PELA_EMPRESA` | Empresa encerrou o processo |
| Resultado | `DESISTENCIA` | Usuário desistiu após aplicar |
| Encerramento | `EXPIRADA` | Vaga retirada ou encerrada |
| Encerramento | `DUPLICADA` | Registro unido a outra vaga |

Os nomes exibidos serão amigáveis e poderão ser ajustados sem alterar os códigos internos.

### 5.2 Regras de histórico

- Toda alteração de estado gera um evento imutável com data, estado anterior, novo estado e observação opcional.
- O usuário pode corrigir uma fase, mas a correção também fica no histórico.
- Entrevistas possuem data, horário, fuso, participantes, tipo, link, notas e lembrete local.
- Reprovações e desistências aceitam motivo estruturado e texto livre.
- Oferta registra remuneração, benefícios, prazo de resposta e decisão.
- Uma vaga pode existir sem candidatura; a candidatura começa somente em `APLICADA`.

## 6. Dashboard e métricas

O painel terá filtros por período, fonte, empresa, cargo, local, faixa de aderência e estado.

### 6.1 Indicadores principais

- vagas novas, revisadas e qualificadas;
- vagas em espera;
- candidaturas enviadas;
- processos ativos;
- entrevistas futuras;
- ofertas e contratações;
- reprovações e desistências;
- taxa de resposta: candidaturas com avanço / candidaturas enviadas;
- conversão entre cada etapa do funil;
- tempo médio até primeiro contato e tempo médio em cada fase;
- pontuação média das vagas aplicadas e das vagas que avançaram;
- desempenho por fonte;
- volume e custo estimado de uso da OpenAI.

### 6.2 Visualizações

- cartões de resumo;
- funil de candidatura;
- série temporal por semana;
- distribuição por estado e por fonte;
- lista de próximas entrevistas e prazos;
- tabela de vagas com ordenação, filtros salvos e ações rápidas;
- relatório de motivos de rejeição para melhorar o perfil e a busca.

As métricas deverão deixar clara a definição do denominador e desconsiderar duplicatas.

## 7. Arquitetura recomendada

### 7.1 Stack

| Camada | Tecnologia | Motivo |
|---|---|---|
| Interface | React + TypeScript + Vite | UI responsiva, ecossistema maduro e build estático |
| Backend local | Python + FastAPI | Integrações web, IA, validação e empacotamento simples |
| Persistência | SQLite em modo WAL | Banco local, transacional e sem serviço externo |
| ORM e migrações | SQLAlchemy + Alembic | Modelo explícito e evolução segura do banco |
| Coleta HTTP | HTTPX + parser HTML | Requisições assíncronas e adaptadores testáveis |
| Agendamento | APScheduler | Tarefas locais recorrentes e persistíveis |
| IA | SDK oficial OpenAI + Responses API | Uso de `gpt-5.6-luna`, ferramentas e saída estruturada |
| Empacotamento | PyInstaller, formato `onedir` | Mais previsível para assets e bibliotecas nativas |
| Testes | Pytest + Vitest + Playwright | Cobertura unitária, integração e ponta a ponta |

O frontend será compilado durante o build e servido pelo FastAPI. Node.js será necessário apenas para desenvolvimento, não para executar o produto empacotado.

### 7.2 Execução do aplicativo

1. `job-finder.exe` impede uma segunda instância concorrente.
2. Valida e migra o banco.
3. Inicia o servidor somente em `127.0.0.1`, nunca em todas as interfaces.
4. Seleciona uma porta livre ou reutiliza a porta configurada.
5. Abre o navegador padrão na URL local.
6. Oferece endpoint de saúde e encerramento controlado.
7. Ao fechar, conclui transações e tarefas em andamento com tempo limite seguro.

Dados, logs e backups ficarão em `%LOCALAPPDATA%\JobFinder`, separados do diretório do executável. O pacote recomendado para o MVP será uma pasta assinável contendo `job-finder.exe`; um binário realmente único (`onefile`) poderá ser avaliado depois, pois aumenta tempo de abertura e complexidade de diagnóstico.

### 7.3 Componentes

```text
Navegador
   |
   v
FastAPI local ---- API de dashboard e workflow
   |     \
   |      +---- Agendador ---- Adaptadores de fontes ---- Web
   |                         \
   |                          +---- OpenAI Responses API
   v
SQLite + arquivos locais (logs, backups e cache)
```

### 7.4 Estrutura prevista do repositório

```text
job-finder/
├── apps/
│   ├── api/                 # FastAPI, domínio, conectores e migrações
│   └── web/                 # React/TypeScript
├── packages/
│   └── schemas/             # Contratos e schemas compartilhados
├── tests/
│   ├── fixtures/            # HTML/JSON autorizado para testes de parsers
│   └── e2e/
├── scripts/                 # build, empacotamento e smoke tests
├── docs/                    # decisões de arquitetura e guias
├── .github/workflows/       # CI e build Windows
├── PLANEJAMENTO.md
├── README.md
└── LICENSE
```

## 8. Modelo de dados

Entidades mínimas:

- `profile` e `profile_version`: critérios atuais e histórico;
- `source`: tipo, configuração, frequência e estado do conector;
- `search_run`: execução, duração, contadores, erros e custo;
- `job`: vaga normalizada, conteúdo, URL canônica, origem e validade;
- `job_source`: relação entre vaga e uma ou mais fontes;
- `job_analysis`: versão do perfil/modelo/prompt, pontuação e explicação;
- `application`: dados do processo seletivo e estado atual;
- `stage_event`: histórico imutável das transições;
- `interview`: agenda e notas de entrevistas;
- `note` e `tag`: organização manual;
- `ai_usage`: tokens, latência, modelo, operação e custo estimado;
- `app_setting`: preferências não secretas;
- `backup`: metadados de cópias locais.

Descrições brutas e análises serão versionadas. Exclusões relevantes usarão confirmação e, quando viável, lixeira com retenção antes da remoção definitiva.

## 9. API local inicial

Endpoints de referência:

```text
GET    /api/health
GET    /api/profile
PUT    /api/profile
GET    /api/sources
POST   /api/sources
POST   /api/search-runs
GET    /api/search-runs/{id}
POST   /api/search-runs/{id}/cancel
GET    /api/jobs
GET    /api/jobs/{id}
PATCH  /api/jobs/{id}
POST   /api/jobs/import-url
POST   /api/jobs/{id}/reanalyze
POST   /api/applications
PATCH  /api/applications/{id}/stage
GET    /api/dashboard/summary
GET    /api/dashboard/funnel
GET    /api/dashboard/timeseries
POST   /api/backups
POST   /api/backups/{id}/restore
GET    /api/export
```

Todos os contratos deverão ser tipados e versionados. Alterações de estado serão validadas no backend, e não somente na interface.

## 10. Uso do GPT-5.6 Luna

O identificador será configurado como `gpt-5.6-luna`, usando a Responses API. A [documentação oficial do modelo](https://developers.openai.com/api/docs/models/gpt-5.6-luna) o posiciona para cargas sensíveis a custo e confirma suporte a pesquisa web, function calling e structured outputs. Em 15/08/2026, a página oficial informa preços de texto de US$ 0,20 por 1 milhão de tokens de entrada, US$ 0,02 para entrada em cache e US$ 1,20 por 1 milhão de tokens de saída; esses valores deverão ficar em configuração atualizável, pois podem mudar.

### 10.1 Responsabilidades da IA

- gerar consultas a partir do perfil;
- descobrir URLs por pesquisa web quando necessário;
- extrair campos de anúncios não estruturados;
- classificar aderência com evidências;
- resumir responsabilidades, requisitos e benefícios;
- sugerir perguntas para entrevista e pontos a investigar;
- identificar possíveis duplicatas sem decidir sozinha pela exclusão.

### 10.2 Configuração inicial

- `reasoning.effort: low` para extração e classificação em volume;
- `reasoning.effort: medium` apenas para análises detalhadas solicitadas pelo usuário;
- saída JSON validada por schema e rejeição de respostas inválidas;
- prompts versionados e testados com conjunto fixo de vagas;
- perfil estável em prefixo reutilizável para aproveitar cache quando aplicável;
- lotes pequenos, concorrência limitada e repetição apenas de falhas transitórias;
- pesquisa web usada seletivamente, com URL e fonte mantidas como evidência;
- nenhuma decisão de candidatura ou comunicação externa sem ação do usuário.

### 10.3 Custos e limites

- teto diário e mensal configurável;
- estimativa antes de uma busca grande;
- aviso em 50%, 80% e 100% do orçamento;
- pausa automática ao atingir o limite;
- medição de tokens de entrada, cache, saída, latência e custo por operação;
- análise determinística básica disponível quando a API estiver indisponível;
- opção para reanalisar somente vagas selecionadas.

### 10.4 Segurança da chave e privacidade

- solicitar a chave na primeira execução e armazená-la no Windows Credential Manager;
- nunca gravar a chave em banco, logs, Git ou frontend;
- chamar a OpenAI exclusivamente pelo backend local;
- enviar somente dados necessários, com remoção opcional de nome, telefone, e-mail, endereço e documentos;
- mostrar claramente quais dados serão enviados antes da primeira análise;
- não registrar prompts completos que contenham dados pessoais;
- permitir apagar análises e exportar todos os dados do usuário.

## 11. Segurança local e confiabilidade

- bind somente em `127.0.0.1`;
- token de sessão local e validação de origem para impedir requisições de páginas externas;
- CORS restrito e proteção contra CSRF nas mutações;
- URLs externas validadas para reduzir SSRF, com bloqueio de endereços locais e esquemas perigosos;
- sanitização de HTML antes de renderizar descrições;
- limite de tamanho, tempo e redirecionamentos nas coletas;
- dependências fixadas e verificadas por CI;
- logs rotativos sem segredos;
- migrações transacionais e backup automático antes de alteração destrutiva do schema;
- integridade do SQLite verificada na inicialização e antes de restaurar backup.

## 12. Experiência do usuário

### 12.1 Telas

1. **Onboarding:** perfil, critérios, chave OpenAI, orçamento e fontes.
2. **Caixa de entrada:** novas vagas com aderência, evidências e ações rápidas.
3. **Vagas:** tabela completa, filtros, busca, tags e visualização de duplicatas.
4. **Detalhe da vaga:** anúncio, análise, notas, origem e histórico.
5. **Pipeline:** quadro por fases com transições validadas.
6. **Agenda:** entrevistas, desafios e prazos.
7. **Dashboard:** métricas e tendências.
8. **Fontes e buscas:** conectores, agendamento, resultados e erros.
9. **Configurações:** perfil, IA, orçamento, dados, backup e exportação.

### 12.2 Acessibilidade

- navegação completa por teclado;
- foco visível e semântica apropriada;
- contraste compatível com WCAG 2.2 AA;
- gráficos acompanhados de tabela ou resumo textual;
- datas, moeda e fuso no padrão configurado pelo usuário;
- interface inicial em português do Brasil, preparada para internacionalização.

## 13. Plano de entrega

Estimativas abaixo consideram uma pessoa desenvolvedora em dedicação principal e incluem testes. Devem ser recalibradas após a definição das fontes prioritárias.

### Fase 0 — Descoberta e decisões (2–3 dias)

- validar perfil, critérios, orçamento e frequência;
- escolher três fontes iniciais com uso permitido;
- definir licença do repositório;
- criar decisões de arquitetura (ADRs);
- montar conjunto de 30–50 vagas para avaliação de qualidade.

**Saída:** escopo fechado do MVP e critérios mensuráveis de aderência.

### Fase 1 — Fundação local (4–6 dias)

- estruturar monorepo, CI e padrões de código;
- implementar FastAPI, React e SQLite;
- criar migrações e configuração de ambiente;
- implementar launcher, health check e abertura do navegador;
- produzir primeiro build Windows.

**Saída:** executável abre uma tela local e persiste configurações.

### Fase 2 — Perfil e workflow (5–7 dias)

- CRUD e versionamento do perfil;
- cadastro manual de vaga e importação por URL;
- pipeline, eventos de fase, notas e tags;
- filtros e busca local;
- exportação básica.

**Saída:** acompanhamento manual completo, ainda sem busca automática.

### Fase 3 — Coleta e deduplicação (7–10 dias)

- framework de adaptadores;
- três fontes iniciais;
- agendador, cancelamento, limites e tratamento de erros;
- normalização, canonicalização e deduplicação;
- tela de execução e diagnóstico de fontes.

**Saída:** vagas novas entram automaticamente sem duplicação evidente.

### Fase 4 — Inteligência e avaliação (5–8 dias)

- integração com Responses API e Credential Manager;
- schemas de extração e aderência;
- filtros determinísticos e pontuação híbrida;
- custos, limites, cache e fallback;
- avaliação do prompt contra o conjunto de referência.

**Saída:** cada vaga recebe análise reproduzível, explicável e mensurada.

### Fase 5 — Dashboard e agenda (4–6 dias)

- agregações do funil;
- indicadores, séries temporais e desempenho por fonte;
- entrevistas, prazos e lembretes locais;
- estados vazios, carregamento, erros e acessibilidade.

**Saída:** painel operacional com métricas consistentes.

### Fase 6 — Empacotamento e endurecimento (4–6 dias)

- build reproduzível para Windows;
- smoke test em máquina limpa;
- backup, restauração e migração;
- revisão de segurança, privacidade e logs;
- documentação de instalação e solução de problemas.

**Saída:** release candidata distribuível.

### Fase 7 — Beta e estabilização (5–10 dias corridos)

- uso real controlado;
- correção de parsers e métricas;
- calibração de pesos, prompts e limites;
- medição de precisão, custo e tempo economizado;
- release `v0.1.0`.

**Estimativa total:** 31–46 dias úteis de desenvolvimento, mais o período de observação beta. Uma versão vertical reduzida pode ficar utilizável após as Fases 1–4.

## 14. Estratégia de testes

### 14.1 Desenvolvimento orientado a testes (TDD)

O projeto adotará **TDD como prática obrigatória** para comportamentos novos, correções de defeitos e regras de negócio. Antes de implementar uma funcionalidade, será criado ou ajustado um teste automatizado que descreva o resultado esperado.

O ciclo de trabalho será sempre:

1. **Red:** escrever um teste pequeno e específico que falha pelo motivo esperado;
2. **Green:** implementar o mínimo necessário para fazê-lo passar;
3. **Refactor:** melhorar o design mantendo todos os testes verdes.

Regras de execução:

- cada história do backlog deverá explicitar cenários verificáveis antes do desenvolvimento;
- regras de pontuação, deduplicação, transição de fases, agregação de métricas e limites de custo exigem testes unitários antes da implementação;
- endpoints, adaptadores de fontes e contratos de IA exigem testes de integração ou de contrato antes de serem considerados concluídos;
- correções de bugs começam por um teste de regressão que reproduza a falha;
- protótipos exploratórios podem ser descartáveis, mas qualquer código promovido ao produto deverá ser refeito seguindo TDD;
- o pipeline de CI bloqueará mudanças quando a suíte relevante falhar;
- revisões verificarão a qualidade dos cenários e o comportamento coberto, não apenas o percentual de cobertura.

### 14.2 Testes automatizados

- unitários: normalização, filtros, pontuação, transições e métricas;
- contratos: respostas dos adaptadores e schemas da IA;
- parsers: fixtures HTML/JSON versionadas, sem depender da internet na CI;
- integração: SQLite temporário e OpenAI simulada;
- ponta a ponta: onboarding, triagem, candidatura, entrevista e dashboard;
- empacotamento: inicialização, migração, porta ocupada, navegador e encerramento.

### 14.3 Avaliação da IA

- conjunto de vagas rotuladas manualmente;
- métricas de extração por campo;
- correlação e erro da pontuação;
- taxa de falsos negativos entre vagas qualificadas;
- presença de evidências para cada conclusão;
- consistência em execuções repetidas;
- custo e latência por vaga;
- comparação de `low` e `medium` em tarefas representativas.

Mudanças de prompt ou modelo somente serão promovidas quando não houver regressão relevante no conjunto de avaliação.

## 15. Critérios de aceite do MVP

O MVP estará pronto quando:

- `job-finder.exe` iniciar em uma instalação limpa do Windows e abrir a interface no navegador;
- os dados sobreviverem a reinicializações e houver backup/restauração testados;
- o usuário puder criar o perfil e configurar critérios sem editar arquivos;
- pelo menos três fontes aprovadas funcionarem por adaptadores independentes;
- buscas manuais e agendadas puderem ser iniciadas, canceladas e auditadas;
- duplicatas forem identificadas e unidas sem perda do histórico de origem;
- vagas tiverem pontuação, explicação, evidências e versão da análise;
- todos os estados do funil e entrevistas puderem ser registrados;
- o dashboard refletir corretamente os eventos do pipeline;
- orçamento e uso da OpenAI estiverem visíveis e limitáveis;
- nenhuma chave ou dado pessoal sensível aparecer em logs ou no repositório;
- testes críticos e smoke test do pacote Windows estiverem aprovados;
- cada comportamento novo e cada correção relevante tiverem sido desenvolvidos com ciclo TDD e a suíte correspondente estiver verde;
- a documentação explicar instalação, configuração, backup e solução de problemas.

## 16. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Mudança frequente no HTML das fontes | Conectores quebrados | Adaptadores isolados, fixtures e monitoramento de falhas |
| Restrição de termos ou bloqueio anti-bot | Fonte indisponível | Priorizar APIs/feeds, limitar frequência e oferecer importação manual |
| Classificação incorreta da IA | Boas vagas descartadas | Filtros explicáveis, confiança, caixa de revisão e evals |
| Custos inesperados | Orçamento excedido | Tetos, alertas, cache, lotes e medição por operação |
| Vazamento de dados pessoais | Dano de privacidade | Redação, minimização, keyring e logs sem conteúdo sensível |
| Banco local corrompido | Perda de histórico | WAL, backups automáticos, verificação e restauração testada |
| Executável bloqueado pelo Windows | Má experiência | build reproduzível, assinatura futura e documentação clara |
| Métricas enganosas | Decisões ruins | definições versionadas, testes de agregação e denominadores visíveis |

## 17. Backlog posterior ao MVP

- geração assistida de currículo e carta, sempre com revisão humana;
- comparação entre versões de currículo e taxa de avanço;
- integração oficial com calendário e e-mail;
- notificações no sistema operacional;
- plugin/extensão para capturar uma vaga aberta no navegador;
- sincronização criptografada opcional;
- múltiplos perfis e estratégias de busca;
- instalador, atualização automática e assinatura de código;
- suporte a macOS e Linux;
- sugestões de preparação de entrevista baseadas na vaga;
- relatórios mensais exportáveis em PDF/CSV.

## 18. Decisões necessárias antes da implementação

1. Perfil profissional inicial e currículo que servirão para os testes.
2. Países, idiomas e regime de trabalho prioritários.
3. Três fontes iniciais autorizadas.
4. Frequência desejada e orçamento mensal máximo da OpenAI.
5. Política de retenção para vagas rejeitadas e logs.
6. Licença do repositório público.
7. Preferência por pacote portátil ou instalador na primeira release.

## 19. Próximo marco recomendado

O primeiro marco deve ser uma fatia vertical: cadastrar perfil, importar uma vaga por URL, analisar com `gpt-5.6-luna`, mover a vaga até `APLICADA` e visualizar a alteração no dashboard. Essa fatia valida cedo a arquitetura, a experiência e o custo antes de investir em vários conectores.
