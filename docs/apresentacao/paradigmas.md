# Paradigmas da Programação

O enunciado pede um problema implementado em quatro paradigmas e valoriza a análise comparativa. O problema escolhido é decidir a próxima fase de atendimento de um cruzamento.

## 1. Explique a regra comum

A política atende, nesta ordem: emergência solicitada, espera acima do limite, ônibus quando a opção estiver ligada e maior demanda. Os desempates usam antiguidade e identificador da fase, conforme o [contrato dos controladores](../../controladores/README.md).

Cada implementação recebe o mesmo estado e devolve uma proposta: manter, transicionar ou aguardar. O motor verifica tempos e conflitos antes de abrir o sinal. Escolher uma fase não significa liberá-la imediatamente.

## 2. Abra os arquivos nesta ordem

| Ordem | Arquivo | Trecho para mostrar |
| --- | --- | --- |
| 1 | [contratos.py](../../controladores/contratos.py) | `Estado` e `Decisao`: entrada e saída comuns, com dados imutáveis |
| 2 | [imperativo.py](../../controladores/imperativo.py) | `ControladorImperativo.propor`: laços, acumuladores e `if/elif` |
| 3 | [orientado_objetos.py](../../controladores/orientado_objetos.py) | `DemandaDaFase`, `RegraEmergencia` e `PoliticaPrioridades` |
| 4 | [funcional.py](../../controladores/funcional.py) | `avaliar_fase` e `decidir`: transformação de dados sem alterar a entrada |
| 5 | [logico.pl](../../controladores/logico.pl) | `precedencia/2`, `prioridade/7` e `escolher/3` |

Use a busca do editor pelo nome indicado. Não é necessário percorrer `motor.py` inteiro. Se perguntarem como Python conversa com Prolog, abra [adaptador_prolog.py](../../controladores/adaptador_prolog.py): ele envia o estado e converte a resposta; a decisão é calculada em Prolog.

## 3. Compare usando o mesmo exemplo

Considere uma fila grande no norte–sul e uma ambulância com emergência solicitada no leste–oeste. Com a prioridade ligada e o atendimento mínimo cumprido, os quatro controladores propõem atender a emergência. Se houver uma travessia conflitante em andamento, o motor espera sua conclusão.

| Paradigma | Como representa a decisão | Facilidade | Dificuldade |
| --- | --- | --- | --- |
| Imperativo | Percorre pedidos, guarda os mais antigos e compara chaves | Acompanhar a execução passo a passo | Uma regra nova pode exigir mais variáveis e ramos |
| Orientado a objetos | Divide demanda, regras e seleção em objetos | Localizar a responsabilidade de cada regra | Há mais classes para uma política pequena |
| Funcional | Filtra pedidos, transforma fases e seleciona o menor valor | Testar funções sem preparar estado interno | Expressões com várias transformações exigem atenção |
| Lógico | Declara relações e regras de precedência | Expressar condições de atendimento | Entender ordem das cláusulas, cortes e integração com Python |

Uma classe com `propor` não torna toda a solução orientada a objetos: no funcional ela só adapta a interface. No imperativo, o algoritmo continua organizado por laços e condicionais.

## 4. Discuta uma mudança

Pergunta para orientar a comparação: “Como incluir uma nova prioridade?”

- No imperativo, acrescentar a condição e os dados necessários ao laço.
- No OO, criar uma regra e definir sua posição em `PoliticaPrioridades`.
- No funcional, acrescentar uma condição e sua chave em `avaliar_fase`.
- No lógico, declarar a precedência e a cláusula correspondente em `prioridade/7`.

Em todos os casos é preciso definir os desempates e verificar equivalência. A mudança deve produzir a mesma política nas quatro versões.

## 5. Mostre a evidência

[test_paradigmas.py](../../tests/test_paradigmas.py) verifica prioridades, empates, 500 estados aleatórios e execuções completas. [test_prolog.py](../../tests/test_prolog.py) usa o processo Prolog real e verifica também falhas de integração.

Para executar somente essa parte, na raiz:

```bash
.venv/bin/python -m pytest tests/test_paradigmas.py tests/test_prolog.py -q
```

Na interface, abra **Escolher controle dos sinais → Regras**, selecione cada paradigma e clique em **Ativar regras**. A troca preserva o trânsito em andamento. Isso serve como demonstração; a equivalência é verificada pelos testes com entradas iguais.

**Tempos fixos** é uma referência separada. Não representa um quinto paradigma, e os resultados de trânsito não medem qual linguagem executa mais rápido.
