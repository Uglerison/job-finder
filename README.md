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
