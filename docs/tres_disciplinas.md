# Três entregas, três formas de usar o laboratório

A interface separa **Paradigmas**, **Redes neurais** e **Semáforo urbano**. Abrir uma aba não muda a simulação. O aviso **Modo ativo** mostra a política que está comandando os sinais; use o botão de ativação da respectiva aba. Trocar de modo preserva veículos, relógio e demanda. Para uma comparação científica, use execuções novas, pois as métricas da sessão acumulam desde o início.

## 1. Paradigmas da programação

O enunciado pede o mesmo problema em quatro paradigmas e dá prioridade à análise comparativa. As quatro implementações existentes foram preservadas: recebem o mesmo estado, aplicam a mesma ordem de prioridades e produzem propostas equivalentes. Aplicar um controlador nesta aba volta ao modo Paradigmas e aos tempos originais de 10 s de atendimento. A baseline fixa é uma referência adicional, não um quinto paradigma equivalente.

| Dimensão | Imperativo | Orientado a objetos | Funcional | Lógico |
|---|---|---|---|---|
| Arquivo | `controladores/imperativo.py` | `controladores/orientado_objetos.py` | `controladores/funcional.py` | `controladores/logico.pl` |
| Representação do problema | Variáveis, laços e condicionais | Objetos de demanda, regras e política | Transformações de dados imutáveis | Fatos, relações e regras |
| Encontrar demanda | Acumula quantidade e pedidos mais antigos em um laço | `DemandaDaFase` encapsula os pedidos da fase | `filter`, `map`, `min` e tuplas | `include`, `maplist` e predicados |
| Prioridades | Cadeia de `if/elif` | Classes `RegraEmergencia`, `RegraEspera`, `RegraOnibus`, `RegraVolume` | Tupla ordenada de condições e funções puras | `prioridade/7` e fatos `precedencia/2` |
| Seleção | Atualiza a variável `melhor` | `PoliticaPrioridades.selecionar` | `min` com uma chave | `findall` e `keysort` |
| Onde é confortável | Seguir uma decisão passo a passo | Acrescentar e organizar regras de domínio | Testar e compor transformações sem efeitos colaterais | Expressar relações, elegibilidade e precedência |
| Onde exige cuidado | Alterar vários acumuladores sem inconsistência | Mais classes e indireções para uma política pequena | Expressões compostas podem dificultar a leitura de iniciantes | Ordem das cláusulas, cortes e integração Python/Prolog |
| Efeitos sobre o mundo | Nenhum: devolve uma proposta | Nenhum: devolve uma proposta | Funções da política não alteram o estado | Consulta usa estado local, sem `assert/retract` persistente |

### Exemplo para apresentar

Há muitos carros no eixo norte–sul e uma ambulância com solicitação de emergência no eixo leste–oeste. Com a prioridade habilitada, as quatro implementações classificam a emergência antes do volume comum. Se ainda houver atendimento mínimo ou uma travessia conflitante em andamento, a fase desejada pode ser escolhida sem estar autorizada a abrir. A máquina semafórica comum executa a transição.

No imperativo, explique como `emergencia` é acumulada e vira a primeira chave. No OO, acompanhe `DemandaDaFase` → `RegraEmergencia` → `PoliticaPrioridades`. No funcional, acompanhe os filtros dos pedidos e a seleção pelo menor valor da chave. No Prolog, mostre o predicado `emergencia/1`, a cláusula de prioridade e a ordenação. Não atribua diferença de eficiência do trânsito à sintaxe do paradigma: a política é a mesma.

### Análise de uma mudança

Para inserir uma prioridade nova, o imperativo ganha um ramo e, possivelmente, um acumulador; o OO ganha uma regra e sua posição na lista; o funcional ganha uma condição/transformação; o lógico ganha cláusulas e precedência. Em todos os casos é preciso decidir a posição da nova regra e testar empates. Objetos facilitam separar responsabilidades, mas custam estrutura. Funções puras facilitam testes, mas não eliminam a complexidade do domínio. Prolog aproxima o código das relações, porém a ordem das regras e o protocolo entre processos precisam ser explicados. Nenhum desses estilos é automaticamente superior para todo problema.

A evidência está em `tests/test_paradigmas.py` e `tests/test_prolog.py`: prioridades, empates, estados aleatórios, independência da ordem de entrada e execuções completas equivalentes. Os testes de equivalência demonstram a política; não são um benchmark de tempo de CPU entre linguagens.

## 2. Redes neurais artificiais

### Parte obrigatória do documento

O arquivo `experimento_neural/and_perceptron_adaline.ipynb` continua sendo a entrega do enunciado: entradas binárias, saída bipolar, bias, η=0,1, até 100 épocas, regras implementadas manualmente, curvas, pesos, reta de decisão e predição interativa. Nada na extensão altera esses pesos ou esse treinamento.

- Perceptron: calcula `y = sinal(w·x)` e atualiza `w += η(d-y)x`. Uma classificação correta produz erro zero.
- Adaline: atualiza `w += η(d-w·x)x` usando a saída linear. Mesmo uma classificação correta pode produzir uma atualização. Usa o sinal na predição final.

A AND aprendida não pode superar a AND direta nas mesmas quatro entradas. A eficácia no trânsito é uma extensão separada, não uma exigência inventada para o enunciado.

### Extensão aplicada ao trânsito

Na aba Redes neurais, escolha **Rede aplicada ao trânsito** e clique em **Ativar rede no trânsito**. Isso ativa uma política própria, independente do controlador selecionado em Paradigmas. A seleção inferior **Modelo neural** continua sendo o avaliador AND acadêmico e não ativa a extensão.

Cada rede faz comparações entre duas fases usando:

```
x = [1,
     (fila_próxima_candidata − fila_próxima_atual) / 20,
     (maior_espera_candidata − maior_espera_atual) / 60,
     (aproximações_candidata − aproximações_atual) / 20,
     custo_de_troca_ativo]
u = w·x
y = +1 se u ≥ 0; caso contrário, −1
```

`+1` prefere a candidata; `−1` conserva a preferência atual. Uma sequência determinística de comparações escolhe a fase. Na fase verde atual, o atributo de troca representa a perda de tempo ao interromper o atendimento. Cada rede tem pesos próprios, treinados do zero. Alterar sua saída altera a proposta real, o que é verificado por teste; não se trata apenas de atualizar um diagnóstico.

O treinamento usa 2.400 exemplos **sintéticos**, rotulados pela preferência `sinal(Δfila + 0,5·Δespera + 0,2·Δaproximação − 0,12·troca)`, e 1.200 exemplos separados para teste. A semente é 20260928. Ambas usam inicialização zero, η=0,1 e até 100 épocas, com as mesmas regras de aprendizagem do experimento acadêmico. Não são dados coletados de uma cidade, aprendizagem por reforço ou uma otimização comprovada do trânsito. A rede aprende a imitar essa preferência, com erros e pesos diferentes. As diferenças sintéticas de treino variam entre −1 e +1 após normalização; situações maiores na simulação exigem extrapolação e não têm acurácia garantida.

Emergências e espera prolongada são prioridades explícitas compartilhadas pelos modos aplicados. As redes não são responsáveis pela proteção contra conflitos. O ganho em relação aos paradigmas vem do conjunto **preferência de atendimento + verde variável**, e não prova superioridade intrínseca de uma rede sobre qualquer algoritmo de regras.

Execute a partir da raiz:

```bash
experimento_neural/.venv/bin/python experimento_transito/treinar.py
```

Caso o ambiente ainda não exista, instale as dependências de `experimento_neural/requirements.txt` em um ambiente virtual. O programa produz `pesos_transito.json` e `aprendizado.png`, imprime as épocas e informa a acurácia sintética. Reinicie o motor para carregar novos pesos. O treinamento não acontece durante a simulação.

Para a apresentação: mostre primeiro a AND e as regras de atualização; depois ative cada rede na extensão, observe entradas, pesos, soma e preferência no painel; por último abra a comparação medida. Acerto no conjunto sintético e redução de espera são métricas diferentes.

## 3. Semáforo urbano

Clique em **Semáforo urbano → Ativar semáforo urbano**. Esse modo não consulta os quatro controladores nem os pesos neurais. Sua política compara:

```
pontuação = participantes próximos + 0,2·aproximações
            + maior espera / 6 + bônus de continuidade
```

O bônus é 7 quando a fase já está verde e ainda há participantes próximos. Ele representa o custo de interromper uma corrente que está escoando. As aproximações próximas são estimadas pela posição, velocidade de referência e distância até a retenção, com horizonte de 6 s. Pedestres pendentes são considerados prontos. A espera usada na pontuação acumula tempo parado e espera externa; não confunde todo o percurso de aproximação com fila.

A emergência solicitada mais antiga prevalece. Sem emergência, uma espera acumulada de pelo menos 60 s tem precedência, para proteger vias com pouca demanda. Depois é aplicada a pontuação. O verde não tem mais o encerramento periódico obrigatório de 10 s: continua enquanto a fase escolhida permanece a atual. Uma fase sem demanda concorrente pode permanecer verde. Quando outra fase deve ser atendida, a transição acontece após o mínimo de 3 s.

O mínimo de 3 s, o amarelo de 3 s, a liberação mínima de 1 s e a proteção de trajetórias ocupadas são parâmetros do simulador, não regras do treinamento AND. Preservam coerência e impedem abrir movimentos conflitantes. Prioridade de emergência não significa interromper uma travessia já iniciada. A política é uma heurística calibrada para este cruzamento, sem prova de ótimo global e sem garantia de eliminar filas sob saturação.

## Medição reproduzível

```bash
.venv/bin/python experimento_transito/comparar.py --segundos 240 --sementes 42 73 101
.venv/bin/python experimento_transito/relatorio.py
```

São cinco políticas, três cenários e três sementes: 45 execuções novas. Os quatro paradigmas são representados pelo imperativo, pois implementam a mesma política. O cenário desbalanceado usa 36 carros/min por origem em N/S e 6 em L/O; o equilibrado usa 22 em todas; na inversão, as taxas 36/6 são trocadas na metade. Cada origem tem ainda 0,3 ambulância/min, e cada travessia, 1 pedestre/min. Todos recebem as mesmas chegadas para cada par cenário/semente. A semente 11 foi usada na calibração preliminar, não na tabela final.

O relatório mede fila média, concluídos, espera dos concluídos, espera acumulada de todos os solicitados e emergências atendidas/pendentes. A espera acumulada inclui quem ainda está no sistema, mas não sua espera futura. Uma política pode favorecer emergências e piorar a média geral. Compare também remanescentes e vazão: não escolha um vencedor por uma única métrica.

`resultados.json` preserva os números por execução. `relatorio.md` apresenta as médias e as variações em relação ao imperativo. O relatório é copiado para `cena_3d/public/comparacao-transito.json` para consulta na aba urbana. Alterar código de decisão, treinamento, geometria ou parâmetros exige executar novamente os ensaios. A tabela não é calculada a partir da sessão visual atual.
