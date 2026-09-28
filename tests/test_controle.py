from itertools import combinations

import pytest
from pydantic import ValidationError

from motor_python.controle import ConfiguracaoControle, MOVIMENTOS, Proposta, conflitos_iniciais
from motor_python.motor import Motor
from motor_python.movimento import PERFIS, DISTANCIA_RETENCAO, FOLGA_RETENCAO


def inserir(motor, origem="N", categoria="carro", identificador="pedido", quantidade=1):
    parametros = (dict(categoria=categoria, travessia=origem.split(":")[0], lado=origem[-1], quantidade=quantidade)
                  if categoria == "pedestre" else dict(categoria=categoria, origem=origem, movimento="seguir_em_frente", quantidade=quantidade))
    motor.receber_comando(dict(command_id=identificador, tipo="inserir_participante", parametros=parametros), lambda _: None)


def ate(motor, passo):
    while motor.instantaneo().step < passo:
        motor.avancar()
    return motor.instantaneo()


def test_matriz_cobre_conflitos_veiculares_e_travessias_simetrica():
    matriz = conflitos_iniciais()
    for a in MOVIMENTOS:
        assert not matriz[a][a]
        for b in MOVIMENTOS:
            assert matriz[a][b] == matriz[b][a]
    assert not matriz['N-seguir_em_frente']['S-seguir_em_frente']
    assert matriz['N-seguir_em_frente']['L-seguir_em_frente']
    assert matriz['N-seguir_em_frente']['N-TR']
    assert matriz['N-seguir_em_frente']['S-TR']
    assert not matriz['N-seguir_em_frente']['L-TR']


@pytest.mark.parametrize("falha", ["assimetria", "omissao", "diagonal", "fase_conflitante", "desconhecido", "sem_atendimento", "tempo_zero", "tempo_fracionario", "sequencia_repetida"])
def test_rejeita_configuracoes_que_violam_integridade(falha):
    dados = ConfiguracaoControle().model_dump()
    matriz = dados['conflitos']
    if falha == 'assimetria':
        matriz['N-TR']['L-TR'] = True
    elif falha == 'omissao':
        matriz['N-TR']['N-seguir_em_frente'] = matriz['N-seguir_em_frente']['N-TR'] = False
    elif falha == 'diagonal':
        matriz['N-TR']['N-TR'] = True
    elif falha == 'fase_conflitante':
        dados['fases']['F-NS'].append('L-seguir_em_frente')
    elif falha == 'desconhecido':
        dados['fases']['F-NS'].append('N-direita')
    elif falha == 'sem_atendimento':
        dados['fases']['F-PED'].remove('N-TR')
    elif falha == 'tempo_zero':
        dados['amarelo_passos'] = 0
    elif falha == 'tempo_fracionario':
        dados['verde_passos'] = 1.5
    else:
        dados['sequencia'].append('F-NS')
    with pytest.raises(ValidationError):
        ConfiguracaoControle.model_validate(dados)


def test_baseline_obedece_tempos_fixos_e_historico_sem_troca_direta():
    motor = Motor()
    esperados = {
        0: (None, 'liberacao'), 9: (None, 'liberacao'), 10: ('F-NS', 'atendimento'),
        109: ('F-NS', 'atendimento'), 110: ('F-NS', 'encerramento'), 139: ('F-NS', 'encerramento'),
        140: ('F-NS', 'liberacao'), 149: ('F-NS', 'liberacao'), 150: ('F-LO', 'atendimento'),
        250: ('F-LO', 'encerramento'), 280: ('F-LO', 'liberacao'), 290: ('F-PED', 'atendimento'),
        390: ('F-PED', 'liberacao'), 400: ('F-NS', 'atendimento'),
    }
    for passo, (fase, transicao) in esperados.items():
        estado = ate(motor, passo)
        assert (estado.fase, estado.estado_transicao) == (fase, transicao)
        if transicao == 'liberacao':
            assert set(estado.semaforos.values()) == {'vermelho'}
            assert set(estado.semaforos_pedestres.values()) == {'vermelho'}
        if transicao == 'encerramento':
            assert 'amarelo' in estado.semaforos.values()
            assert 'verde' not in estado.semaforos.values()
        assert 'amarelo' not in estado.semaforos_pedestres.values()
    transicoes = [e for e in motor._eventos if e.tipo == 'transicao_semaforica']
    assert [e.passo for e in transicoes] == [10, 110, 140, 150, 250, 280, 290, 390, 400]


def test_proposta_invalida_e_precoce_bloqueada_e_verde_maximo_preservado():
    motor = Motor()
    ate(motor, 10)
    motor.controle.aplicar(Proposta('transicionar', 'F-LO', 'Teste'), 11, ())
    assert motor.controle.fase == 'F-NS'
    assert 'mínimo' in motor.controle.ultima_validacao['motivo']
    motor.controle.aplicar(Proposta('transicionar', 'inexistente', 'Teste'), 110, ())
    assert motor.controle.estado == 'encerramento'
    assert motor.controle.permissoes() == ()
    assert not motor.controle.ultima_validacao['aceita']
    assert any(e.tipo == 'proposta_bloqueada' for e in motor._eventos)


def test_controlador_recebe_estado_imutavel_e_matriz_e_fases_nao_podem_ser_modificadas():
    motor = Motor()
    estado = motor.controle.leitura(1, ())
    with pytest.raises(AttributeError):
        estado.fase = 'F-LO'
    with pytest.raises(TypeError):
        motor.controle.conflitos['N-TR']['N-seguir_em_frente'] = False
    with pytest.raises(TypeError):
        motor.controle.fases['F-NS'] = ('N-TR',)


def test_onibus_ja_autorizado_conclui_no_vermelho_e_atrasa_nova_fase():
    motor = Motor()
    ate(motor, 324)
    inserir(motor, categoria='onibus')
    # Aproximação mais longa: aguarda o ciclo em que o ônibus alcança a barra.
    autorizado = None
    bloqueou = False
    for _ in range(1000):
        estado = motor.avancar()
        for p in estado.participantes:
            if p.instante_autorizacao is not None:
                autorizado = p.id
        if autorizado and estado.ocupacoes['N-seguir_em_frente'] and estado.estado_transicao == 'liberacao':
            bloqueou = True
            assert estado.semaforos['L'] == 'vermelho'
        if estado.metricas['total']['concluidos']:
            break
    assert autorizado and bloqueou
    assert estado.metricas['total']['concluidos'] == 1
    assert len([e for e in motor._eventos if e.tipo == 'movimento_autorizado']) == 1


@pytest.mark.parametrize('origem', list('NSLO'))
@pytest.mark.parametrize('categoria', list(PERFIS))
def test_percurso_completo_respeita_permissoes_e_conclui_uma_vez(origem, categoria):
    motor = Motor()
    inserir(motor, origem, categoria)
    autorizado = False
    posicao_anterior = None
    for _ in range(700):
        estado = motor.avancar()
        for p in estado.participantes:
            distancia = motor._distancias[p.id]
            retencao = DISTANCIA_RETENCAO - FOLGA_RETENCAO - p.dimensoes.comprimento / 2
            if p.instante_autorizacao is not None and not autorizado:
                assert estado.semaforos[origem] == 'verde'
                autorizado = True
            if not autorizado:
                assert distancia <= retencao + 1e-8
            if posicao_anterior is not None:
                assert distancia >= posicao_anterior
            posicao_anterior = distancia
        if estado.metricas['total']['concluidos']:
            break
    assert autorizado
    assert estado.participantes == []
    assert estado.metricas['total']['concluidos'] == 1
    assert estado.metricas['total']['vazao_por_minuto'] == pytest.approx(60 / estado.simulation_time)
    assert estado.metricas['por_categoria'][categoria]['concluidos'] == 1
    assert estado.metricas['por_origem'][origem]['concluidos'] == 1
    motor.avancar()
    assert len([e for e in motor._eventos if e.tipo == 'percurso_concluido']) == 1


def test_integridade_e_distancia_em_filas_mistas_durante_varios_ciclos():
    motor = Motor()
    for origem in 'NSLO':
        for i, categoria in enumerate(['onibus', 'moto', 'carro', 'ambulancia'] * 2):
            inserir(motor, origem, categoria, f'{origem}-{i}')
    for _ in range(1600):
        estado = motor.avancar()
        permissoes = estado.controle['permissoes']
        assert all(not motor.controle.conflitos[a][b] for a, b in combinations(permissoes, 2))
        ocupados = [m for m, ids in estado.ocupacoes.items() if ids]
        assert all(not motor.controle.conflitos[a][b] for a in permissoes for b in ocupados)
        assert all(not motor.controle.conflitos[a][b] for a, b in combinations(ocupados, 2))
        for origem in 'NSLO':
            fila = sorted([p for p in estado.participantes if p.origem == origem], key=lambda p: -motor._distancias[p.id])
            for a, b in zip(fila, fila[1:]):
                folga = motor._distancias[a.id] - motor._distancias[b.id] - (a.dimensoes.comprimento + b.dimensoes.comprimento) / 2
                assert folga >= PERFIS[b.categoria].distancia_minima - 1e-6
        assert len(estado.participantes) + len(estado.solicitacoes) + estado.metricas['total']['concluidos'] == 32
    assert estado.metricas['total']['concluidos'] == 32


def test_pedestre_iniciado_continua_apos_vermelho_e_bloqueia_conflito():
    motor = Motor()
    ate(motor, 387)
    inserir(motor, 'N-TR:A', 'pedestre')
    ate(motor, 389)
    assert motor.instantaneo().participantes[0].estado == 'em_travessia'
    autorizacao = motor.instantaneo().participantes[0].instante_autorizacao
    estado = ate(motor, 400)
    assert estado.semaforos_pedestres['N-TR'] == 'vermelho'
    assert estado.semaforos['N'] == 'vermelho'
    assert estado.estado_transicao == 'liberacao'
    posicao = estado.participantes[0].posicao
    assert motor.avancar().participantes[0].posicao != posicao
    for _ in range(150):
        estado = motor.avancar()
        if estado.metricas['total']['concluidos']:
            break
        assert estado.semaforos['N'] == 'vermelho'
        assert estado.participantes[0].instante_autorizacao == autorizacao
    assert estado.metricas['por_categoria']['pedestre']['concluidos'] == 1
    assert estado.participantes == []
    assert motor.avancar().semaforos['N'] == 'verde'


def test_pedestres_reservam_percurso_sem_sobrepor_novos_admitidos():
    motor = Motor()
    for t in ('N-TR', 'S-TR', 'L-TR', 'O-TR'):
        for lado in ('A', 'B'):
            inserir(motor, f'{t}:{lado}', 'pedestre', f'{t}:{lado}', quantidade=3)
    concluiu = False
    for _ in range(1200):
        estado = motor.avancar()
        for a, b in combinations(estado.participantes, 2):
            assert (a.posicao.x - b.posicao.x) ** 2 + (a.posicao.z - b.posicao.z) ** 2 >= 0.8 ** 2 - 1e-8
        if estado.metricas['total']['concluidos']:
            concluiu = True
        assert len(estado.participantes) + len(estado.solicitacoes) + estado.metricas['total']['concluidos'] == 24
    assert concluiu


def test_metricas_preservam_espera_externa_e_interna_dos_nao_concluidos():
    motor = Motor(configuracao_controle=ConfiguracaoControle(liberacao_passos=1000))
    for i in range(16):
        inserir(motor, identificador=str(i))
    estado = ate(motor, 400)
    total = estado.metricas['total']
    assert total['concluidos'] == total['vazao_por_minuto'] == 0
    assert total['ativos'] == 13 and total['pendentes'] == 3
    assert total['espera_pendentes_externa_total'] == pytest.approx(3 * (estado.simulation_time - 0.1))
    assert total['espera_ativos_interna_total'] == sum(p.espera_interna for p in estado.participantes)
    assert total['espera_ativos_externa_total'] == pytest.approx(sum(p.instante_inserido - p.instante_solicitado for p in estado.participantes))
    assert total['espera_ativos_interna_total'] > 0
