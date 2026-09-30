# Experimento neural — AND bipolar

Abra [and_perceptron_adaline.ipynb](and_perceptron_adaline.ipynb). O notebook é
independente do laboratório e contém treinamento manual, resultados executados,
gráficos, tabela, comparação em Markdown de 13 linhas, exportação JSON e um laço interativo para ambos os modelos.
As únicas bibliotecas importadas pelo experimento são **NumPy e Matplotlib**,
além de módulos da biblioteca padrão do Python. Nenhum modelo pronto é utilizado.

Para apresentar, siga o [roteiro de Redes Neurais](../docs/apresentacao/redes_neurais.md). O [índice das figuras](artefatos/README.md) indica o que mostrar em cada etapa.

## Mapa da pasta

| Arquivo | Uso |
| --- | --- |
| [and_perceptron_adaline.ipynb](and_perceptron_adaline.ipynb) | Entrega principal: teoria, treinamento, comparação e interação |
| [artefatos/](artefatos/README.md) | Figuras e texto da comparação já produzidos |
| [executar_notebook.py](executar_notebook.py) | Executar o notebook automaticamente, sem a célula de teclado |
| [verificar_experimento.py](verificar_experimento.py) | Validar treinamento, pesos, gráficos e entradas interativas |
| `requirements.in` / `requirements.txt` | Bibliotecas numéricas e gráficas; dependências diretas / versões fixadas |
| `requirements-jupyter.in` / `requirements-jupyter.txt` | Ferramentas adicionais para abrir e executar o notebook |

O arquivo de pesos utilizado pelo motor fica na raiz: [pesos_neurais.json](../pesos_neurais.json).

## Abrir e executar

Ambiente verificado: Python **3.12.3**, NumPy **2.2.6**, Matplotlib **3.10.3**.
Use um ambiente próprio, sem instalar as dependências de FastAPI ou Prolog:

```bash
cd experimento_neural
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-jupyter.txt
python -m jupyter lab and_perceptron_adaline.ipynb
```

Execute as células em ordem. A última célula pede entradas pelo `input()`:
digite `0` ou `1` para cada valor. Texto inválido repete a solicitação.
`sair`, inclusive com espaços ou maiúsculas, encerra a interação e pode ser
digitado em qualquer uma das duas entradas. Cada par informado exibe a predição
do Perceptron e a do Adaline, usando seus respectivos pesos treinados.

Para reproduzir automaticamente os cálculos e salvar o notebook com saídas:

```bash
python executar_notebook.py
python verificar_experimento.py
```

`executar_notebook.py` usa a infraestrutura Jupyter em um kernel novo e pula
apenas a célula de teclado, marcada `interativa`. O código do experimento não
importa Jupyter. `verificar_experimento.py` exercita também o laço conjunto com
entradas programadas, casos inválidos, `sair` e fim da entrada; grava artefatos
de teste somente em pasta temporária. Os 15 testes usam biblioteca padrão,
NumPy e Matplotlib e não precisam de Jupyter ou do motor.

`requirements.txt` fixa as dependências numéricas e gráficas, incluindo suas
dependências transitivas. `requirements-jupyter.txt` acrescenta as ferramentas
de edição/execução; os arquivos `.in` registram dependências diretas. Para somente
executar os testes, basta instalar `requirements.txt`. Após a instalação, todo
o experimento funciona localmente, sem rede, servidor ou dados externos.

## Convenções matemáticas

- Base fixa: `(0,0)→−1`, `(0,1)→−1`, `(1,0)→−1`, `(1,1)→+1`, nessa ordem.
- Vetor de entrada `[1,x1,x2]`; pesos `[w0,w1,w2]`; `w0` é o bias.
- Cada modelo recebe sua própria cópia de `[0,0,0]`, com `η=0,1` e até 100 épocas.
- Sinal: `+1` se `u >= 0`, senão `−1`. Não há tolerância adicional no sinal.
- Perceptron: `w ← w + η(d−y)x`; contabiliza erros antes de cada atualização e
  para após uma época inteira sem erro.
- Adaline: `w ← w + η(d−u)x`, sem sinal no treinamento. SSE é recalculado nas
  quatro amostras com os pesos do final de cada época; compara variações somente
  a partir da segunda. Para com `abs(SSE_atual−SSE_anterior) < 1e-6` ou em 100 épocas.

O notebook imprime métricas por época e as quatro atualizações da primeira época
de cada modelo. Os históricos preservam os pesos finais de cada época.

## Resultados efetivamente obtidos

| Modelo | Épocas | Motivo de parada | Verificação da AND |
| --- | ---: | --- | --- |
| Perceptron | 4 | Época inteira sem erro | 4/4 combinações corretas |
| Adaline | 100 | Limite de épocas | 4/4 combinações corretas |

O SSE final do Adaline foi **1,0182233733404706**, com última variação de
**0,00002065933792971819**. Portanto, a tolerância de `1e-6` **não foi atingida**.
O limite não foi estendido nem a taxa modificada para produzir outro resultado.
SSE residual e acerto da classificação são medidas diferentes.

O Perceptron produziu os pesos `[-0.4000000000000001, 0.4, 0.2]`. A soma para
`(1,0)` é aproximadamente `−5,55e−17`. Arredondar o bias para `−0.4` mudaria essa
saída para zero e, pela convenção de sinal, para `+1`: uma divergência da AND.
Por isso, a tabela arredonda apenas a apresentação; o JSON conserva todos os
dígitos necessários ao round-trip de `float64`. O validador detecta essa divergência.
O resultado numérico observado não representa uma margem robusta de separação.

## Arquivos produzidos

- [pesos_neurais.json](../pesos_neurais.json): pesos completos, metadados e históricos, na raiz do projeto.
- [Curvas de aprendizado](artefatos/curvas_aprendizado.png): subplots com erros
  de classificação do Perceptron e SSE do Adaline, em escalas identificadas.
- [Tabela de pesos](artefatos/tabela_pesos.png): pesos, épocas e equações das retas.
- [Retas de decisão](artefatos/retas_decisao.png): fronteiras e as quatro amostras.
- [Comparação acadêmica](artefatos/comparacao.txt): 13 linhas geradas dos resultados.

Todas as figuras também são exportadas em SVG para o relatório. Ao abrir pela
raiz ou pela pasta do experimento, as figuras são gravadas em
`experimento_neural/artefatos` e os pesos em `pesos_neurais.json` na raiz. Se o
notebook for copiado para outro diretório, usa o diretório atual. A função
`salvar_pesos_neurais` valida e atualiza o JSON com os resultados da execução.
A exportação acontece antes da interação, para não depender do teclado.

## Contrato de exportação para o motor

O esquema tem `schema_version: "1.0"`, `experimento: "and_bipolar"`, versão do
experimento, `dtype_calculo: "float64"`, ordem dos pesos, convenções de entrada
e saída, base de treino e versões de Python/NumPy/Matplotlib.
`modelos.perceptron` e `modelos.adaline` contêm:

- identificação/versão, indicador de treinamento e pesos `[w0,w1,w2]`;
- inicialização, taxa, ordem das amostras, máximo e número efetivo de épocas;
- regras de atualização, métricas, critérios/tolerância e motivo de parada;
- histórico por época e verificação das quatro combinações.

A célula `validar_documento` rejeita versão/convenções incompatíveis, modelos
sem treinamento, pesos com tamanho/tipo inválido ou valores não finitos,
parâmetros incompatíveis e inconsistência entre pesos finais e histórico.
Ela recalcula as quatro combinações e retorna `apto_para_ativacao` e
`divergencias` por modelo. O arquivo é lido de volta e validado após a exportação.
Declarar `correto: true` no arquivo não substitui essa verificação.

O motor carrega o JSON ao iniciar, valida o contrato e recalcula as quatro
predições antes de permitir a ativação. Em cada avaliação, `x1` representa uma
solicitação de atendimento e `x2`, a admissibilidade. O resultado indica
se a fase é elegível; não é uma porcentagem de confiança.

Na interface, com o modo Regras ativo, abra **Regras → Para estudar: lógica AND**,
escolha o modelo e clique em **Aplicar ao exercício**. Os cálculos aparecem em
**Ver cálculos da AND**. A prioridade e a proteção das transições continuam no
motor. Aprender AND não demonstra ganho de desempenho no trânsito.

O arquivo utilizado pelo motor é `pesos_neurais.json`, na raiz. A antiga cópia
`pesos_and.json` foi guardada no [histórico](../docs/historico/README.md).
Os pesos do outro treinamento, aplicado ao trânsito, ficam em
[experimento_transito](../experimento_transito/README.md).

## Referências

As Seções 11 e 12 da [especificação original](../docs/historico/requisitos-2026-09-13.md) definem os algoritmos e
parâmetros. As operações de infraestrutura são
[numpy.dot](https://numpy.org/doc/stable/reference/generated/numpy.dot.html) e
[matplotlib.pyplot.subplots](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.subplots.html).
