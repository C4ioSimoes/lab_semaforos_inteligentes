"""Políticas aplicadas independentes dos quatro paradigmas e do experimento AND."""
import json
from math import isfinite
from pathlib import Path
from .controle import Proposta
from .movimento import DISTANCIA_RETENCAO, PERFIS

ARQUIVO = Path(__file__).resolve().parent.parent / 'experimento_transito/pesos_transito.json'

class ControleTransito:
    def __init__(self):
        self.documento = None
        self.erro = None
        try:
            documento = json.loads(ARQUIVO.read_text())
            for nome in ('perceptron', 'adaline'):
                w = documento['modelos'][nome]['pesos']
                if len(w) != 5 or not all(type(v) in (int, float) and isfinite(v) for v in w):
                    raise ValueError('São necessários cinco pesos finitos por modelo.')
            self.documento = documento
        except (OSError, ValueError, KeyError, TypeError) as erro:
            self.erro = f'Pesos de trânsito indisponíveis: {erro}'

    def comparar(self, modelo, candidata, atual, troca):
        x = [1., (candidata['proximos']-atual['proximos'])/20,
             (candidata['maior_espera']-atual['maior_espera'])/60,
             (candidata['aproximando']-atual['aproximando'])/20, float(troca)]
        w = self.documento['modelos'][modelo]['pesos']
        u = sum(a*b for a,b in zip(x,w))
        return {'modelo': modelo, 'entradas': x, 'pesos': w, 'soma_ponderada': u,
                'saida': 1 if u >= 0 else -1, 'candidata': candidata['fase'], 'atual': atual['fase']}

    def decidir(self, motor):
        tempo = motor._step / 10
        participantes = [*motor._participantes.values(), *(p for fila in motor._entradas.values() for p in fila)]
        pendentes = [p for p in participantes if p.instante_autorizacao is None]
        ocupados = tuple(m for m, ids in motor._ocupacoes().items() if ids)
        avaliacoes = []
        for fase, movimentos in sorted(motor.controle.fases.items()):
            pedidos = [p for p in pendentes if p.trajetoria in movimentos]
            proximos = 0
            aproximando = 0
            for p in pedidos:
                if p.categoria == 'pedestre':
                    proximos += 1
                elif p.instante_inserido is not None:
                    distancia = motor._distancias[p.id]
                    eta = max(0, DISTANCIA_RETENCAO-distancia-p.dimensoes.comprimento/2) / PERFIS[p.categoria].velocidade
                    if eta <= 6:
                        proximos += 1
                    else:
                        aproximando += 1
                else:
                    aproximando += 1
            espera = max((p.espera_interna + (tempo-p.instante_solicitado if p.instante_inserido is None else p.instante_inserido-p.instante_solicitado)
                          for p in pedidos), default=0.)
            emergencias = [p for p in pedidos if p.categoria == 'ambulancia' and p.solicitacao_prioritaria]
            admissivel, bloqueio = motor.controle.admissibilidade(fase, motor._step, ocupados)
            avaliacoes.append({'fase': fase, 'demanda': len(pedidos), 'proximos': proximos,
                'aproximando': aproximando, 'maior_espera': espera,
                'emergencia': min((p.instante_solicitado for p in emergencias), default=None),
                'criterio': 'fila_e_espera', 'admissivel': admissivel, 'bloqueio': bloqueio,
                'elegivel': bool(pedidos) and admissivel})
        candidatas = [a for a in avaliacoes if a['demanda']]
        atual = next((a for a in avaliacoes if a['fase'] == motor.controle.fase), None)
        emergencia = min((a for a in candidatas if a['emergencia'] is not None),
                         key=lambda a:(a['emergencia'], a['fase']), default=None)
        antiga = max((a for a in candidatas if a['maior_espera'] >= 60), key=lambda a:(a['maior_espera'], a['fase']), default=None)
        neural = None
        if emergencia:
            escolhida, criterio = emergencia, 'emergencia'
        elif antiga:
            escolhida, criterio = antiga, 'espera_prolongada'
        elif motor.operacao.modo == 'neural':
            escolhida = atual if atual and atual['demanda'] else next(iter(candidatas), None)
            for a in candidatas:
                if a is escolhida:
                    continue
                calculo = self.comparar(motor.operacao.modelo, a, escolhida,
                    motor.controle.estado == 'atendimento' and escolhida is atual)
                neural = calculo
                if calculo['saida'] == 1:
                    escolhida = a
            criterio = 'preferencia_neural'
        else:
            def pontuacao(a):
                # Custo de troca reduz alternâncias; espera cresce mesmo com fila pequena.
                bonus = 7.0 if a is atual and motor.controle.estado == 'atendimento' and a['proximos'] else 0
                return a['proximos'] + .2*a['aproximando'] + a['maior_espera']/6 + bonus
            escolhida = max(candidatas, key=lambda a:(pontuacao(a), a['fase']), default=None)
            criterio = 'fila_e_espera'
        atendimento = motor.controle.estado == 'atendimento'
        minimo = motor._step - motor.controle.inicio_passo < motor.controle.verde_minimo
        if atendimento and (minimo or escolhida is None or escolhida is atual):
            proposta = Proposta('manter', motor.controle.fase,
                'Atendimento mínimo protegido.' if minimo else 'Manter verde enquanto não há vantagem em trocar de fase.')
        elif escolhida:
            proposta = Proposta('transicionar', escolhida['fase'], f'Atender {escolhida["fase"]}: {criterio}.')
        else:
            proposta = Proposta('aguardar', None, 'Aguardar demanda.')
        for a in avaliacoes:
            if a is escolhida:
                a['criterio'] = criterio
        return proposta, avaliacoes, criterio, neural, ocupados
