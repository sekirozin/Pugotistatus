"""PQA-124: a barra do Codex desaparece quando a sessão termina."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from install import instalar_tmux_config


@unittest.skipUnless(shutil.which("tmux") and shutil.which("script"), "tmux e script necessários")
class TerminalTest(unittest.TestCase):
    def test_tmux_reserva_linha_e_restaura_terminal(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            comando_status = raiz / "status"
            comando_status.write_text("#!/bin/sh\nprintf 'PQA-124-BARRA'\n", encoding="utf-8")
            comando_status.chmod(0o755)
            config = instalar_tmux_config(raiz / "tmux.conf", comando_status)
            transcricao = raiz / "terminal.typescript"
            socket = "pqa124-" + str(os.getpid())
            chamada = (f"{shutil.which('tmux')} -L {socket} -f {config} "
                       "new-session 'printf PQA-124-CODEX; sleep 1'")
            ambiente = {**os.environ, "TERM": "xterm-256color"}
            processo = subprocess.run(
                ["script", "-q", "-e", "-c", chamada, str(transcricao)],
                env=ambiente, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                timeout=15, check=False,
            )
            self.assertEqual(processo.returncode, 0, processo.stderr.decode(errors="replace"))
            tela = transcricao.read_bytes()
            self.assertIn(b"PQA-124-CODEX", tela)
            self.assertIn(b"PQA-124-BARRA", tela)
            self.assertGreater(tela.rfind(b"\x1b[?1049l"), tela.rfind(b"PQA-124-BARRA"))


if __name__ == "__main__":
    unittest.main()
