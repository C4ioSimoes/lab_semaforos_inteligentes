import pytest

from motor_python.controle import ConfiguracaoControle
from motor_python.gerador import ConfiguracaoGerador
from motor_python.motor import Motor
from motor_python.movimento import PERFIS


def inserir(motor, origem, categoria, identificador):
    motor.receber_comando({
        'command_id': identificador, 'tipo': 'inserir_participante',
        'parametros': {'categoria': categoria, 'origem': origem,
                       'movimento': 'seguir_em_frente', 'quantidade': 1},
    }, lambda _: None)


@pytest.mark.parametrize('origem,sinal', [('N', -1), ('S', 1), ('L', -1), ('O', 1)])
@pytest.mark.parametrize('categoria', PERFIS)
def test_duas_faixas_cabem_na_pista_e_respeitam_retencao(origem, sinal, categoria):
    motor = Motor(configuracao_controle=ConfiguracaoControle(liberacao_passos=1000))
    for i in range(2):
        inserir(motor, origem, categoria, str(i))
    estado = motor.avancar()
    assert len(estado.participantes) == 2
    assert [p.faixa for p in estado.participantes] == ['externa', 'interna']
    for _ in range(240):
        estado = motor.avancar()
        for p in estado.participantes:
            lateral = p.posicao.x if origem in 'NS' else p.posicao.z
            longitudinal = p.posicao.z if origem in 'NS' else p.posicao.x
            assert lateral == sinal * (4.5 if p.faixa == 'externa' else 1.5)
            assert 0 < abs(lateral) - p.dimensoes.largura / 2
            assert abs(lateral) + p.dimensoes.largura / 2 < 6
            assert abs(longitudinal) - p.dimensoes.comprimento / 2 >= 11.725 - 1e-8
            assert estado.semaforos[origem] == 'vermelho'
    assert all(p.estado == 'aguardando_retencao' for p in estado.participantes)
    assert estado.filas['internas'][origem] == 2


@pytest.mark.parametrize('origem', 'NSLO')
def test_moto_na_faixa_livre_avanca_independente_do_onibus(origem):
    motor = Motor(configuracao_controle=ConfiguracaoControle(liberacao_passos=1000))
    inserir(motor, origem, 'onibus', 'onibus')
    inserir(motor, origem, 'moto', 'moto')
    inicial = motor.avancar()
    for _ in range(30):
        estado = motor.avancar()
    for antes, depois in zip(inicial.participantes, estado.participantes):
        eixo = 'z' if origem in 'NS' else 'x'
        deslocamento = abs(getattr(depois.posicao, eixo) - getattr(antes.posicao, eixo))
        assert deslocamento == pytest.approx(PERFIS[depois.categoria].velocidade * 3)
        assert depois.faixa == antes.faixa
    inserir(motor, origem, 'carro', 'terceiro')
    terceiro = motor.avancar().participantes[-1]
    # Ambas as entradas estão livres; a fila da moto ocupa menos espaço.
    assert terceiro.faixa == 'interna'


def test_geracao_automatica_distribui_nas_duas_faixas_sem_alterar_reprodutibilidade():
    config = ConfiguracaoGerador()
    config.taxas_veiculares['N']['carro'] = 600
    motores = [Motor(), Motor()]
    for motor in motores:
        motor.receber_comando({'command_id': 'gerador', 'tipo': 'configurar_gerador',
                              'parametros': config.model_dump()}, lambda _: None)
    for _ in range(100):
        estados = [m.avancar() for m in motores]
        a, b = [[(p.categoria, p.faixa, p.posicao, p.instante_inserido)
                 for p in e.participantes] for e in estados]
        assert a == b
    assert {p.faixa for p in estados[0].participantes} == {'externa', 'interna'}
    assert all(p.fonte == 'automatico' for p in estados[0].participantes)


def test_segunda_faixa_respeita_limite_global_sem_perder_pedidos():
    motor = Motor(limite_ativos=1)
    for i in range(3):
        inserir(motor, 'N', 'carro', str(i))
    estado = motor.avancar()
    assert len(estado.participantes) == 1
    assert len(estado.solicitacoes) == 2
    assert 'ativos' in estado.demanda['motivo_interrupcao']
    assert motor.avancar() == estado
