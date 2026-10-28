#!/usr/bin/env python3
"""Instala a seleção nativa de indicadores do Codex CLI."""

import argparse
import datetime
import os
from pathlib import Path
import re
import shutil
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


def instalar_lancador(destino: Path) -> Path:
    """Instala o comando que acrescenta barras reais ao terminal Codex."""
    origem = Path(__file__).with_name("pugotistatus.py")
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origem, destino)
    destino.chmod(0o755)
    return destino


def instalar_funcao_fish(destino: Path, lancador: Path) -> bool:
    """Faz o comando interativo `codex` abrir com barras no Fish."""
    conteudo = (
        "# Pugotistatus: o Codex interativo usa barras de uso.\n"
        "function codex\n"
        "    for arg in $argv\n"
        "        if contains -- $arg exec app-server login logout update mcp agents cloud completion --help --version -h -V\n"
        "            command codex $argv\n"
        "            return\n"
        "        end\n"
        "    end\n"
        "    if isatty stdin; and isatty stdout\n"
        f"        command {lancador} $argv\n"
        "        return\n"
        "    end\n"
        "    command codex $argv\n"
        "end\n"
    )
    if destino.exists():
        atual = destino.read_text(encoding="utf-8")
        if atual == conteudo:
            return False
        if not atual.startswith("# Pugotistatus: o Codex interativo usa barras de uso.\n"):
            raise FileExistsError(f"Função Fish já existe; não foi substituída: {destino}")
        destino.with_suffix(".fish.bak-pugotistatus").write_text(atual, encoding="utf-8")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path.home() / ".codex" / "config.toml")
    parser.add_argument("--bars", action="store_true", help="Instala o comando pugotistatus com barras visuais")
    argumentos = parser.parse_args()
    alterado, backup = instalar(argumentos.config.expanduser())
    print("Pugotistatus instalado." if alterado else "Pugotistatus já está instalado.")
    if backup:
        print(f"Backup: {backup}")
    if argumentos.bars:
        destino = instalar_lancador(Path.home() / ".local" / "bin" / "pugotistatus")
        print(f"Barras: {destino} (inicie com 'pugotistatus')")
        if Path(os.environ.get("SHELL", "")).name == "fish":
            funcao = Path.home() / ".config" / "fish" / "functions" / "codex.fish"
            instalar_funcao_fish(funcao, destino)
            print(f"Fish: 'codex' sem argumentos abrirá com barras na próxima sessão ({funcao}).")
    print("Reinicie o Codex CLI para ver a barra.")


if __name__ == "__main__":
    main()
