import pytest
from fastapi.testclient import TestClient
from motor_python.main import app
from motor_python.motor import Motor
from motor_python.gerador import ConfiguracaoGerador


def enviar(m, tipo, parametros=None, ident=None):
    respostas = []
    comando = dict(command_id=ident or tipo, tipo=tipo, parametros=parametros or {})
    m.receber_comando(comando, respostas.append)
    return respostas


def test_reset_limpa_execucao_preserva_configuracao_e_reinicia_semente():
    m = Motor()
    gerador = ConfiguracaoGerador(semente=73)
    gerador.taxas_veiculares['N']['carro'] = 60
    enviar(m, 'configurar_gerador', gerador.model_dump())
    enviar(m, 'configurar_controlador', {'controlador':'funcional', 'prioridade_onibus':True})
    enviar(m, 'configurar_operacao', {'modo':'neural', 'modelo':'adaline'})
    for _ in range(100):
        m.avancar()
    antes = m.instantaneo()
    assert antes.participantes
    configuracao = m.configuracao_experimento()
    respostas = enviar(m, 'resetar_simulacao')
    assert m.instantaneo().run_id == antes.run_id
    depois = m.avancar()
    assert depois.run_id != antes.run_id
    assert depois.step == 0 and depois.simulation_time == 0
    assert not depois.participantes and not depois.solicitacoes
    assert set(depois.semaforos.values()) == {'vermelho'}
    assert depois.metricas['total']['concluidos'] == 0
    assert depois.metricas['chegadas_solicitadas'] == 0
    assert m.configuracao_experimento() == configuracao
    assert m.exportar_experimento()['configuracao_inicial'] == configuracao
    assert [h['step'] for h in m.exportar_experimento()['historico_metricas']] == [0]
    assert respostas[0].confirmacao.passo_aplicacao == 0
    novo = Motor()
    novo.gerador.configurar(gerador, 0)
    assert m.gerador._fontes['N:carro'].getstate() == novo.gerador._fontes['N:carro'].getstate()
    assert m.avancar().step == 1
    assert m.controle.registrar.__self__ is m


def test_reset_funciona_interrompido_e_nao_repete_por_command_id():
    m = Motor()
    m.avancar()
    m._interromper('Limite técnico')
    respostas = enviar(m, 'resetar_simulacao', ident='reset-1')
    novo = m.avancar()
    assert novo.demanda['motivo_interrupcao'] is None
    m.avancar()
    assert enviar(m, 'resetar_simulacao', ident='reset-1') == respostas
    assert m.avancar().run_id == novo.run_id
    enviar(m, 'resetar_simulacao', ident='reset-2')
    segundo = m.avancar()
    assert segundo.run_id != novo.run_id
    assert enviar(m, 'resetar_simulacao', ident='reset-1') == respostas
    assert m.avancar().run_id == segundo.run_id


def test_reset_preserva_assinantes_descarta_estados_antigos_e_cancela_pendentes():
    m = Motor()
    filas = [m.assinar(), m.assinar()]
    m.avancar()
    enviar(m, 'resetar_simulacao')
    respostas = enviar(m, 'inserir_participante', {'categoria':'carro','origem':'N','movimento':'seguir_em_frente','quantidade':1})
    novo = m.avancar()
    assert respostas[0].confirmacao.status == 'rejeitado'
    for fila in filas:
        assert fila.get_nowait() == novo
        assert fila.empty()
    assert set(filas) == m._assinantes
    assert not m.avancar().participantes


def test_reset_rejeita_parametros_extras():
    m = Motor()
    antes = m.instantaneo().run_id
    r = enviar(m, 'resetar_simulacao', {'apagar_configuracao':True})
    assert r[0].confirmacao.status == 'rejeitado'
    assert m.avancar().run_id == antes


def test_reset_websocket_confirma_e_publica_nova_execucao_sem_desconectar():
    with TestClient(app) as client:
        with client.websocket_connect('/ws') as ws:
            antes = ws.receive_json()
            ws.send_json(dict(command_id='reset-ws',tipo='resetar_simulacao',parametros={}))
            confirmacao = None
            for _ in range(20):
                recebido = ws.receive_json()
                if recebido.get('tipo') == 'confirmacao_comando':
                    confirmacao = recebido
                elif recebido['run_id'] != antes['run_id']:
                    break
            assert confirmacao['confirmacao']['status'] == 'aplicado'
            assert recebido['run_id'] != antes['run_id'] and recebido['step'] == 0
            assert ws.receive_json()['step'] == 1
