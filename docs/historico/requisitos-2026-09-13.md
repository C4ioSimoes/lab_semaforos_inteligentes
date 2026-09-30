Documento de requisitos
Laboratório 3D de Semáforos Inteligentes
Especificação funcional e técnica para projeto acadêmico integrado
Controle	Definição
Versão e data	1.0 • 13 de setembro de 2026
Responsável pela proposta	Caio Simões Martins e equipe acadêmica de três integrantes
Disciplinas	Cidades Inteligentes; Redes Neurais Artificiais; Paradigmas de Programação
Finalidade	Base para implementação, testes, comparação e apresentação do laboratório
Plataforma	Aplicação web 3D local com motor de simulação em Python

Objetivo do documento
Consolidar as decisões do projeto em requisitos verificáveis. O laboratório permitirá observar um cruzamento com múltiplos movimentos e travessias, controlar a chegada de participantes, executar situações de estresse e investigar as decisões de quatro implementações de controlador e de dois neurônios artificiais clássicos.
Resultado esperado
Uma interface 3D com câmera orbital centrada no cruzamento, veículos e pedestres simulados, inserção manual por rua, geração aleatória regulável, diagnóstico das decisões e reprodução de experimentos. As categorias de veículos serão carro, moto, ônibus e ambulância.
Base de consolidação
As escolhas de produto registradas na conversa são requisitos desta versão. Detalhes ainda não definidos anteriormente são explicitados como parâmetros iniciais ou convenções de implementação, sujeitos a revisão versionada. Este documento especifica o sistema a construir; não constitui evidência de implementação ou de desempenho já medido.
A organização com três integrantes foi informada aos docentes, conforme confirmação do responsável pela proposta. Não se exige nova confirmação de composição da equipe neste documento.
Convenções de leitura
RF identifica requisito funcional; RNF, requisito não funcional; RN, regra de negócio; CT, cenário de aceitação. “Deverá” indica obrigação. Limites numéricos de trânsito apresentados como parâmetros didáticos não representam dimensionamento para implantação viária real.

1 Escopo acadêmico e de produto
Problema e objetivo urbano
Investigar a distribuição de atendimento entre movimentos de veículos e travessias de pedestres em um cruzamento com demanda variável. O objetivo experimental é comparar controle fixo e atendimento por demanda com prioridades, medindo filas, espera, atendimento e atendimento de emergências.
A equipe deverá contextualizar um cruzamento ou problema urbano real, com observações ou fontes identificadas. Dados sintéticos e resultados simulados deverão ser identificados como tais. Não há, nos materiais recebidos, enunciado completo de Cidades Inteligentes além da exigência de solucionar um problema real da cidade.
Disciplina	Evidência a produzir
Cidades Inteligentes	Contextualização urbana; protótipo; comparação de políticas; discussão dos resultados e limitações.
Redes Neurais	Notebook Python de Perceptron e Adaline aprendendo AND, com todas as exigências do enunciado e integração de predição ao laboratório.
Paradigmas	Mesmo núcleo de decisão implementado de forma imperativa, orientada a objetos, funcional e lógica; análise comparativa e apresentação.

Incluído na versão final do escopo
    • Um cruzamento com quatro aproximações e múltiplos semáforos, movimentos configurados e travessias de pedestres.
    • Carros, motos, ônibus, ambulâncias e pedestres, com trajetórias e parâmetros próprios.
    • Operação manual e aleatória, controle global e por rua de chegadas, diagnósticos e experimentos reproduzíveis.
    • Quatro controladores equivalentes, regra AND de referência, Perceptron e Adaline, além de uma política fixa para comparação urbana.
Fora do escopo inicial
Reconhecimento por câmera, treinamento de detectores de objetos, previsão de fluxo, aprendizado por reforço, coordenação entre vários cruzamentos, hardware semafórico, implantação real, usuários autenticados e infraestrutura em nuvem. Esses itens somente poderão entrar por revisão do escopo.
Separação da contribuição neural
A categoria dos participantes será informada pelo gerador da simulação. Os neurônios aprenderão exclusivamente a AND obrigatória. Admissibilidade e prioridade serão determinadas por regras explícitas; o projeto não atribuirá aos modelos detecção visual, planejamento completo ou ganho urbano autônomo.

2 Arquitetura e responsabilidades
Componente	Tecnologia e responsabilidade
Interface	TypeScript, HTML e CSS: comandos, seletores, diagnósticos e indicadores.
Cena 3D	Three.js: desenho do cruzamento, participantes, semáforos e câmera orbital.
Motor	Python: relógio oficial, filas, trajetórias, fases, aplicação de comandos e métricas.
Comunicação	FastAPI e WebSocket: comandos e instantâneos de estado ordenados.
Controladores	Python para imperativo, OO e funcional; SWI-Prolog para lógico, integrado ao Python por adaptador persistente.
Experimento neural	Notebook independente com Python, NumPy e Matplotlib; regras de aprendizado escritas manualmente.
Persistência local	Arquivos versionados de cenário, eventos, pesos e resultados; banco de dados não obrigatório no primeiro escopo.

Autoridade do estado
O motor Python será a fonte oficial do estado. O navegador deverá exibir os estados recebidos e enviar comandos, sem decidir localmente as fases ou a posição física oficial dos participantes. A interpolação gráfica poderá suavizar deslocamentos sem alterar tempos, decisões ou métricas.
Isolamento das entregas
O notebook neural deverá executar sem iniciar a aplicação e sem importar FastAPI, Three.js, bibliotecas de modelos prontos ou adaptadores Prolog. As dependências externas do laboratório não serão dependências do experimento neural. Os pesos exportados deverão preservar a ordem [w0, w1, w2] e a convenção bipolar.
Contrato do controlador
Cada versão receberá uma cópia somente para leitura de um estado padronizado e retornará uma proposta de ação e sua justificativa estruturada. O motor aplicará uma validação comum de integridade antes de executar a proposta. Uma rejeição deverá permanecer visível nos diagnósticos.
Execução local
Após instalação das dependências, o laboratório deverá operar localmente, sem API paga de inteligência artificial. Recursos visuais necessários deverão ser distribuídos com a aplicação. Configuração de ambiente e comandos de inicialização serão registrados no README, com versões fixadas para reprodução.

3 Modelo do cruzamento e participantes
RF01 Representar o cruzamento
A cena deverá representar aproximações norte, sul, leste e oeste, faixas de circulação, linhas de retenção, calçadas, travessias e grupos semafóricos identificados. Nomes de ruas poderão ser associados aos identificadores estáveis.
Aceite: Cada rua, faixa, movimento, travessia e fase possuir identificador único e correspondência visível na interface.
RF02 Definir trajetórias e conflitos
O cenário deverá declarar trajetórias de seguir em frente e conversões habilitadas, bem como uma matriz simétrica de conflitos entre movimentos veiculares e de pedestres. Cada fase será um conjunto de movimentos compatíveis.
Aceite: O carregamento rejeitar uma fase que contenha dois movimentos conflitantes; movimento não previsto não aparecer como opção de inserção.
RF03 Distinguir os participantes
O laboratório deverá distinguir carro, moto, ônibus, ambulância e pedestre por aparência, categoria e identificador. Dimensões, velocidade desejada, aceleração e distância mínima serão parâmetros didáticos por categoria.
Aceite: Cada categoria poder ser inserida e inspecionada; métricas permitirem separar as cinco categorias.
RF04 Movimentar e formar filas
Participantes deverão percorrer trajetórias predefinidas, respeitar distância de seguimento, retenção e autorização de entrada. A simulação deverá registrar entrada, início de espera e conclusão do percurso.
Aceite: Um participante parar atrás do anterior sem sobreposição e não ultrapassar a retenção sem permissão.
Convenções iniciais de mobilidade
Motos circularão inicialmente em fila na faixa escolhida, sem circulação entre faixas ou ultrapassagem. Ônibus poderão ocupar maior comprimento configurado. Ambulâncias terão solicitação de prioridade explícita. Pedestres usarão origens e destinos de travessia próprios, não a pista destinada a veículos.
O modelo será microscópico simplificado, com trajetórias conhecidas e passo discreto. Não se pressupõe um modelo físico calibrado de tráfego. Conversões e comportamentos adicionais serão introduzidos somente após validar os conflitos dos movimentos básicos.

4 Interface e navegação visual
RF05 Controlar a câmera orbital
A câmera deverá orbitar ao redor de um alvo fixo no centro do cruzamento, com zoom, rotação e limites de inclinação e distância. O deslocamento lateral do alvo ficará desabilitado.
Aceite: Arrastar e ampliar não deslocar o alvo; câmera não atravessar o solo; existir restauração da vista e vista superior.
RF06 Organizar o laboratório
A interface deverá manter cena central, controles de participantes à esquerda, diagnósticos à direita e execução, linha do tempo e métricas na região inferior. Painéis poderão recolher sem alterar a simulação.
Aceite: O operador conseguir inserir participante, pausar e consultar a decisão mantendo o cruzamento visível.
RF07 Inspecionar elementos
Ao selecionar participante, rua, travessia ou fase, a interface deverá destacar o elemento e exibir seus dados, incluindo categoria, origem, destino, estado e espera quando aplicáveis.
Aceite: Os identificadores mostrados coincidirem com os registros do motor e da linha do tempo.
RF08 Controlar a execução
Disponibilizar iniciar, pausar, retomar, reiniciar, avançar um passo e velocidades 0,5×, 1×, 2× e 5×. O passo inicial do motor será de 0,1 segundo simulado, registrado no cenário.
Aceite: Em pausa, o relógio não avançar; avançar um passo executar exatamente um passo; mudar velocidade não mudar chegadas por minuto simulado.
RF09 Selecionar algoritmos
Permitir selecionar controlador imperativo, OO, funcional ou lógico e avaliador AND de referência, Perceptron ou Adaline. A política fixa deverá estar disponível como baseline separado.
Aceite: Seletores serem independentes; modelo sem pesos válidos ficar indisponível; troca durante exploração ser registrada.
Distinção obrigatória nos controles
A interface deverá rotular separadamente “velocidade da simulação”, “intensidade de chegadas” e “prioridade de atendimento”. A primeira altera o ritmo de execução no computador; a segunda, a demanda por tempo simulado; a terceira, a ordem de decisão do controlador.

5 Inserção manual por rua
RF10 Inserir veículos na rua escolhida
O formulário de inserção deverá exigir categoria, rua de origem e movimento válido, permitindo quantidade unitária ou lote. Deverá incluir botões ou opções para carro, moto, ônibus e ambulância.
Aceite: Ao selecionar rua leste e moto, a solicitação receber essa origem e categoria; nenhum sorteio substituir a escolha manual.
RF11 Inserir pedestres
A inserção de pedestres deverá exigir travessia e lado de origem, com quantidade configurável. A chegada deverá registrar uma solicitação de travessia.
Aceite: Pedestre surgir no acesso de calçada correspondente e aguardar autorização da travessia correta.
RF12 Aguardar espaço de entrada
Quando a área de inserção estiver ocupada, a solicitação deverá aguardar em uma fila externa por origem. O sistema deverá diferenciar horário solicitado e horário efetivamente inserido.
Aceite: Solicitações consecutivas não criarem sobreposição; painel mostrar pendências e espera externa por rua.
RF13 Validar comandos
Rejeitar categoria, origem, trajeto ou quantidade inválidos com mensagem específica. Cada comando deverá possuir identificador para evitar execução duplicada durante retransmissões.
Aceite: Reenviar o mesmo identificador não duplicar participantes; quantidade não inteira ou negativa ser rejeitada.
RF14 Registrar ações manuais
Ações de inserção e mudanças de parâmetros deverão ser registradas no passo oficial do motor, com ordem estável de processamento. Comandos recebidos em pausa poderão ser preparados para o próximo passo.
Aceite: Reproduzir o registro gerar as mesmas solicitações nos mesmos instantes simulados.
Origem e destino
“Rua de origem” designa a aproximação pela qual o participante chega ao cruzamento. A interface deverá traduzir essa escolha para faixa e trajetória válidas. O destino poderá ser derivado do movimento selecionado. Para pedestres, a seleção será feita por travessia e lado, evitando ambiguidade com as quatro aproximações veiculares.
Coexistência dos modos
Inserção manual e geração automática poderão coexistir. O diagnóstico identificará a origem de cada solicitação como manual ou automática. Inserções manuais aumentarão a demanda efetiva e não reduzirão silenciosamente a taxa do gerador.

6 Geração aleatória e intensidade
RF15 Gerar chegadas automaticamente
O software deverá gerar veículos e pedestres aleatoriamente a partir de uma semente registrada. O gerador deverá sortear instantes, categoria, origem e movimento segundo parâmetros do cenário, respeitando trajetórias válidas.
Aceite: Mesma semente, configuração e versão produzirem a mesma sequência de solicitações de chegada.
RF16 Regular demanda por rua
Permitir definir taxas veiculares em participantes por minuto simulado para cada aproximação e taxas de pedestres por travessia ou acesso. Deverá haver multiplicador global e controle específico de carros por rua.
Aceite: Aumentar carros na rua norte não alterar a taxa de pedestres nem a taxa base de motos; definir taxa zero impedir novas chegadas dessa combinação.
RF17 Configurar composição e movimentos
Manter taxas por categoria e rua, ou distribuição equivalente explicitamente exibida. Probabilidades de movimentos deverão somar 1 entre os movimentos habilitados de cada origem.
Aceite: Parâmetros inconsistentes serem rejeitados; painel mostrar taxa efetiva por categoria e rua antes da execução.
RF18 Alterar intensidade durante execução
O operador poderá diminuir ou intensificar o volume durante exploração. Mudanças serão aplicadas em fronteira de passo e afetarão chegadas futuras; participantes já gerados permanecerão no sistema.
Aceite: Mudança aparecer na linha do tempo com configuração anterior e nova, sem apagar filas existentes.
RF19 Disponibilizar perfis de demanda
Fornecer perfis configuráveis de baixa demanda, equilibrado, assimétrico, pico, pedestres intensos e estresse. Cada perfil deverá revelar os valores utilizados.
Aceite: Selecionar perfil preencher parâmetros visíveis e registrar a seleção; perfil de estresse aumentar demanda, não apenas velocidade visual.
RF20 Mostrar demanda solicitada e admitida
Exibir contagens e taxas observadas de solicitações, inserções efetivas, fila externa e recusas explícitas. Limite técnico de capacidade não poderá descartar eventos silenciosamente.
Aceite: Via saturada manter contabilização da demanda que não conseguiu entrar e motivo de eventual interrupção.

7 Convenções do gerador e ensaios de carga
Modelo aleatório inicial
Como convenção de implementação desta versão, cada combinação de origem e categoria terá chegadas por processo de Poisson por trechos de taxa constante. Em cada passo de duração Δt, o número solicitado será amostrado de Poisson(λ × Δt / 60), em que λ é a taxa por minuto simulado. Essa distribuição é um modelo didático, não uma calibração urbana.
O gerador deverá permitir múltiplas chegadas no mesmo passo. Não será utilizada uma probabilidade limitada a uma única chegada por passo, pois isso distorceria testes com volume elevado. A sequência dentro do passo será ordenada por identificadores e regra documentada.
Taxas efetivas
A taxa efetiva de uma categoria em uma rua será sua taxa base multiplicada pelo fator global e pelo fator local configurado. Pedestres terão fator próprio; o controle específico de carros não alterará as demais categorias. O painel mostrará o resultado em participantes por minuto simulado.
Um valor zero interrompe novas solicitações automáticas daquela fonte. Valores positivos indicam média estatística, e não promessa de quantidade exata a cada minuto. A faixa máxima aceita será parametrizada conforme o limite técnico medido e exibida ao usuário.
Reprodutibilidade independente do controlador
O gerador de demanda terá estado aleatório independente do controlador. Entradas ocupadas não suspenderão a geração de solicitações: os eventos irão para fila externa. A reprodução formal utilizará preferencialmente um calendário de chegadas persistido, evitando diferenças causadas por consumo distinto de números aleatórios.
Perfis progressivos de estresse
Os ensaios poderão aplicar degraus de volume ao longo do tempo simulado. Cada degrau terá início, duração e taxas explícitas. O relatório deverá distinguir saturação do tráfego, quando filas crescem, de saturação computacional, quando o motor não acompanha o ritmo solicitado.
Limites técnicos transparentes
Deverão existir limites configuráveis de participantes ativos e pendências. Quando atingidos, o laboratório deverá alertar e pausar ou encerrar o ensaio com motivo registrado. Uma solicitação recusada será contabilizada. Não será permitido remover veículos, pedestres ou solicitações para aparentar fluidez.

8 Fases e regras de integridade
Regra	Obrigação
RN01 Compatibilidade	Jamais autorizar simultaneamente movimentos declarados conflitantes.
RN02 Transição	Encerrar permissões da fase atual, cumprir amarelo veicular aplicável e intervalo de liberação antes de autorizar fase conflitante.
RN03 Ocupação	A nova autorização deverá considerar conclusão ou liberação das trajetórias conflitantes já ocupadas.
RN04 Pedestres	A solicitação não equivale a início da travessia. Travessia iniciada deverá ter seu intervalo de conclusão preservado.
RN05 Tempos	Respeitar mínimos, máximos e intervalos definidos no cenário. Tempos serão didáticos e positivos quando exigidos.
RN06 Validação	A proposta deverá passar por validação comum antes da execução; bloqueios e causas deverão ficar registrados.

RF21 Executar a máquina de estados
O controlador proporá manter fase ou solicitar transição. O motor executará estados explícitos de atendimento, encerramento, liberação e próximo atendimento, com relógios e permissões por grupo semafórico.
Aceite: Não ocorrer troca direta de verde entre fases conflitantes; toda transição possuir histórico de estados.
RF22 Calcular admissibilidade
Para cada fase candidata, calcular se o atendimento pode ser autorizado naquele instante, considerando conflitos, transição, tempos e ocupação. Demanda e admissibilidade alimentarão a AND.
Aceite: Uma fase solicitada durante travessia conflitante apresentar demanda 1 e admissibilidade 0, com justificativa verificável.
RF23 Tratar propostas inválidas
Propostas inconsistentes deverão ser rejeitadas e registradas. O motor deverá preservar a conclusão de movimentos já autorizados e impedir novas permissões conflitantes.
Aceite: Uma proposta de conflito aparecer como rejeitada, sem ser corrigida silenciosamente nem executada.
Elegibilidade e planejamento
Uma fase ainda inadmissível poderá permanecer na fila de solicitações prioritárias e ser escolhida como destino de transição. A AND indica elegibilidade para autorizar atendimento naquele instante; não impede o controlador de planejar o encerramento da fase atual para atender uma solicitação futura.

9 Política inicial de prioridades
A política abaixo formaliza uma convenção inicial para tornar as quatro implementações comparáveis. Parâmetros e alterações deverão ser versionados. As restrições RN01 a RN06 sempre prevalecerão sobre a ordem de preferência.
Ordem	Critério inicial
1	Concluir movimentos e travessias já autorizados e respeitar as condições de transição.
2	Atender solicitação de emergência ativa, com transição regular. Entre emergências, priorizar a solicitação mais antiga.
3	Priorizar demanda que ultrapassou o limiar configurado de espera, pela maior espera.
4	Considerar prioridade de ônibus quando habilitada e sem suprimir o critério de espera anterior.
5	Entre demais demandas, selecionar a fase associada à solicitação mais antiga; usar demanda acumulada como próximo critério.
Desempate final	Utilizar identificador estável de fase em ordem crescente.

RF24 Gerenciar solicitações prioritárias
Ambulâncias poderão solicitar prioridade de emergência; ônibus terão prioridade condicionada e configurável. Carros e motos seguirão atendimento ordinário. Pedestres serão protegidos por solicitação e envelhecimento de espera.
Aceite: Duas emergências conflitantes produzirem decisão determinística; a categoria e o motivo aparecerem no diagnóstico.
RF25 Acompanhar espera excessiva
O sistema deverá acompanhar a solicitação pendente mais antiga por fase e emitir alerta quando ultrapassar o limiar de espera. O envelhecimento será considerado na seleção ordinária.
Aceite: Demanda pequena não ficar invisível por ter fila menor; ultrapassagem do limiar aparecer em métricas e eventos.
Limite da garantia de espera
O limiar é um mecanismo de prioridade e alerta, não uma promessa incondicional de tempo máximo. Demanda acima da capacidade ou fluxo contínuo de emergências pode impedir atendimento no limite desejado. Essas situações deverão permanecer visíveis no relatório, sem alegação de ausência absoluta de espera indefinida.
Política fixa de referência
A baseline utilizará sequência e tempos fixos declarados, com as mesmas regras de integridade, geometria, parâmetros de movimento e demanda. A ausência de prioridade adaptativa será identificada no relatório. A comparação urbana avaliará políticas; a comparação de paradigmas manterá a política idêntica.

10 Implementação em quatro paradigmas
RF26 Resolver o mesmo problema quatro vezes
As quatro versões deverão receber o estado do cruzamento e solicitações, avaliar fases, aplicar a mesma política e devolver ação, fase alvo e justificativa. Não basta distribuir partes diferentes do sistema entre paradigmas.
Aceite: Uma coleção comum de estados produzir ações e fases equivalentes, incluindo desempates.
Versão	Características a demonstrar
Imperativa em Python	Sequência explícita, laços, condicionais e variáveis locais para avaliação e seleção.
Orientada a objetos em Python	Responsabilidades distribuídas entre objetos de domínio e política; encapsulamento efetivo, além de uma função envolvida em classe.
Funcional em Python	Funções puras, composição e estados imutáveis; efeitos externos isolados no adaptador.
Lógica em Prolog	Fatos e regras sobre demanda, conflitos, admissibilidade e precedência; consultas para obter a decisão.

RF27 Comparar decisões lado a lado
Disponibilizar modo de observação em que todos os controladores avaliam o mesmo instantâneo, mas somente o selecionado comanda o motor. Comparações deverão usar versões e configurações iguais.
Aceite: Divergências destacarem estado de entrada, saídas e regras associadas, sem alterar a execução pelos observadores.
Compartilhamento permitido
Motor, dados de entrada, geometria, serialização, visualização e verificação de integridade poderão ser compartilhados. A avaliação e seleção que constituem o problema comparado deverão estar presentes em cada implementação, sem delegar toda a decisão a uma função comum que apague as diferenças de paradigma.
Critérios de análise acadêmica
Comparar clareza, representação de estado, composição, extensibilidade, testabilidade, resolução de conflitos, integração e dificuldades reais. Registrar tentativas incompletas e limitações de forma honesta. Quantidade de linhas e tempo de execução poderão complementar, mas não substituir a análise, que é o foco do enunciado.
O treinamento neural não precisa ser reimplementado em quatro paradigmas. Concorrência poderá existir na infraestrutura, mas não substitui nenhuma das quatro versões exigidas. A apresentação deverá permitir que os três integrantes expliquem as escolhas e os paradigmas sob sua responsabilidade.

11 Especificação do experimento neural
RF28 Preservar a base AND
Treinar Perceptron e Adaline em Python, apenas com NumPy e Matplotlib, implementando manualmente as regras. Usar entradas binárias e saídas bipolares, bias como peso w0 com x0 = 1.
Aceite: Notebook executar autonomamente, sem scikit-learn, Keras, TensorFlow ou biblioteca que implemente os modelos.
x1	x2	d
0	0	−1
0	1	−1
1	0	−1
1	1	+1

Convenção: x = [1, x1, x2]; w = [w0, w1, w2]; u = w · x. A predição retorna +1 se u ≥ 0 e −1 se u < 0. Na integração, x1 representa solicitação de atendimento e x2, admissibilidade naquele instante.
RF29 Treinar Perceptron
Inicializar pesos em zero; usar η = 0,1, até 100 épocas e ordem fixa das quatro amostras. Atualizar w ← w + η(d − y)x, com y após a função sinal. Imprimir erros de classificação por época e parar após época inteira sem erro.
Aceite: Atualização incluir bias; histórico e motivo de parada serem preservados; não alterar os parâmetros obrigatórios.
RF30 Treinar Adaline
Usar cópia independente da mesma inicialização, η = 0,1 e até 100 épocas. Atualizar amostra a amostra por w ← w + η(d − u)x. Não usar sinal na atualização. Imprimir SSE por época e parar por |SSEt − SSEt−1| < 10⁻⁶ ou pelo limite.
Aceite: Erro de treino ser calculado sobre saída linear; motivo e época de parada ficarem disponíveis.
Convenção de SSE e comparação
Calcular SSE ao final de cada época sobre as quatro amostras com os pesos daquele final: SSE = soma de (d − w · x)². Avaliar a variação a partir de duas épocas medidas. A convenção deverá constar no notebook. SSE não é contagem de erros; não se exigirá SSE zero nem queda estritamente monotônica nas atualizações amostra a amostra.

12 Entregáveis neurais e diagnóstico
RF31 Executar predição interativa
Após treinamento, cada modelo deverá oferecer laço que solicita dois valores, exibe predição e repete até receber sair. Tratar texto inválido; no domínio adotado, aceitar somente 0 e 1.
Aceite: Os dois laços encerrarem por sair e continuarem funcionando após uma entrada inválida.
RF32 Produzir a comparação obrigatória
No mesmo notebook, apresentar curvas de erros por época do Perceptron e SSE do Adaline, em subplots ou sobrepostas com escalas claras; tabela de pesos, épocas e reta de decisão; texto de 10 a 15 linhas.
Aceite: A tabela conter w0 + w1x1 + w2x2 = 0 para cada modelo e o texto explicar onde cada modelo mede o erro, descrevendo as curvas efetivamente obtidas.
RF33 Integrar pesos treinados
Exportar pesos e metadados de modelo, inicialização, taxa, épocas, convenção de sinal e versão. Validar antes de permitir seleção no laboratório e verificar as quatro combinações.
Aceite: Pesos não finitos, formato inválido ou modelo sem treinamento impedirem ativação; divergências da AND serem exibidas.
RF34 Exibir diagnóstico neural
Para cada avaliação, mostrar modelo, entradas, pesos, bias, soma ponderada, saída e resultado AND de referência. Classificar a saída como elegibilidade, sem porcentagem de confiança.
Aceite: Valores exibidos corresponderem ao cálculo registrado; soma ponderada não ser rotulada como probabilidade.
RF35 Explicar a decisão do controlador
Exibir fase atual, candidatas, descartes e motivos, prioridades, desempate, proposta, ação executada e bloqueio eventual. O registro deverá ser gerado pelo algoritmo e motor, não por texto fictício independente.
Aceite: Ao selecionar um evento, ser possível reconstruir os critérios e identificar por que uma fase foi mantida ou substituída.
Relação entre aprendizado e desempenho urbano
Se os dois modelos reproduzirem corretamente a AND, espera-se equivalência com a regra de referência nas mesmas entradas. Isso evidencia integração e aprendizado, não superioridade de gestão de tráfego. Os gráficos acadêmicos medem aprendizado; as métricas de espera medem o comportamento da política de controle.

13 Contratos e dados de execução
Estrutura	Campos mínimos
Cenário	schema_version, scenario_id, geometria, movimentos, conflitos, fases, tempos, parâmetros de participantes, taxas, semente e passo.
Participante	id, categoria, origem, destino, trajetória, posição, estado, instante solicitado, instante inserido e solicitação prioritária.
Instantâneo	run_id, step, simulation_time, fase, estado de transição, ocupações, filas, solicitações e versão de configuração.
Comando	command_id, tipo, parâmetros, passo solicitado quando aplicável e confirmação com passo de aplicação ou erro.
Decisão	decision_id, step, controlador, política, modelo, candidatas, avaliações, motivos, proposta e resultado da validação.
Evento	event_id, ordem, passo, tempo simulado, tipo, origem, parâmetros e resultado.
Resultado	Versões, configuração, demanda solicitada e admitida, métricas, motivo de término e limites atingidos.

RF36 Sincronizar interface e motor
Comandos e atualizações deverão conter identificadores e ordem. O cliente deverá descartar instantâneos antigos e receber estado completo ao conectar ou reconectar.
Aceite: Reconexão não duplicar comandos nem retroceder o estado visual; indicar conexão perdida e estado desatualizado.
Comportamento em perda de conexão
Como convenção local inicial, o motor pausará ao perder a conexão do operador. A retomada exigirá sincronização e comando explícito. Esse evento será registrado; não se presumirá que a imagem congelada representa uma simulação em execução.
Passo e ordenação
Em cada passo: aplicar comandos confirmados; gerar solicitações programadas; admitir participantes quando houver espaço; atualizar o estado necessário à decisão; obter e validar proposta; avançar movimentos e relógios; registrar métricas; emitir instantâneo. A ordem definitiva deverá ser fixa e versionada, incluindo tratamento dos eventos simultâneos.
O adaptador Prolog deverá preservar tipos, unidades, identificadores e ordenação do contrato. Sua comunicação terá tratamento explícito de falha, sem trocar silenciosamente para outro paradigma. O tempo do adaptador será separado do cálculo quando a instrumentação permitir.

14 Reprodução e avaliação experimental
RF37 Salvar e reproduzir experimentos
Salvar cenário, semente, calendário de chegadas, comandos, parâmetros, pesos e versões. Permitir reiniciar do estado inicial e reproduzir eventos nos mesmos passos.
Aceite: Repetição com a mesma versão reproduzir sequência de decisões e métricas determinísticas, ressalvadas medições de tempo de computador.
RF38 Comparar políticas e implementações
Executar controle fixo e por demanda sobre o mesmo calendário. Comparar paradigmas com a mesma política. Em ensaios formais, fixar algoritmo por execução; trocas exploratórias deverão ser marcadas.
Aceite: Relatório identificar exatamente o que variou e impedir comparação apresentada como equivalente quando configurações diferirem.
RF39 Medir e exportar resultados
Exportar configuração e eventos em JSON e métricas tabulares em CSV. Disponibilizar indicadores por rua e categoria, com intervalo observado e motivo de encerramento.
Aceite: Resultados incluírem participantes concluídos, ativos e pendentes de entrada, sem ocultar os não atendidos.
Métrica	Definição operacional inicial
Espera interna	Tempo acumulado com velocidade abaixo de limiar configurado após inserção; separar por categoria.
Espera externa	Tempo entre solicitação de chegada e inserção; pendentes acumulam até o término.
Espera de pedestre	Tempo da solicitação até autorização/início de travessia, distinguindo solicitação pendente.
Fila	Participantes aguardando atendimento por aproximação; média ponderada pelo tempo e máximo.
Vazão	Percursos concluídos por unidade de tempo simulado, com total de chegadas informado.
Emergência	Tempo da solicitação prioritária ao início de atendimento e à conclusão do percurso.
Integridade	Contagem de conflitos autorizados, propostas bloqueadas e violações temporais.

Interpretação
Separar espera dos concluídos e espera acumulada dos participantes ainda presentes, pois apenas os concluídos podem produzir viés. Repetir cenários aleatórios com sementes pareadas entre políticas. Ganhos percentuais somente serão calculados sobre métricas comparáveis e denominador não nulo; nenhum ganho é presumido nesta especificação.

15 Requisitos não funcionais
ID	Requisito e verificação
RNF01 Determinismo	Passo fixo e eventos ordenados. Repetir execução deverá preservar resultados lógicos independentemente de FPS, câmera ou velocidade de reprodução.
RNF02 Observabilidade	Toda proposta deverá possuir entrada associada, critérios e resultado da aplicação; diagnosticar divergências sem ocultar rejeições.
RNF03 Modularidade	Motor, renderização, controladores, adaptadores e treino deverão ter interfaces separadas e execução verificável.
RNF04 Dependências	Notebook somente com NumPy e Matplotlib; laboratório com versões documentadas e instalação reproduzível.
RNF05 Interface	Cores acompanhadas de texto ou ícones; controles rotulados, foco de teclado e mensagens de erro específicas.
RNF06 Robustez	Validar comandos, arquivos e números não finitos; informar falhas do motor, comunicação e Prolog, sem substituição oculta.
RNF07 Persistência	Versionar esquema e configuração; rejeitar arquivo incompatível com mensagem e não sobrescrever resultado anterior sem ação explícita.
RNF08 Desempenho	Medir FPS, duração dos passos, tempo de decisão e atraso visual separadamente; informar quando não acompanhar o ritmo solicitado.
RNF09 Execução experimental	Disponibilizar ensaios sem renderização; separar aquecimento, carga e repetições. Registrar hardware e ambiente.
RNF10 Limites	Exibir capacidade configurada e contabilizar pendências, recusas e motivo de pausa; proibir descarte silencioso.
RNF11 Documentação	README, instruções de reprodução, contrato, política e análise acadêmica deverão acompanhar o código.
RNF12 Operação local	Não depender de inferência paga ou de conexão externa após instalação; manter recursos necessários localmente.

Metas iniciais de desempenho
Adotar como alvo provisório pelo menos 30 FPS no cenário básico na máquina de referência, e passo do motor abaixo de 100 ms para execução em 1× com Δt = 0,1 s. Esses alvos deverão ser medidos e não representam capacidade garantida. Em 5×, o orçamento necessário para acompanhar o relógio será menor.
A quantidade máxima suportada não está definida sem medição. O primeiro benchmark deverá registrar processador, memória, GPU, navegador, versões, número de participantes e percentis de duração. Comparar paradigmas não autoriza atribuir à linguagem um custo que pertence ao transporte ou à renderização.

16 Cenários de aceitação
ID	Execução e resultado esperado	Cobertura
CT01	Orbitar e ampliar: alvo permanece no centro; restaurar vista funciona.	RF05–07
CT02	Adicionar moto na rua oeste: origem preservada, sem sobreposição e com categoria correta.	RF03–04; RF10–13
CT03	Adicionar pedestres por travessia: aguardam e cruzam somente com autorização.	RF11; RN04
CT04	Repetir semente e calendário: mesmas solicitações em cada passo.	RF15; RF37
CT05	Aumentar apenas carros ao norte: taxa efetiva muda só no alvo; outras fontes preservadas.	RF16–18
CT06	Executar estresse: fila externa cresce e é contada; limite técnico gera motivo explícito.	RF19–20; RNF10
CT07	Ambulância durante travessia: pedido registrado, sem liberação conflitante; atendimento após transição.	RF21–25
CT08	Emergências simultâneas: desempate reproduzível e diagnóstico com motivo.	RF24; política
CT09	Mesmo estado nos quatro paradigmas: mesma ação e fase; divergência é destacada.	RF26–27
CT10	Treinar e consultar os modelos: convenções, parâmetros, logs e quatro entradas verificados.	RF28–34
CT11	Pausar, avançar e reproduzir em velocidades diferentes: mesmo estado por passo.	RF08; RNF01
CT12	Desconectar e reconectar: pausa, sincronização e ausência de comandos duplicados.	RF13; RF36
CT13	Comparar políticas: mesmas chegadas, configurações identificadas e pendentes incluídos.	RF38–39
CT14	Forçar proposta conflitante: bloqueio registrado, nenhuma nova permissão conflitante.	RF23; RN01
CT15	Receber entrada inválida no notebook: mensagem, nova tentativa e saída por sair em ambos.	RF31

Conclusão dos testes
Cada cenário deverá produzir identificação da versão, parâmetros, resultado esperado, observado e evidência. CT09 verifica equivalência funcional, não igualdade textual de justificativas. CT10 não deverá inventar pesos ou épocas: valores serão obtidos da execução efetiva.

17 Entregas e sequência de implementação
Marco	Resultado verificável
M1 Contrato e cena	Contrato de dados, geometria inicial, câmera orbital e formulário de inserção por rua.
M2 Fluxo completo	Motor Python integrado: participante entra, espera, recebe atendimento e aparece no diagnóstico; pausa e passo funcionam.
M3 Demanda e participantes	Motos, ônibus, ambulâncias, pedestres, geração aleatória, controles por rua e contabilização externa.
M4 Controle completo	Fases, conflitos, conversões previstas, prioridades, integridade e baseline fixa.
M5 Paradigmas	Quatro versões da mesma decisão e modo de comparação com entradas comuns.
M6 Redes neurais	Notebook completo, pesos exportados, seleção e diagnóstico de Perceptron e Adaline.
M7 Experimentos	Replay, perfis de estresse, exportações, benchmarks e análise acadêmica.

Primeiro incremento obrigatório
Demonstrar uma trajetória completa: selecionar rua, adicionar carro, observar entrada e parada no vermelho, visualizar motivo de espera, acompanhar a mudança de fase e a passagem. A estrutura deverá prever outras categorias desde o início. A aparência poderá usar geometria simples, mantendo legibilidade e identificadores.
Artefatos de entrega
    • Código da aplicação, motor e quatro controladores, com instruções de ambiente e execução.
    • Notebook neural autônomo com treinamento, interação, gráficos, tabela e texto obrigatório.
    • Cenários, calendários de chegada, configurações e resultados reproduzíveis.
    • Relatório urbano e análise comparativa dos paradigmas, com evidências e limitações.
    • Roteiro de apresentação em que a equipe de três integrantes demonstra e explica o projeto.
Rastreabilidade resumida
Cidades Inteligentes: RF01–25 e RF37–39, contexto urbano e métricas. Paradigmas: RF26–27, contrato comum, política e análise. Redes Neurais: RF28–34 e enunciado integral. Laboratório transversal: RF05–20, RF35–39 e RNF01–12. A implementação final deverá atender todos os RF; os marcos representam ordem de construção, não exclusão de requisitos.

18 Fontes e gestão da especificação
Documentos acadêmicos de referência
Trabalho_Redes_Neurais_Artificiais.docx. Enunciado fornecido pelo responsável pela proposta. Exige Perceptron e Adaline para AND, Python com NumPy e Matplotlib, treinamento manual, convenções e parâmetros específicos, interação e comparação no mesmo notebook.
Trabalho_paradigmas_de_programacao_av1.docx. Enunciado fornecido pelo responsável pela proposta. Exige o mesmo problema nos paradigmas imperativo, orientado a objetos, funcional e lógico e prioriza a análise comparativa sobre a mera execução do código.
Decisões consolidadas da conversa de planejamento: cruzamento complexo, participantes e prioridades; plataforma web 3D local; câmera orbital fixa no centro; diagnóstico real; escolha por rua; adição de motos; geração aleatória e regulagem de intensidade; organização com três integrantes comunicada aos docentes.
Referências técnicas consultadas no planejamento
Three.js. OrbitControls. Câmera orbital, alvo, zoom e desativação de pan. https://threejs.org/docs/pages/OrbitControls.html
FastAPI. WebSockets. Comunicação bidirecional entre cliente e servidor. https://fastapi.tiangolo.com/advanced/websockets/
SWI-Prolog. Machine Query Interface Overview. Integração de Prolog com Python. https://www.swi-prolog.org/pldoc/man?section=mqi-overview
NumPy. numpy.dot. Produto escalar utilizado nos cálculos manuais. https://numpy.org/doc/stable/reference/generated/numpy.dot.html
Itens a calibrar durante a implementação
    • Geometria final, movimentos e matriz de conflitos do cruzamento escolhido.
    • Tempos semafóricos, parâmetros de mobilidade e limiares de espera didáticos.
    • Taxas dos perfis, limite técnico de participantes e hardware de referência.
    • Contextualização urbana e eventuais exigências adicionais de Cidades Inteligentes.
Esses itens não impedem o início do primeiro incremento. Seus valores deverão ficar explícitos nos cenários e resultados. Alterações em política, contrato, gerador ou semântica de métricas exigirão atualização de versão para manter a comparabilidade dos experimentos.
Histórico
Versão	Registro
1.0	Consolidação inicial do laboratório e requisitos acadêmicos; inclusão de motos, geração aleatória, intensidade ajustável, estresse e inserção manual por rua.
