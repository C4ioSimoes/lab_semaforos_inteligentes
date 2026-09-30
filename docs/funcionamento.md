# Guia técnico — Laboratório de Semáforos Inteligentes

Motor FastAPI e cena Three.js, com relógio oficial Python
(Δt = 0,1 s), inserção manual de quatro categorias veiculares e pedestres,
retenção no vermelho, filas sem sobreposição, demanda automática Poisson e
controle semafórico com tempos fixos, quatro paradigmas, redes aplicadas e modo automático.
Para a apresentação, use o [roteiro das disciplinas](apresentacao/README.md); os valores atuais estão em [Parâmetros](parametros.md).
Posições, admissões, solicitações e taxas observadas pertencem exclusivamente ao
Python. Ambiente Python validado: 3.12.3.

Para executar a interface em outro terminal: `cd cena_3d`, `npm ci` e
`npm run dev`. Consulte [as instruções da cena 3D](../cena_3d/README.md).

## Executar

Na raiz do projeto, com Python 3.12 instalado:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r motor_python/requirements.txt
python -m uvicorn motor_python.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Use um único processo (`--workers 1`): o estado oficial reside na memória desse
processo. Reiniciar o servidor cria uma execução com novo `run_id` e passo zero.
As dependências diretas e transitivas estão fixadas nos arquivos `requirements.txt`
e `requirements-dev.txt`; os arquivos `.in` registram as dependências diretas.

Para **Lógico (Prolog)**, instale também SWI-Prolog no sistema, com `swipl` no
PATH. Ambiente validado: **SWI-Prolog 9.0.4** e **swiplserver 1.0.2** (esta biblioteca
Python já está fixada nos requirements). Em Debian/Ubuntu:

```bash
sudo apt install swi-prolog-nox
swipl --version
swipl -q -g "use_module(library(mqi)),halt"
```

A integração usa a [Machine Query Interface oficial](https://www.swi-prolog.org/pldoc/man?section=mqi-overview).
Uma sessão persistente executa `controladores/logico.pl`; nenhuma nova instância
SWI é criada por tick. Após a instalação, o processamento é inteiramente local.
Sem SWI/MQI, a seleção é rejeitada com erro explícito. Se a sessão falhar durante
a execução, o motor congela o ensaio, preserva o controlador selecionado e exibe
o motivo. Reinicie o motor para iniciar outro ensaio; não existe fallback automático.

## Comunicação

Conecte a interface a `ws://127.0.0.1:8000/ws`. A conexão recebe imediatamente um
objeto JSON `Instantaneo`, sem envelope adicional. Em 1× há uma atualização por passo;
na execução acelerada, a publicação periódica é limitada a 20 estados por segundo real.
Confirmações de comandos usam `tipo: "confirmacao_comando"`.
O [protocolo 1.8](../motor_python/PROTOCOLO.md) documenta os payloads de inserção e
configuração, posições oficiais e diagnóstico de demanda. Os nomes dos contratos
da Seção 13 foram normalizados para `snake_case`, sem acentos.

O relógio começa na inicialização do servidor e avança a cada 0,1 segundo, em 1×.
O tempo simulado é calculado como `step / 10`, evitando soma acumulada de floats.
O agendamento usa relógio monotônico; atraso de processamento não aumenta o passo
simulado nem elimina passos. Os clientes compartilham a mesma execução e recebem
cópias dos estados. A conexão não cria outro relógio.

O transporte aceita `inserir_participante`, `configurar_gerador` e
`configurar_controlador`, `configurar_modelo_neural`, `configurar_operacao`,
`configurar_velocidade` e `resetar_simulacao`. O motor valida,
deduplica por `command_id`, aplica no próximo passo e confirma ao solicitante.
Veículos selecionam categoria e N/S/L/O; pedestres selecionam travessia, lado e
quantidade. Todos aguardam espaço na entrada. Veículos param antes da retenção
ou atrás do líder; pedestres aguardam na calçada até a fase autorizada.
A baseline alterna Norte/Sul → Leste/Oeste → Pedestres: 10 s de atendimento,
3 s de amarelo veicular e pelo menos 1 s de vermelho de liberação. Ocupação
conflitante prolonga a liberação; quem já iniciou termina com proteção.
O amarelo bloqueia novas entradas neste modelo didático simplificado.

No painel **Trânsito**, **Entrada de trânsito** liga/desliga novas chegadas.
**Incluir pedestres** pode ser desmarcado para impedir apenas novas chegadas de pedestres; **Quantidade de trânsito** ajusta as taxas durante a execução.
A geração começa desligada. Desligar impede novas chegadas; pedidos já aceitos
continuam sendo atendidos. A cena ocupa toda a janela; **Dados** e **Trânsito** recolhem os painéis translúcidos. O painel de dados mostra conexão, tempo, fase,
contagens, vazão e espera média. Inserção manual permanece disponível pela API.
Os modos ficam em **Escolher controle dos sinais**. Downloads ficam em **Salvar resultados**; diagnósticos, em **Detalhes técnicos**. Veja [implementação e trechos de código](../cena_3d/README.md).

Um cliente que acumule 100 mensagens pendentes tem o fluxo encerrado com código 1013 e deve reconectar
para obter o estado atual. Esse limite protege o relógio contra clientes lentos.

## Estrutura

- `motor_python/modelos.py`: Cenário, Participante, Instantâneo, Comando, Decisão,
  Evento e Resultado, conforme a Seção 13.
- `motor_python/motor.py`: relógio e distribuição dos instantâneos.
- `motor_python/movimento.py`: trajetórias, dimensões, velocidades e folgas por categoria.
- `motor_python/gerador.py`: Poisson por fonte, configuração, semente e diagnóstico.
- `motor_python/pedestres.py`: acessos e posições de espera nas calçadas.
- `motor_python/controle.py`: matriz de conflitos, validação comum, estados e baseline.
- `motor_python/metricas.py`: vazão e esperas por origem, categoria e situação.
- `controladores/`: contratos imutáveis e políticas imperativa, OO, funcional e lógica (Prolog/MQI).
- `motor_python/main.py`: ciclo de vida FastAPI e endpoint WebSocket.
- `tests/`: verificação do relógio, contratos, inserção, movimento e transporte.

## Testes

```bash
python -m pip install -r motor_python/requirements-dev.txt
python -m pytest -q
```

## Recursos e limites atuais

O reinício pela interface e a velocidade de 1× a 24× estão implementados.
Pausa, retomada e avanço manual de um passo não estão disponíveis. O relógio
continua avançando sem clientes conectados.

Também não há carregamento completo de cenários, conversões adicionais,
comparação simultânea de execuções na tela, persistência automática ou replay.
A tabela de comparação disponível na interface vem de ensaios separados.
A baseline de tempos fixos não considera prioridades de ambulância ou ônibus.

Os limites padrão são 200 ativos, 2.000 pendências e taxa efetiva de até 6.000/min
por combinação veicular ou travessia. Atingir capacidade interrompe o ensaio com
motivo e recusas contabilizadas; nenhuma fila é apagada. Use **Recomeçar simulação** para
um novo ensaio. Veja as convenções e a medição inicial no protocolo.

Referências de infraestrutura: [WebSockets no FastAPI](https://fastapi.tiangolo.com/advanced/websockets/)
e [ciclo de vida da aplicação](https://fastapi.tiangolo.com/advanced/events/).


## Controle e métricas

Os oito movimentos habilitados (quatro retos e quatro travessias) têm matriz
simétrica explícita em `controle.py`. `ConfiguracaoControle` rejeita fases
incompatíveis, movimentos desconhecidos, conflitos omitidos e tempos inválidos.
É possível fornecer essa configuração ao construir `Motor`; os tempos são passos
inteiros de 0,1 s. O controlador recebe um estado imutável e apenas propõe ações;
a máquina do motor valida e executa as mudanças. O ciclo começa em liberação.

Veículos mantêm seguimento ao atravessar e só saem do instantâneo quando toda a
carroceria alcançou a saída. Cada sentido utiliza duas faixas, externa e interna,
com admissão e seguimento independentes. A escolha da faixa ocorre na entrada:
entre as livres, o motor favorece a menor extensão de fila, alternando em empates.
O veículo permanece na faixa escolhida até concluir o percurso; não há troca de
faixa. Filas e métricas por origem somam as duas faixas. A saída fica em ±90 unidades.

Na abertura do verde, todos os
pedestres admitidos das travessias permitidas são autorizados no mesmo passo.
Percursos individuais, sentidos separados e preferência local nas esquinas
preservam as distâncias; quem iniciou termina mesmo após o vermelho. O motor
mantém bloqueadas as fases conflitantes até a saída de todos os autorizados.

O painel mostra vazão e espera média dos concluídos; as métricas completas por
origem/categoria, ativos e pendentes continuam disponíveis nas exportações.
Todos os valores vêm do Python.


## Selecionar controlador e prioridades

Em **Escolher controle dos sinais → Regras**, escolha **Tempos fixos** ou uma das quatro opções de prioridades (Imperativo, Orientado a objetos, Funcional ou Lógico). Nas opções de prioridades, ajuste **Dar prioridade após (segundos)**, **Priorizar ambulâncias** e **Priorizar ônibus**. Clique em **Ativar regras**: o motor confirma a aplicação no próximo passo e registra a troca
como exploração. Não reinicia o ensaio, a fase, as filas ou o gerador.

A baseline continua sendo o padrão. Os outros quatro implementam a mesma política
em código independente: proteção dos movimentos/transições → emergências → espera
acima do limiar → ônibus → maior demanda. A política atual usa maior demanda
como critério ordinário; a especificação original usava antiguidade nesse ponto.
Os desempates e contratos estão em [Controladores](../controladores/README.md).

Para uma ambulância inserida pela API, use `solicitacao_prioritaria`. As
automáticas recebem o pedido explícito por convenção do gerador. A prioridade não
permite ultrapassar a fila física nem ignorar amarelo, liberação ou pedestres.
As configurações do experimento mostram controlador vigente, proposta e avaliações por fase,
incluindo maior espera, demanda, critério e motivo de inadmissibilidade.

## Experimento neural

O [notebook de Perceptron e Adaline](../experimento_neural/and_perceptron_adaline.ipynb)
executa de forma independente, usando Python, NumPy e Matplotlib. Contém as
atualizações manuais para AND bipolar, históricos, subplots, tabela, retas de
decisão, comparação acadêmica e um laço interativo que exibe ambos os modelos.
Os [pesos e metadados exportados](../pesos_neurais.json) preservam a
precisão completa e foram verificados nas quatro combinações da AND.

Veja [instalação, reprodução e contrato JSON](../experimento_neural/README.md).
As dependências do experimento ficam em ambiente próprio. O motor carrega os
pesos exportados ao iniciar, conforme a seção seguinte.


## Integração da AND e exportações

Com `pesos_neurais.json` na raiz, inicie o motor normalmente. Com o modo Regras ativo, abra **Regras → Para estudar: lógica AND**, escolha **AND de referência**, **Perceptron** ou **Adaline** e clique em **Aplicar ao exercício**. A troca é confirmada no próximo passo, sem trocar
o paradigma, reiniciar a simulação ou modificar a demanda. O motor valida
formato, treinamento, parâmetros, pesos finitos e as quatro combinações AND.
Modelos inválidos ficam indisponíveis e as divergências aparecem na interface.
Para carregar um novo arquivo de pesos, reinicie o servidor.

A seção **Ver cálculos da AND** mostra cada fase, modelo, entradas, pesos completos,
bias, soma linear, saída bipolar e AND de referência. `x1` é a solicitação:
demanda pendente nos adaptativos e solicitação programada na baseline fixa.
`x2` é a admissibilidade calculada pelo motor antes da transição. A elegibilidade
controla a abertura da fase; a prioridade ainda escolhe o destino da transição.
Amarelo, liberação, tempo mínimo e ocupações continuam sendo validados pelo motor.
Os resultados não são probabilidades. Os modelos válidos reproduzem a AND;
a integração não implica superioridade no controle de trânsito.

Em **Salvar resultados**, **Baixar histórico (JSON)** baixa
`GET http://127.0.0.1:8000/exportar/eventos`, incluindo configurações inicial e
atual, semente, pesos/metadados, comandos aplicados, eventos, transições de fase,
participantes ativos e pendentes, métricas e intervalo observado.
**Baixar planilha (CSV)** usa `GET /exportar/metricas`: uma série de resumos
acumulados desde zero, amostrada a cada segundo simulado, incluindo também o
passo exato do download. Há linhas de total, origem, categoria e origem/categoria;
esses escopos se sobrepõem e não devem ser somados entre si.

O CSV inclui vazão por minuto simulado, esperas dos concluídos e dos não
atendidos separadamente, filas médias/máximas internas e externas, tempos de
emergência, fase, controlador, avaliador, chegadas e propostas bloqueadas.
Filas médias usam o comprimento ao final de cada passo ponderado por 0,1 s.
Os instantes exatos das mudanças de fase estão em `historico_fases` no JSON.
`motivo_encerramento=em_andamento` identifica um recorte de uma execução viva;
um ensaio interrompido inclui o motivo efetivo. Cada arquivo tem run_id e passo
de exportação; dois downloads consecutivos podem cobrir passos diferentes.

Os downloads não pausam o motor. Eventos e séries ficam em memória durante a
execução: exporte antes de reiniciar o servidor para preservá-los. Não há replay
nem persistência automática. Trocas exploratórias de modelo e
controlador ficam registradas e devem ser consideradas nas comparações.

### Resetar sem reiniciar o servidor

O botão **Recomeçar simulação**, abaixo dos resultados, zera tempo, veículos, pedestres, filas e métricas. O modo e as configurações de geração são mantidos; se a geração estiver ligada, novos participantes voltarão a chegar. A semente é reiniciada para permitir repetir o experimento. O botão também permite sair de uma interrupção por limite técnico. Para conservar o histórico atual, exporte os dados antes de resetar.

### Acelerar a simulação

Abaixo de **Quantidade de trânsito**, use **Velocidade da simulação**, de **1×**
a **24×**. A mudança é automática e vale para todos os clientes conectados.
O valor **Ativa** confirma a velocidade aplicada. O reset mantém essa escolha.

A velocidade acelera o relógio inteiro: semáforos, veículos, pedestres e chegadas.
As taxas, tempos de espera e métricas continuam em unidades simuladas. Os cálculos
mantêm passos de 0,1 s e os mesmos resultados para a mesma semente e comandos nos
mesmos passos. Só as atualizações da tela são limitadas a 20 por segundo real.
O ritmo alcançado depende do computador; sob carga o motor desacelera, sem pular
passos ou mudar as regras. Os históricos acumulam mais rápido no tempo real.
