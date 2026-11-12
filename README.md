# Assistente de Reuniões

Software local (100% offline) que escuta suas reuniões — o que os outros participantes falam
(áudio de sistema) e o que você fala (microfone) — transcreve tudo, e usa um LLM local para gerar
um resumo estruturado: assunto, projeto/módulo da Voltbras identificado, pessoas citadas e
próximos passos combinados.

## Como funciona

1. Fica escutando o áudio de sistema em segundo plano. Quando detecta som sustentado (~5s), começa
   a gravar sozinho (mic + sistema); quando detecta silêncio sustentado (~30s), para e processa.
2. Também dá pra controlar manualmente pelo dashboard (`Iniciar reunião` / `Parar reunião`).
3. Ao parar, transcreve os dois áudios com `whisper.cpp`, intercala por timestamp (tagueando
   "Bruno Sales" no microfone e "Outros participantes" no áudio de sistema), e manda pro `Ollama`
   (LLM local) com o contexto dos projetos reais da empresa (`api`, `app-expo`,
   `chargepoint-simulator`, `dashboard`, lidos da pasta irmã `/Users/sls/voltbras`) pra casar o
   assunto com projeto/módulo.
4. Tudo fica salvo em `data/meetings.db` (SQLite) e visível no dashboard local.

## Limitações (v1)

- Identificação de fala é binária: "Bruno Sales" (microfone) vs "Outros participantes" (sistema).
  Não separa individualmente vozes de terceiros — nomes de outras pessoas citadas são extraídos do
  texto pelo LLM, não por reconhecimento de voz.
- Transcrição roda em lote logo após a reunião parar, não palavra-por-palavra ao vivo.
- Resumo usa um modelo local (`llama3.1:8b`), mais simples que Claude/GPT, mas sem custo e 100%
  privado.

## Setup (uma vez só)

```bash
./scripts/setup.sh
```

Isso instala `whisper-cpp`, `ollama`, `python@3.12` via Homebrew, baixa o modelo de transcrição e
o modelo do Ollama, cria o `.venv` e o `.env`. Se o `BlackHole 2ch` ainda não estiver instalado,
o script pausa e pede pra você rodar `brew install --cask blackhole-2ch` (o instalador dele pede
senha de admin, por isso não dá pra automatizar).

Depois, é preciso configurar o roteamento de áudio (uma vez só, é GUI do macOS):

1. Abra "Audio MIDI Setup" (o setup.sh já tenta abrir pra você)
2. Clique no "+" → "Create Multi-Output Device"
3. Marque sua saída normal (alto-falantes/fone) **e** "BlackHole 2ch"
4. Em Ajustes do Sistema → Som → Saída, selecione esse Multi-Output Device
5. Conceda permissão de microfone ao Terminal quando o macOS pedir

## Rodando

```bash
./scripts/run.sh
```

Abre em `http://localhost:8756`. Deixe rodando durante o dia pra ele ficar escutando as reuniões
sozinho, ou use os botões do dashboard pra controlar manualmente.

## Configuração

Ajustes em `.env` (copiado de `.env.example` no setup): modelo do whisper, modelo do Ollama, nome
de quem fala no microfone, limiares do modo automático, etc.
