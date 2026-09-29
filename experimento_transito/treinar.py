"""Extensão aplicada; não substitui o notebook AND exigido pelo enunciado.
Aprendizado supervisionado de preferências sintéticas entre duas fases.
Somente NumPy/Matplotlib, com regras implementadas manualmente.
"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PASTA = Path(__file__).resolve().parent

def amostras(rng, n):
    # Diferenças normalizadas: fila próxima, espera acumulada e aproximações.
    valores = rng.uniform(-1, 1, (n, 3))
    troca = rng.integers(0, 2, n)
    x = np.column_stack((np.ones(n), valores, troca))
    utilidade = valores @ np.array([1., .5, .2]) - .12 * troca
    return x, np.where(utilidade >= 0, 1., -1.)

def treinar():
    rng = np.random.default_rng(20260928)
    x, d = amostras(rng, 2400)
    teste, alvo = amostras(rng, 1200)
    modelos = {}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, nome in zip(axes, ('perceptron', 'adaline')):
        w = np.zeros(x.shape[1])
        historico = []
        anterior = None
        for epoca in range(1, 101):
            erros = 0
            for entrada, desejado in zip(x, d):
                u = float(w @ entrada)
                y = 1 if u >= 0 else -1
                erros += y != desejado
                w += .1 * (desejado - (y if nome == 'perceptron' else u)) * entrada
            sse = float(np.sum((d - x @ w) ** 2))
            historico.append({'epoca': epoca, 'erros': int(erros), 'sse': sse})
            print(f'{nome} | época {epoca} | erros={erros} | SSE={sse:.6f}')
            if (nome == 'perceptron' and erros == 0) or (nome == 'adaline' and anterior is not None and abs(sse-anterior) < 1e-6):
                break
            anterior = sse
        modelos[nome] = {'pesos': w.tolist(), 'epocas': epoca, 'taxa': .1,
                         'acuracia_teste_sintetico': float(np.mean(np.where(teste @ w >= 0, 1, -1) == alvo)),
                         'historico': historico}
        ax.plot([h['epoca'] for h in historico], [h['erros' if nome == 'perceptron' else 'sse'] for h in historico])
        ax.set(title=nome.title(), xlabel='Época', ylabel='Erros de classificação' if nome == 'perceptron' else 'SSE')
    fig.tight_layout()
    fig.savefig(PASTA / 'aprendizado.png', dpi=140)
    documento = {'versao': 1, 'semente': 20260928, 'amostras_treino': len(x), 'amostras_teste': len(teste),
                 'origem': 'Preferências sintéticas: sinal(delta_fila + 0.5*delta_espera + 0.2*delta_aproximacao - 0.12*troca). Não são dados reais.',
                 'entradas': ['bias', 'delta_fila_proxima/20', 'delta_espera/60', 'delta_aproximacao/20', 'troca'],
                 'modelos': modelos}
    (PASTA / 'pesos_transito.json').write_text(json.dumps(documento, indent=2)+'\n')
    print(json.dumps({n: {k:v for k,v in m.items() if k!='historico'} for n,m in modelos.items()}, indent=2))

if __name__ == '__main__':
    treinar()
