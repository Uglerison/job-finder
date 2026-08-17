# Job Finder

Aplicação local para descobrir vagas compatíveis com um perfil profissional e acompanhar candidaturas, entrevistas e resultados.

O planejamento está em [PLANEJAMENTO.md](./PLANEJAMENTO.md) e o acompanhamento da implementação em [TASKS.md](./TASKS.md).

## Instalação rápida (Windows)

### Usar o executável

O pacote de usuário não exige Python, Node.js ou pnpm instalados:

1. Copie `JobFinder.exe` para uma pasta local (ou extraia o arquivo recebido).
2. Execute `JobFinder.exe` com duplo clique ou, no PowerShell, use `.\JobFinder.exe`.
3. O navegador abrirá uma URL `http://127.0.0.1:<porta>`.
4. Para encerrar, volte ao console do aplicativo e pressione `Ctrl+C`.

Quando o build é feito neste checkout, o executável fica diretamente na raiz:

```text
C:\Users\ugleb\dev\job-finder\JobFinder.exe
```

O arquivo `release-manifest.json` ao lado do executável registra a versão e o
SHA-256. O executável é autocontido e pode ser movido; mantenha o manifesto ao
lado quando quiser conferir a integridade da cópia. O modo single-file extrai
os recursos internamente ao iniciar.

### Gerar o executável a partir do código

Na raiz do projeto, em um Windows com Python 3.10+:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip install -r packaging\requirements-build.txt
.\scripts\build_windows.ps1
.\JobFinder.exe
```

O build do frontend é executado pelo script com pnpm. Para validar o arquivo
gerado sem abrir o navegador:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_packaged.py .\JobFinder.exe
```

## Desenvolvimento do backend

No Windows, com Python 3.10 ou superior:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

## Desenvolvimento do frontend

Use somente pnpm:

```powershell
pnpm install
pnpm --filter job-finder-web test
pnpm --filter job-finder-web build
```

## Abrir a aplicação local

Após instalar as dependências e compilar a interface, inicie a aplicação. Ela
abre o navegador na URL local e escuta apenas em `127.0.0.1`:

```powershell
pnpm --filter job-finder-web build
.\.venv\Scripts\python.exe scripts\run_local.py
```

Para cadastrar a chave, abra a seção **IA** da navegação. A chave OpenAI é
gravada apenas como ciphertext no SQLite local; crie e guarde uma senha de
cofre com pelo menos 12 caracteres. Essa senha não é persistida e será pedida
para desbloquear a chave depois que o aplicativo for reiniciado.

## Smoke test local

Com o frontend compilado, valide a fundação completa no Windows:

```powershell
pnpm --filter job-finder-web build
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

## Release Windows (E7)

O pacote de distribuição agora é um único `JobFinder.exe` na raiz do checkout.
O builder é fixado em `packaging/requirements-build.txt`; em uma máquina
Windows limpa, instale as dependências e execute:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip install -r packaging\requirements-build.txt
.\scripts\build_windows.ps1
.\.venv\Scripts\python.exe scripts\smoke_packaged.py .\JobFinder.exe
```

Para repetir os budgets locais de abertura, listagem e painel:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_local.py
```

O script compila o frontend com pnpm, inclui as migrações e o `alembic.ini`,
gera `release-manifest.json` com SHA-256 e não copia `.env` nem o banco local.
O executável escuta somente em `127.0.0.1`; dados, logs e backups ficam em
`%LOCALAPPDATA%\JobFinder`.

### Backup e restauração local

Backups são snapshots consistentes do SQLite, com manifesto, checksum SHA-256,
verificação `PRAGMA integrity_check` e retenção dos cinco arquivos mais novos:

```powershell
.\.venv\Scripts\python.exe scripts\backup.py create
.\.venv\Scripts\python.exe scripts\backup.py validate <caminho-do-zip>
.\.venv\Scripts\python.exe scripts\backup.py restore <caminho-do-zip>
```

Antes de uma migração de banco existente, o backend cria automaticamente um
backup quando a revisão instalada está atrás da revisão do código. A
restauração preserva o arquivo atual como `job-finder.db.pre-restore-*`; feche
o Job Finder antes de restaurar para liberar conexões SQLite no Windows.

## Primeiro uso e configuração

1. Abra **Perfil** e salve cargos, competências, localização, regime e filtros.
2. Em **IA**, crie a senha do cofre e informe a chave OpenAI. A senha não é
   persistida; a chave é armazenada somente cifrada no SQLite local.
3. Em **Busca**, informe cargo e localização e execute a busca unificada.
4. Se usar JSearch, configure a chave RapidAPI no cofre local ou em
   `JOB_FINDER_JSEARCH_API_KEY`. O endpoint atual é `/search-v2`.
5. Abra o detalhe da vaga para analisar, descartar, manter em espera ou usar
   **Marcar como aplicada**.

O aplicativo não envia candidaturas automaticamente. O botão de preparação de
entrevista direciona para o produto externo [Se Prepara AI](https://sepreparai.com.br/).

## Solução de problemas

- **O navegador não abriu:** copie a URL exibida no console e cole no navegador.
- **A porta já está em uso:** encerre outra instância do Job Finder e execute
  novamente; o iniciador normalmente reutiliza a instância saudável.
- **A busca não encontrou vagas:** abra **Ver detalhes da busca e do log**. A
  tela diferencia provider sem chave, limite atingido, falha de rede e busca sem
  correspondência.
- **JSearch retorna erro 404:** confirme que a chave RapidAPI está ativa e que
  a configuração usa a rota `/search-v2`; chaves antigas não são exibidas na
  interface.
- **O Windows bloqueou o executável:** confirme a origem do arquivo, abra as
  propriedades e marque **Desbloquear** quando essa opção estiver disponível.
- **Precisa restaurar dados:** feche o aplicativo, valide o ZIP e só então use
  `scripts\backup.py restore`. O banco anterior permanece como cópia
  `job-finder.db.pre-restore-*`.

Logs locais ficam em `%LOCALAPPDATA%\JobFinder\logs\job-finder.log`. Chaves,
senhas e dados pessoais detectáveis são redigidos antes de serem gravados.

## Busca e fontes (E4)

A área **Busca unificada** consulta providers em sequência sem pedir que o
usuário escolha uma API. Remote OK, Arbeitnow e Jobicy continuam listados no
painel técnico como fallback legado, sem credenciais; o agendamento fica
desligado por padrão.

Os contratos HTTP locais principais são:

- `GET /api/sources` e `PUT /api/sources/{source_key}` para configuração e limites;
- `POST /api/sources/{source_key}/test` para testar uma fonte sem persistir vagas;
- `POST /api/search-runs` para execuções legadas auditáveis (`wait=true` é útil em testes);
- `GET /api/search-runs` e `POST /api/search-runs/{id}/cancel` para acompanhar/cancelar;
- `GET /api/duplicates` e `POST /api/duplicates/{id}/confirm|dismiss` para revisão;
- `POST /api/scheduler/tick` para disparar fontes agendadas já vencidas.

Cada execução registra duração, contadores, cursor, falhas e cancelamento. A
deduplicação exata usa URL canônica, identidade externa e hash de conteúdo; uma
semelhança de cargo/empresa/local fica pendente até confirmação explícita.

### Agendas da busca unificada

Na seção **Agendador local**, salve uma consulta, localização, modalidade e
frequência. A agenda nasce pausada; ao ativá-la, o worker do backend executa
somente enquanto o Job Finder estiver aberto. Cada execução e cada vaga ficam
persistidas no SQLite, inclusive o resultado da deduplicação, e podem ser
consultados depois em:

- `POST|GET /api/scheduled-searches` para criar/listar agendas;
- `PUT|DELETE /api/scheduled-searches/{id}` para editar, pausar ou remover uma agenda;
- `POST /api/scheduled-searches/tick` para disparar manualmente as agendas vencidas;
- `GET /api/scheduled-searches/{id}/runs` e `/jobs` para consultar histórico e vagas encontradas.

Remover uma agenda não remove vagas, candidaturas, análises ou eventos já
coletados. Redescobertas atualizam origens e versões do conteúdo, sem rebaixar
uma candidatura de `applied`, entrevista ou resultado terminal.

Para registrar uma confirmação humana de envio, use o botão **Marcar como
aplicada** na caixa, no detalhe ou no cartão de busca. O backend cria a
candidatura e o evento inicial/transição em uma única transação; repetição é
idempotente e não envia candidatura automaticamente a nenhum site.

## Chave OpenAI local

O modelo preparado é `gpt-5.6-luna`. A configuração local não inicia análises
automaticamente: a análise é sempre uma ação explícita sobre uma vaga. A senha
do cofre e a chave nunca são devolvidas pela API, mostradas novamente na
interface ou gravadas nos logs.

O botão **Testar conexão** faz uma chamada mínima e sem dados de perfil ou
vagas pelo backend local. O cliente usa a [Responses API](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6),
`gpt-5.6-luna`, `reasoning.effort: low` e `store: false`; o navegador nunca
chama a OpenAI diretamente.

Com o perfil salvo e o cofre desbloqueado, a API local também permite analisar
uma vaga individualmente:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:<porta-exibida>/api/jobs/1/analysis `
  -ContentType 'application/json' -Body '{"mode":"batch"}'
```

Ela envia somente o perfil e o anúncio após a redação de dados pessoais
detectáveis, pede JSON estrito à Responses API e valida cargo, requisitos,
local, regime, salário e evidências antes de responder. Cada chamada explícita
cria uma versão imutável, associada ao perfil, conteúdo, modelo e prompt usados;
consulte o histórico com `GET /api/jobs/1/analyses`.

A resposta também inclui `fit`: filtros obrigatórios têm precedência e zeram a
nota quando uma restrição é incompatível. Para vagas aceitas, os pesos
reconhecidos do perfil calculam a parte determinística e o contexto do modelo
tem influência fixa de 20%; idade, gênero, raça, religião, deficiência,
estado civil, nacionalidade e rótulos desconhecidos não participam do score.

Em `explanation`, cada citação é conferida localmente no título, metadados ou
texto visível da vaga. Somente itens com uma citação exata existente ficam como
`supported`; resumos, pontos fortes, lacunas, alertas e alegações sem essa
prova aparecem como `needs_review` para revisão humana.

### Operação E5: custo, descoberta e reanálise

Os contadores locais ficam disponíveis em `GET /api/ai/usage`. Quando quiser
definir um teto mensal, configure antes de iniciar o backend:

```powershell
$env:JOB_FINDER_OPENAI_MONTHLY_BUDGET_USD = "5"
```

Os preços usados na estimativa também são configuráveis por
`JOB_FINDER_OPENAI_INPUT_PRICE_USD_PER_MILLION`,
`JOB_FINDER_OPENAI_CACHED_INPUT_PRICE_USD_PER_MILLION` e
`JOB_FINDER_OPENAI_OUTPUT_PRICE_USD_PER_MILLION`. No teto, apenas novas chamadas
à IA são interrompidas; busca, triagem e pipeline locais continuam funcionando.

`POST /api/ai/discovery` recebe `source_keys`, `query`, `location` e `limit` e
executa somente as fontes públicas selecionadas. Cada execução continua
registrada em `search_runs`, com URL e evidência para revisão humana; o endpoint
não envia candidaturas. Se a OpenAI estiver indisponível ou o orçamento acabar,
`POST /api/jobs/{id}/analysis` salva uma triagem determinística identificada
como `fallback`, sem inventar fatos. Na interface, use as caixas de seleção da
caixa de entrada para confirmar e reanalisar somente as vagas escolhidas.

## Dashboard E6

### Busca unificada E4.1

`POST /api/search` recebe `query`, `location`, `work_model`, `page` e `limit` e
retorna vagas normalizadas em uma única resposta. O backend tenta JSearch,
Adzuna e Jooble de forma sequencial, acionando fontes legadas somente quando
faltam resultados. Falhas individuais são resumidas em `provider_runs` sem
expor chaves ou respostas brutas. A interface não solicita uma fonte técnica;
cada cartão mantém apenas a origem pública disponível e oferece o link externo
para [Se Prepara AI](https://sepreparai.com.br/) para treino de entrevista.
Na JSearch via RapidAPI, a rota atual é `/search-v2`; a rota aposentada `/search`
é migrada automaticamente pelo adaptador.

Quando não há vagas, a resposta também informa o motivo: filtros sem
correspondência, provider ainda não configurado, limite de consultas, falha de
conexão ou resultado parcial. Abra **Ver detalhes da busca e do log** para ver
o status, quantidade e duração de cada provider, sem expor credenciais.

As credenciais podem ser definidas como variáveis `JOB_FINDER_*` ou salvas no
SQLite criptografado por senha local através de `/api/search/providers`. A
senha nunca é persistida. Depois de reiniciar o app, desbloqueie cada provider
com `POST /api/search/providers/{provider}/unlock` ou pelo botão **Desbloquear**
que aparece ao lado de um provider bloqueado na seção de credenciais. A busca
continua sem expor a chave no navegador.

Se o navegador informar que não conseguiu conectar ao serviço local, feche a
aba antiga e execute novamente o comando de inicialização. O iniciador valida
`/api/health` antes de reutilizar uma instância registrada e recupera um lock
que aponta para um servidor interrompido. Falhas internas inesperadas da busca
são registradas em `%LOCALAPPDATA%\\JobFinder\\logs\\job-finder.log` e voltam à
interface com uma mensagem segura.

O painel local consulta `GET /api/dashboard/summary`, aceitando `from`, `to`,
`timezone` e `source_key`. Ele exibe cartões, funil com denominadores, séries
semanais, desempenho por fonte e contadores de agenda. Vagas removidas não
entram nos denominadores; quando uma vaga possui várias origens, a primeira
origem registrada recebe o crédito de conversão.

Filtros recorrentes podem ser salvos e aplicados pela caixa de entrada em
`/api/saved-filters`; somente campos de busca aprovados são persistidos.

## Qualidade de código

No backend, execute as verificações com o ambiente virtual do projeto:

```powershell
.\.venv\Scripts\ruff.exe check apps/api/src tests scripts
.\.venv\Scripts\ruff.exe format --check apps/api/src tests scripts
.\.venv\Scripts\mypy.exe apps/api/src
```

No frontend, use `pnpm`:

```powershell
pnpm --filter job-finder-web format:check
pnpm --filter job-finder-web lint
pnpm --filter job-finder-web test
pnpm --filter job-finder-web build
```
