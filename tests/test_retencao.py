from itertools import permutations

import pytest

from motor_python.motor import Motor
from motor_python.controle import ConfiguracaoControle
from motor_python.movimento import PERFIS, BORDA_VIA


def inserir(motor, origem, categoria, identificador):
    respostas = []
    motor.receber_comando({
        "command_id": identificador, "tipo": "inserir_participante",
        "parametros": {"categoria": categoria, "origem": origem,
                       "movimento": "seguir_em_frente", "quantidade": 1},
    }, respostas.append)
    return respostas


def centro_desde_borda(p):
    coordenada = p.posicao.z if p.origem in "NS" else p.posicao.x
    return BORDA_VIA - abs(coordenada)


@pytest.mark.parametrize("origem", ["N", "S", "L", "O"])
@pytest.mark.parametrize("categoria,comprimento,largura,altura", [
    ("carro", 4, 1.8, 1.3), ("moto", 2, .8, 1.2),
    ("onibus", 10, 2.5, 3), ("ambulancia", 5, 2, 2.4),
])
def test_categorias_parametros_e_parada_antes_da_barra(origem, categoria, comprimento, largura, altura):
    motor = Motor(configuracao_controle=ConfiguracaoControle(liberacao_passos=1000))
    respostas = inserir(motor, origem, categoria, "unico")
    primeiro = motor.avancar().participantes[0]
    assert respostas[0].confirmacao.status == "aplicado"
    assert primeiro.categoria == categoria
    assert primeiro.dimensoes.model_dump() == dict(comprimento=comprimento, largura=largura, altura=altura)
    assert primeiro.posicao.y == altura / 2
    assert centro_desde_borda(primeiro) == comprimento / 2
    for _ in range(240):
        estado = motor.avancar()
        p = estado.participantes[0]
        # Usa a geometria real da barra: borda externa em 11,225, mais folga de 0,5.
        assert BORDA_VIA - centro_desde_borda(p) - comprimento / 2 >= 11.725 - 1e-8
        assert estado.semaforos[origem] == "vermelho"
    assert p.estado == "aguardando_retencao"
    assert BORDA_VIA - centro_desde_borda(p) - comprimento / 2 == pytest.approx(11.725)
    assert estado.filas["internas"][origem] == 1


@pytest.mark.parametrize("origem", ["N", "S", "L", "O"])
@pytest.mark.parametrize("ordem", list(permutations(["carro", "moto", "onibus", "ambulancia"])))
def test_filas_mistas_sem_ultrapassagem_sobreposicao_ou_descarte(origem, ordem):
    motor = Motor(configuracao_controle=ConfiguracaoControle(liberacao_passos=1000))
    pedidos = (*ordem, *(["onibus"] * 16))
    for i, categoria in enumerate(pedidos):
        inserir(motor, origem, categoria, str(i))
    anterior = {}
    for _ in range(500):
        estado = motor.avancar()
        participantes = estado.participantes
        assert len(participantes) + len(estado.solicitacoes) == len(pedidos)
        assert [p.categoria for p in participantes] == list(pedidos)[:len(participantes)]
        for p in participantes:
            progresso = centro_desde_borda(p)
            assert progresso >= anterior.get(p.id, progresso) - 1e-8
            anterior[p.id] = progresso
            assert progresso - p.dimensoes.comprimento / 2 >= -1e-8
            assert BORDA_VIA - progresso - p.dimensoes.comprimento / 2 >= 11.725 - 1e-8
        for faixa in ("externa", "interna"):
            fila = [p for p in participantes if p.faixa == faixa]
            for lider, seguidor in zip(fila, fila[1:]):
                espaco = centro_desde_borda(lider) - centro_desde_borda(seguidor) - (
                    lider.dimensoes.comprimento + seguidor.dimensoes.comprimento
                ) / 2
                assert espaco >= PERFIS[seguidor.categoria].distancia_minima - 1e-8
    assert estado.solicitacoes  # a fila externa não desaparece ao saturar
    assert all(p.estado.startswith("aguardando_") for p in participantes)
    assert estado.filas["internas"][origem] == len(participantes)
    assert estado.filas["externas"][origem] == len(estado.solicitacoes)
    parado = [p.posicao for p in participantes]
    assert [p.posicao for p in motor.avancar().participantes] == parado
