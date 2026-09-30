# Apresentação do projeto

O laboratório simula um cruzamento. O Python controla o tempo, os participantes e os semáforos. O navegador apresenta o estado recebido.

## Abra somente o material da disciplina

| Disciplina | Roteiro | Código principal |
| --- | --- | --- |
| Paradigmas da Programação | [Paradigmas](paradigmas.md) | Os quatro controladores em `controladores/` |
| Redes Neurais Artificiais | [Redes neurais](redes_neurais.md) | O notebook em `experimento_neural/` |

Os roteiros usam os dois enunciados fornecidos como referência. Eles não acrescentam exigências às disciplinas. A extensão de trânsito pode ser mostrada ao final, se houver tempo.

O [índice das entregas](../entregas.md) relaciona cada requisito às células do notebook, aos gráficos e aos arquivos de código.

## Preparação

1. Inicie o sistema seguindo o [README principal](../../README.md). Abra o endereço informado pelo Vite.
2. Deixe este roteiro e os arquivos da disciplina abertos no editor.
3. Para Redes Neurais, abra o notebook com os resultados já executados. As figuras também estão em [artefatos](../../experimento_neural/artefatos/README.md).
4. Para Paradigmas, confirme que SWI-Prolog está instalado antes de selecionar **Lógico**.
5. Use **Recomeçar simulação** antes da demonstração. O botão mantém as configurações; confira o modo, a geração e a velocidade desejados.

## Como explicar o conjunto

“O problema é escolher qual grupo deve receber atendimento no cruzamento. Escrevemos a mesma política em quatro paradigmas. Em um experimento separado, implementamos Perceptron e Adaline para aprender a porta AND. O motor reúne essas partes e valida as mudanças dos sinais.”

O modo **Rede neural** da interface usa outro treinamento, voltado a preferências entre fases. O exercício obrigatório da AND aparece em **Regras → Para estudar: lógica AND**. Os dois usam arquivos de pesos diferentes.

## Consultas rápidas

- [Parâmetros atuais](../parametros.md): tempos, velocidades, prioridades e treinamento.
- [Mapa do back-end](../../motor_python/README.md): onde procurar cada responsabilidade.
- [Resultados atuais](../../experimento_transito/relatorio.md): comparação de trânsito produzida por execuções novas, independente da sessão aberta no navegador.

As pastas `.venv`, `__pycache__`, `.pytest_cache`, `node_modules` e `dist` são ambientes, caches ou arquivos gerados. Não é necessário abri-las na apresentação.
