"""PQA-123: instalação, preservação da configuração e roteamento Fish do Codex."""

from pathlib import Path
import tempfile
import tomllib
import unittest

from install import INDICADORES, instalar, atualizar, instalar_funcao_fish


class InstalacaoTest(unittest.TestCase):
    def test_funcao_fish_nao_substitui_arquivo_existente(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "codex.fish"
            lancador = Path(pasta) / "pugotistatus"
            self.assertTrue(instalar_funcao_fish(caminho, lancador))
            self.assertFalse(instalar_funcao_fish(caminho, lancador))
            self.assertIn("command codex $argv", caminho.read_text(encoding="utf-8"))
            self.assertIn(f"command {lancador} $argv", caminho.read_text(encoding="utf-8"))
            self.assertNotIn("-eq 0", caminho.read_text(encoding="utf-8"))
            self.assertIn("if contains -- $arg exec app-server", caminho.read_text(encoding="utf-8"))
            caminho.write_text("function codex\nend\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                instalar_funcao_fish(caminho, lancador)

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
