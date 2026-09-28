import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from motor_python.main import app
from motor_python.modelos import Instantaneo
from motor_python.motor import LIMITE_INSTANTANEOS_PENDENTES, Motor
from motor_python.pedestres import ACESSOS


def test_relogio_sem_acumulo_de_erro_e_estado_simulado():
    motor = Motor()
    inicial = motor.instantaneo()
    assert inicial.step == 0
    assert inicial.simulation_time == 0
    for _ in range(10_000):
        estado = motor.avancar()
    assert estado.step == 10_000
    assert estado.simulation_time == 1000
    assert estado.run_id == inicial.run_id
    assert estado.fase in motor.controle.fases
    assert not any(estado.ocupacoes.values())
    assert estado.filas == {
        "externas": dict.fromkeys((*"NSLO", *ACESSOS), 0),
        "internas": dict.fromkeys((*"NSLO", *ACESSOS), 0),
    }
    assert set(estado.semaforos) == set("NSLO")
    assert set(estado.semaforos.values()) <= {"vermelho", "amarelo", "verde"}
    assert estado.solicitacoes == []


def test_assinantes_compartilham_relogio_e_recebem_copias():
    motor = Motor()
    primeira, segunda = motor.assinar(), motor.assinar()
    assert primeira.get_nowait() == segunda.get_nowait()
    motor.avancar()
    a, b = primeira.get_nowait(), segunda.get_nowait()
    assert a == b
    a.filas["teste"] = 99
    assert b.filas == motor.instantaneo().filas
    assert "teste" not in b.filas


def test_cliente_lento_e_removido_sem_parar_relogio():
    motor = Motor()
    fila = motor.assinar()
    for _ in range(LIMITE_INSTANTANEOS_PENDENTES):
        motor.avancar()
    assert fila.get_nowait() is None
    motor.avancar()
    assert fila.empty()
    assert motor.instantaneo().step == LIMITE_INSTANTANEOS_PENDENTES + 1


@pytest.mark.parametrize("campo,valor", [("step", -1), ("step", 1.5), ("simulation_time", float("nan")), ("simulation_time", float("inf"))])
def test_instantaneo_rejeita_relogio_invalido(campo, valor):
    dados = Motor().instantaneo().model_dump()
    dados[campo] = valor
    with pytest.raises(ValidationError):
        Instantaneo.model_validate(dados)


def test_websocket_publica_passos_ordenados_e_sincroniza_clientes():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            inicial = ws.receive_json()
            for incremento in range(1, 4):
                estado = ws.receive_json()
                assert estado["run_id"] == inicial["run_id"]
                assert estado["step"] == inicial["step"] + incremento
                assert estado["simulation_time"] == estado["step"] / 10
            with client.websocket_connect("/ws") as outro:
                sincronizado = outro.receive_json()
                assert sincronizado["run_id"] == estado["run_id"]
                assert sincronizado["step"] >= estado["step"]
                seguinte = outro.receive_json()
                assert seguinte["step"] == sincronizado["step"] + 1
        with client.websocket_connect("/ws") as reconectado:
            assert reconectado.receive_json()["step"] >= seguinte["step"]
    assert app.state.motor._assinantes == set()


def test_cliente_nao_pode_substituir_estado_oficial():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"step": 999999, "simulation_time": 99999.9})
            for _ in range(20):
                resposta = ws.receive_json()
                if resposta.get("tipo") == "confirmacao_comando":
                    break
            assert resposta["confirmacao"]["status"] == "rejeitado"
            assert app.state.motor.instantaneo().step < 999999


def test_loop_tem_passo_fixo_e_pode_ser_cancelado():
    async def verificar():
        motor = Motor()
        fila = motor.assinar()
        fila.get_nowait()
        tarefa = asyncio.create_task(motor.executar())
        try:
            for passo in range(1, 4):
                estado = await asyncio.wait_for(fila.get(), timeout=2)
                assert estado.step == passo
                assert estado.simulation_time == passo / 10
        finally:
            tarefa.cancel()
            with pytest.raises(asyncio.CancelledError):
                await tarefa

    asyncio.run(verificar())
