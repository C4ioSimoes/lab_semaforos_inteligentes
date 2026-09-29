import pytest
from fastapi.testclient import TestClient

from motor_python.main import app
from motor_python.motor import Motor
from motor_python.controle import ConfiguracaoControle


def comando(origem="N", command_id="pedido-1", **parametros):
    return {
        "command_id": command_id, "tipo": "inserir_participante",
        "parametros": {"categoria": "carro", "origem": origem,
                       "movimento": "seguir_em_frente", "quantidade": 1, **parametros},
    }


@pytest.mark.parametrize("origem,inicial,seguinte,destino", [
    ("N", (-4.5, -88), (-4.5, -87.4), "S"),
    ("S", (4.5, 88), (4.5, 87.4), "N"),
    ("L", (88, -4.5), (87.4, -4.5), "O"),
    ("O", (-88, 4.5), (-87.4, 4.5), "L"),
])
def test_cria_na_origem_e_move_somente_no_passo_oficial(origem, inicial, seguinte, destino):
    motor, respostas = Motor(), []
    motor.receber_comando(comando(origem), respostas.append)
    assert motor.instantaneo().participantes == []
    assert respostas == []
    carro = motor.avancar().participantes[0]
    assert carro.origem == origem
    assert carro.destino == destino
    assert (carro.posicao.x, carro.posicao.z) == inicial
    assert carro.instante_inserido == carro.instante_solicitado == 0.1
    assert respostas[0].confirmacao.passo_aplicacao == 1
    proximo = motor.avancar().participantes[0]
    assert proximo.id == carro.id
    assert (proximo.posicao.x, proximo.posicao.z) == seguinte
    assert proximo.posicao.y == 0.65
    # A cópia enviada anteriormente não é alterada pelo motor.
    assert (carro.posicao.x, carro.posicao.z) == inicial


def test_retransmissao_antes_depois_e_id_reutilizado():
    motor, respostas = Motor(), []
    pedido = comando()
    motor.receber_comando(pedido, respostas.append)
    motor.receber_comando(pedido, respostas.append)
    assert len(motor.avancar().participantes) == 1
    assert len(respostas) == 2
    motor.receber_comando(pedido, respostas.append)
    assert respostas[-1] == respostas[0]
    motor.receber_comando(comando("L"), respostas.append)
    assert respostas[-1].confirmacao.status == "rejeitado"
    assert len(motor.avancar().participantes) == 1
    assert len([e for e in motor._eventos if e.tipo == "insercao_solicitada"]) == 1


@pytest.mark.parametrize("alteracao,campo", [
    ({"categoria": "aviao"}, "Categoria"), ({"origem": "X"}, "origem"),
    ({"movimento": "virar"}, "Movimento"), ({"quantidade": 0}, "Quantidade"),
    ({"quantidade": -1}, "Quantidade"), ({"quantidade": 1.5}, "Quantidade"),
    ({"quantidade": True}, "Quantidade"), ({"quantidade": "1"}, "Quantidade"),
    ({"quantidade": 2}, "Quantidade"), ({"posicao": {"x": 999}}, "posicao"),
])
def test_rejeita_parametros_invalidos_sem_gerar_carro(alteracao, campo):
    motor, respostas = Motor(), []
    motor.receber_comando(comando(**alteracao), respostas.append)
    assert respostas[0].confirmacao.status == "rejeitado"
    assert campo in respostas[0].confirmacao.erro
    assert motor.avancar().participantes == []


def test_entrada_ocupada_aguarda_sem_sobreposicao():
    motor = Motor()
    for i in range(3):
        motor.receber_comando(comando("L", str(i)), lambda resposta: None)
    estado = motor.avancar()
    assert len(estado.participantes) == 2
    assert {p.faixa for p in estado.participantes} == {"externa", "interna"}
    assert estado.filas["externas"]["L"] == 1
    assert len(estado.solicitacoes) == 1
    for _ in range(30):
        estado = motor.avancar()
        for faixa in ("externa", "interna"):
            carros = sorted((p for p in estado.participantes if p.faixa == faixa), key=lambda p: p.posicao.x)
            for a, b in zip(carros, carros[1:]):
                assert b.posicao.x - a.posicao.x >= 6 - 1e-9
    assert len(estado.participantes) == 3
    assert estado.solicitacoes == []
    assert estado.participantes[2].instante_inserido > estado.participantes[2].instante_solicitado


def test_vermelho_retem_carro_e_registra_inicio_de_espera_uma_vez():
    motor = Motor(configuracao_controle=ConfiguracaoControle(liberacao_passos=1000))
    motor.receber_comando(comando(), lambda resposta: None)
    motor.avancar()
    for _ in range(160):
        estado = motor.avancar()
    assert estado.fase is None
    assert estado.participantes[0].posicao.z == -13.725
    assert estado.participantes[0].estado == "aguardando_retencao"
    assert estado.participantes[0].instante_inicio_espera is not None
    for _ in range(160):
        estado = motor.avancar()
    assert estado.participantes[0].posicao.z == -13.725
    assert len([e for e in motor._eventos if e.tipo == "inicio_espera"]) == 1
    assert not any(e.tipo == "percurso_concluido" for e in motor._eventos)


def test_websocket_confirma_insercao_e_compartilha_carro_com_observador():
    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws") as operador, cliente.websocket_connect("/ws") as observador:
            operador.receive_json()
            observador.receive_json()
            operador.send_json(comando("O"))
            confirmacao = None
            for _ in range(30):
                recebido = operador.receive_json()
                if recebido.get("tipo") == "confirmacao_comando":
                    confirmacao = recebido
                elif recebido["participantes"]:
                    break
            assert confirmacao["confirmacao"]["status"] == "aplicado"
            carro = recebido["participantes"][0]
            assert carro["origem"] == "O"
            for _ in range(30):
                outro = observador.receive_json()
                assert "tipo" not in outro  # confirmação pertence ao solicitante
                if outro["participantes"]:
                    break
            assert outro["participantes"][0]["id"] == carro["id"]
            operador.send_text("{json-invalido")
            for _ in range(30):
                resposta = operador.receive_json()
                if resposta.get("tipo") == "confirmacao_comando":
                    break
            assert resposta["confirmacao"]["status"] == "rejeitado"
        with cliente.websocket_connect("/ws") as reconectado:
            assert reconectado.receive_json()["participantes"][0]["id"] == carro["id"]
            reconectado.send_json(comando("O"))
            for _ in range(30):
                resposta = reconectado.receive_json()
                if resposta.get("tipo") == "confirmacao_comando":
                    break
            assert resposta == confirmacao
            assert len(app.state.motor.instantaneo().participantes) == 1
