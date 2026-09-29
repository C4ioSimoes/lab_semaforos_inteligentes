"""Ensaios pareados: mesmas chegadas, horizonte, sementes e geometria em cada política."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from motor_python.motor import Motor
from motor_python.pedestres import VELOCIDADE_PEDESTRE
from motor_python.gerador import ConfiguracaoGerador

PASTA = Path(__file__).resolve().parent
MODOS = ('baseline', 'imperativo', 'perceptron', 'adaline', 'urbano')
CENARIOS = {'desbalanceado': (36, 6), 'equilibrado': (22, 22), 'inversao_de_fluxo': (36, 6)}

def comando(m, ident, tipo, **parametros):
    def confirmar(r):
        if r.confirmacao.status != 'aplicado':
            raise RuntimeError(f'{tipo}: {r.confirmacao.erro}')
    m.receber_comando(dict(command_id=ident, tipo=tipo, parametros=parametros), confirmar)

def geracao(semente, taxas):
    c = ConfiguracaoGerador(semente=semente)
    for origem in 'NSLO':
        c.taxas_veiculares[origem]['carro'] = taxas[0 if origem in 'NS' else 1]
        c.taxas_veiculares[origem]['ambulancia'] = .3
    for travessia in c.taxas_pedestres:
        c.taxas_pedestres[travessia] = 1
    return c.model_dump()

def executar(modo, cenario, semente, segundos):
    m = Motor()
    try:
        if modo in ('baseline', 'imperativo'):
            comando(m, 'modo', 'configurar_controlador', controlador=modo)
        else:
            comando(m, 'modo', 'configurar_operacao', modo='urbano' if modo == 'urbano' else 'neural', modelo=modo if modo != 'urbano' else 'perceptron')
        taxas = CENARIOS[cenario]
        comando(m, 'gerador', 'configurar_gerador', **geracao(semente, taxas))
        for passo in range(segundos * 10):
            if cenario == 'inversao_de_fluxo' and passo == segundos * 5:
                comando(m, 'inverter', 'configurar_gerador', **geracao(semente, tuple(reversed(taxas))))
            e = m.avancar()
            if e.demanda['motivo_interrupcao']:
                raise RuntimeError(e.demanda['motivo_interrupcao'])
            for a in m.controle.permissoes():
                for b, ids in e.ocupacoes.items():
                    if ids and m.controle.conflitos[a][b]:
                        raise AssertionError(f'Conflito: {a}, {b}')
        t = e.metricas['total']
        total_espera = (t['espera_concluidos_total_media']*t['concluidos'] +
                       t['espera_ativos_interna_total']+t['espera_ativos_externa_total']+t['espera_pendentes_externa_total'])
        return {'cenario': cenario, 'semente': semente, 'modo': modo, 'segundos': segundos,
                'solicitados': sum(m._solicitados.values()), 'concluidos': t['concluidos'],
                'em_sistema': t['ativos']+t['pendentes'],
                'espera_acumulada_por_solicitado': total_espera/sum(m._solicitados.values()) if sum(m._solicitados.values()) else 0,
                'fila_media': t['fila_interna_media']+t['fila_externa_media'],
                'espera_concluidos': t['espera_concluidos_total_media'],
                'emergencias_atendidas': t['emergencias_atendidas'],
                'emergencias_nao_atendidas': t['emergencias_nao_atendidas'],
                'tempo_emergencia': t['emergencia_tempo_ate_atendimento_medio'],
                'espera_emergencias_pendentes': t['emergencia_espera_nao_atendidos_total'],
                'trocas': sum(e.tipo=='transicao_semaforica' and e.resultado['estado']=='atendimento' for e in m._eventos)}
    finally:
        m.fechar()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--segundos',type=int,default=240)
    p.add_argument('--sementes',type=int,nargs='+',default=[42,73,101])
    p.add_argument('--saida',type=Path,default=PASTA/'resultados.json')
    args=p.parse_args()
    resultados=[]
    for cenario in CENARIOS:
        for semente in args.sementes:
            for modo in MODOS:
                r=executar(modo,cenario,semente,args.segundos)
                resultados.append(r)
                print(f'{cenario} {semente} {modo}: espera={r["espera_acumulada_por_solicitado"]:.2f}s fila={r["fila_media"]:.2f} concluidos={r["concluidos"]}',flush=True)
    for cenario in CENARIOS:
        for semente in args.sementes:
            assert len({r['solicitados'] for r in resultados if r['cenario']==cenario and r['semente']==semente}) == 1
    args.saida.write_text(json.dumps({'velocidade_pedestre': VELOCIDADE_PEDESTRE, 'metodologia':'Ensaios pareados; espera acumulada até o horizonte inclui concluídos, ativos e pendentes. Não estima a espera futura dos ainda presentes.', 'resultados':resultados},indent=2)+'\n')

if __name__=='__main__':
    main()
