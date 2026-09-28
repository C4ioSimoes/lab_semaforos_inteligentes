"""Domínio encapsulado: demanda de fase, regras e coordenação da política."""
from .contratos import Avaliacao, Decisao, Estado, Proposta


class DemandaDaFase:
    def __init__(self, fase, pedidos, tempo):
        self.fase = fase
        self._pedidos = tuple(p for p in pedidos if p.movimento in fase.movimentos)
        self._tempo = tempo

    @property
    def quantidade(self):
        return len(self._pedidos)

    def mais_antigo(self, categoria=None, emergencia=False):
        instantes = [p.instante for p in self._pedidos if (categoria is None or p.categoria == categoria)
                     and (not emergencia or p.prioritaria)]
        return min(instantes, default=None)

    @property
    def espera(self):
        instante = self.mais_antigo()
        return max(0, round(self._tempo - instante, 6)) if instante is not None else 0


class RegraEmergencia:
    criterio = 'emergencia'

    def avaliar(self, demanda, estado):
        instante = demanda.mais_antigo('ambulancia', emergencia=True)
        if estado.prioridade_ambulancia and instante is not None:
            return (0, instante, 0., demanda.fase.id)


class RegraEspera:
    criterio = 'limiar_espera'

    def avaliar(self, demanda, estado):
        if demanda.espera > estado.limiar_espera:
            return (1, -demanda.espera, 0., demanda.fase.id)


class RegraOnibus:
    criterio = 'onibus'

    def avaliar(self, demanda, estado):
        instante = demanda.mais_antigo('onibus')
        if estado.prioridade_onibus and instante is not None:
            return (2, instante, 0., demanda.fase.id)


class RegraVolume:
    criterio = 'maior_demanda'

    def avaliar(self, demanda, estado):
        return (3, -demanda.quantidade, demanda.mais_antigo(), demanda.fase.id)


class PoliticaPrioridades:
    def __init__(self):
        self._regras = (RegraEmergencia(), RegraEspera(), RegraOnibus(), RegraVolume())

    def avaliar(self, demanda, estado):
        criterio, chave = 'sem_demanda', (4, 0., 0., demanda.fase.id)
        if demanda.quantidade:
            for regra in self._regras:
                resultado = regra.avaliar(demanda, estado)
                if resultado is not None:
                    criterio, chave = regra.criterio, resultado
                    break
        return Avaliacao(demanda.fase.id, demanda.quantidade, demanda.espera, criterio, chave,
                         demanda.fase.admissivel, demanda.fase.bloqueio)

    def selecionar(self, avaliacoes):
        candidatas = [a for a in avaliacoes if a.demanda]
        return min(candidatas, key=lambda a: a.chave, default=None)


class ControladorOrientadoObjetos:
    def __init__(self):
        self._politica = PoliticaPrioridades()

    def propor(self, estado: Estado) -> Decisao:
        demandas = [DemandaDaFase(f, estado.solicitacoes, estado.tempo) for f in estado.fases]
        avaliacoes = tuple(self._politica.avaliar(d, estado) for d in demandas)
        escolhida = self._politica.selecionar(avaliacoes)
        if estado.relogio.estado == 'atendimento' and estado.relogio.decorrido_passos < estado.verde_passos:
            proposta = Proposta('manter', estado.relogio.fase, 'Preservar o tempo de atendimento e movimentos autorizados.')
        elif escolhida:
            proposta = Proposta('transicionar', escolhida.fase, f'Prioridade: {escolhida.criterio}. Respeitar transição e ocupações.')
        else:
            proposta = Proposta('aguardar', None, 'Sem solicitações pendentes; encerrar permissões e aguardar em vermelho.')
        return Decisao(proposta, avaliacoes, escolhida.criterio if escolhida else 'sem_demanda')
