"""Resumo estruturado da reunião via Ollama (LLM local)."""

from __future__ import annotations

import json
import os

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

SYSTEM_PROMPT = (
    "Você é um assistente que analisa transcrições de reuniões de trabalho em português "
    "e devolve APENAS um JSON válido com os campos: summary (string, resumo em 3 a 6 frases), "
    "topics (lista de strings com os principais assuntos discutidos), project (string ou null, "
    "o nome do projeto da empresa mais provável dentre os projetos conhecidos listados abaixo, "
    "ou null se não for possível identificar ou se a reunião não for sobre nenhum desses projetos "
    "— por exemplo, se for uma reunião sobre o desenvolvimento deste próprio assistente de "
    "reuniões, use null, pois ele não é um dos projetos da empresa listados), modules (lista de "
    "strings com módulos/serviços citados, de preferência entre os módulos conhecidos), "
    "participants_mentioned (lista de nomes de pessoas citadas na conversa, incluindo quem fala "
    "no microfone quando identificável), action_items (lista de strings com próximos passos "
    "combinados, vazio se nenhum), closing_summary (string, um resumo de fechamento em 2 a 4 "
    "frases, para ser exibido ao final da transcrição, dizendo especificamente quais "
    "serviços/módulos e quais contextos de projeto da empresa foram falados na reunião e qual "
    "foi o ponto principal discutido)."
)


def _build_schema(known_projects: list[str]) -> dict:
    project_field = (
        {"type": ["string", "null"], "enum": [*known_projects, None]}
        if known_projects
        else {"type": ["string", "null"]}
    )
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "topics": {"type": "array", "items": {"type": "string"}},
            "project": project_field,
            "modules": {"type": "array", "items": {"type": "string"}},
            "participants_mentioned": {"type": "array", "items": {"type": "string"}},
            "action_items": {"type": "array", "items": {"type": "string"}},
            "closing_summary": {"type": "string"},
        },
        "required": [
            "summary",
            "topics",
            "project",
            "modules",
            "participants_mentioned",
            "action_items",
            "closing_summary",
        ],
    }


def analyze_transcript(transcript_text: str, project_context: str, known_projects: list[str]) -> dict:
    user_prompt = (
        f"Projetos conhecidos da empresa (escolha o campo project somente entre estes nomes "
        f"exatos, ou null): {', '.join(known_projects) if known_projects else '(nenhum)'}\n\n"
        f"Contexto de cada projeto:\n{project_context}\n\n"
        f"Transcrição da reunião:\n{transcript_text}\n\n"
        "Analise e responda somente com o JSON pedido."
    )
    response = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "format": _build_schema(known_projects),
            "stream": False,
        },
        timeout=300,
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return json.loads(content)
