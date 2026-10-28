#!/usr/bin/env python3
"""Instala a seleção nativa de indicadores do Codex CLI."""

import argparse
import datetime
import os
from pathlib import Path
import re
import tempfile
import tomllib


INDICADORES = (
    "model-with-reasoning",
    "project-name",
    "git-branch",
    "context-remaining",
    "five-hour-limit",
    "weekly-limit",
)
LINHA = "status_line = [" + ", ".join(f'"{item}"' for item in INDICADORES) + "]"
SECAO = re.compile(r"(?m)^\s*\[([^\]\n]+)\]\s*(?:#.*)?$")
ATRIBUTO = re.compile(r"(?m)^[ \t]*status_line[ \t]*=[^\n]*(?:\n|$)")


def atualizar(conteudo: str) -> str:
    """Atualiza apenas o atributo tui.status_line, sem reformatar as demais opções."""
    tomllib.loads(conteudo)
    secoes = list(SECAO.finditer(conteudo))
    tui = next((i for i, item in enumerate(secoes) if item.group(1).strip() == "tui"), None)
    if tui is None:
        separador = "" if not conteudo or conteudo.endswith("\n") else "\n"
        return conteudo + separador + "\n[tui]\n" + LINHA + "\n"
    inicio = secoes[tui].end()
    fim = secoes[tui + 1].start() if tui + 1 < len(secoes) else len(conteudo)
    corpo = conteudo[inicio:fim]
    ocorrencias = list(ATRIBUTO.finditer(corpo))
    if len(ocorrencias) > 1:
        raise ValueError("Há mais de uma opção status_line em [tui].")
    if ocorrencias:
        inicio_linha, fim_linha = ocorrencias[0].span()
        corpo = corpo[:inicio_linha] + LINHA + "\n" + corpo[fim_linha:]
    else:
        corpo = "\n" + LINHA + corpo if not corpo.startswith("\n") else "\n" + LINHA + corpo
        if not corpo.endswith("\n"):
            corpo += "\n"
    resultado = conteudo[:inicio] + corpo + conteudo[fim:]
    tomllib.loads(resultado)
    return resultado


def instalar(caminho: Path) -> tuple[bool, Path | None]:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    original = caminho.read_text(encoding="utf-8") if caminho.exists() else ""
    novo = atualizar(original)
    if novo == original:
        return False, None
    backup = None
    if caminho.exists():
        instante = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = caminho.with_name(caminho.name + f".bak-pugotistatus-{instante}")
        indice = 1
        while backup.exists():
            backup = caminho.with_name(caminho.name + f".bak-pugotistatus-{instante}-{indice}")
            indice += 1
        backup.write_bytes(caminho.read_bytes())
        os.chmod(backup, 0o600)
    fd, temporario = tempfile.mkstemp(prefix=".pugotistatus-", dir=caminho.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            arquivo.write(novo)
        os.chmod(temporario, caminho.stat().st_mode & 0o777 if caminho.exists() else 0o600)
        os.replace(temporario, caminho)
    finally:
        if os.path.exists(temporario):
            os.unlink(temporario)
    return True, backup


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path.home() / ".codex" / "config.toml")
    argumentos = parser.parse_args()
    alterado, backup = instalar(argumentos.config.expanduser())
    print("Pugotistatus instalado." if alterado else "Pugotistatus já está instalado.")
    if backup:
        print(f"Backup: {backup}")
    print("Reinicie o Codex CLI para ver a barra.")


if __name__ == "__main__":
    main()
