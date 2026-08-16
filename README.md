# Job Finder

Aplicação local para descobrir vagas compatíveis com um perfil profissional e acompanhar candidaturas, entrevistas e resultados.

O planejamento está em [PLANEJAMENTO.md](./PLANEJAMENTO.md) e o acompanhamento da implementação em [TASKS.md](./TASKS.md).

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

## Busca e fontes (E4)

A área **Fontes e execuções** na interface lista três conectores públicos
iniciais — Remote OK, Arbeitnow e Jobicy — sem credenciais. O agendamento fica
desligado por padrão; a busca manual pode ser iniciada escolhendo cargo,
localização e fonte.

Os contratos HTTP locais principais são:

- `GET /api/sources` e `PUT /api/sources/{source_key}` para configuração e limites;
- `POST /api/sources/{source_key}/test` para testar uma fonte sem persistir vagas;
- `POST /api/search-runs` para iniciar uma execução (`wait=true` é útil em testes);
- `GET /api/search-runs` e `POST /api/search-runs/{id}/cancel` para acompanhar/cancelar;
- `GET /api/duplicates` e `POST /api/duplicates/{id}/confirm|dismiss` para revisão;
- `POST /api/scheduler/tick` para disparar fontes agendadas já vencidas.

Cada execução registra duração, contadores, cursor, falhas e cancelamento. A
deduplicação exata usa URL canônica, identidade externa e hash de conteúdo; uma
semelhança de cargo/empresa/local fica pendente até confirmação explícita.

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

O painel local consulta `GET /api/dashboard/summary`, aceitando `from`, `to`,
`timezone` e `source_key`. Ele exibe cartões, funil com denominadores, séries
semanais, desempenho por fonte e contadores de agenda. Vagas removidas não
entram nos denominadores; quando uma vaga possui várias origens, a primeira
origem registrada recebe o crédito de conversão.

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
