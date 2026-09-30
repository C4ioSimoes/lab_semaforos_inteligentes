# Parâmetros atuais

Conferidos no código em 30/09/2026. Esta página documenta os valores existentes; não é um arquivo de configuração. As configurações de uma sessão em andamento podem ser diferentes dos padrões.

## Tempo e atendimento

| Parâmetro | Valor | Onde está definido |
| --- | --- | --- |
| Passo da simulação | 0,1 s | [motor.py](../motor_python/motor.py), `PASSO_SEGUNDOS` |
| Velocidade inicial / permitida | 1× / inteiros de 1× a 24× | [motor.py](../motor_python/motor.py), [modelos.py](../motor_python/modelos.py) |
| Atualizações da tela na execução acelerada | Até 20 por segundo real | `INTERVALO_PUBLICACAO`, em `motor.py` |
| Atendimento no modo Regras | 10 s por fase | [controle.py](../motor_python/controle.py), `verde_passos = 100` |
| Verde mínimo em Rede neural e Automático | 3 s | `MaquinaSemaforica.verde_minimo`, em `controle.py` |
| Verde máximo nos modos aplicados | Sem limite fixo; depende da decisão | `MaquinaSemaforica.verde_maximo` |
| Amarelo veicular | 3 s | `amarelo_passos = 30` |
| Liberação entre fases | Pelo menos 1 s; pode aguardar ocupações | `liberacao_passos = 10` |

## Prioridades

| Parâmetro | Modo Regras | Rede neural e Automático |
| --- | --- | --- |
| Espera que recebe prioridade | Acima de 30 s por padrão; ajustável até 3.600 s | Pelo menos 60 s |
| Emergência solicitada | Ligada por padrão; opção configurável | Tem precedência explícita |
| Prioridade de ônibus | Desligada por padrão; opção configurável | Sem a regra opcional dos quatro paradigmas |
| Critério ordinário | Maior número de pedidos pendentes | Preferência neural ou pontuação de fila e espera |

Fontes: [modelos.py](../motor_python/modelos.py), [controladores](../controladores/README.md) e [transito.py](../motor_python/transito.py).

No modo Regras, a idade do pedido conta desde a solicitação. Nos modos aplicados, a espera usada na decisão acumula tempo parado e espera externa. São definições diferentes.

## Participantes e geração

| Parâmetro | Valor atual | Fonte |
| --- | --- | --- |
| Velocidade do pedestre | 1,7 unidade/s | [pedestres.py](../motor_python/pedestres.py) |
| Velocidade de referência: carro / moto / ônibus / ambulância | 6 / 7 / 4 / 6 unidades/s | [movimento.py](../motor_python/movimento.py), `PERFIS` |
| Faixas por sentido | 2 | `FAIXAS`, em `movimento.py` |
| Borda das vias | ±90 unidades | `BORDA_VIA`, em `movimento.py` |
| Semente inicial | 42 | [gerador.py](../motor_python/gerador.py) |
| Geração ao iniciar o motor | Taxas zeradas | `ConfiguracaoGerador` |
| Capacidade padrão | 200 ativos e 2.000 pendentes | `Motor.__init__` |
| Limite de taxa efetiva | 6.000 chegadas/min por fonte | `LIMITE_TAXA_EFETIVA`, em `gerador.py` |

As unidades de distância são do simulador. Os valores não representam uma calibração de trânsito real.

Ao ligar a geração pela interface, o perfil-base por origem é 12 carros, 3 motos, 1 ônibus e 0,2 ambulância por minuto; por travessia, 8 pedestres por minuto. O controle de quantidade aplica o fator `0,4 + intensidade × 0,016`, com intensidade de 0 a 100. Na posição 50, o fator é **1,2**. Portanto, essas taxas-base não são as taxas efetivas da posição média. Fonte: [geracao.ts](../cena_3d/src/geracao.ts).

Desmarcar **Incluir pedestres** zera novas chegadas de pedestres. Pedidos já aceitos continuam no percurso. Acelerar o relógio não altera as taxas por minuto simulado.

## Treinamento da AND

| Parâmetro | Valor |
| --- | --- |
| Entradas / saída | 0 ou 1 / −1 ou +1 |
| Bias | Entrada fixa 1; pesos na ordem `[w0, w1, w2]` |
| Inicialização | `[0, 0, 0]` para cada modelo |
| Taxa / limite | 0,1 / 100 épocas |
| Parada do Perceptron | Uma época inteira sem erros |
| Parada do Adaline | Variação absoluta de SSE menor que `10⁻⁶`, ou limite |
| Resultado | Perceptron: 4 épocas; Adaline: 100; ambos acertam as quatro entradas |

Fonte: [notebook](../experimento_neural/and_perceptron_adaline.ipynb) e [pesos exportados](../pesos_neurais.json).

## Extensão de trânsito e ensaios

O treinamento de [treinar.py](../experimento_transito/treinar.py) usa semente **20260928**, 2.400 amostras sintéticas de treino e 1.200 de teste, cinco entradas, pesos iniciais zero, taxa 0,1 e até 100 épocas. Os pesos existentes registram Perceptron em 70 épocas com 100% de acerto no teste sintético; Adaline em 2 épocas com 93,75%.

Os [ensaios de trânsito](../experimento_transito/README.md) usam outra configuração: sementes **42, 73 e 101**, horizonte de **240 s**, três cenários e cinco políticas. Não usam o perfil do controle de quantidade da interface. A precisão no teste sintético e a espera medida no cruzamento são resultados distintos.
