"""Gera relatório e cópia servida pela interface a partir dos ensaios completos."""
import json
from pathlib import Path
from statistics import mean

PASTA = Path(__file__).resolve().parent

def main():
    dados = json.loads((PASTA/'resultados.json').read_text())
    resultados = dados['resultados']
    sementes = ', '.join(str(s) for s in sorted({r['semente'] for r in resultados}))
    horizontes = ', '.join(str(s) for s in sorted({r['segundos'] for r in resultados}))
    linhas = ['# Comparação medida dos modos de controle', '',
              f'Médias das sementes {sementes}; horizontes de {horizontes} segundos. A semente 11 foi usada na calibração preliminar. Consulte `resultados.json` para as execuções individuais.', '',
              'A espera é o tempo acumulado até o horizonte por participante solicitado, incluindo concluídos, ativos e pendentes; não inclui espera futura dos remanescentes. Valores negativos na variação indicam redução em relação ao imperativo.', '',
              '| Cenário | Política | Espera (s) | Variação vs. imperativo | Fila média | Concluídos | Ainda no sistema | Emergências atendidas / pendentes | Tempo até atendimento de emergência (s) |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for cenario in dict.fromkeys(r['cenario'] for r in resultados):
        base = mean(r['espera_acumulada_por_solicitado'] for r in resultados if r['cenario']==cenario and r['modo']=='imperativo')
        for modo in ('baseline','imperativo','perceptron','adaline','urbano'):
            rs=[r for r in resultados if r['cenario']==cenario and r['modo']==modo]
            media=lambda chave: mean(r[chave] for r in rs)
            espera=media('espera_acumulada_por_solicitado')
            n=sum(r['emergencias_atendidas'] for r in rs)
            emergencia=sum(r['tempo_emergencia']*r['emergencias_atendidas'] for r in rs)/n if n else 0
            linhas.append(f'| {cenario} | {modo} | {espera:.2f} | {(espera/base-1)*100:+.1f}% | {media("fila_media"):.2f} | {media("concluidos"):.1f} | {media("em_sistema"):.1f} | {n} / {sum(r["emergencias_nao_atendidas"] for r in rs)} | {emergencia:.2f} |')
    linhas += ['', f'Velocidade dos pedestres nestes ensaios: {dados.get("velocidade_pedestre", "não registrada")} unidade/s. Os números descrevem essa configuração, não uma execução com outra velocidade.', '', 'Os resultados não isolam o efeito do aprendizado: os modos aplicados também usam verde variável. Todos os ensaios mantêm proteções de transição e verificam conflitos entre permissões e trajetórias ocupadas a cada passo. Acurácia sintética não é eficiência de trânsito.', '',
               'O ganho depende da demanda. Uma eventual piora aparece na tabela e deve fazer parte da apresentação. Não há prova de ótimo global; as taxas, geometria, mistura de veículos, horizonte e sementes definem o alcance desta comparação.', '']
    (PASTA/'relatorio.md').write_text('\n'.join(linhas))
    publico=PASTA.parent/'cena_3d/public'
    publico.mkdir(exist_ok=True)
    (publico/'comparacao-transito.json').write_text(json.dumps(dados,indent=2)+'\n')
    print('\n'.join(linhas))

if __name__=='__main__':
    main()
