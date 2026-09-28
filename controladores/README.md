# Quatro paradigmas — incremento M5

Quatro implementações independentes da política `prioridades_demanda_v1`:

| Arquivo | Organização da avaliação e seleção |
| --- | --- |
| `imperativo.py` | Varre fases e solicitações com laços, variáveis locais e condicionais; seleciona a menor chave explicitamente. |
| `orientado_objetos.py` | `DemandaDaFase` encapsula solicitações e idade; regras de emergência, espera, ônibus e volume avaliam o domínio; `PoliticaPrioridades` coordena a seleção. |
| `logico.pl` | Fatos de precedência, regras de demanda/admissibilidade/conflito e consulta determinística; MQI persistente em `adaptador_prolog.py`. |
| `funcional.py` | Funções puras `avaliar_fase` e `decidir`, composição com `map`, `filter`, `partial` e tuplas imutáveis. A classe é apenas adaptador. |

`contratos.py` compartilha somente tipos imutáveis. Nenhum dos quatro módulos chama
o algoritmo de seleção de outro ou uma função de ranking comum. Geometria,
conflitos, admissibilidade física e execução de sinais continuam compartilhados
no motor, conforme RF26. A baseline continua separada em `motor_python/controle.py`.

## Política versionada

A instrução do incremento M5 pediu **maior demanda** no último critério. Isso
altera o item 5 original da Seção 9, que começava pela solicitação mais antiga.
Este incremento segue a instrução mais recente e registra a variante como
`prioridades_demanda_v1`; os quatro paradigmas usam exatamente essa mesma variante.
O documento de requisitos original foi preservado.

1. Preservar movimentos iniciados, tempos e transições. O motor protege as
   ocupações. Nenhuma preferência cria permissão sem validação RN06.
2. Com prioridade de ambulância habilitada, preferir a emergência ativa mais
   antiga (`categoria=ambulancia`, `solicitacao_prioritaria=true`, ainda não
   autorizada).
3. Preferir a fase cuja solicitação pendente tem a maior espera, quando excede
   estritamente o limiar. Igualdade ao limiar ainda não ativa esse critério.
4. Com prioridade de ônibus habilitada, preferir a solicitação de ônibus mais
   antiga, sem superar emergência ou espera excessiva.
5. Entre as demais, preferir maior quantidade de solicitações pendentes; em
   empate, a solicitação mais antiga.
6. Empates restantes usam identificador de fase em ordem crescente.

Nos critérios 2–4, empate na antiguidade/espera vai diretamente ao identificador
estável da fase. O volume ordinário não altera esses desempates. A idade é
`tempo_simulado − instante_solicitado`, arredondada a seis casas; inclui
aproximação e fila externa. É distinta da métrica de espera interna com velocidade
abaixo do limiar. Solicitações já autorizadas não concorrem novamente.

A demanda inclui participantes admitidos ainda não autorizados e pendências
externas. O limiar padrão é 30 s; emergência vem habilitada e prioridade de ônibus
desabilitada. O parâmetro de limiar é finito, positivo e até 3.600 s. A interface
edita em incrementos de 0,1 s. O envelhecimento alerta e prioriza, sem garantia
absoluta contra saturação ou fluxo contínuo de emergências.

## Contrato e transição

Cada `Estado` contém o relógio imutável, fases e seus movimentos, admissibilidade
atual e motivo, solicitações, tempo simulado, parâmetros de prioridade e pares imutáveis da matriz de conflitos. A
resposta `Decisao` contém `Proposta`, avaliações de todas as fases e critério.
Cada avaliação inclui demanda, maior espera, chave de ordenação, admissibilidade
e bloqueio. Não há acesso ao estado mutável do motor nem ao gerador aleatório.

Escolher um destino para transição é diferente de autorizá-lo agora: uma fase
com emergência pode ser proposta enquanto a trajetória conflitante está ocupada.
Ela continua inadmissível e a máquina do motor mantém sua cor vermelha. O
indicador de elegibilidade usa o avaliador selecionado no motor: AND de referência,
Perceptron ou Adaline. O resultado governa a abertura após as guardas de integridade,
sem alterar as regras de prioridade implementadas em cada paradigma.

Os tempos do M4 permanecem: atendimento de 10 s (mínimo e máximo iguais neste
incremento), amarelo veicular de 3 s e liberação mínima de 1 s, prolongada por
ocupação conflitante. Durante o atendimento mínimo, o controlador propõe manter.
Após esse período, seleciona o destino por prioridade. Se somente a fase atual
possui demanda, ela pode ser selecionada novamente, mas cumpre encerramento e
liberação antes de renovar o verde. Demandas novas podem alterar o destino
planejado durante a transição, sem reiniciar seus relógios.

Sem pedidos, propõe `aguardar` com fase nula: termina o atendimento e o amarelo
regularmente e permanece em vermelho até surgir demanda. A ação nunca apaga
participantes nem interrompe movimentos autorizados. Trocar controlador não muda
a máquina semafórica ou seus tempos, as filas, os IDs, o relógio ou o RNG.

## Emergências explícitas

A inserção manual de ambulância oferece `Solicitar emergência`. O payload inclui
`solicitacao_prioritaria: true/false`; omitir significa falso. Atribuir o pedido a
outra categoria é rejeitado. Ambulâncias automáticas recebem solicitação explícita
verdadeira no gerador, registrada em `emergencia_solicitada`, sem novo sorteio.
O interruptor global decide se a política considera essa prioridade; desligá-lo
não apaga a solicitação. A baseline ignora prioridades adaptativas. Não há comando
separado de emergência para um veículo que já foi inserido neste incremento.

## Verificação e alcance

`tests/test_paradigmas.py` testa resultados esperados em cada prioridade,
desempates e igualdade ao limiar; compara 500 estados aleatórios; verifica entrada
imutável, execução completa equivalente, ausência de conflitos, troca durante
travessia, demanda vazia, renovação de fase e comandos inválidos/deduplicados.
A integração WebSocket e o navegador testam seleção, parâmetros, confirmação,
edições durante ticks, reconexão e solicitação explícita de emergência.

A comparação simultânea na interface (RF27) e os avaliadores neurais
não estão incluídos neste incremento. A equivalência dos quatro paradigmas é
verificada automaticamente nos testes. Registros permanecem em memória; replay persistido e
comparação formal entre políticas continuam pendentes.

## Lógico: SWI-Prolog e MQI

`logico.pl` contém fatos de precedência e regras que extraem a demanda, calculam
idade/antiguidade, verificam conflitos simétricos e admissibilidade, constroem
chaves e escolhem a fase. O código Python do adaptador somente serializa a entrada,
consulta, valida o formato e converte para `Decisao`/`Proposta`/`Avaliacao`.
Nenhum controlador Python calcula a resposta do Prolog. A guarda temporal vem
do contrato comum de admissibilidade; as regras Prolog também verificam os pares
de conflitos recebidos. A escolha do destino considera demanda mesmo quando a
fase ainda não pode abrir; o motor continua validando a execução de toda proposta.

O estado é um argumento da consulta `logico:decidir_json/2`. Não há fatos dinâmicos
acumulados com `assert`/`retract`; pedidos de uma consulta não vazam para a próxima.
O transporte usa JSON dentro de uma string Prolog escapada, preservando IDs Unicode,
nulos, booleanos, listas ordenadas, segundos e passos. O adaptador exige exatamente
uma resposta, números finitos e avaliações na ordem das fases de entrada.

`swiplserver==1.0.2` gerencia um processo e uma conexão persistentes. Em POSIX,
usa socket Unix; nos demais sistemas, conexão local TCP. Foram testados Linux,
Python 3.12.3 e SWI-Prolog 9.0.4. Consultas têm limite de 1 s no SWI, comunicação
de 3 s e inicialização de 5 s de tempo real. Um watchdog encerra o processo se ele
deixar de responder, inclusive quando o limite interno do Prolog não puder executar.
Esses limites não alteram o passo simulado de 0,1 s. A chamada MQI é síncrona;
uma falha pode atrasar o loop até o limite de comunicação, sem pular passos.

Alterar somente prioridades mantém a sessão. Trocar de algoritmo ou encerrar o
FastAPI fecha processo e conexão. Dependência ausente, erro Prolog, timeout,
desconexão, ausência/multiplicidade de resultados ou formato inválido produzem
`FalhaProlog`. A sessão com falha é encerrada, sem reconexão ou substituição oculta.
O diagnóstico persistente e o evento `falha_controlador` identificam a causa.

`tests/test_paradigmas.py` compara os quatro paradigmas em prioridades, desempates,
500 estados aleatórios e 900 passos de execução completa. `tests/test_prolog.py`
exercita sessão real, round-trip de identificadores, conflitos, fronteira do limiar,
perda do processo, processo congelado, timeout, respostas inválidas, RN06,
WebSocket e encerramento. SWI-Prolog é necessário para executar essa suíte; os
testes de integração não substituem o paradigma por uma simulação Python.

Referência: [API Python oficial de MQI](https://www.swi-prolog.org/packages/mqi/prologmqi.html).
