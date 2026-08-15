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
