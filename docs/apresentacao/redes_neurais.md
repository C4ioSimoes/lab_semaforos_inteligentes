# Redes Neurais Artificiais

O trabalho obrigatório é implementar Perceptron e Adaline em Python para aprender a porta AND. A entrega principal é [and_perceptron_adaline.ipynb](../../experimento_neural/and_perceptron_adaline.ipynb).

## 1. Apresente os dados

| x₁ | x₂ | Saída desejada |
| ---: | ---: | ---: |
| 0 | 0 | −1 |
| 0 | 1 | −1 |
| 1 | 0 | −1 |
| 1 | 1 | +1 |

O vetor completo é `[1, x1, x2]`. O primeiro valor corresponde ao bias. Ambos os modelos começam com pesos zero, taxa 0,1 e limite de 100 épocas. Na predição, a soma `u = w·x` retorna +1 quando `u ≥ 0`, e −1 nos demais casos.

## 2. Mostre o treinamento

Use os títulos das células para navegar:

| Parte do notebook | O que explicar |
| --- | --- |
| Base obrigatória e convenções | Entradas binárias, saída bipolar e bias |
| Perceptron | `treinar_perceptron`: calcula o sinal antes da correção |
| Adaline | `treinar_adaline`: corrige usando a saída linear |
| Predição e verificação exaustiva da AND | As quatro combinações com os pesos finais |
| Curvas de aprendizado | Erros por época e SSE, em escalas diferentes |
| Pesos, épocas e retas de decisão | Tabela e equação `w0 + w1·x1 + w2·x2 = 0` |
| Comparação acadêmica | Diferença entre erro de classificação e erro linear |
| Última célula | Consulta interativa de ambos os modelos |

**Perceptron:** `w ← w + 0,1 · (d − y) · x`. O erro depende da classe obtida após a função sinal. Para depois de uma época inteira sem classificação errada.

**Adaline:** `w ← w + 0,1 · (d − u) · x`. O erro é calculado antes do sinal. Ao final de cada época, calcula o SSE nas quatro amostras. Para quando a variação absoluta do SSE fica abaixo de `10⁻⁶`, ou ao atingir 100 épocas.

As regras foram implementadas manualmente. O experimento usa NumPy e Matplotlib, além da biblioteca padrão; Jupyter é a ferramenta para abrir o notebook.

## 3. Explique os resultados

| Modelo | Épocas | Motivo de parada | AND |
| --- | ---: | --- | --- |
| Perceptron | 4 | Época sem erro | 4 de 4 corretas |
| Adaline | 100 | Limite de épocas | 4 de 4 corretas |

O SSE final do Adaline é aproximadamente **1,01822337**. A última variação foi **0,0000206593**, acima da tolerância. Acertar todas as classes não significa zerar o erro linear.

O Perceptron conta erros discretos, por isso sua curva muda em saltos. O Adaline mede uma função quadrática contínua dos pesos, mas as atualizações por amostra não garantem queda em todas as épocas. Nesta execução, houve 55 aumentos de SSE. Mostre o gráfico observado e explique esse comportamento.

Os pesos completos estão em [pesos_neurais.json](../../pesos_neurais.json). No Perceptron, arredondar o bias pode mudar a classificação de uma entrada na fronteira; use o JSON original nos cálculos e a [tabela](../../experimento_neural/artefatos/tabela_pesos.png) na exposição.

## 4. Faça a predição interativa

Execute as células em ordem e, na última, informe `0` ou `1` para cada entrada. Mostre `(0, 0)` e `(1, 1)`. Digite um texto inválido para mostrar o tratamento de erro. Digite `sair` para encerrar.

As figuras e a [comparação em 13 linhas](../../experimento_neural/artefatos/comparacao.txt) já estão salvas. A [pasta do experimento](../../experimento_neural/README.md) explica como executar e validar tudo novamente.

## 5. Se houver tempo, mostre a integração

Em **Regras → Para estudar: lógica AND**, o motor usa duas entradas: pedido de atendimento e admissibilidade da fase. O resultado indica se a fase é elegível. O motor continua responsável pelos tempos e conflitos.

A aba **Rede neural** é uma extensão separada: usa cinco entradas e pesos de [pesos_transito.json](../../experimento_transito/pesos_transito.json), treinados com preferências sintéticas de trânsito. Não substitui o exercício AND nem comprova eficiência urbana pelo simples acerto das predições.
