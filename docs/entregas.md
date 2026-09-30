# Entregas das disciplinas

Este índice relaciona os dois enunciados fornecidos com os materiais do repositório. O notebook é a entrega principal de Redes Neurais; a análise dos quatro controladores é a de Paradigmas. O Automático e a rede aplicada ao trânsito são extensões do laboratório.

## Redes Neurais Artificiais

Referência: `Trabalho_Redes_Neurais_Artificiais.docx`, tema Perceptron e Adaline aprendendo AND.

| Pedido do trabalho | Onde encontrar |
| --- | --- |
| Implementação manual com NumPy e Matplotlib, sem bibliotecas de modelos prontos | [Notebook](../experimento_neural/and_perceptron_adaline.ipynb), células `ambiente`, `treinar-perceptron` e `treinar-adaline` |
| Entradas binárias, saída bipolar, bias e sinal com limiar zero | Notebook, células `base-and` e `dados-e-sinal` |
| Mesma inicialização, taxa 0,1 e limite de 100 épocas | Notebook, célula `ambiente`: pesos zero, `ETA`, `MAX_EPOCAS` |
| Regra de Rosenblatt, contagem impressa dos erros e parada em época sem erro | Notebook, célula `treinar-perceptron` |
| Regra delta com saída linear, SSE impresso e parada por variação menor que 10⁻⁶ ou limite | Notebook, célula `treinar-adaline` |
| Predição interativa, saída com `sair` e tratamento de entradas inválidas | Notebook, células `funcoes-interativas` e `interacao-final`; laço compartilhado mostra ambos os modelos |
| Curvas de aprendizado, com escalas identificadas | Notebook, célula `curvas`; [figura PNG](../experimento_neural/artefatos/curvas_aprendizado.png) e [SVG](../experimento_neural/artefatos/curvas_aprendizado.svg) |
| Tabela com pesos, épocas e equação da reta | Notebook, célula `tabela`; [figura PNG](../experimento_neural/artefatos/tabela_pesos.png) e [SVG](../experimento_neural/artefatos/tabela_pesos.svg) |
| Texto de 10 a 15 linhas sobre as curvas e o ponto onde cada modelo mede o erro | Notebook, célula `comparacao-texto`, com 13 linhas; reproduzido no [README](../README.md#comparação-pedida-no-trabalho--13-linhas) |

As células são identificadas pelo campo `id` do notebook. No Jupyter, use os títulos de seção para encontrá-las; o [roteiro de apresentação](apresentacao/redes_neurais.md) indica a ordem.

O notebook também inclui [retas de decisão](../experimento_neural/artefatos/retas_decisao.png), verificação das quatro combinações e exportação dos [pesos completos](../pesos_neurais.json). A [comparação em texto](../experimento_neural/artefatos/comparacao.txt) acrescenta os números observados nessa execução.

O Perceptron parou em 4 épocas sem erro. O Adaline acertou as quatro entradas, mas atingiu 100 épocas sem cumprir a tolerância do SSE. Esse resultado é apresentado como foi obtido; os critérios não foram alterados para forçar uma convergência.

## Paradigmas da Programação

Referência: `Trabalho_paradigmas_de_programacao_av1.docx`, o mesmo problema em quatro paradigmas. O foco do enunciado é a análise comparativa.

| Pedido do trabalho | Onde encontrar |
| --- | --- |
| Um problema comum | Escolher a próxima fase de atendimento do cruzamento; entrada e saída em [contratos.py](../controladores/contratos.py) |
| Implementação imperativa | [imperativo.py](../controladores/imperativo.py): laços, variáveis e condicionais |
| Implementação orientada a objetos | [orientado_objetos.py](../controladores/orientado_objetos.py): demanda, regras e política |
| Implementação funcional | [funcional.py](../controladores/funcional.py): funções puras e dados imutáveis |
| Implementação lógica | [logico.pl](../controladores/logico.pl): fatos e regras consultados pelo adaptador Python |
| Análise do que é confortável ou difícil em cada paradigma | [Comparação no README](../README.md#quatro-paradigmas-o-mesmo-problema) e [roteiro de Paradigmas](apresentacao/paradigmas.md), com o mesmo exemplo e uma mudança de prioridade |
| Explicação durante a apresentação | [Sequência de arquivos e trechos](apresentacao/paradigmas.md), para apoiar a exposição de cada integrante |

Os testes de [equivalência](../tests/test_paradigmas.py) e [integração Prolog](../tests/test_prolog.py) apoiam a análise. Eles não substituem a discussão sobre clareza, manutenção, organização e integração.

## Demonstração de desempenho

O modo **Automático** teve a menor espera média e a menor fila média nos três cenários dos 45 ensaios atuais. A [tabela completa](../experimento_transito/relatorio.md) inclui as outras medidas; o [gráfico](imagens/desempenho.png) compara a espera. Esse resultado não transforma o Automático em uma rede neural nem em um quinto paradigma equivalente: sua política é diferente.

O enunciado de Paradigmas não solicita gráficos de desempenho. O de Redes Neurais solicita curvas do treinamento da AND. A comparação de trânsito complementa essas entregas e deve ser apresentada com essa distinção.
