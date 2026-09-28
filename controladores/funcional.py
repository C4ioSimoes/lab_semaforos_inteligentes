"""Avaliação e seleção puras sobre contratos imutáveis, sem estado interno."""
from functools import partial
from .contratos import Avaliacao, Decisao, Estado, Proposta


def avaliar_fase(estado: Estado, fase) -> Avaliacao:
    pedidos = tuple(filter(lambda p: p.movimento in fase.movimentos, estado.solicitacoes))
    quantidade = len(pedidos)
    antiga = min(map(lambda p: p.instante, pedidos), default=0.)
    espera = max(0, round(estado.tempo - antiga, 6)) if pedidos else 0.
    emergencia = min(map(lambda p: p.instante, filter(lambda p: p.categoria == 'ambulancia' and p.prioritaria, pedidos)), default=None)
    onibus = min(map(lambda p: p.instante, filter(lambda p: p.categoria == 'onibus', pedidos)), default=None)
    opcoes = (
        (not pedidos, 'sem_demanda', (4, 0., 0., fase.id)),
        (estado.prioridade_ambulancia and emergencia is not None, 'emergencia', (0, emergencia, 0., fase.id)),
        (espera > estado.limiar_espera, 'limiar_espera', (1, -espera, 0., fase.id)),
        (estado.prioridade_onibus and onibus is not None, 'onibus', (2, onibus, 0., fase.id)),
        (True, 'maior_demanda', (3, -quantidade, antiga, fase.id)),
    )
    _, criterio, chave = next(filter(lambda opcao: opcao[0], opcoes))
    return Avaliacao(fase.id, quantidade, espera, criterio, chave, fase.admissivel, fase.bloqueio)


def decidir(estado: Estado) -> Decisao:
    avaliacoes = tuple(map(partial(avaliar_fase, estado), estado.fases))
    escolhida = min(filter(lambda a: a.demanda > 0, avaliacoes), key=lambda a: a.chave, default=None)
    proposta = (
        Proposta('manter', estado.relogio.fase, 'Preservar o tempo de atendimento e movimentos autorizados.')
        if estado.relogio.estado == 'atendimento' and estado.relogio.decorrido_passos < estado.verde_passos else
        Proposta('transicionar', escolhida.fase, f'Prioridade: {escolhida.criterio}. Respeitar transição e ocupações.')
        if escolhida else
        Proposta('aguardar', None, 'Sem solicitações pendentes; encerrar permissões e aguardar em vermelho.')
    )
    return Decisao(proposta, avaliacoes, escolhida.criterio if escolhida else 'sem_demanda')


class ControladorFuncional:
    """Adaptador sem estado; a política está nas funções puras acima."""
    propor = staticmethod(decidir)
