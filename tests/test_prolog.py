"""Integração real com SWI/MQI, integridade e falhas sem fallback."""
from dataclasses import replace
import json
import os
import signal
from time import monotonic
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from swiplserver import PrologMQI

from controladores.adaptador_prolog import AdaptadorProlog, FalhaProlog
from controladores.funcional import decidir
from controladores.contratos import Fase
from motor_python.main import app
from motor_python.motor import Motor
from test_paradigmas import estado, pedido, configurar, inserir, ate


@pytest.fixture
def motor():
    m = Motor()
    yield m
    m.fechar()


def test_sessao_persistente_sem_fatos_obsoletos_e_serializacao_segura():
    identificador = "F-'\\\"), halt. %\nÔnibus 🚑"
    entrada = estado(pedido(id=identificador), fases=(Fase(identificador, ('N-seguir_em_frente',), True),))
    with AdaptadorProlog() as a:
        pid, thread = a._mqi.process_id(), a._thread.goal_thread_id
        assert a.propor(entrada) == decidir(entrada)
        assert a.propor(replace(entrada, solicitacoes=())) == decidir(replace(entrada, solicitacoes=()))
        assert (pid, thread) == (a._mqi.process_id(), a._thread.goal_thread_id)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    with pytest.raises(FalhaProlog, match='encerrada'):
        a.propor(entrada)
    a.fechar()  # idempotente


def test_admissibilidade_prolog_consulta_conflitos_simetricos():
    entrada = estado(pedido('L', 'ambulancia', 90, True),
                     conflitos=(('N-seguir_em_frente', 'L-seguir_em_frente'),))
    entrada = replace(entrada, relogio=replace(entrada.relogio, ocupados=('N-seguir_em_frente',)))
    with AdaptadorProlog() as a:
        saida = a.propor(entrada)
    assert saida.proposta.fase == 'F-LO'  # planejar não significa autorizar
    lo = next(a for a in saida.avaliacoes if a.fase == 'F-LO')
    assert not lo.admissivel and 'Conflito' in lo.bloqueio


@pytest.mark.parametrize('instante', [69.9999995, 69.9999994, 69.9999996, 70., 69.9])
def test_arredondamento_e_fronteira_do_limiar(instante):
    entrada = estado(pedido('N', instante=instante), pedido('L', instante=90), pedido('L', instante=90))
    with AdaptadorProlog() as a:
        assert a.propor(entrada) == decidir(entrada)


def test_ativacao_sem_executavel_rejeita_comando_sem_confirmar_troca(monkeypatch, motor):
    def indisponivel(_):
        raise FileNotFoundError('swipl indisponível')
    monkeypatch.setattr(PrologMQI, 'start', indisponivel)
    respostas = configurar(motor, 'logico')
    e = motor.avancar()
    assert respostas[0].confirmacao.status == 'rejeitado'
    assert 'swipl indisponível' in respostas[0].confirmacao.erro
    assert e.controle['configuracao_controlador']['controlador'] == 'baseline'
    assert 'ativo permanece baseline' in e.controle['falha_controlador']
    assert not e.demanda['motivo_interrupcao']
    assert configurar(motor, 'logico')[0] == respostas[0]  # comando rejeitado deduplicado


def test_troca_e_parametros_preservam_sessao_e_shutdown_fecha_processo(motor):
    configurar(motor, 'logico')
    motor.avancar()
    adaptador = motor.controlador
    pid = adaptador._mqi.process_id()
    configurar(motor, 'logico', id='parametros', limiar_espera=40)
    e = motor.avancar()
    assert motor.controlador is adaptador and adaptador._mqi.process_id() == pid
    assert e.controle['configuracao_controlador']['limiar_espera'] == 40
    configurar(motor, 'imperativo', id='sair')
    motor.avancar()
    assert adaptador._fechado
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_processo_morto_interrompe_antes_de_novas_autorizacoes_sem_fallback(motor):
    configurar(motor, 'logico')
    inserir(motor)
    for _ in range(600):
        antes = motor.avancar()
        if any(antes.ocupacoes.values()):
            break
    assert antes.controle['configuracao_controlador']['controlador'] == 'logico'
    autorizados = motor._autorizados.copy()
    assert autorizados and any(antes.ocupacoes.values())
    os.kill(motor.controlador._mqi.process_id(), signal.SIGKILL)
    e = motor.avancar()
    assert 'SWI-Prolog/MQI' in e.controle['falha_controlador']
    assert e.controle['configuracao_controlador']['controlador'] == 'logico'
    assert e.controle['decisao'] is None and not e.controle['validacao']['aceita']
    assert [p.posicao for p in e.participantes] == [p.posicao for p in antes.participantes]
    assert motor._autorizados == autorizados
    assert motor.avancar() == e
    assert any(v.tipo == 'falha_controlador' and v.parametros['etapa'] == 'decisao' for v in motor._eventos)


def test_logico_preserva_travessia_ja_iniciada_ao_receber_emergencia(motor):
    ate(motor, 387)
    inserir(motor, 'N', 'pedestre', id='ped')
    ate(motor, 389)
    assert motor.instantaneo().participantes[0].estado == 'em_travessia'
    configurar(motor, 'logico')
    inserir(motor, 'N', 'ambulancia', emergencia=True)
    bloqueou = False
    for _ in range(200):
        e = motor.avancar()
        if any(p.categoria == 'pedestre' for p in e.participantes):
            assert e.semaforos['N'] == 'vermelho'
            assert e.controle['decisao']['proposta']['fase'] == 'F-NS'
            bloqueou |= 'ocupada' in e.controle['validacao']['motivo']
        else:
            assert motor.avancar().semaforos['N'] == 'verde'
            break
    else:
        pytest.fail('Pedestre não concluiu a travessia protegida.')
    assert bloqueou


@pytest.mark.parametrize('resposta', [False, True, [], [{}, {}], [{'Resposta': '{}'}],
                                    [{'Resposta': '{"proposta":NaN}'}]])
def test_resultado_invalido_encerra_sessao_e_nao_calcula_decisao_python(monkeypatch, resposta):
    with AdaptadorProlog() as a:
        monkeypatch.setattr(a._thread, 'query', Mock(return_value=resposta))
        with pytest.raises(FalhaProlog, match='Falha na decisão'):
            a.propor(estado(pedido()))
        assert a._fechado


def test_timeout_de_consulta_explicito(monkeypatch):
    with AdaptadorProlog(timeout_consulta=.03) as a:
        query = a._thread.query
        monkeypatch.setattr(a._thread, 'query', lambda *_a, **kw: query('sleep(2)', **kw))
        inicio = monotonic()
        with pytest.raises(FalhaProlog, match='PrologQueryTimeoutError'):
            a.propor(estado())
        assert monotonic() - inicio < 2


@pytest.mark.skipif(os.name != 'posix', reason='SIGSTOP/SIGKILL são sinais POSIX')
def test_watchdog_interrompe_processo_congelado():
    with AdaptadorProlog(timeout_comunicacao=.2) as a:
        os.kill(a._mqi.process_id(), signal.SIGSTOP)
        inicio = monotonic()
        with pytest.raises(FalhaProlog, match='não respondeu'):
            a.propor(estado())
        assert monotonic() - inicio < 2


def test_rn06_bloqueia_proposta_prolog_de_fase_desconhecida(monkeypatch, motor):
    configurar(motor, 'logico')
    motor.avancar()
    query = motor.controlador._thread.query

    def adulterar(*args, **kwargs):
        respostas = query(*args, **kwargs)
        resposta = json.loads(respostas[0]['Resposta'])
        resposta['proposta'].update(acao='transicionar', fase='F-INEXISTENTE')
        respostas[0]['Resposta'] = json.dumps(resposta)
        return respostas

    monkeypatch.setattr(motor.controlador._thread, 'query', adulterar)
    e = motor.avancar()
    assert not e.controle['validacao']['aceita']
    assert not e.controle['permissoes']
    assert not e.controle['falha_controlador']  # rejeição de integridade, não transporte
    assert e.controle['decisao']['proposta']['fase'] == 'F-INEXISTENTE'


def test_websocket_logico_reconexao_e_lifespan_sem_processo_orfao():
    with TestClient(app) as cliente:
        with cliente.websocket_connect('/ws') as ws:
            ws.receive_json()
            ws.send_json(dict(command_id='prolog', tipo='configurar_controlador', parametros=dict(controlador='logico')))
            confirmou = False
            for _ in range(20):
                e = ws.receive_json()
                if e.get('tipo') == 'confirmacao_comando':
                    assert e['confirmacao']['status'] == 'aplicado'
                    confirmou = True
                elif e['controle']['configuracao_controlador']['controlador'] == 'logico':
                    break
            assert confirmou and e['controle']['decisao']['controlador'] == 'logico'
            pid = app.state.motor.controlador._mqi.process_id()
        with cliente.websocket_connect('/ws') as ws:
            assert ws.receive_json()['controle']['configuracao_controlador']['controlador'] == 'logico'
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
