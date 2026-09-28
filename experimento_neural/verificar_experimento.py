"""Testes independentes de treinamento, exportação e interação, sem o laboratório.

Execute com o Python do experimento. Usa apenas biblioteca padrão, NumPy e
Matplotlib; não necessita de Jupyter, FastAPI, Prolog ou servidor em execução.
"""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ["MPLBACKEND"] = "Agg"
import numpy as np
import matplotlib.pyplot as plt

PASTA = Path(__file__).resolve().parent


def fonte(celula):
    return "".join(celula["source"])


class TestExperimentoNeural(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads((PASTA / "and_perceptron_adaline.ipynb").read_text(encoding="utf-8"))
        cls.temporario = TemporaryDirectory()
        cls.addClassCleanup(cls.temporario.cleanup)
        cls.ns = {"__name__": "__experimento_testado__"}
        anterior = Path.cwd()
        try:
            os.chdir(cls.temporario.name)
            with redirect_stdout(StringIO()), patch.object(plt, "show"):
                for celula in cls.notebook["cells"]:
                    if celula["cell_type"] == "code" and "interativa" not in celula["metadata"].get("tags", []):
                        exec(compile(fonte(celula), f"notebook:{celula['id']}", "exec"), cls.ns)
        finally:
            os.chdir(anterior)
            plt.close("all")

    def test_importacoes_permitidas_e_isolamento(self):
        permitidos = sys.stdlib_module_names | {"numpy", "matplotlib"}
        for celula in self.notebook["cells"]:
            if celula["cell_type"] != "code":
                continue
            for node in ast.walk(ast.parse(fonte(celula))):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(a.name.split(".")[0] in permitidos for a in node.names))
                if isinstance(node, ast.ImportFrom):
                    self.assertEqual(node.level, 0)
                    self.assertIn(node.module.split(".")[0], permitidos)
        for proibido in ("fastapi", "swiplserver", "sklearn", "tensorflow", "keras", "torch"):
            self.assertNotIn(proibido, sys.modules)

    def test_base_ordem_bias_e_parametros(self):
        np.testing.assert_array_equal(self.ns["X"], [[1, 0, 0], [1, 0, 1], [1, 1, 0], [1, 1, 1]])
        np.testing.assert_array_equal(self.ns["D"], [-1, -1, -1, 1])
        self.assertEqual(self.ns["ETA"], .1)
        self.assertEqual(self.ns["MAX_EPOCAS"], 100)
        self.assertEqual(self.ns["TOLERANCIA_SSE"], 1e-6)
        np.testing.assert_array_equal(self.ns["PESOS_INICIAIS"], [0, 0, 0])

    def test_primeira_epoca_perceptron_calculo_manual(self):
        p = self.ns["perceptron"]
        primeiro = p["primeira_epoca"][0]
        self.assertEqual((primeiro["u"], primeiro["y"], primeiro["erro"]), (0, 1, -2))
        np.testing.assert_allclose(primeiro["pesos_depois"], [-.2, 0, 0], atol=1e-15)
        np.testing.assert_allclose(p["historico"][0]["pesos"], [0, .2, .2], atol=1e-15)
        self.assertEqual(p["historico"][0]["erros"], 2)

    def test_primeira_epoca_adaline_calculo_manual_sem_sinal(self):
        a = self.ns["adaline"]
        # Quatro atualizações manuais: -0,1; [-0,19,0,-0,09];
        # [-0,271,-0,081,-0,09]; [-0,1268,0,0632,0,0542].
        esperados = [[-.1, 0, 0], [-.19, 0, -.09], [-.271, -.081, -.09], [-.1268, .0632, .0542]]
        for passo, esperado in zip(a["primeira_epoca"], esperados):
            np.testing.assert_allclose(passo["pesos_depois"], esperado, atol=1e-15)
        self.assertAlmostEqual(a["historico"][0]["sse"], 3.51828232, places=12)

    def test_sse_recalculado_com_pesos_finais_e_parada(self):
        historico = self.ns["adaline"]["historico"]
        self.assertIsNone(historico[0]["variacao_sse"])
        for i, h in enumerate(historico):
            # Forma escalar independente da agregação vetorizada do notebook.
            w0, w1, w2 = h["pesos"]
            esperado = sum((d - (w0 + w1 * x1 + w2 * x2)) ** 2
                           for (x1, x2), d in zip(((0, 0), (0, 1), (1, 0), (1, 1)), (-1, -1, -1, 1)))
            self.assertAlmostEqual(h["sse"], esperado, places=12)
            if i:
                self.assertAlmostEqual(h["variacao_sse"], abs(h["sse"] - historico[i - 1]["sse"]), places=15)
                if i < len(historico) - 1:
                    self.assertGreaterEqual(h["variacao_sse"], 1e-6)
        self.assertEqual(len(historico), 100)
        self.assertEqual(self.ns["adaline"]["motivo_parada"], "limite_epocas")
        self.assertGreaterEqual(historico[-1]["variacao_sse"], 1e-6)
        p = self.ns["perceptron"]
        self.assertEqual(p["motivo_parada"], "epoca_sem_erros")
        self.assertEqual(p["historico"][-1]["erros"], 0)
        self.assertTrue(all(h["erros"] > 0 for h in p["historico"][:-1]))

    def test_quatro_combinacoes_e_sinal_em_zero(self):
        self.assertEqual(self.ns["sinal"](0), 1)
        for nome in ("perceptron", "adaline"):
            self.assertEqual([r["saida"] for r in self.ns["verificacoes"][nome]], [-1, -1, -1, 1])
            self.assertEqual([r["elegivel"] for r in self.ns["verificacoes"][nome]], [False, False, False, True])

    def test_inicializacao_independente_e_reprodutibilidade(self):
        for nome in ("perceptron", "adaline"):
            with redirect_stdout(StringIO()):
                repetido = self.ns[f"treinar_{nome}"]()
            original = self.ns[nome]
            np.testing.assert_array_equal(repetido["pesos"], original["pesos"])
            self.assertEqual(repetido["historico"], original["historico"])
            self.assertFalse(np.shares_memory(repetido["pesos"], original["pesos"]))
        self.assertFalse(np.shares_memory(self.ns["perceptron"]["pesos"], self.ns["adaline"]["pesos"]))

    def test_exportacao_round_trip_sem_arredondar_e_resultado_entregue(self):
        gravado = json.loads(self.ns["ARQUIVO_PESOS"].read_text(encoding="utf-8"))
        entregue = json.loads((PASTA.parent / "pesos_neurais.json").read_text(encoding="utf-8"))
        for nome in ("perceptron", "adaline"):
            np.testing.assert_array_equal(gravado["modelos"][nome]["pesos"], self.ns[nome]["pesos"])
            self.assertEqual(entregue["modelos"][nome], gravado["modelos"][nome])
        self.assertTrue(all(r["apto_para_ativacao"] for r in self.ns["validar_documento"](gravado).values()))

    def test_rejeita_pesos_invalidos_ou_modelo_nao_treinado(self):
        casos = [
            ("pesos", [1, 2]), ("pesos", [1, 2, 3, 4]), ("pesos", [True, 0, 1]),
            ("pesos", ["1", 0, 1]), ("pesos", None), ("pesos", [float("nan"), 0, 1]),
            ("pesos", [float("inf"), 0, 1]), ("pesos", [float("-inf"), 0, 1]),
            ("treinado", False), ("epocas_executadas", 0), ("epocas_executadas", True),
            ("epocas_executadas", 101), ("taxa_aprendizado", .2), ("inicializacao", [1, 1, 1]),
            ("historico", []), ("motivo_parada", "inventado"),
        ]
        for nome in ("perceptron", "adaline"):
            for campo, valor in casos:
                with self.subTest(modelo=nome, campo=campo, valor=valor):
                    dados = deepcopy(self.ns["documento"])
                    dados["modelos"][nome][campo] = valor
                    with self.assertRaises(ValueError):
                        self.ns["validar_documento"](dados)

    def test_rejeita_versao_ordem_e_convencoes_incompativeis(self):
        for campo, valor in (("schema_version", "99"), ("ordem_pesos", ["w1", "w2", "w0"]),
                             ("convencao_saida", {}), ("entradas", {}), ("dtype_calculo", "float32"),
                             ("modelos", {"perceptron": {}})):
            with self.subTest(campo=campo):
                dados = deepcopy(self.ns["documento"])
                dados[campo] = valor
                with self.assertRaises(ValueError):
                    self.ns["validar_documento"](dados)

    def test_divergencia_recalculada_mesmo_se_arquivo_declara_sucesso(self):
        dados = deepcopy(self.ns["documento"])
        modelo = dados["modelos"]["perceptron"]
        modelo["pesos"] = [round(w, 6) for w in modelo["pesos"]]
        modelo["historico"][-1]["pesos"] = modelo["pesos"][:]
        # A tabela gravada continua dizendo que acertou todas as combinações.
        self.assertTrue(all(r["correto"] for r in modelo["verificacao_and"]))
        relatorio = self.ns["validar_documento"](dados)["perceptron"]
        self.assertFalse(relatorio["apto_para_ativacao"])
        self.assertEqual(relatorio["divergencias"][0]["entradas"], [1, 0])

    def test_laco_recupera_texto_invalido_e_prediz_ambos_os_modelos(self):
        teclado = ["abc", "0.5", "-1", "2", "nan", "0", "inválido", "0", "0", "1", "1", "0", "1", "1", " SAIR "]
        saida = StringIO()
        with patch("builtins.input", side_effect=teclado), redirect_stdout(saida):
            self.ns["interagir"]()
        texto = saida.getvalue()
        self.assertEqual(texto.count("Entrada inválida"), 6)
        self.assertEqual(texto.count("| y="), 8)
        self.assertEqual(texto.count("| y=+1"), 2)
        for nome in ("Perceptron", "Adaline"):
            linhas = [linha for linha in texto.splitlines() if linha.startswith(nome + " |")]
            self.assertEqual(len(linhas), 4)
            for linha, esperado in zip(linhas, (-1, -1, -1, 1)):
                self.assertIn(f"| y={esperado:+d}", linha)
        self.assertIn("Laço de predição encerrado", texto)

    def test_sair_em_qualquer_entrada_e_fim_do_teclado(self):
        for entrada in (["sair"], ["1", "sair"], EOFError, KeyboardInterrupt):
            with self.subTest(entrada=entrada):
                saida = StringIO()
                with patch("builtins.input", side_effect=entrada), redirect_stdout(saida):
                    self.ns["interagir"]()
                self.assertIn("Laço de predição encerrado", saida.getvalue())
                self.assertNotIn("| y=", saida.getvalue())
        final = self.notebook["cells"][-1]
        self.assertIn("interativa", final["metadata"]["tags"])
        saida = StringIO()
        with patch("builtins.input", side_effect=["sair"]), redirect_stdout(saida):
            exec(fonte(final), self.ns)
        self.assertIn("Laço de predição encerrado", saida.getvalue())

    def test_exportacao_na_raiz_partindo_das_duas_pastas(self):
        ambiente = next(c for c in self.notebook["cells"] if c["id"] == "ambiente")
        with TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            pasta_notebook = raiz / "experimento_neural"
            pasta_notebook.mkdir()
            for pasta in (raiz, pasta_notebook):
                ns = {}
                with patch("pathlib.Path.cwd", return_value=pasta), redirect_stdout(StringIO()):
                    exec(fonte(ambiente), ns)
                self.assertEqual(ns["ARQUIVO_PESOS"], raiz / "pesos_neurais.json")
                destino = self.ns["salvar_pesos_neurais"](self.ns["documento"], ns["ARQUIVO_PESOS"])
                self.assertEqual(json.loads(destino.read_text(encoding="utf-8")), self.ns["documento"])

    def test_comparacao_e_figuras_exportadas(self):
        linhas = (self.ns["ARTEFATOS"] / "comparacao.txt").read_text(encoding="utf-8").splitlines()
        self.assertTrue(10 <= len(linhas) <= 15)
        self.assertIn("100 épocas", "\n".join(linhas))
        for figura in ("curvas_aprendizado", "tabela_pesos", "retas_decisao"):
            self.assertTrue((self.ns["ARTEFATOS"] / f"{figura}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertIn("<svg", (self.ns["ARTEFATOS"] / f"{figura}.svg").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
