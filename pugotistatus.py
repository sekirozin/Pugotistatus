#!/usr/bin/env python3
"""Abre o Codex CLI com barras de uso em uma faixa própria do terminal."""

import argparse
import fcntl
import json
import os
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import threading
import time
import tty


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


def redimensionar(fd, linhas, colunas):
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", max(3, linhas - 1), colunas, 0, 0))


def desenhar(janelas):
    linhas, colunas = tamanho()
    conteudo = faixa(janelas, colunas)
    # Salva a posição do cursor; a última linha pertence só à faixa de status.
    os.write(sys.stdout.fileno(),
             f"\x1b7\x1b[{linhas};1H\x1b[2K\x1b[48;5;235m\x1b[38;5;255m {conteudo}\x1b[0m\x1b8".encode())


def executar(argumentos):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit("Pugotistatus precisa de um terminal interativo. Use --preview para testar.")
    codex = shutil.which("codex")
    if not codex:
        raise SystemExit("Codex CLI não encontrado no PATH.")
    janelas = consultar_limites(codex)
    mestre, escravo = pty.openpty()
    linhas, colunas = tamanho()
    redimensionar(escravo, linhas, colunas)
    comando = [codex, "-c", 'tui.status_line=["model-with-reasoning","project-name","git-branch","context-remaining"]', *argumentos]
    processo = subprocess.Popen(comando, stdin=escravo, stdout=escravo, stderr=escravo,
                                start_new_session=True)
    os.close(escravo)
    entrada = sys.stdin.fileno()
    anterior = termios.tcgetattr(entrada)
    parar = threading.Event()

    def atualizar():
        nonlocal janelas
        while not parar.wait(90):
            janelas = consultar_limites(codex)

    thread = threading.Thread(target=atualizar, daemon=True)
    thread.start()
    try:
        tty.setraw(entrada)
        os.write(sys.stdout.fileno(), b"\x1b[?1049h\x1b[?25h")
        desenhar(janelas)
        ultima_atualizacao = janelas
        while processo.poll() is None:
            if (tamanho() != (linhas, colunas)):
                linhas, colunas = tamanho()
                redimensionar(mestre, linhas, colunas)
                os.killpg(processo.pid, signal.SIGWINCH)
                desenhar(janelas)
            prontos, _, _ = select.select([entrada, mestre], [], [], 0.5)
            if entrada in prontos:
                dados = os.read(entrada, 8192)
                if dados:
                    os.write(mestre, dados)
            if mestre in prontos:
                try:
                    dados = os.read(mestre, 65536)
                except OSError:
                    break
                if not dados:
                    break
                os.write(sys.stdout.fileno(), dados)
                desenhar(janelas)
            elif janelas is not ultima_atualizacao:
                desenhar(janelas)
            ultima_atualizacao = janelas
        if processo.poll() is None:
            processo.terminate()
        return processo.wait()
    finally:
        parar.set()
        if processo.poll() is None:
            processo.terminate()
            processo.wait()
        os.close(mestre)
        os.write(sys.stdout.fileno(), b"\x1b[?1049l")
        termios.tcsetattr(entrada, termios.TCSADRAIN, anterior)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Mostra uma amostra das barras e sai")
    opcoes, argumentos = parser.parse_known_args()
    if opcoes.preview:
        print(faixa(consultar_limites(), tamanho()[1], cores=sys.stdout.isatty()))
        return
    raise SystemExit(executar(argumentos))


if __name__ == "__main__":
    main()
