# Registro da revisão

Revisão realizada em **30/09/2026**, sobre os arquivos locais do projeto.

## O que foi organizado

- Roteiros separados de Paradigmas da Programação e Redes Neurais, a partir dos enunciados fornecidos.
- Índices por pasta e mapa dos métodos principais do motor.
- Parâmetros documentados com os valores do código atual.
- Guias corrigidos sobre reinício, aceleração, integração neural e exportações.
- Especificação original, medição antiga, comparação com pedestres a 1,4 e cópia duplicada dos pesos AND guardadas em `docs/historico/`.
- Resultados de trânsito recalculados e cópia servida pela interface atualizada.

Os arquivos de código, o notebook e os pesos ativos foram comparados por SHA-256 antes e depois desta organização: **60 arquivos permaneceram idênticos**. As mudanças de código de etapas anteriores do projeto já estavam presentes na referência inicial desta revisão.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 362 testes passaram |
| `experimento_neural/.venv/bin/python experimento_neural/verificar_experimento.py` | 15 testes passaram |
| Treinamento aplicado, executado em pasta temporária | Pesos, históricos e acurácias idênticos ao JSON existente |
| Ensaios de trânsito | 45 execuções concluídas, sem conflito detectado pelas verificações do ensaio |
| Quantidade solicitada por cenário/semente | Igual nas cinco políticas |
| Contagem de participantes | Solicitados = concluídos + ainda no sistema em todas as execuções |
| Dados servidos pela interface | Idênticos a `experimento_transito/resultados.json` |

Ambiente do back-end: **Python 3.12.3**; **SWI-Prolog version 9.0.4 for x86_64-linux**. A suíte Python emitiu um aviso de depreciação de `BlockingPortal`, da dependência de testes, sem falhas.

Não houve alteração no código da interface nesta revisão. Os testes de navegador não foram repetidos.

## Como os números foram atualizados

```bash
.venv/bin/python experimento_transito/comparar.py --segundos 240 --sementes 42 73 101 --saida /tmp/lab-resultados-atualizados.json
```

Depois de confirmar a conclusão dos 45 ensaios, o arquivo foi copiado para `experimento_transito/resultados.json`, e o relatório foi gerado com:

```bash
.venv/bin/python experimento_transito/relatorio.py
```

Cada ensaio usou um motor novo e a velocidade atual dos pedestres, **1,7 unidade/s**. A sessão aberta no navegador não foi usada como fonte nem reiniciada. Os valores completos estão no [JSON](../experimento_transito/resultados.json); as médias, no [relatório](../experimento_transito/relatorio.md).

## Identificação dos arquivos

Os hashes identificam os arquivos usados nesta revisão. Eles permitem reconhecer uma alteração posterior; não substituem uma nova execução dos ensaios.

| Arquivo | SHA-256 |
| --- | --- |
| `experimento_transito/resultados.json` | `7b44f4d76252cc1ed05ec0fdad8b70867db33c65d53e8f415b344d715c33c995` |
| `pesos_neurais.json` | `7b2e721df1d0831f9a8794cd571351eb4be9f1a1b713638b96431d959fbd7c58` |
| `experimento_transito/pesos_transito.json` | `7b848ca6bb3d1be1c071a569023b77e28a8b664dbba6070f7e3d556b524e9aa6` |

A assinatura agregada dos arquivos `.py` e `.pl` de `motor_python/` e `controladores/` é `fc159e5ca5d44a2bfe94595701842a7f5240531425ee22082ea3af6102f1d415`. Ela é calculada ordenando os caminhos e concatenando `caminho:sha256` com uma quebra de linha por arquivo, antes de aplicar SHA-256 ao conjunto.

## Preparação da publicação no GitHub

Ainda em 30/09/2026, o README principal foi ampliado com a comparação dos paradigmas,
os fundamentos das redes neurais e os resultados do modo Automático. A captura da
interface foi atualizada e o gráfico de desempenho foi gerado a partir dos 45 ensaios.

- `npm run build`: compilação aprovada; aviso de tamanho do pacote JavaScript.
- `npm test -- --workers=1`: 32 testes de navegador aprovados.
- Os códigos Python e os pesos ativos continuam iguais aos verificados nesta revisão;
  as suítes Python e AND não foram repetidas nessa etapa de documentação.

A referência acima à ausência de repetição dos testes de navegador descreve a etapa
anterior de organização. A suíte completa foi executada nesta preparação da publicação.
