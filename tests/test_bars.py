"""PQA-116: barras visuais do Codex mostram limites reais e ausências."""

import unittest

from pugotistatus import barra, faixa


class BarrasTest(unittest.TestCase):
    def test_porcentagem_restante_e_cores(self):
        self.assertEqual(barra({"usedPercent": 25}, largura=8, cores=False), "██████░░ 75%")
        self.assertEqual(barra({"usedPercent": 100}, largura=8, cores=False), "░░░░░░░░ 0%")
        self.assertIn("\x1b[31m", barra({"usedPercent": 95}, cores=True))

    def test_indisponivel_e_terminal_estreito(self):
        self.assertIn("5h —", faixa({}, 80, cores=False))
        self.assertIn("7d —", faixa({}, 80, cores=False))
        self.assertNotIn("7d", faixa({300: {"usedPercent": 10}}, 30, cores=False))
        self.assertIn("7d", faixa({10080: {"usedPercent": 20}}, 55, cores=False))


if __name__ == "__main__":
    unittest.main()
