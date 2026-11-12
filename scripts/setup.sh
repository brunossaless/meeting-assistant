#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Instalando dependências via Homebrew (whisper-cpp, ollama, python@3.12)"
brew install whisper-cpp ollama python@3.12

if ! brew list --cask blackhole-2ch >/dev/null 2>&1; then
  echo
  echo "==> BlackHole 2ch ainda não está instalado."
  echo "    O instalador dele pede senha de administrador, então precisa rodar você mesmo:"
  echo
  echo "      brew install --cask blackhole-2ch"
  echo
  read -r -p "Pressione ENTER depois de instalar o BlackHole para continuar o setup..." _
fi

MODEL_PATH="data/models/ggml-medium.bin"
mkdir -p data/models
if [ ! -f "$MODEL_PATH" ]; then
  echo "==> Baixando modelo whisper (ggml-medium, ~1.5GB)"
  curl -L -o "$MODEL_PATH" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin"
fi

echo "==> Criando ambiente virtual Python 3.12"
PY312="$(brew --prefix python@3.12)/bin/python3.12"
"$PY312" -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Criado .env a partir do .env.example"
fi

echo "==> Iniciando o serviço do Ollama"
brew services start ollama
sleep 2
echo "==> Baixando o modelo llama3.1:8b (~4.7GB, pode demorar)"
ollama pull llama3.1:8b

echo
echo "==> Setup automatizado concluído."
echo "    Falta só o passo manual de roteamento de áudio (uma vez só):"
open -a "Audio MIDI Setup" || true
cat <<'EOF'

   No app "Audio MIDI Setup" que acabou de abrir:
   1. Clique no "+" no canto inferior esquerdo -> "Create Multi-Output Device"
   2. Marque sua saída normal (ex: alto-falantes/fone) E "BlackHole 2ch"
   3. Vá em Ajustes do Sistema > Som > Saída e selecione esse Multi-Output Device

   Depois disso, rode ./scripts/run.sh para iniciar o assistente.
EOF
