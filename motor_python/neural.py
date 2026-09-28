"""Inferência escalar dos pesos do notebook, sem biblioteca de modelos."""
from copy import deepcopy
import json
from math import isfinite
from pathlib import Path

ARQUIVO_PESOS = Path(__file__).resolve().parent.parent / 'pesos_neurais.json'
MODELOS = ('AND_referencia', 'perceptron', 'adaline')
CONVENCAO = {'negativa': -1, 'positiva': 1, 'limiar': 0.0, 'positivo_inclui_limiar': True}


def calcular(modelo, pesos, x1, x2):
    if type(x1) is not int or type(x2) is not int or x1 not in (0, 1) or x2 not in (0, 1):
        raise ValueError('Entradas neurais devem ser binárias.')
    referencia = 1 if x1 and x2 else -1
    # Preserve a ordem da soma e todos os dígitos: o Perceptron tem margem
    # muito pequena em (1, 0). Não arredondar, usar tolerância ou math.fsum.
    u = None if pesos is None else (pesos[0] + pesos[1] * x1) + pesos[2] * x2
    y = referencia if u is None else (1 if u >= 0 else -1)
    return {'modelo': modelo, 'entradas': [x1, x2], 'pesos': list(pesos) if pesos is not None else None,
            'bias': 1, 'peso_bias': pesos[0] if pesos is not None else None,
            'soma_ponderada': u, 'saida': y, 'and_referencia': referencia,
            'elegivel': y == 1, 'divergencia': y != referencia}


class AvaliadoresNeurais:
    def __init__(self, arquivo=ARQUIVO_PESOS):
        self._pesos = {}
        self.documento = None
        self._estado = {'AND_referencia': {'disponivel': True, 'erro': None, 'verificacao_and': []}}
        try:
            dados = json.loads(Path(arquivo).read_text(encoding='utf-8'))
            self._validar_contrato(dados)
        except (OSError, ValueError, TypeError) as erro:
            for nome in MODELOS[1:]:
                self._estado[nome] = {'disponivel': False, 'erro': f'Arquivo de pesos inválido: {erro}', 'verificacao_and': []}
            return
        self.documento = dados
        for nome in MODELOS[1:]:
            try:
                modelo = dados['modelos'][nome]
                self._validar_modelo(nome, modelo)
                pesos = tuple(float(w) for w in modelo['pesos'])
                tabela = [calcular(nome, pesos, x1, x2) for x1, x2 in ((0, 0), (0, 1), (1, 0), (1, 1))]
                disponivel = all(not r['divergencia'] for r in tabela)
                self._estado[nome] = {'disponivel': disponivel,
                    'erro': None if disponivel else 'Os pesos divergem da AND; ativação impedida.',
                    'verificacao_and': tabela, 'epocas': modelo['epocas_executadas'],
                    'motivo_parada': modelo['motivo_parada'], 'versao': modelo['versao']}
                if disponivel:
                    self._pesos[nome] = pesos
            except (ValueError, TypeError, KeyError, OverflowError) as erro:
                self._estado[nome] = {'disponivel': False, 'erro': str(erro), 'verificacao_and': []}

    @staticmethod
    def _validar_contrato(dados):
        if not isinstance(dados, dict) or dados.get('schema_version') != '1.0' or dados.get('experimento') != 'and_bipolar':
            raise ValueError('Esquema ou experimento incompatível.')
        if not isinstance(dados.get('versao_experimento'), str) or not dados['versao_experimento']:
            raise ValueError('Versão do experimento ausente.')
        if dados.get('ordem_pesos') != ['w0', 'w1', 'w2'] or dados.get('dtype_calculo') != 'float64':
            raise ValueError('Ordem dos pesos ou precisão incompatível.')
        if dados.get('convencao_saida') != CONVENCAO:
            raise ValueError('Convenção bipolar incompatível.')
        entradas = dados.get('entradas')
        if not isinstance(entradas, dict) or entradas.get('ordem') != ['bias', 'x1', 'x2'] or entradas.get('bias') != 1 or entradas.get('dominio') != [0, 1]:
            raise ValueError('Domínio ou bias incompatível.')
        if not isinstance(dados.get('modelos'), dict) or set(dados['modelos']) != {'perceptron', 'adaline'}:
            raise ValueError('O arquivo deve conter ambos os modelos.')

    @staticmethod
    def _validar_modelo(nome, modelo):
        if not isinstance(modelo, dict) or modelo.get('modelo') != nome or not isinstance(modelo.get('versao'), str) or not modelo['versao']:
            raise ValueError(f'{nome}: identificação ou versão inválida.')
        epocas = modelo.get('epocas_executadas')
        if modelo.get('treinado') is not True or type(epocas) is not int or not 1 <= epocas <= 100:
            raise ValueError(f'{nome}: modelo sem treinamento válido.')
        w = modelo.get('pesos')
        if not isinstance(w, list) or len(w) != 3 or any(type(v) not in (int, float) or not isfinite(v) for v in w):
            raise ValueError(f'{nome}: informe três pesos numéricos finitos.')
        if modelo.get('inicializacao') != [0, 0, 0] or modelo.get('taxa_aprendizado') != .1 or modelo.get('max_epocas') != 100:
            raise ValueError(f'{nome}: parâmetros de treinamento incompatíveis.')
        motivos = {'limite_epocas', 'epoca_sem_erros' if nome == 'perceptron' else 'variacao_sse_abaixo_tolerancia'}
        if modelo.get('motivo_parada') not in motivos:
            raise ValueError(f'{nome}: motivo de parada inválido.')
        if nome == 'adaline' and modelo.get('tolerancia_sse') != 1e-6:
            raise ValueError('Adaline: tolerância incompatível.')
        historico = modelo.get('historico')
        if not isinstance(historico, list) or len(historico) != epocas or any(
            not isinstance(h, dict) or h.get('epoca') != i for i, h in enumerate(historico, 1)
        ) or historico[-1].get('pesos') != w:
            raise ValueError(f'{nome}: histórico inconsistente com os pesos finais.')

    def validar_selecao(self, modelo):
        if modelo not in self._estado or not self._estado[modelo]['disponivel']:
            raise ValueError(self._estado.get(modelo, {}).get('erro') or 'Modelo neural desconhecido.')

    def avaliar(self, modelo, x1, x2):
        self.validar_selecao(modelo)
        return calcular(modelo, self._pesos.get(modelo), x1, x2)

    def disponibilidade(self):
        return deepcopy(self._estado)

    def pesos_exportaveis(self):
        # Somente modelos validados: evita serializar NaN/Infinity de um arquivo rejeitado.
        return {nome: deepcopy(self.documento['modelos'][nome]) for nome in self._pesos}
