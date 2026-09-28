"""CSV de métricas acumuladas por intervalo, origem e categoria (RF39)."""
import csv
from io import StringIO


def metricas_csv(experimento):
    linhas = []
    for amostra in experimento['historico_metricas']:
        metricas = amostra['metricas']
        comuns = {k: amostra[k] for k in ('step', 'tempo_simulado', 'fase', 'estado_transicao', 'controlador', 'modelo', 'propostas_bloqueadas')}
        comuns.update(run_id=experimento['run_id'], versao_motor=experimento['versao_motor'],
                      intervalo_inicio=0, intervalo_fim=amostra['tempo_simulado'],
                      motivo_encerramento=experimento['motivo_encerramento'],
                      passo_exportacao=experimento['passo_exportacao'],
                      chegadas_solicitadas=sum(amostra['solicitados'].values()),
                      chegadas_admitidas=sum(amostra['admitidos'].values()),
                      chegadas_recusadas=sum(amostra['recusados'].values()))
        grupos = [('total', '', '', metricas['total'])]
        grupos += [('origem', o, '', g) for o, g in metricas['por_origem'].items()]
        grupos += [('categoria', '', c, g) for c, g in metricas['por_categoria'].items()]
        grupos += [('origem_categoria', o, c, g) for o, categorias in metricas['por_origem_categoria'].items() for c, g in categorias.items()]
        for escopo, origem, categoria, grupo in grupos:
            linhas.append({**comuns, 'escopo': escopo, 'origem': origem, 'categoria': categoria, **grupo})
    arquivo = StringIO(newline='')
    escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
    escritor.writeheader()
    escritor.writerows(linhas)
    return arquivo.getvalue()
