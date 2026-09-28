from itertools import combinations
from random import Random
from statistics import mean, pvariance

import pytest
from pydantic import ValidationError

from motor_python.gerador import ConfiguracaoGerador, GeradorDemanda, poisson
from motor_python.motor import Motor
from motor_python.pedestres import ACESSOS


def pedir(motor, parametros, tipo="inserir_participante", identificador="pedido"):
    respostas = []
    motor.receber_comando({"command_id": identificador, "tipo": tipo, "parametros": parametros}, respostas.append)
    return respostas


def pedestre(acesso="N-TR:A", quantidade=1):
    travessia, lado = acesso.split(":")
    return dict(categoria="pedestre", travessia=travessia, lado=lado, quantidade=quantidade)


def configurar(motor, configuracao, identificador="config"):
    return pedir(motor, configuracao.model_dump(), "configurar_gerador", identificador)


@pytest.mark.parametrize("acesso", ACESSOS)
def test_pedestre_aguarda_na_calcada_da_travessia_escolhida(acesso):
    motor = Motor()
    respostas = pedir(motor, pedestre(acesso))
    assert motor.instantaneo().participantes == []
    estado = motor.avancar()
    p = estado.participantes[0]
    assert respostas[0].confirmacao.status == "aplicado"
    assert p.origem == acesso
    assert p.destino == acesso[:-1] + ("B" if acesso[-1] == "A" else "A")
    assert p.trajetoria == acesso.split(":")[0]
    assert abs(p.posicao.x) >= 7 and abs(p.posicao.z) >= 7
    assert p.estado == "aguardando_travessia"
    assert p.instante_inicio_espera == p.instante_inserido == 0.1
    assert p.fonte == "manual"
    for _ in range(50):
        assert motor.avancar().participantes[0].posicao == p.posicao
    assert len([e for e in motor._eventos if e.tipo == "travessia_solicitada"]) == 1
    assert len([e for e in motor._eventos if e.tipo == "inicio_espera"]) == 1


def test_calcadas_compartilhadas_nao_sobrepoem_e_lotes_excedentes_aguardam():
    motor = Motor()
    for acesso in ACESSOS:
        pedir(motor, pedestre(acesso, 20), identificador=acesso)
    for _ in range(25):
        estado = motor.avancar()
        for a, b in combinations(estado.participantes, 2):
            assert (a.posicao.x - b.posicao.x) ** 2 + (a.posicao.z - b.posicao.z) ** 2 >= 1 - 1e-9
    assert len(estado.participantes) + len(estado.solicitacoes) == 160
    assert len(estado.solicitacoes) > 0
    assert all(estado.filas["externas"][acesso] >= 4 for acesso in ACESSOS)
    assert all(p.estado == "aguardando_travessia" for p in estado.participantes)
    assert estado.demanda["motivo_interrupcao"] is None  # saturação física, não técnica


@pytest.mark.parametrize("alteracao", [
    {"travessia": "N"}, {"lado": "X"}, {"origem": "N"}, {"posicao": {"x": 0}},
    {"quantidade": 0}, {"quantidade": 101}, {"quantidade": 1.5}, {"quantidade": True},
])
def test_rejeita_pedestre_invalido(alteracao):
    motor = Motor()
    respostas = pedir(motor, {**pedestre(), **alteracao})
    assert respostas[0].confirmacao.status == "rejeitado"
    assert motor.avancar().participantes == []


@pytest.mark.parametrize("media", [0, 2.5, 55])
def test_amostragem_poisson_tem_media_variancia_e_multiplas_chegadas(media):
    rng = Random(42)
    amostras = [poisson(rng, media) for _ in range(20_000)]
    assert mean(amostras) == pytest.approx(media, abs=max(0.08, media * 0.02))
    assert pvariance(amostras) == pytest.approx(media, abs=max(0.1, media * 0.04))
    assert all(isinstance(n, int) and n >= 0 for n in amostras)
    if media:
        assert max(amostras) > 1
    else:
        assert set(amostras) == {0}


def test_fatores_efetivos_e_divisao_entre_acessos_pedestres():
    c = ConfiguracaoGerador()
    c.taxas_veiculares["N"].update(carro=10, moto=5)
    c.taxas_pedestres["N-TR"] = 12
    c.fator_global, c.fatores_locais["N"], c.fator_pedestres = 2, 3, 4
    g = GeradorDemanda()
    g.configurar(c, 0)
    taxas = g.diagnostico(0)["taxas_efetivas"]
    assert taxas["N:carro"] == 60
    assert taxas["N:moto"] == 30
    assert taxas["N-TR:A:pedestre"] == taxas["N-TR:B:pedestre"] == 24
    assert taxas["S:carro"] == 0


def test_mesma_semente_reproduz_calendario_independente_das_insercoes_manuais():
    c = ConfiguracaoGerador()
    c.taxas_veiculares["N"]["carro"] = 600
    c.taxas_pedestres["S-TR"] = 120
    motores = [Motor(), Motor()]
    for motor in motores:
        configurar(motor, c)
    pedir(motores[1], pedestre("L-TR:A", 3))
    for _ in range(100):
        for motor in motores:
            motor.avancar()
    calendarios = [[(e.passo, e.parametros) for e in m._eventos if e.tipo == "chegadas_automaticas"] for m in motores]
    assert calendarios[0] == calendarios[1]
    assert any(e[1]["quantidade"] > 1 for e in calendarios[0])
    assert motores[0].instantaneo().demanda["solicitados"]["automatico"] > 3
    assert motores[0].instantaneo().filas["externas"]["N"] > 0


def test_alterar_carros_nao_altera_outras_fontes_nem_seus_sorteios():
    c = ConfiguracaoGerador()
    c.taxas_veiculares["N"].update(carro=10, moto=60)
    c.taxas_pedestres["N-TR"] = 60
    a, b = GeradorDemanda(), GeradorDemanda()
    a.configurar(c, 0)
    c.taxas_veiculares["N"]["carro"] = 600
    b.configurar(c, 0)
    for _ in range(100):
        a_outras = [(k, n) for k, _, n in a.gerar(0.1) if k != "N:carro"]
        b_outras = [(k, n) for k, _, n in b.gerar(0.1) if k != "N:carro"]
        assert a_outras == b_outras


def test_configuracao_aplica_no_passo_zero_desliga_sem_apagar_filas_e_deduplica():
    motor = Motor()
    c = ConfiguracaoGerador()
    c.taxas_veiculares["N"]["carro"] = 6000
    respostas = configurar(motor, c)
    assert motor.instantaneo().demanda["taxas_efetivas"]["N:carro"] == 0
    motor.avancar()
    assert respostas[0].confirmacao.passo_aplicacao == 1
    for _ in range(10):
        estado = motor.avancar()
    assert estado.demanda["taxas_observadas"]["N:carro"] == pytest.approx(
        estado.demanda["gerados_janela"]["N:carro"] * 60 / 1.1)
    assert all(p.fonte == "automatico" for p in estado.participantes)
    solicitados = estado.demanda["solicitados"]["automatico"]
    ids = {p.id for p in estado.participantes} | {p["id"] for p in estado.solicitacoes}
    assert len(ids) == solicitados
    configurar(motor, ConfiguracaoGerador(), "desligar")
    desligado = motor.avancar()
    assert desligado.demanda["inicio_janela"] == 1.1
    assert sum(desligado.demanda["gerados_janela"].values()) == 0
    for _ in range(15):
        estado = motor.avancar()
    assert estado.demanda["solicitados"]["automatico"] == solicitados
    assert {p.id for p in estado.participantes} | {p["id"] for p in estado.solicitacoes} == ids
    configurar(motor, ConfiguracaoGerador(), "desligar")
    assert motor.avancar().demanda["inicio_janela"] == 1.1
    eventos = [e for e in motor._eventos if e.tipo == "gerador_configurado"]
    assert len(eventos) == 2
    assert eventos[1].parametros["anterior"] == c.model_dump()
    assert eventos[1].resultado["nova"] == ConfiguracaoGerador().model_dump()


def test_limite_de_pendencias_contabiliza_todas_as_chegadas_e_preserva_estado():
    motor = Motor(limite_pendentes=2)
    c = ConfiguracaoGerador()
    c.taxas_veiculares["N"]["carro"] = 6000
    configurar(motor, c)
    estado = motor.avancar()
    d = estado.demanda
    assert d["motivo_interrupcao"]
    assert d["solicitados"]["automatico"] == sum(d["gerados_janela"].values())
    assert d["solicitados"]["automatico"] == len(estado.participantes) + len(estado.solicitacoes) + d["recusados"]["automatico"]
    assert d["recusados"]["automatico"] > 0
    assert motor.avancar() == estado
    assert pedir(motor, pedestre())[0].confirmacao.status == "rejeitado"


def test_limite_ativo_preserva_pendencias_e_lote_manual_excedente_e_atomico():
    motor = Motor(limite_ativos=1)
    pedir(motor, pedestre(quantidade=2))
    motor.avancar()
    estado = motor.avancar()
    assert len(estado.participantes) == len(estado.solicitacoes) == 1
    assert "ativos" in estado.demanda["motivo_interrupcao"]
    assert motor.avancar() == estado
    motor = Motor(limite_pendentes=2)
    respostas = pedir(motor, pedestre(quantidade=3))
    estado = motor.avancar()
    assert respostas[0].confirmacao.status == "rejeitado"
    assert estado.participantes == estado.solicitacoes == []
    assert estado.demanda["recusados"]["manual"] == 3


@pytest.mark.parametrize("campo,valor", [
    ("semente", True), ("semente", -1), ("fator_global", float("nan")),
    ("fator_pedestres", float("inf")), ("fator_global", 11),
    ("fatores_locais", {"N": 1}), ("taxas_pedestres", {"N": 10}),
    ("taxas_veiculares", {}), ("extra", 42),
])
def test_configuracao_invalida_e_rejeitada(campo, valor):
    with pytest.raises(ValidationError):
        ConfiguracaoGerador.model_validate({**ConfiguracaoGerador().model_dump(), campo: valor})


@pytest.mark.parametrize("taxa", [-1, float("nan"), float("inf"), 6001])
def test_taxas_invalidas_nao_entram_no_gerador(taxa):
    dados = ConfiguracaoGerador().model_dump()
    dados["taxas_veiculares"]["N"]["carro"] = taxa
    with pytest.raises(ValidationError):
        ConfiguracaoGerador.model_validate(dados)


def test_fator_nao_pode_ultrapassar_limite_de_taxa_efetiva():
    dados = ConfiguracaoGerador().model_dump()
    dados["taxas_pedestres"]["N-TR"] = 4000
    dados["fator_pedestres"] = 2
    with pytest.raises(ValidationError):
        ConfiguracaoGerador.model_validate(dados)
