import type { ComandoGerador, ConfiguracaoGerador, DiagnosticoDemanda } from './contratos';

const origens = ['N', 'S', 'L', 'O'];
const el = (id: string) => document.getElementById(id)!;
const fator = (intensidade: number) => 0.4 + intensidade * 0.016;
// A ordem das chaves do JSON não faz parte do contrato do motor.
const assinaturaConfiguracao = (config: ConfiguracaoGerador) => JSON.stringify([
  config.semente, config.fator_global, config.fator_pedestres,
  ...origens.flatMap(o => [config.fatores_locais[o], config.taxas_pedestres[`${o}-TR`],
    ...['carro', 'moto', 'onibus', 'ambulancia'].map(c => config.taxas_veiculares[o][c])]),
]);

/** Um único perfil controla todas as fontes; a semente do motor é preservada. */
export function configuracaoIntensidade(semente: number, ligada: boolean, intensidade: number): ConfiguracaoGerador {
  const multiplicador = ligada ? fator(intensidade) : 0;
  return {
    semente,
    taxas_veiculares: Object.fromEntries(origens.map(o => [o, { carro: 12, moto: 3, onibus: 1, ambulancia: 0.2 }])),
    taxas_pedestres: Object.fromEntries(origens.map(o => [`${o}-TR`, 8])),
    fator_global: multiplicador, fator_pedestres: multiplicador,
    fatores_locais: Object.fromEntries(origens.map(o => [o, 1])),
  };
}
export function criarPainelGeracao(enviar: (comando: ComandoGerador) => boolean) {
  const toggle = el('alternar-geracao') as HTMLButtonElement;
  const slider = el('intensidade-transito') as HTMLInputElement;
  let conectado = false, disponivel = false, interrompido = false;
  let ligada = false, intensidade = 50, semente = 42, execucao = '', assinatura = '';
  let alterado = false;
  let oficial: ConfiguracaoGerador | undefined;
  let pendente: { id: string; assinatura: string; aprovado: boolean } | undefined;
  let temporizador: ReturnType<typeof setTimeout> | undefined;

  function mostrar() {
    toggle.disabled = slider.disabled = !conectado || !disponivel || interrompido;
    toggle.setAttribute('aria-checked', String(ligada));
    toggle.setAttribute('aria-busy', String(!!pendente));
    el('estado-geracao').textContent = ligada ? 'Ligada' : 'Desligada';
    slider.value = String(intensidade);
    const nome = intensidade < 34 ? 'Baixo' : intensidade < 67 ? 'Médio' : 'Alto';
    slider.setAttribute('aria-valuetext', `${nome}, ${intensidade}%`);
    slider.style.setProperty('--progresso', `${intensidade}%`);
    el('valor-intensidade').textContent = nome;
  }
  function sincronizar(c: ConfiguracaoGerador) {
    semente = c.semente;
    ligada = Object.entries(c.taxas_veiculares).some(([o, taxas]) => Object.values(taxas).some(t => t * c.fator_global * c.fatores_locais[o] > 0))
      || Object.values(c.taxas_pedestres).some(t => t * c.fator_pedestres > 0);
    if (ligada) intensidade = Math.round(Math.max(0, Math.min(100, (Math.max(c.fator_global, c.fator_pedestres) - 0.4) / 0.016)));
    mostrar();
  }
  function aplicar() {
    clearTimeout(temporizador);
    if (!alterado || pendente || !conectado || !disponivel || interrompido) return;
    const parametros = configuracaoIntensidade(semente, ligada, intensidade);
    const command_id = crypto.randomUUID();
    pendente = { id: command_id, assinatura: assinaturaConfiguracao(parametros), aprovado: false };
    alterado = false;
    if (!enviar({ command_id, tipo: 'configurar_gerador', parametros })) {
      pendente = undefined;
      if (oficial) sincronizar(oficial);
    }
    mostrar();
  }
  const alternar = () => { ligada = !ligada; alterado = true; mostrar(); aplicar(); };
  const ajustar = () => {
    intensidade = Number(slider.value); mostrar();
    // Desligada: prepara a próxima ativação, sem gerar chegadas.
    if (!ligada && !pendente) return;
    alterado = true;
    clearTimeout(temporizador);
    temporizador = setTimeout(aplicar, 180);
  };
  toggle.addEventListener('click', alternar);
  slider.addEventListener('input', ajustar);
  slider.addEventListener('change', aplicar);
  return {
    definirConexao(valor: boolean) {
      conectado = valor;
      if (!valor) {
        clearTimeout(temporizador); pendente = undefined; alterado = false; assinatura = '';
        if (oficial) sincronizar(oficial);
      }
      mostrar();
    },
    confirmar(id: string, aplicado: boolean) {
      if (pendente?.id !== id) return;
      if (aplicado) pendente.aprovado = true;
      else {
        pendente = undefined; alterado = false;
        clearTimeout(temporizador);
        if (oficial) sincronizar(oficial);
      }
      mostrar();
    },
    atualizar(demanda: DiagnosticoDemanda | undefined, runId: string) {
      disponivel = !!demanda; interrompido = !!demanda?.motivo_interrupcao;
      el('limite-demanda').hidden = !interrompido;
      el('limite-demanda').textContent = demanda?.motivo_interrupcao ?? '';
      if (!demanda) { mostrar(); return; }
      oficial = demanda.configuracao;
      const atual = assinaturaConfiguracao(oficial);
      if (runId !== execucao) {
        execucao = runId; pendente = undefined; alterado = false; assinatura = '';
        clearTimeout(temporizador); intensidade = 50;
      }
      if (pendente?.aprovado && atual === pendente.assinatura) pendente = undefined;
      if (!pendente && !alterado && atual !== assinatura) sincronizar(oficial);
      assinatura = atual;
      if (alterado && !pendente) queueMicrotask(aplicar);
      if (el('resultado-geracao').textContent === 'Aguardando configuração do motor.') {
        el('resultado-geracao').textContent = 'Ajuste a intensidade a qualquer momento.';
      }
      mostrar();
    },
    descartar() {
      clearTimeout(temporizador);
      toggle.removeEventListener('click', alternar);
      slider.removeEventListener('input', ajustar);
      slider.removeEventListener('change', aplicar);
    },
  };
}
