"""Política expressa por sequência, laços, variáveis e condicionais."""
from .contratos import Avaliacao, Decisao, Estado, Proposta


class ControladorImperativo:
    def propor(self, estado: Estado) -> Decisao:
        avaliacoes = []
        melhor = None
        for fase in estado.fases:
            quantidade = 0
            mais_antiga = float('inf')
            emergencia = float('inf')
            onibus = float('inf')
            for pedido in estado.solicitacoes:
                if pedido.movimento in fase.movimentos:
                    quantidade += 1
                    if pedido.instante < mais_antiga:
                        mais_antiga = pedido.instante
                    if pedido.categoria == 'ambulancia' and pedido.prioritaria and pedido.instante < emergencia:
                        emergencia = pedido.instante
                    if pedido.categoria == 'onibus' and pedido.instante < onibus:
                        onibus = pedido.instante
            espera = max(0, round(estado.tempo - mais_antiga, 6)) if quantidade else 0
            if quantidade == 0:
                criterio, chave = 'sem_demanda', (4, 0., 0., fase.id)
            elif estado.prioridade_ambulancia and emergencia != float('inf'):
                criterio, chave = 'emergencia', (0, emergencia, 0., fase.id)
            elif espera > estado.limiar_espera:
                criterio, chave = 'limiar_espera', (1, -espera, 0., fase.id)
            elif estado.prioridade_onibus and onibus != float('inf'):
                criterio, chave = 'onibus', (2, onibus, 0., fase.id)
            else:
                criterio, chave = 'maior_demanda', (3, -quantidade, mais_antiga, fase.id)
            avaliacao = Avaliacao(fase.id, quantidade, espera, criterio, chave, fase.admissivel, fase.bloqueio)
            avaliacoes.append(avaliacao)
            if quantidade and (melhor is None or chave < melhor.chave):
                melhor = avaliacao
        relogio = estado.relogio
        if relogio.estado == 'atendimento' and relogio.decorrido_passos < estado.verde_passos:
            proposta = Proposta('manter', relogio.fase, 'Preservar o tempo de atendimento e movimentos autorizados.')
        elif melhor is None:
            proposta = Proposta('aguardar', None, 'Sem solicitações pendentes; encerrar permissões e aguardar em vermelho.')
        else:
            proposta = Proposta('transicionar', melhor.fase, f'Prioridade: {melhor.criterio}. Respeitar transição e ocupações.')
        return Decisao(proposta, tuple(avaliacoes), melhor.criterio if melhor else 'sem_demanda')
