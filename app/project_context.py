"""Lê os projetos reais da Voltbras (pastas irmãs) para dar contexto ao LLM."""

from __future__ import annotations

from pathlib import Path

_EXCLUDE = {"meeting-assistant", "node_modules"}


def _project_dirs(voltbras_dir: str) -> list[Path]:
    root = Path(voltbras_dir)
    if not root.is_dir():
        return []
    return sorted(
        entry
        for entry in root.iterdir()
        if entry.is_dir() and entry.name not in _EXCLUDE and not entry.name.startswith(".")
    )


def list_project_names(voltbras_dir: str) -> list[str]:
    return [d.name for d in _project_dirs(voltbras_dir)]


def build_context(voltbras_dir: str) -> str:
    blocks = [_describe_project(entry) for entry in _project_dirs(voltbras_dir)]
    return "\n\n".join(b for b in blocks if b)


def _describe_project(project_dir: Path) -> str:
    lines = [f"### Projeto: {project_dir.name}"]

    readme = _find_readme(project_dir)
    if readme is not None:
        excerpt = "\n".join(readme.read_text(encoding="utf-8", errors="ignore").splitlines()[:40])
        lines.append(excerpt.strip())

    modules = _list_modules(project_dir)
    if modules:
        lines.append("Módulos/serviços identificados: " + ", ".join(modules))

    return "\n".join(lines)


def _find_readme(project_dir: Path) -> Path | None:
    for name in ("README.md", "readme.md", "Readme.md"):
        candidate = project_dir / name
        if candidate.is_file():
            return candidate
    return None


_GENERIC_DIR_NAMES = {
    # pastas de organização de código / infraestrutura comuns a qualquer projeto,
    # não são "módulos de negócio" e só adicionariam ruído ao contexto do LLM
    "src", "node_modules", "dist", "build", "docs", "doc", "scripts", "bin", "k8s",
    "test", "tests", "__tests__", "__mocks__", "ios", "android", "assets", "public",
    "static", "deployments", "patches", "keys", "config", "cypress", "nginx", "ai_docs",
    "gitlab-ci", "coverage", "fixtures", "generated", "adapters", "application",
    "constants", "contexts", "domain", "drivers", "entry-points", "global-shared-memory",
    "logger", "main", "modules", "packages", "shared", "tools", "types", "utils",
    "components", "hooks", "lib", "services", "theme", "translation", "layouts",
    "navigators", "views", "cards", "atomic-components", "new-components", "react",
    "rest", "client", "chakra", "graphql", "value-objects", "commands", "pubsub",
    "spawner",
}


def _list_modules(project_dir: Path) -> list[str]:
    modules: set[str] = set()

    src = project_dir / "src"
    if src.is_dir():
        modules.update(
            child.name
            for child in src.iterdir()
            if child.is_dir() and not child.name.startswith(".") and child.name not in _GENERIC_DIR_NAMES
        )

    # integrações/negócio às vezes ficam na raiz do projeto (ex.: chargepoint-simulator/edenred)
    modules.update(
        child.name
        for child in project_dir.iterdir()
        if child.is_dir() and not child.name.startswith(".") and child.name not in _GENERIC_DIR_NAMES
    )

    for jsonnet in project_dir.glob("deployment-*.jsonnet"):
        modules.add(jsonnet.stem.replace("deployment-", ""))

    return sorted(modules)
