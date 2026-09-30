# Motor da simulação

Esta pasta mantém o estado oficial do cruzamento: relógio, participantes, filas, sinais e métricas. A interface recebe esse estado por WebSocket.

Para apresentar o trabalho, comece pelo [roteiro da disciplina](../docs/apresentacao/README.md). Para localizar um valor, use a [tabela de parâmetros](../docs/parametros.md).

## Ordem de leitura

| Ordem | Arquivo | Responsabilidade |
| --- | --- | --- |
| 1 | [main.py](main.py) | Inicia um motor, recebe comandos em `/ws` e oferece os downloads |
| 2 | [modelos.py](modelos.py) | Define e valida os formatos de comandos, participantes e respostas |
| 3 | [motor.py](motor.py) | Aplica comandos, avança a simulação e reúne os resultados |
| 4 | [controle.py](controle.py) | Define fases, conflitos, transições e a política de tempos fixos |
| 5 | [neural.py](neural.py) | Carrega e valida os pesos da AND |
| 6 | [transito.py](transito.py) | Implementa os modos Rede neural e Automático |

Os quatro paradigmas estão na pasta [controladores](../controladores/README.md).

## Arquivos de apoio

| Arquivo | Quando consultar |
| --- | --- |
| [gerador.py](gerador.py) | Chegadas aleatórias, taxas e semente |
| [movimento.py](movimento.py) | Trajetórias, faixas, dimensões e velocidades de veículos |
| [pedestres.py](pedestres.py) | Travessias, acessos, distâncias e velocidade dos pedestres |
| [metricas.py](metricas.py) | Como espera, fila, vazão e atendimento são calculados |
| [exportacao.py](exportacao.py) | Como as métricas viram uma planilha CSV |
| [PROTOCOLO.md](PROTOCOLO.md) | Exemplos completos de comandos e respostas |
| `requirements.in` / `requirements.txt` | Dependências diretas / versões fixadas para executar |
| `requirements-dev.in` / `requirements-dev.txt` | Dependências adicionais para testes |
| `__init__.py` | Identifica a pasta como pacote Python |

## Como localizar uma ação em motor.py

| Ação | Método para buscar no editor |
| --- | --- |
| Validar um comando recebido | `receber_comando` |
| Aplicar configurações | `_aplicar_comandos` |
| Recomeçar a simulação | `_reiniciar` |
| Fazer um passo completo | `_avancar` |
| Gerar e admitir participantes | `_gerar_chegadas`, `_admitir_participantes` |
| Decidir no modo Regras | `_decidir` |
| Decidir nos modos aplicados | `_decidir_transito` |
| Mover veículos e pedestres | `_mover_participantes`, `_mover_pedestres` |
| Montar o estado enviado à tela | `instantaneo` |
| Exportar a execução | `exportar_experimento` |
| Agendar os passos no tempo real | `executar` |

O passo permanece em 0,1 segundo simulado. A velocidade de 1× a 24× muda o agendamento. Os controladores propõem decisões; `MaquinaSemaforica`, em `controle.py`, verifica se elas podem ser executadas.

## Executar a partir da raiz

```bash
.venv/bin/python -m uvicorn motor_python.main:app --host 127.0.0.1 --port 8000 --workers 1
```

As instruções de instalação estão no [README principal](../README.md). Use um worker: cada processo tem sua própria simulação em memória.

## Arquivos lidos pelo motor

- [pesos_neurais.json](../pesos_neurais.json): AND acadêmica, três pesos por modelo.
- [pesos_transito.json](../experimento_transito/pesos_transito.json): extensão de trânsito, cinco pesos por modelo.

Eles são carregados na inicialização. Não é preciso treinar novamente para apresentar. Os relatórios de ensaios não são usados para tomar decisões durante a simulação.
