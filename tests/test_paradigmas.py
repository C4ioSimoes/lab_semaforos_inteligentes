from dataclasses import replace
from itertools import combinations
from random import Random

import pytest
from fastapi.testclient import TestClient

from controladores import criar_controlador
from controladores.contratos import Estado, Fase, Solicitacao, Decisao as DecisaoAlgoritmo
from motor_python.controle import ConfiguracaoControle, EstadoControle, Proposta
from motor_python.main import app
from motor_python.motor import Motor

NOMES = ('imperativo', 'orientado_objetos', 'funcional')
FASES = tuple(Fase(k, tuple(v), True) for k, v in ConfiguracaoControle().fases.items())


def pedido(origem='N', categoria='carro', instante=0, prioridade=False, id='p'):
    movimento = f'{origem}-TR' if categoria == 'pedestre' else f'{origem}-seguir_em_frente'
    return Solicitacao(id, movimento, categoria, instante, prioridade)


def estado(*pedidos, **alteracoes):
    return replace(Estado(EstadoControle(None, 'liberacao', 10, ()), 100, FASES, tuple(pedidos), 100, 30, True, True), **alteracoes)


@pytest.fixture(scope='module')
def logico():
    from controladores.adaptador_prolog import AdaptadorProlog
    with AdaptadorProlog() as controlador:
        yield controlador


def decidir(entrada, logico):
    saidas = [criar_controlador(nome, ConfiguracaoControle()).propor(entrada) for nome in NOMES]
    assert saidas[0] == saidas[1] == saidas[2] == logico.propor(entrada)
    return saidas[0]


@pytest.mark.parametrize('pedidos,config,fase,criterio', [
    ([pedido('N', 'ambulancia', 50, True), pedido('L', 'carro', 0)], {}, 'F-NS', 'emergencia'),
    ([pedido('N', 'ambulancia', 50, True), pedido('L', 'ambulancia', 40, True)], {}, 'F-LO', 'emergencia'),
    ([pedido('N', 'ambulancia', 50, False), pedido('L', 'carro', 0)], {}, 'F-LO', 'limiar_espera'),
    ([pedido('N', 'ambulancia', 50, True), pedido('L', 'carro', 0)], {'prioridade_ambulancia': False}, 'F-LO', 'limiar_espera'),
    ([pedido('N', 'onibus', 80), pedido('L', 'pedestre', 0)], {}, 'F-PED', 'limiar_espera'),
    ([pedido('N', 'onibus', 80), pedido('L', 'carro', 80), pedido('O', 'carro', 81)], {}, 'F-NS', 'onibus'),
    ([pedido('N', 'onibus', 80), pedido('L', 'carro', 80), pedido('O', 'carro', 81)], {'prioridade_onibus': False}, 'F-LO', 'maior_demanda'),
    ([pedido('N', instante=70), pedido('L', instante=90), pedido('O', instante=90)], {}, 'F-LO', 'maior_demanda'),
    ([pedido('N', instante=69.9), pedido('L', instante=90), pedido('O', instante=90)], {}, 'F-NS', 'limiar_espera'),
    ([pedido('N', instante=80), pedido('L', instante=90)], {}, 'F-NS', 'maior_demanda'),
    ([pedido('N', instante=80), pedido('L', instante=80)], {}, 'F-LO', 'maior_demanda'),
    ([pedido('N', 'ambulancia', 80, True), pedido('L', 'ambulancia', 80, True)], {}, 'F-LO', 'emergencia'),
    ([pedido('N', 'ambulancia', 80, True), pedido('L', 'ambulancia', 80, True), pedido('N', instante=90)], {}, 'F-LO', 'emergencia'),
    ([pedido('N', instante=0), pedido('L', instante=0), pedido('N', instante=90)], {}, 'F-LO', 'limiar_espera'),
    ([pedido('N', 'onibus', 80), pedido('L', 'onibus', 80), pedido('N', instante=90)], {}, 'F-LO', 'onibus'),
    ([], {}, None, 'sem_demanda'),
])
def test_politica_e_desempates_com_resultados_esperados(pedidos, config, fase, criterio, logico):
    saida = decidir(estado(*pedidos, **config), logico)
    assert saida.proposta.fase == fase
    assert saida.criterio == criterio
    assert saida.proposta.acao == ('aguardar' if fase is None else 'transicionar')


def test_planeja_fase_inadmissivel_sem_confundir_prioridade_com_permissao(logico):
    fases = tuple(replace(f, admissivel=False, bloqueio='Ocupação conflitante.') for f in FASES)
    saida = decidir(estado(pedido('L', 'ambulancia', 90, True), fases=fases), logico)
    assert saida.proposta.fase == 'F-LO'
    assert not next(a for a in saida.avaliacoes if a.fase == 'F-LO').admissivel


def test_mantem_minimo_mesmo_com_emergencia_e_nao_muta_entrada(logico):
    entrada = estado(pedido('L', 'ambulancia', 90, True), relogio=EstadoControle('F-NS', 'atendimento', 99, ('N-seguir_em_frente',)))
    assert decidir(entrada, logico).proposta.acao == 'manter'
    assert decidir(entrada, logico).proposta.fase == 'F-NS'
    with pytest.raises(AttributeError):
        entrada.solicitacoes[0].instante = 2
    assert decidir(replace(entrada, relogio=replace(entrada.relogio, decorrido_passos=100)), logico).proposta.fase == 'F-LO'


def test_equivalencia_em_estados_aleatorios_e_independencia_da_ordem(logico):
    rng = Random(705)
    for _ in range(500):
        pedidos = tuple(pedido(rng.choice('NSLO'), rng.choice(('carro', 'moto', 'onibus', 'ambulancia', 'pedestre')),
                              rng.randrange(101), rng.choice((True, False)), str(i)) for i in range(rng.randrange(50)))
        entrada = estado(*pedidos, limiar_espera=rng.choice((10, 30, 60, 100)), prioridade_ambulancia=rng.choice((True, False)),
                         prioridade_onibus=rng.choice((True, False)), relogio=EstadoControle(rng.choice((None, 'F-NS', 'F-LO', 'F-PED')),
                         rng.choice(('atendimento', 'encerramento', 'liberacao')), rng.randrange(150), ()))
        saida = decidir(entrada, logico)
        embaralhado = replace(entrada, solicitacoes=tuple(reversed(pedidos)), fases=tuple(reversed(FASES)))
        assert decidir(embaralhado, logico).proposta == saida.proposta


def configurar(motor, nome='imperativo', id='config', **parametros):
    respostas = []
    motor.receber_comando(dict(command_id=id, tipo='configurar_controlador', parametros=dict(controlador=nome, **parametros)), respostas.append)
    return respostas


def inserir(motor, origem='N', categoria='carro', id='pedido', emergencia=False):
    parametros = dict(categoria=categoria, origem=origem, movimento='seguir_em_frente', quantidade=1, solicitacao_prioritaria=emergencia)
    if categoria == 'pedestre':
        parametros = dict(categoria=categoria, travessia=f'{origem}-TR', lado='A', quantidade=1)
    respostas = []
    motor.receber_comando(dict(command_id=id, tipo='inserir_participante', parametros=parametros), respostas.append)
    return respostas


def ate(motor, passo):
    while motor.instantaneo().step < passo:
        motor.avancar()
    return motor.instantaneo()


@pytest.mark.parametrize('nome', NOMES)
def test_troca_aplicada_no_passo_e_deduplicada_sem_reiniciar_fase_ou_gerador(nome):
    motor = Motor()
    inserir(motor, 'L')
    antes = ate(motor, 50)
    rng_antes = motor.gerador._fontes['N:carro'].getstate()
    respostas = configurar(motor, nome)
    assert motor.configuracao_controlador.controlador == 'baseline'
    depois = motor.avancar()
    assert respostas[0].confirmacao.passo_aplicacao == 51
    assert depois.run_id == antes.run_id and depois.fase == antes.fase
    assert depois.controle['inicio_passo'] == antes.controle['inicio_passo']
    assert depois.participantes[0].id == antes.participantes[0].id
    assert motor.gerador._fontes['N:carro'].getstate() == rng_antes
    configurar(motor, nome)
    motor.avancar()
    eventos = [e for e in motor._eventos if e.tipo == 'controlador_configurado']
    assert len(eventos) == 1
    assert eventos[0].parametros['anterior']['controlador'] == 'baseline'
    assert eventos[0].resultado['nova']['controlador'] == nome


@pytest.mark.parametrize('nome', NOMES)
def test_pedestre_em_andamento_protegido_de_emergencia_apos_troca(nome):
    motor = Motor()
    ate(motor, 387)
    inserir(motor, 'N', 'pedestre', id='ped')
    ate(motor, 389)
    assert motor.instantaneo().participantes[0].estado == 'em_travessia'
    configurar(motor, nome)
    inserir(motor, 'N', 'ambulancia', emergencia=True)
    observou_bloqueio = False
    for _ in range(200):
        e = motor.avancar()
        pedestres = [p for p in e.participantes if p.categoria == 'pedestre']
        if pedestres:
            assert e.semaforos['N'] == 'vermelho'
            assert e.controle['decisao']['proposta']['fase'] == 'F-NS'
            observou_bloqueio |= 'ocupada' in e.controle['validacao']['motivo']
        else:
            assert motor.avancar().semaforos['N'] == 'verde'
            break
    assert observou_bloqueio


@pytest.mark.parametrize('nome', NOMES)
def test_demanda_vazia_fecha_regularmente_e_nao_reabre_sem_pedidos(nome):
    motor = Motor()
    ate(motor, 100)
    configurar(motor, nome)
    assert ate(motor, 109).estado_transicao == 'atendimento'
    assert ate(motor, 110).estado_transicao == 'encerramento'
    assert ate(motor, 140).estado_transicao == 'liberacao'
    e = ate(motor, 180)
    assert set(e.semaforos.values()) == {'vermelho'}
    assert e.controle['decisao']['proposta']['acao'] == 'aguardar'
    inserir(motor, 'O')
    assert motor.avancar().fase == 'F-LO'


@pytest.mark.parametrize('nome', NOMES)
def test_apenas_demanda_da_fase_atual_renova_com_transicao_completa(nome):
    motor = Motor()
    configurar(motor, nome)
    for i in range(30):
        inserir(motor, id=str(i))
    assert ate(motor, 109).fase == 'F-NS'
    assert ate(motor, 110).estado_transicao == 'encerramento'
    assert ate(motor, 140).estado_transicao == 'liberacao'
    e = ate(motor, 150)
    assert e.fase == 'F-NS' and e.estado_transicao == 'atendimento'
    assert e.controle['validacao']['aceita']


@pytest.mark.parametrize('parametros', [
    {'controlador': 'desconhecido'}, {'controlador': 'funcional', 'limiar_espera': 0},
    {'controlador': 'funcional', 'limiar_espera': float('inf')}, {'controlador': 'imperativo', 'prioridade_onibus': 1},
    {'controlador': 'imperativo', 'limiar_espera': True},
    {'controlador': 'imperativo', 'prioridade_ambulancia': 'sim'}, {'controlador': 'imperativo', 'verde_passos': 0},
])
def test_rejeita_selecao_e_parametros_invalidos(parametros):
    motor, respostas = Motor(), []
    motor.receber_comando(dict(command_id='x', tipo='configurar_controlador', parametros=parametros), respostas.append)
    assert respostas[0].confirmacao.status == 'rejeitado'
    assert motor.configuracao_controlador.controlador == 'baseline'


def test_emergencia_precisa_de_pedido_explicito_e_nao_aceita_categoria_errada():
    motor = Motor()
    assert inserir(motor, emergencia=True)[0].confirmacao.status == 'rejeitado'
    inserir(motor, categoria='ambulancia', emergencia=False, id='sem')
    inserir(motor, origem='L', categoria='ambulancia', emergencia=True, id='com')
    e = motor.avancar()
    assert [p.solicitacao_prioritaria for p in e.participantes] == [False, True]
    assert len([evento for evento in motor._eventos if evento.tipo == 'emergencia_solicitada']) == 1


def test_proposta_de_controlador_invalida_passa_pela_validacao_comum():
    motor = Motor()
    configurar(motor)
    motor.avancar()
    class Invalido:
        def propor(self, entrada):
            return DecisaoAlgoritmo(Proposta('transicionar', 'FASE_INEXISTENTE', 'Teste de bloqueio'), (), 'teste')
    motor.controlador = Invalido()
    e = motor.avancar()
    assert not e.controle['validacao']['aceita']
    assert e.fase is None and set(e.semaforos.values()) == {'vermelho'}
    assert e.controle['decisao']['proposta']['fase'] == 'FASE_INEXISTENTE'
    assert any(evento.tipo == 'proposta_bloqueada' for evento in motor._eventos)


def test_execucoes_completas_equivalentes_e_sem_conflitos_nos_quatro_paradigmas():
    motores = [Motor() for _ in (*NOMES, "logico")]
    try:
        for motor, nome in zip(motores, (*NOMES, "logico")):
            configurar(motor, nome, prioridade_onibus=True, limiar_espera=15)
            for i, (origem, categoria) in enumerate((('N', 'carro'), ('L', 'onibus'), ('O', 'ambulancia'), ('S', 'pedestre'))):
                inserir(motor, origem, categoria, str(i), categoria == 'ambulancia')
        for _ in range(900):
            estados = [m.avancar() for m in motores]
            assinaturas = [(e.fase, e.estado_transicao, e.semaforos, e.metricas, e.controle['decisao']['proposta'],
                            [(p.categoria, p.origem, p.posicao, p.estado) for p in e.participantes]) for e in estados]
            assert assinaturas[0] == assinaturas[1] == assinaturas[2] == assinaturas[3]
            for m, e in zip(motores, estados):
                autorizados = e.controle['permissoes']
                ocupados = [trajetoria for trajetoria, ids in e.ocupacoes.items() if ids]
                assert all(not m.controle.conflitos[a][b] for a, b in combinations(autorizados, 2))
                assert all(not m.controle.conflitos[a][b] for a in autorizados for b in ocupados)
        assert estados[0].metricas['total']['concluidos'] == 4
    finally:
        for motor in motores:
            motor.fechar()


def test_websocket_troca_controlador_e_sincroniza_outro_cliente():
    with TestClient(app) as cliente:
        with cliente.websocket_connect('/ws') as ws:
            ws.receive_json()
            ws.send_json(dict(command_id='algoritmo', tipo='configurar_controlador', parametros=dict(controlador='funcional', limiar_espera=20, prioridade_onibus=True)))
            confirmou = False
            for _ in range(20):
                e = ws.receive_json()
                if e.get('tipo') == 'confirmacao_comando':
                    assert e['confirmacao']['status'] == 'aplicado'
                    confirmou = True
                elif e['controle']['configuracao_controlador']['controlador'] == 'funcional':
                    break
            assert confirmou and e['controle']['configuracao_controlador']['limiar_espera'] == 20
        with cliente.websocket_connect('/ws') as observador:
            assert observador.receive_json()['controle']['configuracao_controlador']['controlador'] == 'funcional'
