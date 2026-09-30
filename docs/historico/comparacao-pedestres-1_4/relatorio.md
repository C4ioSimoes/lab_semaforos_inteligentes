# Comparação medida dos modos de controle

Médias das sementes 42, 73, 101; horizontes de 240 segundos. A semente 11 foi usada na calibração preliminar. Consulte `resultados.json` para as execuções individuais.

A espera é o tempo acumulado até o horizonte por participante solicitado, incluindo concluídos, ativos e pendentes; não inclui espera futura dos remanescentes. Valores negativos na variação indicam redução em relação ao imperativo.

| Cenário | Política | Espera (s) | Variação vs. imperativo | Fila média | Concluídos | Ainda no sistema | Emergências atendidas / pendentes | Tempo até atendimento de emergência (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| desbalanceado | baseline | 28.75 | +96.9% | 42.34 | 241.0 | 111.3 | 11 / 3 | 29.92 |
| desbalanceado | imperativo | 14.60 | +0.0% | 21.42 | 278.0 | 74.3 | 12 / 2 | 14.78 |
| desbalanceado | perceptron | 10.97 | -24.9% | 16.13 | 291.7 | 60.7 | 13 / 1 | 14.58 |
| desbalanceado | adaline | 10.73 | -26.5% | 15.77 | 292.0 | 60.3 | 13 / 1 | 14.78 |
| desbalanceado | urbano | 9.86 | -32.5% | 14.50 | 293.0 | 59.3 | 13 / 1 | 14.69 |
| equilibrado | baseline | 14.65 | +17.4% | 22.53 | 296.3 | 72.0 | 12 / 2 | 26.54 |
| equilibrado | imperativo | 12.48 | +0.0% | 19.23 | 306.3 | 62.0 | 12 / 2 | 14.49 |
| equilibrado | perceptron | 12.64 | +1.3% | 19.42 | 302.3 | 66.0 | 13 / 1 | 13.82 |
| equilibrado | adaline | 13.00 | +4.2% | 19.88 | 300.7 | 67.7 | 13 / 1 | 13.74 |
| equilibrado | urbano | 11.95 | -4.2% | 18.38 | 306.3 | 62.0 | 13 / 1 | 13.91 |
| inversao_de_fluxo | baseline | 21.34 | +50.7% | 30.63 | 257.3 | 87.7 | 12 / 2 | 26.23 |
| inversao_de_fluxo | imperativo | 14.16 | +0.0% | 20.30 | 281.0 | 64.0 | 12 / 2 | 13.98 |
| inversao_de_fluxo | perceptron | 9.61 | -32.1% | 13.76 | 291.7 | 53.3 | 13 / 1 | 13.11 |
| inversao_de_fluxo | adaline | 9.24 | -34.7% | 13.28 | 286.3 | 58.7 | 13 / 1 | 13.47 |
| inversao_de_fluxo | urbano | 8.61 | -39.2% | 12.35 | 287.0 | 58.0 | 13 / 1 | 13.38 |

Velocidade dos pedestres nestes ensaios: 1.4 unidade/s. Os números descrevem essa configuração, não uma execução com outra velocidade.

Os resultados não isolam o efeito do aprendizado: os modos aplicados também usam verde variável. Todos os ensaios mantêm proteções de transição e verificam conflitos entre permissões e trajetórias ocupadas a cada passo. Acurácia sintética não é eficiência de trânsito.

O ganho depende da demanda. Uma eventual piora aparece na tabela e deve fazer parte da apresentação. Não há prova de ótimo global; as taxas, geometria, mistura de veículos, horizonte e sementes definem o alcance desta comparação.
