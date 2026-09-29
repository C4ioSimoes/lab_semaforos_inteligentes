import type { ComandoNeural, Controle, ModeloNeural } from './contratos';

const nomes: Record<ModeloNeural, string> = { AND_referencia: 'AND de referência', perceptron: 'Perceptron', adaline: 'Adaline' };
const el = (id: string) => document.getElementById(id)!;

export function criarPainelNeural(enviar: (comando: ComandoNeural) => boolean) {
  const seletor = el('modelo-neural') as HTMLSelectElement;
  const botao = el('aplicar-neural') as HTMLButtonElement;
  let conectado = false, interrompido = false, alterado = false, revisao = 0, runId = '';
  let controle: Controle | undefined;
  const enviados = new Map<string, number>();
  function disponibilidade() {
    seletor.disabled = !conectado || !controle?.modelos_neurais || interrompido;
    for (const opcao of seletor.options) opcao.disabled = !controle?.modelos_neurais?.[opcao.value as ModeloNeural]?.disponivel;
    botao.disabled = seletor.disabled || !controle?.modelos_neurais?.[seletor.value as ModeloNeural]?.disponivel;
  }
  const editar = () => { alterado = true; revisao++; disponibilidade(); el('resultado-neural').textContent = 'Alteração local. Clique em Aplicar modelo neural.'; };
  const aplicar = (evento: Event) => {
    evento.preventDefault();
    const comando: ComandoNeural = { command_id: crypto.randomUUID(), tipo: 'configurar_modelo_neural', parametros: { modelo: seletor.value as ModeloNeural } };
    if (enviar(comando)) enviados.set(comando.command_id, revisao);
  };
  el('form-neural').addEventListener('submit', aplicar);
  seletor.addEventListener('change', editar);
  return {
    definirConexao(valor: boolean) { conectado = valor; disponibilidade(); },
    confirmar(id: string, aplicado: boolean) {
      if (aplicado && enviados.get(id) === revisao) alterado = false;
      enviados.delete(id);
    },
    atualizar(atual: Controle | undefined, execucao: string, pausado: boolean) {
      controle = atual; interrompido = pausado;
      if (runId !== execucao) { alterado = false; enviados.clear(); runId = execucao; }
      if (!alterado && atual?.modelo_neural) seletor.value = atual.modelo_neural;
      if (atual?.modelo_neural && el('resultado-neural').textContent === 'Aguardando configuração do motor.') {
        el('resultado-neural').textContent = 'Configuração sincronizada com o motor.';
      }
      el('avaliador-atual').textContent = atual?.modelo_neural ? nomes[atual.modelo_neural] : '—';
      el('disponibilidade-neural').textContent = atual?.modelos_neurais
        ? 'Pesos verificados pelo motor nas quatro combinações da AND. Apenas modelos válidos podem ser ativados.'
        : 'Aguardando validação dos pesos pelo motor.';
      const linhas = Object.entries(atual?.modelos_neurais ?? {}).filter(([nome]) => nome !== 'AND_referencia').map(([nome, modelo]) => {
        const linha = document.createElement('p');
        const motivos: Record<string, string> = { epoca_sem_erros: 'época sem erros', limite_epocas: 'limite de épocas', variacao_sse_abaixo_tolerancia: 'tolerância do SSE atingida' };
        linha.textContent = `${nomes[nome as ModeloNeural]}: ${modelo.disponivel ? `validado · ${modelo.epocas} épocas · ${motivos[modelo.motivo_parada ?? ''] ?? modelo.motivo_parada}` : modelo.erro}`;
        for (const d of modelo.verificacao_and.filter(v => v.divergencia)) {
          linha.append(` Divergência: x=[${d.entradas.join(', ')}], saída=${d.saida}, AND=${d.and_referencia}.`);
        }
        return linha;
      });
      el('validacao-neural').replaceChildren(...linhas);
      const decisao = atual?.decisao;
      el('neural-instante').textContent = atual?.operacao && atual.operacao.modo !== 'paradigmas'
        ? 'Avaliador AND inativo neste modo. Acompanhe a política aplicada na aba correspondente.' : decisao
        ? `Passo ${decisao.step} · ${nomes[atual?.modelo_neural ?? 'AND_referencia']} · elegibilidade para abertura da fase.`
        : 'Aguardando avaliações do motor.';
      el('diagnostico-neural').replaceChildren(...(decisao?.avaliacoes ?? []).flatMap(a => {
        if (!a.neural) return [];
        const n = a.neural;
        const bloco = document.createElement('div');
        bloco.className = 'calculo-neural';
        const titulo = document.createElement('strong'); titulo.textContent = a.fase;
        const entrada = document.createElement('p'); entrada.textContent = `x1=${n.entradas[0]} · x2=${n.entradas[1]} · bias x0=${n.bias} · ${a.origem_solicitacao === 'sequencia_fixa' ? 'solicitação programada' : 'solicitação por demanda'}`;
        const pesos = document.createElement('p'); pesos.textContent = n.pesos ? `w0=${n.pesos[0]} · w1=${n.pesos[1]} · w2=${n.pesos[2]}` : 'AND lógica de referência: sem pesos.';
        const soma = document.createElement('p'); soma.textContent = `Soma ponderada u: ${n.soma_ponderada ?? 'não se aplica'}`;
        const saida = document.createElement('p'); saida.textContent = `Saída ${n.saida > 0 ? '+1' : '−1'} · ${n.elegivel ? 'Elegível' : 'Não elegível'} · AND de referência ${n.and_referencia > 0 ? '+1' : '−1'}`;
        bloco.append(titulo, entrada, pesos, soma, saida);
        return [bloco];
      }));
      disponibilidade();
    },
    descartar() {
      el('form-neural').removeEventListener('submit', aplicar);
      seletor.removeEventListener('change', editar);
    },
  };
}
