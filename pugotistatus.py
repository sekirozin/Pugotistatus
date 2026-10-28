#!/usr/bin/env python3
"""Abre o Codex CLI com barras de uso na barra reservada pelo tmux."""

import argparse
import json
import os
import select
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path


def consultar_limites(codex="codex", timeout=10):
    """Lê percentuais oficiais do app-server, sem acessar credenciais diretamente."""
    processo = subprocess.Popen(
        [codex, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, bufsize=1,
    )

    def enviar(mensagem):
        processo.stdin.write(json.dumps(mensagem) + "\n")
        processo.stdin.flush()

    def resposta(identificador):
        prazo = time.monotonic() + timeout
        while time.monotonic() < prazo:
            if not select.select([processo.stdout], [], [], min(1, prazo - time.monotonic()))[0]:
                continue
            linha = processo.stdout.readline()
            if not linha:
                break
            mensagem = json.loads(linha)
            if mensagem.get("id") == identificador:
                return mensagem
        return {}

    try:
        enviar({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "pugotistatus", "version": "0.2"}}})
        if "result" not in resposta(1):
            return {}
        enviar({"method": "initialized"})
        enviar({"id": 2, "method": "account/rateLimits/read"})
        dados = resposta(2).get("result", {}).get("rateLimits") or {}
        janelas = {}
        for bloco in (dados.get("primary"), dados.get("secondary")):
            if isinstance(bloco, dict) and bloco.get("windowDurationMins") in (300, 10080):
                janelas[bloco["windowDurationMins"]] = bloco
        return janelas
    except (OSError, ValueError, KeyError, BrokenPipeError):
        return {}
    finally:
        processo.terminate()
        try:
            processo.wait(timeout=2)
        except subprocess.TimeoutExpired:
            processo.kill()
            processo.wait()


def barra(bloco, largura=12, cores=True):
    if not bloco or not isinstance(bloco.get("usedPercent"), (int, float)):
        return "—"
    usado = max(0, min(100, float(bloco["usedPercent"])))
    livre = 100 - usado
    cheios = round(largura * livre / 100)
    desenho = "█" * cheios + "░" * (largura - cheios)
    if cores:
        cor = "32" if livre > 30 else "33" if livre > 10 else "31"
        desenho = f"\x1b[{cor}m{desenho}\x1b[0m"
    return f"{desenho} {livre:.0f}%"


def faixa(janelas, colunas, cores=True):
    segmentos = [f"5h {barra(janelas.get(300), cores=cores)}",
                 f"7d {barra(janelas.get(10080), cores=cores)}"]
    texto = "  │  ".join(segmentos)
    if colunas < 58:
        segmentos = [f"5h {barra(janelas.get(300), largura=6, cores=cores)}",
                     f"7d {barra(janelas.get(10080), largura=6, cores=cores)}"]
        texto = " · ".join(segmentos)
    if colunas < 37:
        texto = f"5h {barra(janelas.get(300), largura=4, cores=cores)}"
    return texto


def tamanho():
    t = shutil.get_terminal_size((80, 24))
    return t.lines, t.columns


def barra_tmux(bloco, largura=12):
    if not bloco or not isinstance(bloco.get("usedPercent"), (int, float)):
        return "—"
    livre = 100 - max(0, min(100, float(bloco["usedPercent"])))
    cor = "#4ade80" if livre > 30 else "#facc15" if livre > 10 else "#f87171"
    cheios = round(largura * livre / 100)
    return f"#[fg={cor}]{'█' * cheios}{'░' * (largura - cheios)}#[fg=default] {livre:.0f}%"


def faixa_tmux(janelas, colunas):
    largura = 12 if colunas >= 58 else 6
    partes = [f"5h {barra_tmux(janelas.get(300), largura)}",
              f"7d {barra_tmux(janelas.get(10080), largura)}"]
    if colunas < 37:
        partes = partes[:1]
    return "  │  ".join(partes)


def executar(argumentos):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit("Pugotistatus precisa de um terminal interativo. Use --preview para testar.")
    codex = shutil.which("codex")
    if not codex:
        raise SystemExit("Codex CLI não encontrado no PATH.")
    tmux = shutil.which("tmux")
    if not tmux:
        raise SystemExit("tmux não encontrado. Instale-o para usar as barras visuais.")
    if "TMUX" in os.environ:
        return subprocess.call([codex, *argumentos])
    config = Path.home() / ".config" / "pugotistatus" / "tmux.conf"
    if not config.exists():
        raise SystemExit(f"Configuração ausente: {config}. Execute install.py --bars.")
    comando = [codex, "-c", 'tui.status_line=["model-with-reasoning","project-name","git-branch","context-remaining"]', *argumentos]
    return subprocess.call([tmux, "-L", "pugotistatus", "-f", str(config),
                            "new-session", "-c", str(Path.cwd()), shlex.join(comando)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Mostra uma amostra das barras e sai")
    parser.add_argument("--tmux-status", action="store_true", help=argparse.SUPPRESS)
    opcoes, argumentos = parser.parse_known_args()
    if opcoes.preview:
        print(faixa(consultar_limites(), tamanho()[1], cores=sys.stdout.isatty()))
        return
    if opcoes.tmux_status:
        print(faixa_tmux(consultar_limites(), tamanho()[1]))
        return
    raise SystemExit(executar(argumentos))


if __name__ == "__main__":
    main()
