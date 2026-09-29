import type { ComandoOperacao, Controle } from './contratos';
const el = (id: string) => document.getElementById(id)!;
export function criarPainelTransito(enviar: (c: ComandoOperacao) => boolean) {
  const eventos = new AbortController();
  let conectado = false, interrompido = false, controle: Controle | undefined;
  const neural = el('ativar-neural-transito') as HTMLButtonElement;
  const urbano = el('ativar-urbano') as HTMLButtonElement;
  function disponibilidade() {
    urbano.disabled = !conectado || !controle?.operacao || interrompido;
    neural.disabled = urbano.disabled || !!controle?.erro_neural_transito;
  }
  const ativar = (modo: 'neural' | 'urbano') => enviar({command_id: crypto.randomUUID(), tipo: 'configurar_operacao',
    parametros: {modo, ...(modo === 'neural' ? {modelo: (el('rede-transito') as HTMLSelectElement).value as 'perceptron' | 'adaline'} : {})}});
  neural.addEventListener('click', () => ativar('neural'), {signal: eventos.signal});
  urbano.addEventListener('click', () => ativar('urbano'), {signal: eventos.signal});
  el('ver-comparacao').addEventListener('click', async () => {
    const destino = el('comparacao-transito');
    destino.textContent = 'Carregando ensaios…';
    try {
      const resposta = await fetch('/comparacao-transito.json');
      if (!resposta.ok) throw new Error('Resultados indisponíveis. Execute o comparador descrito na documentação.');
      const dados = await resposta.json();
      const resultados = dados.resultados as {cenario: string; modo: string; semente: number; segundos: number;
        espera_acumulada_por_solicitado: number; fila_media: number; concluidos: number}[];
      const tabela = document.createElement('table');
      const cabecalho = tabela.createTHead().insertRow();
      for (const nome of ['Cenário / política', 'Espera¹ (s)', 'Fila média', 'Concluídos']) {
        const th = document.createElement('th'); th.textContent = nome; cabecalho.append(th);
      }
      const grupos = new Map<string, typeof resultados>();
      for (const r of resultados) { const chave = `${r.cenario} / ${r.modo}`; grupos.set(chave, [...(grupos.get(chave) ?? []), r]); }
      const corpo = tabela.createTBody();
      for (const [nome, linhas] of grupos) {
        const row = corpo.insertRow(); row.insertCell().textContent = nome.replaceAll('_', ' ');
        for (const chave of ['espera_acumulada_por_solicitado', 'fila_media', 'concluidos'] as const)
          row.insertCell().textContent = (linhas.reduce((s, r) => s+r[chave], 0)/linhas.length).toFixed(2);
      }
      const nota = document.createElement('p');
      nota.textContent = `Médias de ${new Set(resultados.map(r => r.semente)).size} sementes; ${resultados[0].segundos} s por execução. ¹Espera acumulada até o fim, por participante solicitado; inclui ativos e pendentes. Não inclui espera futura. Menor é melhor. Não garante ganho em todo cenário. Velocidade dos pedestres nestes ensaios: ${dados.velocidade_pedestre ?? 'não registrada'} unidade/s.`;
      destino.replaceChildren(nota, tabela);
    } catch (erro) { destino.textContent = erro instanceof Error ? erro.message : 'Falha ao carregar resultados.'; }
  }, {signal: eventos.signal});
  return {
    definirConexao(valor: boolean) { conectado = valor; disponibilidade(); },
    atualizar(atual: Controle | undefined, pausado: boolean) {
      controle = atual; interrompido = pausado;
      const op = atual?.operacao;
      el('modo-ativo').textContent = `Modo ativo: ${!op || op.modo === 'paradigmas' ? 'Paradigmas' : op.modo === 'urbano' ? 'Semáforo urbano' : `Rede aplicada — ${op.modelo}`}. Selecionar uma aba apenas muda a visualização.`;
      el('treinamento-transito').textContent = Object.entries(atual?.treinamento_transito ?? {}).map(([nome, m]) =>
        `${nome}: ${m.epocas} épocas; ${(100*m.acuracia_teste_sintetico).toFixed(1)}% de acerto em 1.200 preferências sintéticas reservadas para teste.`).join(' ') + ' Essa acurácia mede imitação de preferências, não redução de filas.';
      const d = atual?.transito;
      const c = d?.comparacao;
      el('calculo-transito').textContent = c
        ? `${d?.modelo}: comparar ${c.candidata} com ${c.atual}. Entradas [${c.entradas.map(x => x.toFixed(3)).join(', ')}]. Pesos [${c.pesos.map(x => x.toFixed(4)).join(', ')}]. Soma ${c.soma_ponderada.toFixed(4)} → ${c.saida === 1 ? '+1: preferir candidata' : '−1: manter preferência atual'}.`
        : atual?.erro_neural_transito ?? (op?.modo === 'neural' ? `Decisão atual: ${d?.criterio ?? 'aguardando'}. Não foi necessária uma comparação neural entre duas fases neste passo.` : 'Ative uma rede no trânsito para acompanhar suas comparações.');
      disponibilidade();
    },
    descartar() { eventos.abort(); },
  };
}
