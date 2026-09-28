from itertools import combinations

import pytest

from motor_python.motor import Motor
from motor_python.pedestres import TRAVESSIAS, VELOCIDADE_PEDESTRE


def pedir(motor, travessia, lado, quantidade, identificador):
    motor.receber_comando(dict(command_id=identificador, tipo='inserir_participante',
        parametros=dict(categoria='pedestre', travessia=travessia, lado=lado, quantidade=quantidade)), lambda _: None)


@pytest.mark.parametrize('travessias', [('N-TR',), TRAVESSIAS])
def test_flush_de_30_por_travessia_no_mesmo_tick_sem_colisoes(travessias):
    motor = Motor()
    for t in travessias:
        for lado in 'AB':
            pedir(motor, t, lado, 15, t + lado)
    for _ in range(289):
        antes = motor.avancar()
    quantidade = 30 * len(travessias)
    assert len(antes.participantes) == quantidade
    assert all(p.estado == 'aguardando_travessia' for p in antes.participantes)
    originais = {p.id: p.posicao for p in antes.participantes}
    verde = motor.avancar()
    assert len(verde.participantes) == quantidade
    assert all(p.estado == 'em_travessia' and p.instante_autorizacao == 29 for p in verde.participantes)
    assert all(p.posicao != originais[p.id] for p in verde.participantes)
    assert all(verde.filas['internas'][t + ':' + lado] == 0 for t in travessias for lado in 'AB')
    assert sum(map(len, verde.ocupacoes.values())) == quantidade
    anterior = {p.id: p.posicao for p in verde.participantes}
    for _ in range(510):
        estado = motor.avancar()
        for p in estado.participantes:
            a = anterior[p.id]
            assert (p.posicao.x - a.x)**2 + (p.posicao.z - a.z)**2 <= (VELOCIDADE_PEDESTRE * .1)**2 + 1e-8
            assert p.instante_autorizacao == 29
        for a, b in combinations(estado.participantes, 2):
            assert (a.posicao.x - b.posicao.x)**2 + (a.posicao.z - b.posicao.z)**2 >= .8**2 - 1e-8
        if any(estado.ocupacoes[t] for t in travessias):
            for t in travessias:
                if estado.ocupacoes[t]:
                    assert estado.semaforos[t[0]] == 'vermelho'
        anterior = {p.id: p.posicao for p in estado.participantes}
    assert estado.metricas['total']['concluidos'] == quantidade
    assert not estado.participantes
    assert not motor._percursos_pedestres
    autorizacoes = [e for e in motor._eventos if e.tipo == 'movimento_autorizado']
    assert len(autorizacoes) == quantidade
    assert {e.passo for e in autorizacoes} == {290}


def test_novos_pedestres_entram_durante_verde_e_aguardam_apos_vermelho():
    motor = Motor()
    for _ in range(300): motor.avancar()
    pedir(motor, 'N-TR', 'A', 3, 'durante-verde')
    for _ in range(3): estado = motor.avancar()
    assert len(estado.participantes) == 3
    assert all(p.estado == 'em_travessia' for p in estado.participantes)
    while motor.instantaneo().step < 391: motor.avancar()
    pedir(motor, 'S-TR', 'B', 1, 'apos-vermelho')
    estado = motor.avancar()
    novo = next(p for p in estado.participantes if p.trajetoria == 'S-TR')
    assert novo.estado == 'aguardando_travessia'
    assert novo.instante_autorizacao is None
