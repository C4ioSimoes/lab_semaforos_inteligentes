# Experimento aplicado ao trânsito

Esta é a extensão do laboratório que compara formas de controlar o cruzamento. O exercício obrigatório de Redes Neurais está em [experimento_neural](../experimento_neural/README.md).

## Ordem de leitura

| Arquivo | Função |
| --- | --- |
| [relatorio.md](relatorio.md) | Tabela com as médias e a comparação entre políticas |
| [resultados.json](resultados.json) | Dados das 45 execuções individuais |
| [comparar.py](comparar.py) | Executa cada combinação de cenário, semente e política |
| [relatorio.py](relatorio.py) | Gera a tabela e atualiza a cópia dos dados servida pela interface |
| [treinar.py](treinar.py) | Treina Perceptron e Adaline com preferências sintéticas entre fases |
| [pesos_transito.json](pesos_transito.json) | Pesos, históricos e acurácia no conjunto sintético de teste |
| [aprendizado.png](aprendizado.png) | Curvas desse treinamento |

Os scripts e os pesos mantêm seus caminhos de execução. Resultados antigos ficam no [histórico](../docs/historico/README.md).

## Resultados atuais

Ensaios recalculados em **30/09/2026**, com pedestres a **1,7 unidade/s**. O relatório foi recalculado após a prioridade de emergência nas redes. As versões anteriores, incluindo a que usava velocidade 1,4, estão preservadas no histórico. A [verificação](../docs/verificacao.md) registra a origem dos arquivos.

Espera acumulada por participante solicitado, em segundos, na média de três sementes:

| Cenário | Tempos fixos | Imperativo | Perceptron | Adaline | Automático |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fluxo desbalanceado | 25,63 | 15,85 | 9,95 | 10,26 | 8,89 |
| Fluxo equilibrado | 13,49 | 11,90 | 12,18 | 12,41 | 10,48 |
| Inversão de fluxo | 20,22 | 12,70 | 9,31 | 8,46 | 7,88 |

As duas redes reduziram essa espera no fluxo desbalanceado e na inversão. No fluxo equilibrado, o Perceptron aumentou a espera em 2,3% e o Adaline em 4,2% em relação ao imperativo. Os modos aplicados também usam verde variável; a comparação não isola o efeito do treinamento.

O relatório usa os nomes do código: `baseline` = Tempos fixos; `urbano` = Automático. O imperativo representa a política comum dos quatro paradigmas. Os testes verificam a equivalência entre eles.

## Configuração dos ensaios

- Horizonte: 240 segundos simulados por execução, com passos de 0,1 s.
- Sementes: 42, 73 e 101.
- Políticas: tempos fixos, imperativo, Perceptron, Adaline e automático.
- Fluxo desbalanceado: 36 carros/min por origem em N/S e 6 em L/O.
- Fluxo equilibrado: 22 carros/min por origem.
- Inversão: começa com 36/6 e troca as taxas após 120 s.
- Em todos: 0,3 ambulância/min por origem e 1 pedestre/min por travessia. Motos e ônibus têm taxa zero nesses ensaios.

São **3 cenários × 3 sementes × 5 políticas = 45 execuções novas**. As taxas diferem do perfil da interface. O programa verifica conflitos a cada passo e confirma a mesma quantidade de solicitações para cada par cenário/semente.

## Como ler as medidas

A espera acumulada inclui concluídos, ativos e pendentes até o fim do ensaio. Não estima o tempo que os participantes restantes ainda esperarão. Ela difere da espera média dos concluídos mostrada no painel principal.

No relatório, fila, concluídos e remanescentes são médias das três execuções. As contagens de emergências atendidas/pendentes são somadas entre as sementes. O tempo de atendimento das emergências é ponderado pela quantidade atendida.

Consulte também fila e quantidade ainda no sistema. Uma melhora em uma medida não garante melhora nas demais.

## Reproduzir os resultados

Na raiz, com as dependências do motor instaladas:

```bash
.venv/bin/python experimento_transito/comparar.py --segundos 240 --sementes 42 73 101
.venv/bin/python experimento_transito/relatorio.py
```

O primeiro comando substitui `resultados.json`; o segundo atualiza `relatorio.md` e `cena_3d/public/comparacao-transito.json`. Para um ensaio de exploração, preserve os resultados atuais usando `--saida /tmp/ensaio-transito.json`.

Esses comandos criam motores independentes e não usam a sessão aberta no navegador. A tabela da interface só é atualizada depois da geração do relatório.

## Treinamento aplicado

O treinamento usa 2.400 preferências sintéticas e outras 1.200 para teste, com semente 20260928. O Perceptron registrado tem 70 épocas e 100% de acerto nesse teste; o Adaline, 2 épocas e 93,75%. Esses percentuais medem a reprodução de uma preferência sintética, não a redução de filas.

Para refazer o treinamento, use o ambiente numérico do experimento AND:

```bash
experimento_neural/.venv/bin/python experimento_transito/treinar.py
```

Esse comando substitui os pesos e a figura de aprendizado. Os pesos atuais foram conferidos sem modificá-los; não é necessário treinar para apresentar. O motor carrega o arquivo ao iniciar.
