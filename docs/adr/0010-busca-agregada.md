# ADR 0010 — Busca agregada com fallback seletivo

## Status

Aceita em 16/08/2026.

## Contexto

A busca anterior exigia selecionar Remote OK, Arbeitnow ou Jobicy. Isso expunha
detalhes de integração na experiência principal e limitava a cobertura de
vagas brasileiras. As fontes atuais, o cliente HTTP resiliente, os runs
persistidos e a deduplicação existente continuam funcionais e precisam seguir
compatíveis durante a migração.

## Decisão

- `SearchAggregator` recebe uma lista de `JobProvider` e consulta em ordem:
  JSearch, Adzuna, Jooble e, somente se necessário, fontes legadas habilitadas.
- Cada provider converte seu payload para `SourceCandidate`; URL, texto, datas,
  modalidade, salário e origem pública são normalizados antes do ranking.
- O agregador para quando atinge o mínimo configurado, mas retorna resultado
  parcial e diagnósticos seguros quando uma fonte falha.
- Deduplicação combina URL exata e similaridade conservadora de cargo, empresa
  e local. O ranking é determinístico e deixa o perfil como extensão futura.
- Cache TTL fica em memória por processo para evitar infraestrutura adicional.
- Credenciais dos providers podem vir de variáveis `JOB_FINDER_*` ou da tabela
  `provider_secrets`, cifrada com o mesmo cofre SQLite da OpenAI. Chaves só são
  desbloqueadas em memória e nunca entram no payload do frontend.
- A API pública da aplicação é apenas `POST /api/search`; a UI não oferece
  seletor técnico. O painel histórico/configurações legado permanece acessível
  para compatibilidade operacional.
- Simulação de entrevista não pertence a este produto. Cada cartão aponta para
  `https://sepreparai.com.br/` em nova aba, sem enviar dados na URL.

## Consequências

O primeiro uso com credenciais reais depende das cotas e dos termos dos
providers. Sem chaves, fontes públicas legadas ainda podem complementar a
busca. O cache é perdido no reinício do processo, o que mantém o MVP simples e
não persiste dados pessoais de consulta.
