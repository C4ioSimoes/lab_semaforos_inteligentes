import asyncio

import pytest

from motor_python.gerador import ConfiguracaoGerador
from motor_python.motor import Motor


def configurar(motor, multiplicador, ident='velocidade'):
    respostas = []
    motor.receber_comando({'command_id': ident, 'tipo': 'configurar_velocidade',
                          'parametros': {'multiplicador': multiplicador}}, respostas.append)
    return respostas


@pytest.mark.parametrize('valor', [0, 25, -1, 1.5, True, '12', None, float('inf')])
def test_rejeita_velocidade_invalida_sem_mudar_o_relogio(valor):
    motor = Motor()
    respostas = configurar(motor, valor)
    assert respostas[0].confirmacao.status == 'rejeitado'
    assert motor.instantaneo().velocidade_simulacao == 1
    assert motor.instantaneo().step == 0


def test_velocidade_confirma_no_passo_deduplica_e_permanece_apos_reset():
    motor = Motor()
    respostas = configurar(motor, 24)
    assert not respostas and motor.velocidade_simulacao == 1
    estado = motor.avancar()
    assert estado.velocidade_simulacao == 24 and estado.step == 1
    assert respostas[0].confirmacao.passo_aplicacao == 1
    assert configurar(motor, 24) == respostas
    assert len([e for e in motor._eventos if e.tipo == 'velocidade_configurada']) == 1
    assert motor.exportar_experimento()['configuracao_atual']['velocidade_simulacao'] == 24
    motor.receber_comando({'command_id': 'reset', 'tipo': 'resetar_simulacao', 'parametros': {}}, lambda _: None)
    novo = motor.avancar(publicar=False)
    assert novo.run_id != estado.run_id and novo.step == 0
    assert novo.velocidade_simulacao == 24


@pytest.mark.parametrize('modo', ['baseline', 'imperativo', 'urbano', 'perceptron', 'adaline'])
def test_1x_e_24x_preservam_cada_passo_e_resultados(modo):
    motores = [Motor(), Motor()]
    for motor, fator in zip(motores, [1, 24]):
        motor._run_id = 'ensaio-igual'
        demanda = ConfiguracaoGerador(semente=73)
        for origem in demanda.taxas_veiculares:
            demanda.taxas_veiculares[origem].update(carro=18, moto=4, onibus=2, ambulancia=1)
        demanda.taxas_pedestres = dict.fromkeys(demanda.taxas_pedestres, 3)
        motor.receber_comando({'command_id': 'gerador', 'tipo': 'configurar_gerador',
                              'parametros': demanda.model_dump()}, lambda _: None)
        if modo in ('baseline', 'imperativo'):
            tipo, parametros = 'configurar_controlador', {'controlador': modo}
        else:
            tipo, parametros = 'configurar_operacao', {'modo': 'urbano' if modo == 'urbano' else 'neural',
                                                      'modelo': 'adaline' if modo == 'adaline' else 'perceptron'}
        motor.receber_comando({'command_id': 'modo', 'tipo': tipo, 'parametros': parametros}, lambda _: None)
        configurar(motor, fator)
    for passo in range(1, 801):
        # Transmissão menos frequente não pode interferir nos cálculos.
        a = motores[0].avancar().model_dump(exclude={'velocidade_simulacao'})
        motores[1]._avancar(publicar=passo % 12 == 0)
        b = motores[1].instantaneo().model_dump(exclude={'velocidade_simulacao'})
        assert a == b
    a, b = [m.exportar_experimento() for m in motores]
    for chave in ['metricas', 'historico_metricas', 'participantes_ativos', 'participantes_pendentes', 'demanda']:
        assert a[chave] == b[chave]
    def eventos(dados):
        return [{k: v for k, v in e.items() if k not in ('event_id', 'ordem')}
                for e in dados['eventos'] if e['tipo'] != 'velocidade_configurada']
    assert eventos(a) == eventos(b)
    assert a['metricas']['total']['concluidos'] > 0
    for m in motores:
        m.fechar()


class FimRelogio(Exception):
    pass


@pytest.mark.parametrize('fator', [1, 12, 24])
def test_agendamento_acelera_sem_pular_passos_e_limita_publicacao(monkeypatch, fator):
    motor = Motor()
    configurar(motor, fator)
    tempo = 0.
    enviados = []
    capturas = []
    original = motor.instantaneo
    def capturar():
        capturas.append(motor._step)
        return original()
    monkeypatch.setattr(motor, 'instantaneo', capturar)
    fila = motor.assinar()
    fila.get_nowait()
    def consumir(_fila, mensagem):
        enviados.append((tempo, mensagem.step))
    monkeypatch.setattr(motor, 'enfileirar', consumir)
    class Relogio:
        def time(self):
            return tempo
    async def esperar(atraso):
        nonlocal tempo
        if motor._step == 240:
            raise FimRelogio
        tempo += atraso
    monkeypatch.setattr(asyncio, 'get_running_loop', lambda: Relogio())
    monkeypatch.setattr(asyncio, 'sleep', esperar)
    with pytest.raises(FimRelogio):
        asyncio.run(motor.executar())
    assert motor._step == 240 and motor.instantaneo().simulation_time == 24
    assert tempo == pytest.approx(.1 + 239 * .1 / fator)
    assert len(motor._historico_metricas) == 25
    assert enviados[0] == (.1, 1)  # Confirmação seguida de estado imediato.
    if fator == 1:
        assert [passo for _, passo in enviados] == list(range(1, 241))
    else:
        assert len(enviados) <= 1 + int(tempo * 20)
        assert all(b[0] - a[0] >= .05 - 1e-9 for a, b in zip(enviados, enviados[1:]))
        assert len(capturas) <= len(enviados) + 24 + 2


def test_troca_24x_para_1x_nao_acumula_divida_sob_carga(monkeypatch):
    motor = Motor()
    configurar(motor, 24)
    tempo, pausas = 0., []
    class Relogio:
        def time(self):
            return tempo
    async def esperar(atraso):
        nonlocal tempo
        if motor._step == 20:
            raise FimRelogio
        pausas.append(atraso)
        tempo += atraso
        if motor._step == 10:
            tempo += 2  # Máquina ocupada: não executar 480 passos para compensar.
            configurar(motor, 1, 'normal')
    monkeypatch.setattr(asyncio, 'get_running_loop', lambda: Relogio())
    monkeypatch.setattr(asyncio, 'sleep', esperar)
    with pytest.raises(FimRelogio):
        asyncio.run(motor.executar())
    assert motor._step == 20 and motor.velocidade_simulacao == 1
    assert pausas[-7:] == pytest.approx([.1] * 7)
