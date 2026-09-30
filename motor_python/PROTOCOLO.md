# Protocolo WebSocket 1.8

Referência técnica dos comandos e estados. Para uma leitura inicial, consulte o [mapa do motor](README.md). Os contratos partiram da Seção 13 da [especificação original](../docs/historico/requisitos-2026-09-13.md). A configuração
emitida é `1.8`. `Instantaneo.participantes` é a lista completa de objetos
`Participante`; `semaforos` informa verde/amarelo/vermelho para N/S/L/O,
`semaforos_pedestres` informa verde/vermelho por travessia e `estado_transicao`
é `atendimento`, `encerramento` ou `liberacao`. Cada participante inclui `dimensoes`, `instante_inicio_espera`, `espera_interna`,
`instante_autorizacao` e
`fonte` (`manual` ou `automatico`). O instantâneo também inclui `demanda`, `controle` e `metricas`.
`posicao` mantém `x`, `y`, `z` e `rotacao_y`, todos finitos. A alteração aplica-se
conjuntamente ao motor e à cena. O controlador selecionado propõe fases e o motor as valida; o navegador não envia cores.

Na versão 1.8, `Participante.faixa` identifica `externa` ou `interna` para veículos
admitidos. Pedestres e veículos ainda na fila externa têm `faixa: null`. O motor
escolhe a faixa na admissão, sem novo parâmetro nos comandos de inserção ou geração.
O evento `participante_inserido` registra a faixa veicular. A trajetória semafórica
continua sendo `N/S/L/O-seguir_em_frente`: ambas as faixas obedecem ao mesmo sinal,
e ocupações de qualquer uma delas bloqueiam movimentos conflitantes.

## Comando enviado pelo cliente

```json
{
  "command_id": "92d32417-aecc-4386-9661-c3a93bf39eed",
  "tipo": "inserir_participante",
  "parametros": {
    "categoria": "carro",
    "origem": "L",
    "movimento": "seguir_em_frente",
    "quantidade": 1
  }
}
```

`command_id` identifica o pedido, não o veículo. A escolha da rua é preservada,
sem sorteio. Categorias aceitas: `carro`, `moto`, `onibus`, `ambulancia`; movimento
em frente e quantidade inteira 1.
Campos extras, posições enviadas pelo navegador e valores inválidos são rejeitados.
`confirmacao` e `passo_solicitado` devem ser omitidos ou nulos.

Receber o comando não altera participantes. Na fronteira do próximo passo o motor
cria a solicitação, registra um evento e confirma sua aplicação. Depois admite os
participantes quando há espaço, calcula posições e publica o instantâneo. Uma
inserção veicular nova aparece exatamente na origem no primeiro instantâneo e se desloca
a partir do passo seguinte.

## Confirmação enviada ao solicitante

```json
{
  "tipo": "confirmacao_comando",
  "command_id": "92d32417-aecc-4386-9661-c3a93bf39eed",
  "confirmacao": {
    "status": "aplicado",
    "passo_aplicacao": 12,
    "erro": null
  }
}
```

`aplicado` confirma a criação da solicitação; pode haver espera na fila externa.
Uma rejeição usa `status: "rejeitado"`, `passo_aplicacao: null` e `erro` com motivo
específico. Um JSON inválido ou comando sem ID recebe `command_id: null`.
Confirmações e instantâneos compartilham uma fila de saída por conexão, garantindo
um único escritor WebSocket. Outros clientes recebem os mesmos participantes,
mas a confirmação pertence ao solicitante.

Reenviar o mesmo comando/ID, antes ou depois da aplicação, não duplica o pedido;
o motor entrega a mesma confirmação. Reutilizar o ID com parâmetros diferentes é
rejeitado. O histórico de IDs é em memória e vale durante a execução do processo.

## Participante no instantâneo

Exemplo de elemento de `participantes` no primeiro passo após uma inserção na rua L:

```json
{
  "id": "<run_id>:carro:1",
  "categoria": "carro",
  "origem": "L",
  "destino": "O",
  "trajetoria": "L-seguir_em_frente",
  "posicao": { "x": 88.0, "y": 0.65, "z": -4.5, "rotacao_y": -1.5707963267948966 },
  "estado": "em_movimento",
  "instante_solicitado": 1.2,
  "instante_inserido": 1.2,
  "solicitacao_prioritaria": false,
  "dimensoes": { "comprimento": 4, "largura": 1.8, "altura": 1.3 },
  "instante_inicio_espera": null,
  "fonte": "manual",
  "espera_interna": 0,
  "instante_autorizacao": null
}
```

O ID ilustrativo é gerado pelo motor e inclui a categoria. `posicao` indica o
centro da caixa gráfica e a rotação em Y, em radianos. A cena copia posição,
orientação e dimensões sem integrar velocidade ou decidir quando admitir um veículo.

Coordenadas iniciais de Carro na faixa externa (as demais categorias ajustam o centro pelo comprimento):

| Origem | x inicial | z inicial | Direção | Destino |
| --- | ---: | ---: | --- | --- |
| N | −4,5 | −88 | +Z | S |
| S | +4,5 | +88 | −Z | N |
| L | +88 | −4,5 | −X | O |
| O | −88 | +4,5 | +X | L |

Na faixa interna, a coordenada lateral é −1,5 em N/L e +1,5 em S/O.
A coordenada longitudinal, a direção e o destino são os mesmos da faixa externa.

Parâmetros didáticos em `movimento.py` (unidades do cenário e segundos simulados):

| Categoria | Comprimento | Largura | Altura | Velocidade desejada | Folga de seguimento |
| --- | ---: | ---: | ---: | ---: | ---: |
| Carro | 4 | 1,8 | 1,3 | 6 | 2 |
| Moto | 2 | 0,8 | 1,2 | 7 | 1,5 |
| Ônibus | 10 | 2,5 | 3 | 4 | 2,5 |
| Ambulância | 5 | 2 | 2,4 | 6 | 2 |

A traseira do veículo recém-admitido fica na borda externa da malha (±90). Isso
mantém inclusive um ônibus inteiro dentro da faixa. A coordenada Y do centro é
metade da altura. Cada origem usa duas faixas de entrada de 3 unidades de largura.
O veículo permanece na mesma faixa até sair; não ultrapassa o líder da própria
faixa. Veículos em faixas diferentes avançam independentemente.

O passo permanece 0,1 s. O motor mantém a distância longitudinal de cada veículo
e limita o deslocamento desejado pela retenção e pelo veículo à frente. A frente
para a 0,5 unidade da borda de aproximação da barra: essa borda está a 11,225
unidades do centro do cruzamento. O limite considera metade do comprimento do
próprio veículo, inclusive para ônibus. As posições são arredondadas a seis casas.

Os veículos são atualizados da frente para trás. O seguidor mantém a folga de sua
categoria entre sua frente e a traseira do líder, considerando ambos os comprimentos.
Esse limite vale também enquanto os dois estão em movimento. Não há aceleração
progressiva; a velocidade efetiva se ajusta ao espaço disponível.

## Filas, retenção e espera

Pedidos da mesma origem entram em FIFO, com até duas admissões por passo, uma
por faixa. A admissão verifica comprimento, posição de nascimento e folga do
candidato contra os veículos de cada faixa. Entre as entradas livres, escolhe
a menor soma de comprimentos e folgas dos veículos ainda não autorizados; empates
alternam entre externa e interna, começando pela externa. Não há sorteios extras.
Um pedido que não cabe em nenhuma faixa permanece externo, sem sobreposição nem
descarte. Outras origens têm filas independentes. O limite global de ativos vale
para a soma de todas as faixas e pedestres.

`filas.externas` informa pendências por N/S/L/O e pelos oito acessos de calçada
(como `N-TR:A`); `filas.internas` conta participantes em espera nessas origens. `solicitacoes` contém os pedidos
que aguardam entrada, com ID, categoria, origem, horário solicitado, estado e fonte.
`instante_solicitado` é o tempo do passo que aplicou o comando; `instante_inserido`
é o tempo do passo de admissão. Pedidos externos não são desenhados sobre carros
existentes.

Estados ativos: `em_movimento`, `aguardando_retencao`, `aguardando_fila`. No
primeiro tick sem deslocamento, o motor preenche `instante_inicio_espera` e registra
`inicio_espera` com o motivo. Manter-se parado não duplica esse evento.

Participantes concluem após autorização e percurso até a saída; nunca são
removidos para aparentar fluidez. Ambulâncias respeitam a baseline, sem prioridade
adaptativa. Solicitações, admissões, rejeições, espera, autorização, transições
e conclusão geram eventos em memória; persistência e replay permanecem pendentes.

O painel esquerdo mostra `Veículos na cena` como o total de veículos das quatro
categorias, e `Aguardando entrada` como o
total das solicitações externas. Esses totais são derivados dos instantâneos.


## Inserção de pedestres

```json
{
  "command_id": "pedestres-leste-1",
  "tipo": "inserir_participante",
  "parametros": {
    "categoria": "pedestre",
    "travessia": "L-TR",
    "lado": "B",
    "quantidade": 3
  }
}
```

Travessias: N-TR/S-TR/L-TR/O-TR. Quantidade inteira entre 1 e 100.
Não envie `origem` veicular, movimento ou coordenadas para pedestres.
A origem oficial é `travessia:lado`, o destino é o acesso oposto da mesma
travessia e `trajetoria` identifica a travessia solicitada.

| Travessia | Calçada A | Calçada B |
| --- | --- | --- |
| N-TR | Oeste | Leste |
| S-TR | Leste | Oeste |
| L-TR | Norte | Sul |
| O-TR | Sul | Norte |

O motor emite `travessia_solicitada`; solicitar não autoriza cruzar (RN04).
O pedestre admitido fica em `aguardando_travessia`, com início de espera registrado,
até obter uma reserva de percurso durante sua fase verde.
A cápsula possui dimensões 0,6 × 0,6 × 1,7. Cada acesso tem 16 posições candidatas
em fila alinhada ao sentido da travessia na calçada. A admissão verifica distância de pelo menos 1 unidade
entre centros, incluindo pedestres de travessias vizinhas. A capacidade física
pode ser menor porque acessos compartilham calçadas. Admite-se no máximo um
participante por origem por passo. Sem posição livre, o pedido continua externo.
Lotes manuais são aceitos ou recusados integralmente no limite técnico de pendências.

## Configuração da geração

```json
{
  "command_id": "taxas-1",
  "tipo": "configurar_gerador",
  "parametros": {
    "semente": 42,
    "taxas_veiculares": {
      "N": {"carro": 12, "moto": 3, "onibus": 1, "ambulancia": 0},
      "S": {"carro": 6, "moto": 0, "onibus": 0, "ambulancia": 0},
      "L": {"carro": 6, "moto": 0, "onibus": 0, "ambulancia": 0},
      "O": {"carro": 6, "moto": 0, "onibus": 0, "ambulancia": 0}
    },
    "taxas_pedestres": {"N-TR": 6, "S-TR": 0, "L-TR": 0, "O-TR": 0},
    "fator_global": 1,
    "fatores_locais": {"N": 1, "S": 1, "L": 1, "O": 1},
    "fator_pedestres": 1
  }
}
```

O comando substitui a configuração completa; não é um patch. Campos omitidos
usam os padrões de `ConfiguracaoGerador` (taxas zero, fatores 1, semente 42).
Mapas explicitamente enviados precisam conter todas as chaves mostradas.
Taxas devem ser finitas, não negativas e até 6.000/min; fatores ficam entre 0 e 10.
A taxa efetiva também não pode ultrapassar 6.000/min. Semente: inteiro de 0 a 2³²−1.
Campos extras são rejeitados. O formulário sempre envia a configuração completa.

Para cada categoria/rua, λ efetiva = taxa base × fator global veicular × fator
local da rua. Pedestres usam apenas taxa da travessia × fator de pedestres;
metade corresponde ao acesso A e metade ao B. Alterar a taxa base de carros do
Norte preserva motos e pedestres. O fator local, por sua vez, afeta todas as
categorias veiculares da rua. O único movimento habilitado é seguir em frente
(probabilidade 1); o destino do pedestre é sempre o lado oposto.

Em cada Δt de 0,1 s, cada uma das 24 fontes sorteia
`n ~ Poisson(λ × Δt / 60)`. São permitidas múltiplas chegadas por passo. O método
do produto usa blocos independentes de média até 20 para evitar underflow.
Taxa zero não gera pedidos nem consome números aleatórios daquela fonte.
A distribuição é didática, sem calibração urbana.

Cada fonte tem seu próprio `random.Random`, inicializado com `"semente:fonte"`.
Nenhum sorteio de mobilidade, comando manual, controlador ou ocupação interfere
nesse estado. Mesma versão, semente e calendário de configurações reproduzem as
mesmas contagens por fonte/passo; `run_id` e IDs globais identificam cada ensaio.
Trocar a semente reinicializa os fluxos; reaplicar a mesma semente preserva seu
estado. Replay com calendário persistido continua pendente.

Ordem oficial de cada passo nesta versão:

1. Comandos na ordem de recebimento, com deduplicação por `command_id`.
2. Fontes veiculares N, S, L, O; em cada uma: carro, moto, onibus, ambulancia.
3. Fontes pedestres N-TR, S-TR, L-TR, O-TR; em cada uma: A e B.
4. Admissão por origem; obtenção e validação da proposta do controlador selecionado.
5. Movimento veicular e pedestre, conclusão, métricas e publicação.

Dentro de uma fonte, os pedidos recebem sequência crescente no ID. Manuais e
automáticos usam a mesma fila e as mesmas regras de admissão. Via saturada
continua gerando demanda externa. Configurações afetam chegadas futuras, sem
apagar filas. `gerador_configurado` registra anterior/nova e passo da aplicação;
`chegadas_automaticas` registra fonte e quantidade sorteada, inclusive recusas.

## Diagnóstico de demanda no instantâneo

`demanda` contém:

- `configuracao`: parâmetros vigentes, incluindo semente.
- `taxas_efetivas`: λ por fonte, por exemplo `N:carro` ou `N-TR:A:pedestre`.
- `gerados_janela`: contagens sorteadas por fonte desde a última configuração.
- `inicio_janela`, `duracao_janela`: janela em segundos simulados. Uma configuração
  aplicada no passo k começa a janela em `(k − 1) / 10`, incluindo o intervalo de k.
- `taxas_observadas`: `gerados_janela × 60 / duracao_janela`, ou zero antes de haver
  duração. Inclui solicitações ainda externas ou recusadas. Não é taxa de admissão.
- `solicitados`, `admitidos`, `recusados`: totais acumulados da execução, cada um
  separado em `manual` e `automatico`. Reconfigurar zera apenas a janela observada.
- `limites`: capacidade de ativos, pendências e taxa efetiva máxima aceita.
- `motivo_interrupcao`: nulo durante execução ou motivo do encerramento por limite.

`Veículos na cena` exclui pedestres; `Pedestres na cena` conta pedestres admitidos;
`Aguardando entrada` soma as doze filas externas. O diagnóstico exibe taxa efetiva
e observada do gerador, além dos totais separados por fonte. As inserções manuais
somam solicitações e nunca reduzem a taxa automática.

## Capacidade

`Motor(limite_ativos=200, limite_pendentes=2000)` permite configurar os limites
do ensaio; `LIMITE_TAXA_EFETIVA` em `gerador.py` fixa o teto validado nesta versão.
Ao esgotar capacidade, o motor registra `limite_atingido`, preserva ativos e
pendências, contabiliza recusas e interrompe novos passos após terminar o passo
corrente. O WebSocket permanece enviando o último estado, com o mesmo relógio.
Novos comandos, exceto `resetar_simulacao`, são rejeitados; retransmissões
mantêm sua confirmação original. Use o reset para iniciar um novo ensaio.
Não há remoção de participantes para liberar espaço artificialmente.

A [medição exploratória de 13/09/2026](../docs/historico/medicao-capacidade-2026-09-13.md)
foi preservada como histórico. Ela não mede o desempenho da versão atual.

## Matriz de conflitos e tempos fixos

Movimentos habilitados: `N-seguir_em_frente`, `S-seguir_em_frente`,
`L-seguir_em_frente`, `O-seguir_em_frente`, `N-TR`, `S-TR`, `L-TR`, `O-TR`.
A matriz em `controle.py` tem diagonal falsa e é simétrica:

| Grupo | Conflita com |
| --- | --- |
| Veículos N/S | Veículos L/O e pedestres N-TR/S-TR |
| Veículos L/O | Veículos N/S e pedestres L-TR/O-TR |
| Pedestres N-TR/S-TR | Veículos N/S |
| Pedestres L-TR/O-TR | Veículos L/O |

Movimentos veiculares opostos são paralelos em faixas distintas. Travessias
distintas são compatíveis na matriz; percursos individuais permitem liberação
coletiva. Apenas a passagem nas esquinas compartilhadas tem preferência local.
Nenhuma conversão é habilitada nesta geometria. `ConfiguracaoControle` valida
simetria, cobertura, diagonal, conflitos da geometria, fases, sequência e tempos;
fases com conflitos são rejeitadas antes de iniciar o motor.

| Fase | Permissões | Atendimento | Encerramento |
| --- | --- | --- | --- |
| F-NS | Veículos N/S | 100 passos (10 s) | 30 passos (3 s), amarelo |
| F-LO | Veículos L/O | 100 passos (10 s) | 30 passos (3 s), amarelo |
| F-PED | Quatro travessias | 100 passos (10 s) | Fecha novas admissões, sem amarelo |

Toda mudança passa por liberação vermelha de pelo menos 10 passos (1 s).
O estado inicial também é `liberacao`, com `fase: null`. Após a fase inicial,
`fase` identifica a última fase atendida durante amarelo/liberação; não implica
permissão vigente. `controle.permissoes` lista somente permissões de novas entradas.
A ordem é fixa, independentemente da demanda ou categoria. Não há prioridade
adaptativa de emergência, ônibus ou espera excessiva neste baseline.

O controlador recebe `EstadoControle` imutável e retorna `Proposta` com ação,
fase e motivo. A validação comum do motor verifica o tempo mínimo/máximo fixado,
o encerramento, o intervalo de liberação e a ocupação conflitante. Propostas
inválidas não abrem a fase; ao esgotar o verde, o motor encerra a permissão mesmo
se o controlador insistir em mantê-la ou indicar uma fase desconhecida.
`transicao_semaforica` registra cada mudança e `proposta_bloqueada` registra cada
novo motivo, sem repetir o mesmo evento a cada tick. O diagnóstico mantém o
motivo atual durante toda a espera. Os relógios usam passos inteiros.

`ocupacoes` mapeia movimento para IDs dos participantes autorizados ainda na
área protegida. Veículos ocupam desde a autorização até a traseira ultrapassar
11,725 unidades após o centro, incluindo a travessia de saída e uma margem.
Essa guarda conservadora considera o comprimento do ônibus. Um vermelho mínimo
concluído não abre a próxima fase enquanto houver ocupação conflitante. A espera
por liberação pode prolongar o ciclo nominal; a proteção prevalece sobre o relógio.

## Entrada autorizada e conclusão

A frente veicular ultrapassa a retenção somente no verde. No primeiro avanço
além do limite, o motor registra `movimento_autorizado` e `instante_autorizacao`.
O amarelo é tratado como proibição de novas entradas; não há modelo de dilema de
frenagem. Um veículo autorizado continua no amarelo/vermelho e mantém distância
ao líder. A autorização nunca é concedida por comparação de ponto flutuante
isolada: a permissão verde também é exigida explicitamente.

O veículo conclui quando sua traseira passa da borda de destino (±90), gerando
`percurso_concluido` uma vez. Só então seu ID desaparece de `participantes`.
O frontend não remove por limite gráfico nem calcula a trajetória.

Pedestres admitidos aguardam a fase verde de sua travessia. Todos os que aguardam
uma travessia permitida recebem autorização no mesmo passo, com percursos
individuais, estado `em_travessia` e velocidade de 1,7 unidade/s. Os sentidos
ocupam linhas separadas dentro da faixa; a distância mínima é de 0,8 unidade.
A preferência nas esquinas compartilhadas limita apenas o avanço local.

Após o vermelho, os autorizados continuam até concluir; a ocupação de todos eles
bloqueia as fases conflitantes. Novos admitidos durante o verde são autorizados,
enquanto os admitidos no vermelho aguardam. Pedidos ainda externos permanecem
na fila de entrada até haver espaço. A conclusão limpa o percurso individual,
sem afetar os demais. O modelo permanece didático, sem calibração de multidões.

## Controle e métricas no instantâneo

`controle` informa política (`fixa_referencia`), sequência, estado, início em
passos, tempo decorrido, tempos configurados, permissões, última validação e
quantidade de bloqueios distintos registrados. As cores são calculadas no Python.
A cena representa oito grupos (`semaforo-N`, etc. e `semaforo-N-TR`, etc.) com
cor e texto, sem relógio semafórico local.

`metricas` contém `intervalo_segundos` (desde zero), `chegadas_solicitadas`,
`limiar_velocidade_espera` (0,1 unidade/s), `total`, `por_origem` e `por_categoria`.
Cada agregado contém:

- `concluidos`, `ativos`, `pendentes`: populações separadas; concluídos não somem
  da contabilização ao sair da cena.
- `vazao_por_minuto`: `concluidos × 60 / intervalo_segundos`; zero no início.
- `espera_concluidos_interna_media`, `espera_concluidos_externa_media`,
  `espera_concluidos_total_media`: médias somente dos concluídos, zero sem amostra.
- `espera_ativos_interna_total`: segundos acumulados após inserção com velocidade
  abaixo do limiar, sem contar o tick de nascimento.
- `espera_ativos_externa_total`: espera já cumprida até a admissão dos ativos.
- `espera_pendentes_externa_total`: tempo acumulado desde cada solicitação externa.
- `espera_pedestres_ate_autorizacao_total`: espera da solicitação à autorização,
  incluindo espera atual dos pedestres ainda não autorizados.

Todos os tempos são simulados. A espera externa não é duplicada na espera interna.
O painel principal mostra a média dos concluídos. O diagnóstico e as exportações
registram também as esperas dos ativos e pendentes. Por categoria são informados
os cinco grupos; origens aparecem quando há demanda associada. Eventos de conclusão
registram tempos solicitados/inseridos/autorizados/concluídos e espera interna.
Exportações JSON/CSV, estatísticas temporais de fila e métricas de emergência
estão disponíveis nos endpoints descritos na seção de exportação.


## Comando de seleção e parâmetros

```json
{
  "command_id": "controle-1",
  "tipo": "configurar_controlador",
  "parametros": {
    "controlador": "imperativo",
    "limiar_espera": 30,
    "prioridade_ambulancia": true,
    "prioridade_onibus": false
  }
}
```

Controladores aceitos: `baseline`, `imperativo`, `orientado_objetos`, `funcional`, `logico`.
Limiar em segundos simulados, finito, positivo e até 3.600; booleanos são estritos.
O comando substitui a configuração inteira, usando padrões para campos omitidos.
Campos extras, algoritmo desconhecido ou limiar inválido são rejeitados.
A confirmação e deduplicação seguem o mesmo contrato dos outros comandos.

Na fronteira do passo, o motor prepara o adaptador escolhido e registra
`controlador_configurado` com parâmetros anteriores/novos, comando e marca
`exploracao: true`. A máquina semafórica, relógios, participantes, gerador e
métricas são preservados. Todos os comandos do passo são aplicados antes de
avaliar o controlador. Uma troca durante o amarelo/liberação mantém o tempo já
cumprido. A baseline continua disponível e é o padrão de uma nova execução.

`controle.configuracao_controlador` publica os quatro parâmetros. `controle.politica`
informa `fixa_referencia` ou `prioridades_demanda_v1`. A variante adaptativa usa
maior demanda como critério ordinário e antiguidade como desempate. Ver [política e desempates](../controladores/README.md).

## Solicitação explícita de emergência

O comando de inserção veicular aceita `solicitacao_prioritaria`, booleano opcional
(padrão falso). Valor verdadeiro só é válido para ambulância. A inserção manual
é feita pelo WebSocket. Ambulâncias automáticas são geradas com
pedido explícito verdadeiro, sem consumo adicional de aleatoriedade.
`Participante.solicitacao_prioritaria` e as pendências em `solicitacoes` preservam
o valor. O evento `emergencia_solicitada` registra participante, origem e fonte.

A prioridade está ativa para a decisão enquanto o participante ainda não tiver
`instante_autorizacao`. Desligar a preferência global não apaga o pedido; apenas
retira sua precedência especial. Prioridade de ônibus aplica-se à categoria
quando habilitada, abaixo de emergência e de espera excessiva.

## Decisão, avaliação e validação comum

`controle.decisao` contém a última `Decisao` da Seção 13 (nula antes do primeiro
passo), com ID, passo, controlador, versão de política, modelo AND selecionado,
fases candidatas, avaliações, motivos, proposta e resultado da validação.
Cada avaliação informa fase, demanda, maior espera, critério, chave de ordenação,
admissibilidade, motivo de bloqueio e elegibilidade AND.

Cada paradigma recebe a mesma estrutura imutável, com pedidos ativos e externos
que ainda não foram autorizados. Cada módulo calcula independentemente as
avaliações e a seleção. A admissibilidade física/temporal e execução dos sinais
permanecem no motor, compartilhadas conforme RF26. Uma fase inadmissível pode ser
planejada como destino; a validação RN06 continua impedindo abertura prematura.

As ações são `manter`, `transicionar` e `aguardar`. A última exige fase nula e
encerra atendimento/amarelo regularmente antes de aguardar novas solicitações
em vermelho. Renovar a mesma fase por demanda também exige toda a transição.
No modo Regras, o atendimento tem duração de 10 s;
não há preempção que corte esses tempos. A conclusão de movimentos autorizados
continua protegida, inclusive ao trocar para uma política com emergência ativa.

O snapshot atualiza a decisão a cada passo. O histórico em memória registra
`decisao_controlador` quando mudam ação, fase alvo, critério, estado, modelo,
entradas binárias ou resultado
da validação, incluindo a entrada imutável serializada daquele passo e o resultado.
Ticks de manutenção equivalentes não duplicam o histórico. `limiar_espera_excedido`
registra a entrada de cada fase na condição de espera excessiva e o limiar vigente;
a avaliação do snapshot mostra a idade atual. Reconfigurar pode alterar a
preferência, sem remover a demanda.

O frontend sincroniza configuração e diagnóstico, encaminha comandos e mostra
motivos de rejeição. O transporte requer configuração do controlador válida
e `controle.falha_controlador` nulo ou textual.
Não há comparação simultânea de execuções nem persistência automática entre
reinicializações. A integração de pesos e a exportação do histórico estão disponíveis.

## Prolog persistente e falhas

`configurar_controlador` aceita `controlador: "logico"`, com os mesmos três
parâmetros de prioridade e a mesma política `prioridades_demanda_v1`. Não existe
comando para fornecer código ou consultas Prolog pelo WebSocket. O arquivo local
`controladores/logico.pl` é carregado via MQI uma vez por ativação. Configurar
prioridades mantendo `logico` selecionado reutiliza a sessão existente.

O estado imutável entregue a todos os paradigmas agora inclui `conflitos`, tupla
de pares de IDs conflitantes. A estrutura é serializada como lista de pares no
registro de entrada. O adaptador preserva ordem, tipos e unidades; a proposta
retornada passa pela mesma validação RN06 antes de autorizar qualquer movimento.

O instantâneo inclui `controle.falha_controlador: null | string`:

- **Falha de ativação:** comando rejeitado e deduplicado, mensagem identifica
  explicitamente o controlador que continua ativo. A configuração solicitada
  não é confirmada; o ensaio continua com a configuração anterior.
- **Falha durante a decisão:** `logico` permanece como controlador selecionado,
  `controle.decisao` fica nulo e `controle.validacao.aceita` fica falso. O motivo
  também aparece em `demanda.motivo_interrupcao`. No passo da falha, comandos,
  geração e admissão já ocorreram; movimentos e novas autorizações não executam.
  Os passos seguintes republicam o mesmo estado, sem avançar o relógio. Fase,
  sinais, ocupações e autorizações anteriores são preservados como estado pausado,
  incluindo participantes que estavam atravessando. Não há troca de fase ou
  cancelamento de percurso para mascarar a falha. Reiniciar o motor cria novo ensaio.

O evento `falha_controlador` informa `etapa: ativacao | decisao` e o erro. Na
decisão, registra também a entrada. Uma proposta de fase inválida, mas com
estrutura correta, continua sendo rejeição de integridade RN06 e aparece no
diagnóstico normal de decisão. Não se confunde com falha de comunicação.


## Avaliador da AND

Comando independente do paradigma:

```json
{"command_id":"modelo-1","tipo":"configurar_modelo_neural","parametros":{"modelo":"perceptron"}}
```

Valores: `AND_referencia`, `perceptron`, `adaline`. A confirmação usa o mesmo
contrato de comandos. Seleção inválida ou pesos não validados são rejeitados;
o modelo ativo permanece. O carregamento ocorre uma vez na inicialização,
com caminho resolvido a partir do módulo Python, independente do diretório atual.

`controle.modelo_neural` informa o ativo. `controle.modelos_neurais` mapeia
cada modelo para `disponivel`, `erro`, `verificacao_and` e metadados do treino.
Cada `controle.decisao.avaliacoes[]` inclui `neural` com `modelo`, `entradas`
([x1,x2]), `pesos` ([w0,w1,w2]), `bias` (entrada fixa 1), `peso_bias` (w0),
`soma_ponderada`, `saida`, `and_referencia`, `elegivel` e `divergencia`.
Na AND lógica, pesos, peso_bias e soma são nulos. A precisão não é arredondada.
`origem_solicitacao` distingue `sequencia_fixa` da baseline de `demanda` nos
adaptativos. Os cálculos usam o estado anterior à aplicação da proposta no mesmo
passo; o restante do instantâneo já reflete a aplicação e os movimentos.

`GET /exportar/eventos` retorna JSON de download com schema_version 1.0 e
versao_motor 1.8. Contém configuração inicial/atual, demanda, pesos validados,
lista ordenada de eventos, `historico_fases`, `historico_metricas`, métricas
atuais, ativos e pendentes, run_id, passo_exportacao, intervalo_observado e
motivo_encerramento. `GET /exportar/metricas` retorna CSV UTF-8 com cabeçalho,
vírgula como delimitador e ponto decimal. Cada linha representa um escopo
(total/origem/categoria/origem_categoria) em um instante de amostragem.
As métricas são acumuladas desde zero; amostras a cada 1 s e no passo do download.
Os dois downloads recebem Content-Disposition com nome, run_id e passo.
CORS permite GET da interface local (localhost/127.0.0.1) e expõe esse cabeçalho.
Downloads não encerram o ensaio; `em_andamento` é um motivo de recorte explícito.
Eventos e séries permanecem em memória até a reinicialização do processo.


## Modos de operação e extensão aplicada

`configurar_operacao` recebe `{"modo":"paradigmas"|"neural"|"urbano", "modelo":"perceptron"|"adaline"}`; `modelo` é opcional e vale `perceptron` por padrão. A confirmação e a deduplicação seguem os demais comandos. O modo neural usa `experimento_transito/pesos_transito.json`; pesos ausentes ou inválidos impedem a ativação. O urbano independe deles.

`controle.operacao` identifica o modo efetivo. `controle.transito` contém critério e comparação neural aplicada, quando houver; `controle.treinamento_transito` informa pesos e acurácia sintética. `controle.decisao.controlador` pode ser `neural` ou `urbano`; nesses casos as avaliações não contêm o campo `neural` de duas entradas da AND. `controle.transito.comparacao` usa cinco entradas, incluindo bias, e é um contrato distinto. `controle.verde_variavel`, `verde_minimo_segundos` e `verde_maximo_segundos` descrevem o regime de verde; máximo nulo significa ausência do encerramento periódico fixo.

Aplicar `configurar_controlador` retorna ao modo Paradigmas e seus tempos originais. Aplicar `configurar_modelo_neural` altera apenas o avaliador AND desse modo. Trocar uma aba no navegador não envia comando. Mudanças de modo preservam a transição atual, relógio e participantes. JSON e CSV identificam a política ativa nas amostras; métricas seguem acumuladas desde o início da execução.

Veja `docs/tres_disciplinas.md` para as políticas, limitações e ensaios reproduzíveis.

### Prioridade de emergência nas redes

Em `modo: "neural"`, pedidos de ambulância com `solicitacao_prioritaria: true`
têm precedência sobre Perceptron e Adaline. Se outra fase estiver verde, o motor
inicia seu encerramento no próximo passo, inclusive antes do mínimo normal de 3 s.
A exceção vale somente para encerrar outro verde adaptativo: amarelo de 3 s,
liberação mínima de 1 s, elegibilidade e ocupações conflitantes continuam validados.
A emergência mais antiga mantém sua preferência até ser autorizada. Ambulâncias
sem solicitação explícita não acionam a exceção; as automáticas têm essa solicitação.

O diagnóstico usa `controle.transito.criterio: "emergencia"` e `comparacao: null`.
A interface mostra **Emergência prioritária** junto do modo. O Automático e os
quatro paradigmas mantêm seus tempos e critérios anteriores. A integração AND
acadêmica não muda.

## Reset da simulação

`{"command_id":"reset-1","tipo":"resetar_simulacao","parametros":{}}` agenda uma nova execução no mesmo motor e mantém os WebSockets conectados. A confirmação aplicada usa passo zero e é seguida de um instantâneo com novo `run_id`, tempo zero, sinais vermelhos e nenhuma demanda acumulada. Os passos seguintes retomam a geração configurada.

O reset limpa participantes, filas, métricas, históricos e interrupções. Preserva configuração semafórica, limites, controlador, modo de operação, modelos e configuração de geração. Reinicia as fontes aleatórias a partir da mesma semente. Funciona mesmo quando a execução foi interrompida. Comandos ainda pendentes depois dele são cancelados; repetições de seu `command_id` devolvem a confirmação anterior sem reiniciar novamente. Histórico anterior deixa de fazer parte das exportações: exporte antes caso precise conservá-lo.

## Velocidade da simulação (extensão compatível com 1.8)

`{"command_id":"velocidade-1","tipo":"configurar_velocidade","parametros":{"multiplicador":24}}`
seleciona um inteiro de 1 a 24. Confirmação, validação e deduplicação seguem os
outros comandos. `Instantaneo.velocidade_simulacao` informa o valor aplicado;
`configuracao_atual.velocidade_simulacao` e eventos `velocidade_configurada`
preservam essa informação na exportação JSON. O valor inicial é 1 e o reset o mantém.

O multiplicador altera somente o intervalo real entre passos. Cada passo continua
representando 0,1 s simulados: geração, movimento, decisões, filas e métricas são
calculados em todos os passos. A amostragem exportada continua em 1 s simulado.
A mesma semente e os mesmos comandos nos mesmos passos produzem os mesmos
resultados, independentemente do ritmo. Comandos manuais enviados em momentos
reais diferentes podem, naturalmente, cair em passos simulados diferentes.

Em 1× o WebSocket publica cada passo. Acima disso, publica até 20 estados por
segundo real, além das atualizações imediatas de comandos, resets e interrupções.
Os clientes podem receber saltos no número do passo; isso não significa que os
cálculos intermediários foram descartados. Todos compartilham a mesma velocidade.
Se o computador não alcançar o ritmo solicitado, o relógio real fica mais lento,
sem aumentar o passo, pular cálculos ou acumular uma fila de passos atrasados.
Acelerar exige mais processamento por segundo real; não garante 24× sob toda carga.
