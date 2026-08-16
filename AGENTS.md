# Convenções do projeto

## Gerenciador de pacotes JavaScript

Use exclusivamente **pnpm** neste repositório.

- Nunca execute `npm`, `npx` ou Yarn para instalar, executar scripts ou gerar pacotes.
- Para ferramentas temporárias, use `pnpm dlx`.
- Execute comandos do frontend pelo workspace, por exemplo `pnpm --filter job-finder-web test`.
- Mantenha `pnpm-lock.yaml` versionado e não adicione `package-lock.json`.
