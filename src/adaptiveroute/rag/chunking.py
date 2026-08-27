from __future__ import annotations

from pathlib import Path


SUPPORTED_RAG_EXTENSIONS = {".md", ".txt", ".tex", ".py", ".json", ".yaml", ".yml", ".toml"}


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_supported_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in SUPPORTED_RAG_EXTENSIONS:
            files.append(path)
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in SUPPORTED_RAG_EXTENSIONS:
                    if _should_skip(child):
                        continue
                    files.append(child)
    return files


def chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 160) -> list[str]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size.")

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        if end < len(normalized):
            newline = normalized.rfind("\n", start, end)
            if newline > start + chunk_size // 2:
                end = newline
            else:
                space = normalized.rfind(" ", start, end)
                if space > start + chunk_size // 2:
                    end = space
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def _should_skip(path: Path) -> bool:
    skip_parts = {".git", ".venv", "node_modules", "dist", "__pycache__", ".pytest_cache"}
    return any(part in skip_parts for part in path.parts)
