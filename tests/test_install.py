"""Casos de instalação e preservação da configuração do Codex."""

from pathlib import Path
import tempfile
import tomllib
import unittest

from install import INDICADORES, instalar, atualizar


class InstalacaoTest(unittest.TestCase):
    def test_cria_secao_e_preserva_configuracao(self):
        entrada = 'model = "gpt-6-sol"\n[features]\nsearch = true\n'
        saida = atualizar(entrada)
        dados = tomllib.loads(saida)
        self.assertEqual(dados["model"], "gpt-6-sol")
        self.assertEqual(dados["features"]["search"], True)
        self.assertEqual(dados["tui"]["status_line"], list(INDICADORES))
        self.assertEqual(atualizar(saida), saida)

    def test_substitui_somente_status_e_faz_backup(self):
        with tempfile.TemporaryDirectory() as pasta:
            config = Path(pasta) / "config.toml"
            original = '[tui]\nscreen_reader_detection_done = true\nstatus_line = ["model"]\n[features]\nsearch = true\n'
            config.write_text(original, encoding="utf-8")
            alterado, backup = instalar(config)
            self.assertTrue(alterado)
            self.assertEqual(backup.read_text(encoding="utf-8"), original)
            dados = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertTrue(dados["tui"]["screen_reader_detection_done"])
            self.assertEqual(dados["tui"]["status_line"], list(INDICADORES))
            self.assertEqual(instalar(config), (False, None))


if __name__ == "__main__":
    unittest.main()
