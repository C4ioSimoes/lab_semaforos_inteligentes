# Comparação medida dos modos de controle

Médias das sementes 42, 73, 101; horizontes de 240 segundos. A semente 11 foi usada na calibração preliminar. Consulte `resultados.json` para as execuções individuais.

A espera é o tempo acumulado até o horizonte por participante solicitado, incluindo concluídos, ativos e pendentes; não inclui espera futura dos remanescentes. Valores negativos na variação indicam redução em relação ao imperativo.

| Cenário | Política | Espera (s) | Variação vs. imperativo | Fila média | Concluídos | Ainda no sistema | Emergências atendidas / pendentes | Tempo até atendimento de emergência (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| desbalanceado | baseline | 25.63 | +61.7% | 37.88 | 256.0 | 96.3 | 11 / 3 | 29.21 |
| desbalanceado | imperativo | 15.85 | +0.0% | 23.35 | 266.7 | 85.7 | 12 / 2 | 19.24 |
| desbalanceado | perceptron | 10.12 | -36.2% | 14.95 | 291.0 | 61.3 | 13 / 1 | 14.73 |
| desbalanceado | adaline | 10.00 | -36.9% | 14.71 | 293.3 | 59.0 | 13 / 1 | 14.61 |
| desbalanceado | urbano | 8.89 | -43.9% | 13.10 | 293.0 | 59.3 | 13 / 1 | 14.52 |
| equilibrado | baseline | 13.49 | +13.3% | 20.83 | 300.3 | 68.0 | 12 / 2 | 24.87 |
| equilibrado | imperativo | 11.90 | +0.0% | 18.30 | 308.0 | 60.3 | 12 / 2 | 14.92 |
| equilibrado | perceptron | 12.18 | +2.4% | 18.68 | 302.0 | 66.3 | 13 / 1 | 13.74 |
| equilibrado | adaline | 12.36 | +3.8% | 18.92 | 302.3 | 66.0 | 13 / 1 | 13.74 |
| equilibrado | urbano | 10.48 | -12.0% | 16.15 | 304.3 | 64.0 | 13 / 1 | 13.74 |
| inversao_de_fluxo | baseline | 20.22 | +59.2% | 29.14 | 253.7 | 91.3 | 12 / 2 | 25.52 |
| inversao_de_fluxo | imperativo | 12.70 | +0.0% | 18.22 | 276.7 | 68.3 | 13 / 1 | 15.63 |
| inversao_de_fluxo | perceptron | 9.22 | -27.4% | 13.22 | 292.0 | 53.0 | 13 / 1 | 13.03 |
| inversao_de_fluxo | adaline | 8.44 | -33.5% | 12.14 | 286.3 | 58.7 | 13 / 1 | 13.14 |
| inversao_de_fluxo | urbano | 7.88 | -37.9% | 11.32 | 287.0 | 58.0 | 13 / 1 | 13.12 |

Velocidade dos pedestres nestes ensaios: 1.7 unidade/s. Os números descrevem essa configuração, não uma execução com outra velocidade.

Os resultados não isolam o efeito do aprendizado: os modos aplicados também usam verde variável. Todos os ensaios mantêm proteções de transição e verificam conflitos entre permissões e trajetórias ocupadas a cada passo. Acurácia sintética não é eficiência de trânsito.

O ganho depende da demanda. Uma eventual piora aparece na tabela e deve fazer parte da apresentação. Não há prova de ótimo global; as taxas, geometria, mistura de veículos, horizonte e sementes definem o alcance desta comparação.
