import type { ComandoOperacao, Controle } from './contratos';
import { nomesControladores } from './controladores';
import { nomeFase, nomesRedes } from './rotulos';
const el = (id: string) => document.getElementById(id)!;
export function criarPainelTransito(enviar: (c: ComandoOperacao) => boolean) {
  const eventos = new AbortController();
  let conectado = false, interrompido = false, controle: Controle | undefined;
  let alterado = false, revisao = 0, execucao = '';
  const enviados = new Map<string, number>();
  const seletor = el('rede-transito') as HTMLSelectElement;
  const neural = el('ativar-neural-transito') as HTMLButtonElement;
  const urbano = el('ativar-urbano') as HTMLButtonElement;
  function disponibilidade() {
    urbano.disabled = !conectado || !controle?.operacao || interrompido;
    neural.disabled = urbano.disabled || !!controle?.erro_neural_transito;
    seletor.disabled = neural.disabled;
    neural.disabled ||= enviados.size > 0;
    urbano.disabled ||= enviados.size > 0;
  }
  const ativar = (modo: 'neural' | 'urbano') => {
    const command_id = crypto.randomUUID();
    if (enviar({command_id, tipo: 'configurar_operacao', parametros: {
      modo, ...(modo === 'neural' ? {modelo: seletor.value as 'perceptron' | 'adaline'} : {}),
    }})) enviados.set(command_id, revisao);
    disponibilidade();
  };
  seletor.addEventListener('change', () => {
    alterado = true; revisao++;
    el('resultado-neural-transito').textContent = 'Clique em Ativar rede neural para aplicar.';
  }, {signal: eventos.signal});
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
      for (const nome of ['Teste / controle', 'Espera¹ (s)', 'Fila média', 'Passagens']) {
        const th = document.createElement('th'); th.textContent = nome; cabecalho.append(th);
      }
      const grupos = new Map<string, typeof resultados>();
      for (const r of resultados) { const chave = `${r.cenario} / ${r.modo}`; grupos.set(chave, [...(grupos.get(chave) ?? []), r]); }
      const corpo = tabela.createTBody();
      const nomes: Record<string, string> = { baseline: 'Tempos fixos', imperativo: 'Regras', urbano: 'Automático',
        perceptron: 'Perceptron', adaline: 'Adaline', desbalanceado: 'Uma via mais cheia', equilibrado: 'Vias equilibradas', inversao: 'Mudança de fluxo' };
      for (const [nome, linhas] of grupos) {
        const row = corpo.insertRow(); row.insertCell().textContent = nome.split(' / ').map(n => nomes[n] ?? n.replaceAll('_', ' ')).join(' / ');
        for (const chave of ['espera_acumulada_por_solicitado', 'fila_media', 'concluidos'] as const)
          row.insertCell().textContent = (linhas.reduce((s, r) => s+r[chave], 0)/linhas.length).toFixed(2);
      }
      const nota = document.createElement('p');
      nota.textContent = `Média de ${new Set(resultados.map(r => r.semente)).size} repetições de ${resultados[0].segundos} s. ¹Espera acumulada por pessoa ou veículo solicitado, incluindo quem ainda aguarda. Não inclui espera futura. Menor é melhor; o resultado varia com o trânsito.`;
      destino.replaceChildren(nota, tabela);
    } catch (erro) { destino.textContent = erro instanceof Error ? erro.message : 'Falha ao carregar resultados.'; }
  }, {signal: eventos.signal});
  return {
    definirConexao(valor: boolean) {
      conectado = valor;
      if (!valor) { enviados.clear(); alterado = false; }
      disponibilidade();
    },
    confirmar(id: string, aplicado: boolean) {
      if (enviados.get(id) === revisao) alterado = false;
      enviados.delete(id);
      if (!aplicado && !alterado && controle?.operacao) seletor.value = controle.operacao.modelo;
      disponibilidade();
      return alterado;
    },
    atualizar(atual: Controle | undefined, pausado: boolean, runId: string) {
      controle = atual; interrompido = pausado;
      const op = atual?.operacao;
      if (runId !== execucao) { execucao = runId; enviados.clear(); alterado = false; }
      if (op && !alterado && !enviados.size) seletor.value = op.modelo;
      const regra = atual?.configuracao_controlador?.controlador;
      const nome = op?.modo === 'urbano' ? 'Automático' : op?.modo === 'neural' ? `Rede neural · ${nomesRedes[op.modelo]}`
        : regra ? `Regras · ${nomesControladores[regra]}` : 'aguardando dados';
      const emergenciaNeural = op?.modo === 'neural' && atual?.transito?.criterio === 'emergencia';
      el('modo-ativo').textContent = `Controle: ${nome}${emergenciaNeural ? ' · Emergência prioritária' : ''}`;
      if (atual?.erro_neural_transito) el('resultado-neural-transito').textContent = 'Rede indisponível. Consulte os detalhes abaixo.';
      el('treinamento-transito').textContent = Object.entries(atual?.treinamento_transito ?? {}).map(([nome, m]) =>
        `${nomesRedes[nome] ?? nome}: ${(100*m.acuracia_teste_sintetico).toFixed(1)}% de acerto no teste sintético (${m.epocas} épocas).`).join(' ') + ' Mede o aprendizado, não a redução das filas.';
      const d = atual?.transito;
      const c = d?.comparacao;
      el('calculo-transito').textContent = emergenciaNeural
        ? 'Prioridade de emergência: liberar a via da ambulância assim que o cruzamento estiver seguro.'
        : c
        ? `${nomeFase(c.candidata)} ou ${nomeFase(c.atual)}: preferência por ${nomeFase(c.saida === 1 ? c.candidata : c.atual)}. Entradas [${c.entradas.map(x => x.toFixed(2)).join(', ')}] · Pesos [${c.pesos.map(x => x.toFixed(3)).join(', ')}] · Soma ${c.soma_ponderada.toFixed(3)}.`
        : atual?.erro_neural_transito ?? (op?.modo === 'neural' ? 'Sem comparação entre direções neste instante.' : 'Ative a rede para ver as decisões.');
      disponibilidade();
    },
    descartar() { eventos.abort(); },
  };
}
