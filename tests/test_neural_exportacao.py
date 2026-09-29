import csv
from copy import deepcopy
from io import StringIO
import json

import pytest
from fastapi.testclient import TestClient

from motor_python.controle import ConfiguracaoControle, MaquinaSemaforica, Proposta
from motor_python.exportacao import metricas_csv
from motor_python.main import app
from motor_python.motor import Motor
from motor_python.neural import ARQUIVO_PESOS, AvaliadoresNeurais, calcular


def selecionar(motor, modelo, id='neural'):
    respostas = []
    motor.receber_comando(dict(command_id=id, tipo='configurar_modelo_neural', parametros=dict(modelo=modelo)), respostas.append)
    return respostas


@pytest.mark.parametrize('modelo', ['AND_referencia', 'perceptron', 'adaline'])
def test_quatro_combinacoes_e_diagnostico_sem_arredondamento(modelo):
    avaliadores = AvaliadoresNeurais()
    for x1, x2 in ((0, 0), (0, 1), (1, 0), (1, 1)):
        r = avaliadores.avaliar(modelo, x1, x2)
        assert r['saida'] == (1 if x1 and x2 else -1)
        assert r['bias'] == 1 and r['entradas'] == [x1, x2]
        assert r['elegivel'] == (r['saida'] == 1)
        if r['pesos']:
            w0, w1, w2 = r['pesos']
            assert r['soma_ponderada'] == (w0 + w1*x1) + w2*x2
    assert calcular('perceptron', [0., 0., 0.], 0, 0)['saida'] == 1


@pytest.mark.parametrize('campo,valor', [
    ('pesos', [float('nan'), 0, 1]), ('pesos', [float('inf'), 0, 1]), ('pesos', [1, 2]),
    ('pesos', [True, 1, 1]), ('pesos', ['1', 1, 1]), ('treinado', False),
    ('epocas_executadas', 0), ('epocas_executadas', True), ('inicializacao', [1, 1, 1]),
    ('taxa_aprendizado', .2), ('historico', []), ('versao', ''),
])
def test_pesos_invalidos_impedem_ativacao_e_exportacao_continua_valida(tmp_path, campo, valor):
    dados = json.loads(ARQUIVO_PESOS.read_text())
    dados['modelos']['perceptron'][campo] = valor
    arquivo = tmp_path / 'pesos.json'
    arquivo.write_text(json.dumps(dados))
    motor = Motor(arquivo_pesos=arquivo)
    respostas = selecionar(motor, 'perceptron')
    motor.avancar()
    assert respostas[0].confirmacao.status == 'rejeitado'
    assert motor.modelo_neural == 'AND_referencia'
    assert not motor.neurais.disponibilidade()['perceptron']['disponivel']
    json.dumps(motor.exportar_experimento(), allow_nan=False)


def test_arquivo_ausente_invalido_e_divergencia_explicita(tmp_path):
    arquivo = tmp_path / 'pesos.json'
    for conteudo in (None, 'invalido', '[]', '{}'):
        if conteudo is not None:
            arquivo.write_text(conteudo)
        avaliadores = AvaliadoresNeurais(arquivo)
        assert avaliadores.disponibilidade()['AND_referencia']['disponivel']
        assert not avaliadores.disponibilidade()['adaline']['disponivel']
    dados = json.loads(ARQUIVO_PESOS.read_text())
    p = dados['modelos']['perceptron']
    p['pesos'] = [-.4, .4, .2]
    p['historico'][-1]['pesos'] = p['pesos'][:]
    arquivo.write_text(json.dumps(dados))
    estado = AvaliadoresNeurais(arquivo).disponibilidade()['perceptron']
    assert not estado['disponivel']
    assert [r['entradas'] for r in estado['verificacao_and'] if r['divergencia']] == [[1, 0]]


def test_selecao_aplica_no_passo_deduplica_e_preserva_estado():
    motor = Motor()
    antes = motor.avancar()
    respostas = selecionar(motor, 'adaline')
    assert motor.modelo_neural == 'AND_referencia'
    depois = motor.avancar()
    assert depois.run_id == antes.run_id and depois.step == antes.step+1
    assert respostas[0].confirmacao.passo_aplicacao == depois.step
    assert depois.controle['decisao']['modelo'] == 'adaline'
    assert selecionar(motor, 'adaline')[0] == respostas[0]
    assert len([e for e in motor._eventos if e.tipo == 'modelo_neural_configurado']) == 1
    assert selecionar(motor, 'inexistente', 'ruim')[0].confirmacao.status == 'rejeitado'
    assert motor.modelo_neural == 'adaline'


@pytest.mark.parametrize('controlador', ['baseline', 'imperativo', 'orientado_objetos', 'funcional', 'logico'])
def test_modelos_equivalentes_e_elegibilidade_participa_da_abertura(controlador):
    motores = [Motor() for _ in range(3)]
    try:
        for motor, modelo in zip(motores, ('AND_referencia', 'perceptron', 'adaline')):
            selecionar(motor, modelo)
            motor.receber_comando(dict(command_id='controle', tipo='configurar_controlador', parametros=dict(controlador=controlador)), lambda _: None)
            for i, origem in enumerate('NL'):
                motor.receber_comando(dict(command_id=str(i), tipo='inserir_participante', parametros=dict(
                    categoria='carro', origem=origem, movimento='seguir_em_frente', quantidade=1)), lambda _: None)
        for _ in range(160):
            estados = [m.avancar() for m in motores]
            assinatura = lambda e: (e.fase, e.estado_transicao, e.semaforos, e.metricas)
            assert assinatura(estados[0]) == assinatura(estados[1]) == assinatura(estados[2])
            for e in estados:
                for a in e.controle['decisao']['avaliacoes']:
                    n = a['neural']
                    assert n['entradas'][1] == int(a['admissivel'])
                    assert a['elegivel'] == n['elegivel']
        # Injetar uma saída negativa demonstra que o modelo governa a abertura,
        # não apenas o texto do diagnóstico; usa fase temporalmente admissível.
        motor = motores[1]
        motor.receber_comando(dict(command_id='extra', tipo='inserir_participante', parametros=dict(
            categoria='carro', origem='N', movimento='seguir_em_frente', quantidade=1)), lambda _: None)
        motor.controle.estado = 'liberacao'
        motor.controle.inicio_passo = 0
        original = motor.neurais.avaliar
        def negar(modelo, x1, x2):
            return {**original(modelo, x1, x2), 'saida': -1, 'elegivel': False}
        motor.neurais.avaliar = negar
        motor.avancar()
        assert motor.controle.estado == 'liberacao'
        assert not motor.controle.ultima_validacao['aceita']
    finally:
        for motor in motores:
            motor.fechar()


def test_elegibilidade_positiva_nao_ignora_tempo_ou_conflitos():
    c = MaquinaSemaforica(ConfiguracaoControle(), lambda *args: None)
    proposta = Proposta('transicionar', 'F-NS', 'teste')
    c.aplicar(proposta, 1, (), elegivel=True)
    assert c.estado == 'liberacao'
    c.aplicar(proposta, 10, ('L-seguir_em_frente',), elegivel=True)
    assert c.estado == 'liberacao'
    c.aplicar(proposta, 11, (), elegivel=False)
    assert c.estado == 'liberacao'
    c.aplicar(proposta, 12, (), elegivel=True)
    assert c.estado == 'atendimento'


def test_exportacoes_incluem_nao_atendidos_historico_e_recorte_imutavel():
    motor = Motor()
    for _ in range(10):
        motor.avancar()
    for i in range(3):
        motor.receber_comando(dict(command_id=str(i), tipo='inserir_participante', parametros=dict(
            categoria='carro', origem='N', movimento='seguir_em_frente', quantidade=1)), lambda _: None)
    for _ in range(3):
        motor.avancar()
    dados = motor.exportar_experimento()
    assert dados['metricas']['total']['ativos'] == 2
    assert dados['metricas']['total']['pendentes'] == 1
    assert len(dados['participantes_pendentes']) == 1
    assert {p['faixa'] for p in dados['participantes_ativos']} == {'externa', 'interna'}
    assert dados['participantes_pendentes'][0]['faixa'] is None
    assert dados['historico_fases'] and dados['pesos_treinados']['adaline']['treinado']
    assert dados['configuracao_atual']['gerador']['semente'] == 42
    assert [h['step'] for h in dados['historico_metricas']] == [0, 10, 13]
    assert dados['motivo_encerramento'] == 'em_andamento'
    linhas = list(csv.DictReader(StringIO(metricas_csv(dados))))
    ultima = next(l for l in linhas if l['step'] == '13' and l['escopo'] == 'total')
    assert ultima['ativos'] == '2' and ultima['pendentes'] == '1'
    assert float(ultima['espera_pendentes_externa_total']) > 0
    assert any(l['origem'] == 'N' and l['categoria'] == 'carro' for l in linhas)
    antes = deepcopy(dados)
    motor.avancar()
    assert dados == antes
    motor._interromper('fim do teste')
    assert motor.exportar_experimento()['motivo_encerramento'] == 'fim do teste'


def test_rotas_download_websocket_e_reconexao():
    with TestClient(app) as cliente:
        with cliente.websocket_connect('/ws') as ws:
            primeiro = ws.receive_json()
            assert primeiro['controle']['modelos_neurais']['perceptron']['disponivel']
            ws.send_json(dict(command_id='modelo', tipo='configurar_modelo_neural', parametros=dict(modelo='perceptron')))
            for _ in range(20):
                recebido = ws.receive_json()
                if recebido.get('controle', {}).get('modelo_neural') == 'perceptron':
                    break
            assert recebido['controle']['decisao']['avaliacoes'][0]['neural']['modelo'] == 'perceptron'
        with cliente.websocket_connect('/ws') as ws:
            assert ws.receive_json()['controle']['modelo_neural'] == 'perceptron'
        json_response = cliente.get('/exportar/eventos', headers={'Origin': 'http://localhost:5173'})
        assert json_response.status_code == 200
        assert 'attachment' in json_response.headers['content-disposition']
        assert json_response.headers['access-control-allow-origin'] == 'http://localhost:5173'
        dados = json_response.json()
        assert dados['run_id'] == primeiro['run_id']
        assert any(e['tipo'] == 'modelo_neural_configurado' for e in dados['eventos'])
        csv_response = cliente.get('/exportar/metricas')
        assert csv_response.status_code == 200
        assert list(csv.DictReader(StringIO(csv_response.text)))[-1]['modelo'] == 'perceptron'


def test_filas_medias_ponderadas_e_emergencias_separam_nao_atendidos():
    from types import SimpleNamespace
    from motor_python.metricas import Metricas
    m = Metricas()
    p = SimpleNamespace(origem='N', categoria='ambulancia', solicitacao_prioritaria=True,
        instante_solicitado=0., instante_inserido=None, instante_autorizacao=None,
        espera_interna=0., estado='pendente')
    m.registrar_filas([], [p], .1)
    m.registrar_filas([], [p], .1)
    r = m.instantaneo(.2, [], [p], 1)['total']
    assert r['fila_externa_media'] == 1 and r['fila_externa_max'] == 1
    assert r['emergencias_nao_atendidas'] == 1 and r['emergencias_atendidas'] == 0
    assert r['emergencia_espera_nao_atendidos_total'] == .2
    p.instante_inserido = .2
    p.instante_autorizacao = .3
    r = m.instantaneo(.3, [p], [], 1)['total']
    assert r['emergencias_atendidas'] == 1 and r['emergencia_tempo_ate_atendimento_medio'] == .3
    assert r['emergencias_concluidas'] == 0
    m.concluir(p, 1.)
    r = m.instantaneo(1., [], [], 1)['total']
    assert r['emergencias_concluidas'] == 1 and r['emergencia_tempo_ate_conclusao_medio'] == 1.
    assert r['fila_externa_media'] == .2
