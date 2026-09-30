# Histórico

Esta pasta guarda materiais anteriores que não devem ser usados como referência dos parâmetros atuais.

| Material | Por que foi guardado |
| --- | --- |
| [requisitos-2026-09-13.md](requisitos-2026-09-13.md) | Especificação original. Inclui propostas que mudaram ou não foram implementadas |
| [comparacao-pedestres-1_4/relatorio.md](comparacao-pedestres-1_4/relatorio.md) | Comparação anterior, executada com pedestres a 1,4 unidade/s |
| [comparacao-pedestres-1_4/resultados.json](comparacao-pedestres-1_4/resultados.json) | As 45 execuções que deram origem à comparação anterior |
| [medicao-capacidade-2026-09-13.md](medicao-capacidade-2026-09-13.md) | Medição exploratória de uma versão inicial; não é um benchmark atual |
| [antes-prioridade-neural/relatorio.md](antes-prioridade-neural/relatorio.md) | Comparação antes da antecipação do encerramento por emergência nas redes; dados preservados na mesma pasta |
| [pesos_and.json](pesos_and.json) | Cópia antiga de `experimento_neural/pesos_and.json`, idêntica aos pesos da raiz na revisão de 30/09/2026 |

O motor usa [pesos_neurais.json](../../pesos_neurais.json), na raiz. A cópia da AND foi retirada da pasta de trabalho para evitar dúvida sobre qual arquivo é carregado. Nenhum código a referenciava.

A configuração atual usa pedestres a **1,7 unidade/s**. Consulte os [parâmetros atuais](../parametros.md) e os [resultados atualizados](../../experimento_transito/relatorio.md).
