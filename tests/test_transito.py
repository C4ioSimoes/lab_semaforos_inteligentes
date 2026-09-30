from itertools import combinations

import pytest

from motor_python.motor import Motor
from motor_python.controle import ConfiguracaoControle, MaquinaSemaforica, Proposta
from experimento_transito.comparar import comando


def inserir(m, ident, origem, categoria='carro', emergencia=False):
    comando(m, ident, 'inserir_participante', categoria=categoria, origem=origem,
            movimento='seguir_em_frente', quantidade=1, solicitacao_prioritaria=emergencia)


def ativar(m, modo):
    comando(m, 'modo', 'configurar_operacao', modo='urbano' if modo == 'urbano' else 'neural',
            modelo=modo if modo != 'urbano' else 'perceptron')


def test_verde_variavel_preserva_amarelo_liberacao_e_ocupacao():
    c = MaquinaSemaforica(ConfiguracaoControle(), lambda *a: None)
    c.adaptativo = True
    c.aplicar(Proposta('transicionar', 'F-NS', 'teste'), 10, ())
    c.aplicar(Proposta('manter', 'F-NS', 'teste'), 150, ())
    assert c.estado == 'atendimento'  # Não encerra automaticamente aos 10 s.
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 151, ())
    assert c.estado == 'encerramento'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 180, ())
    assert c.estado == 'encerramento'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 181, ())
    assert c.estado == 'liberacao'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 190, ())
    assert c.estado == 'liberacao'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 191, ('N-seguir_em_frente',))
    assert c.estado == 'liberacao'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 192, ())
    assert c.estado == 'atendimento' and c.fase == 'F-LO'


@pytest.mark.parametrize('modo', ['urbano', 'perceptron', 'adaline'])
def test_emergencia_supera_volume_sem_depender_de_paradigma_ou_and(modo):
    m = Motor()
    ativar(m, modo)
    for i in range(12):
        inserir(m, str(i), 'N')
    inserir(m, 'emergencia', 'L', 'ambulancia', True)
    # Se as políticas aplicadas consultarem o avaliador AND, o teste falha.
    m.neurais.avaliar = lambda *a: pytest.fail('AND não deve governar o modo aplicado')
    e = m.avancar()
    assert e.controle['decisao']['proposta']['fase'] == 'F-LO'
    assert e.controle['transito']['criterio'] == 'emergencia'
    for _ in range(400):
        e = m.avancar()
        permissoes = m.controle.permissoes()
        assert all(not m.controle.conflitos[a][b] for a,b in combinations(permissoes,2))
        assert all(not m.controle.conflitos[a][b] for a in permissoes for b,ids in e.ocupacoes.items() if ids)
    assert e.metricas['total']['emergencias_atendidas'] == 1
    assert e.metricas['total']['emergencias_nao_atendidas'] == 0


@pytest.mark.parametrize('modelo', ['perceptron', 'adaline'])
def test_saida_aprendida_muda_a_escolha_de_fase(modelo):
    # Torneio entre duas fases: uma saída forçada distinta deve mudar a proposta real.
    propostas = []
    for bias in (-1., 1.):
        m = Motor()
        ativar(m, modelo)
        inserir(m, 'n', 'N')
        inserir(m, 'l', 'L')
        m.transito.documento['modelos'][modelo]['pesos'] = [bias, 0., 0., 0., 0.]
        e = m.avancar()
        propostas.append(e.controle['decisao']['proposta']['fase'])
        assert e.controle['transito']['comparacao']['saida'] == bias
    assert propostas == ['F-LO', 'F-NS']


def test_troca_de_modo_preserva_relogio_participantes_e_rng_e_retorna_a_paradigmas():
    m = Motor()
    inserir(m, 'carro', 'N')
    for _ in range(20):
        m.avancar()
    anterior = m.instantaneo()
    rng = m.gerador._fontes['N:carro'].getstate()
    ativar(m, 'urbano')
    e = m.avancar()
    assert e.step == anterior.step+1 and e.run_id == anterior.run_id
    assert e.controle['inicio_passo'] == anterior.controle['inicio_passo']
    assert e.participantes[0].id == anterior.participantes[0].id
    assert m.gerador._fontes['N:carro'].getstate() == rng
    comando(m, 'voltar', 'configurar_controlador', controlador='funcional')
    e = m.avancar()
    assert e.controle['operacao']['modo'] == 'paradigmas'
    assert not m.controle.adaptativo
    assert e.controle['transito'] is None


def test_pesos_indisponiveis_rejeitam_neural_mas_nao_urbano():
    m = Motor()
    m.transito.erro = 'Arquivo inválido'
    respostas = []
    m.receber_comando(dict(command_id='neural', tipo='configurar_operacao', parametros={'modo':'neural'}), respostas.append)
    m.avancar()
    assert respostas[0].confirmacao.status == 'rejeitado'
    assert m.operacao.modo == 'paradigmas'
    ativar(m, 'urbano')
    assert m.avancar().controle['operacao']['modo'] == 'urbano'


@pytest.mark.parametrize('modo', ['urbano', 'perceptron', 'adaline'])
def test_travessia_iniciada_permanece_protegida_na_troca(modo):
    m = Motor()
    for _ in range(387):
        m.avancar()
    comando(m, 'pedestre', 'inserir_participante', categoria='pedestre', travessia='N-TR', lado='A', quantidade=1)
    m.avancar()
    m.avancar()
    assert m.instantaneo().participantes[0].estado == 'em_travessia'
    ativar(m, modo)
    inserir(m, 'emergencia', 'N', 'ambulancia', True)
    viu_bloqueio = False
    for _ in range(200):
        e = m.avancar()
        if any(p.categoria == 'pedestre' for p in e.participantes):
            assert e.semaforos['N'] == 'vermelho'
            viu_bloqueio = True
    assert viu_bloqueio
    assert e.metricas['total']['emergencias_atendidas'] == 1


@pytest.mark.parametrize('modelo', ['perceptron', 'adaline'])
def test_emergencia_neural_antecipa_fechamento_sem_encurtar_transicao(modelo):
    m = Motor()
    ativar(m, modelo)
    inserir(m, 'normal', 'N')
    for _ in range(10):
        m.avancar()
    assert m.controle.estado == 'atendimento' and m.controle.fase == 'F-NS'
    inserir(m, 'emergencia', 'L', 'ambulancia', True)
    m.transito.comparar = lambda *a: pytest.fail('Emergência deve prevalecer sobre qualquer saída neural')
    e = m.avancar()
    assert e.controle['transito']['criterio'] == 'emergencia'
    assert e.controle['decisao']['proposta']['fase'] == 'F-LO'
    assert e.semaforos['N'] == 'amarelo'  # Só 0,1 s de verde foi cumprido.
    assert e.semaforos['L'] == 'vermelho'
    inicio = e.step
    for _ in range(29):
        e = m.avancar()
        assert e.semaforos['N'] == 'amarelo'
        assert e.semaforos['L'] == 'vermelho'
    for _ in range(10):
        e = m.avancar()
        assert all(cor == 'vermelho' for cor in e.semaforos.values())
    e = m.avancar()
    assert e.step - inicio == 40  # 3 s de amarelo + 1 s de liberação.
    assert e.semaforos['L'] == 'verde'
    # A preferência permanece até a ambulância alcançar a retenção, mesmo
    # com outra emergência mais nova e pedidos normais em outra fase.
    inserir(m, 'emergencia-mais-nova', 'N', 'ambulancia', True)
    ambulancia = next(p for p in e.participantes if p.categoria == 'ambulancia')
    for _ in range(200):
        e = m.avancar()
        assert e.controle['decisao']['proposta']['fase'] == 'F-LO'
        assert e.semaforos['L'] == 'verde'
        p = next(p for p in e.participantes if p.id == ambulancia.id)
        if p.instante_autorizacao is not None:
            break
    else:
        pytest.fail('Ambulância prioritária não recebeu autorização')
    m.fechar()


@pytest.mark.parametrize('modelo', ['perceptron', 'adaline'])
def test_emergencia_neural_fecha_pedestres_mas_aguarda_travessia_iniciada(modelo):
    m = Motor()
    ativar(m, modelo)
    comando(m, 'pedestre', 'inserir_participante', categoria='pedestre', travessia='N-TR', lado='A', quantidade=1)
    for _ in range(10):
        e = m.avancar()
    assert e.semaforos_pedestres['N-TR'] == 'verde'
    assert e.participantes[0].estado == 'em_travessia'
    inserir(m, 'emergencia', 'N', 'ambulancia', True)
    e = m.avancar()
    assert e.semaforos_pedestres['N-TR'] == 'vermelho'
    assert e.semaforos['N'] == 'vermelho'
    bloqueou = False
    for _ in range(250):
        # A decisão usa as ocupações do início do passo: não pode liberar
        # a ambulância enquanto o pedestre ainda atravessa.
        ocupado = bool(e.ocupacoes['N-TR'])
        e = m.avancar()
        if ocupado:
            assert e.semaforos['N'] == 'vermelho'
            bloqueou = True
        assert all(not m.controle.conflitos[a][b] for a in m.controle.permissoes()
                   for b, ids in e.ocupacoes.items() if ids)
    assert bloqueou
    assert e.metricas['total']['emergencias_atendidas'] == 1
    m.fechar()


@pytest.mark.parametrize('modo,emergencia', [('perceptron', False), ('adaline', False), ('urbano', True)])
def test_minimo_normal_preservado_sem_preempcao_neural(modo, emergencia):
    m = Motor()
    ativar(m, modo)
    inserir(m, 'normal', 'N')
    for _ in range(10):
        m.avancar()
    inserir(m, 'ambulancia', 'L', 'ambulancia', emergencia)
    for _ in range(29):
        e = m.avancar()
        assert e.semaforos['N'] == 'verde'
    m.fechar()


def test_preempcao_nao_altera_minimo_fixo_nem_libera_ocupacao_ou_fase_inelegivel():
    c = MaquinaSemaforica(ConfiguracaoControle(), lambda *a: None)
    c.aplicar(Proposta('transicionar', 'F-NS', 'teste'), 10, ())
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 11, (), prioridade_emergencia=True)
    assert c.estado == 'atendimento'  # Referência e paradigmas preservados.
    c.adaptativo = True
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 12, (), prioridade_emergencia=True)
    assert c.estado == 'encerramento'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 42, (), prioridade_emergencia=True)
    assert c.estado == 'liberacao'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 52, ('N-seguir_em_frente',), prioridade_emergencia=True)
    assert c.estado == 'liberacao'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 53, (), elegivel=False, prioridade_emergencia=True)
    assert c.estado == 'liberacao'
    c.aplicar(Proposta('transicionar', 'F-LO', 'teste'), 54, (), prioridade_emergencia=True)
    assert c.estado == 'atendimento' and c.fase == 'F-LO'
