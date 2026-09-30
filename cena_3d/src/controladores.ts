import type { ComandoControlador, ConfiguracaoControlador, Controle, NomeControlador } from './contratos';

export const nomesControladores: Record<NomeControlador, string> = {
  baseline: 'Tempos fixos', imperativo: 'Imperativo', orientado_objetos: 'Orientado a objetos', funcional: 'Funcional',
  logico: 'Lógico (Prolog)',
};
const el = (id: string) => document.getElementById(id)!;
const input = (id: string) => el(id) as HTMLInputElement;

export function criarPainelControlador(enviar: (comando: ComandoControlador) => boolean) {
  let conectado = false, disponivel = false, interrompido = false, alterado = false;
  let runId = '', assinatura = '', revisao = 0;
  const enviados = new Map<string, number>();
  const ler = (): ConfiguracaoControlador => ({
    controlador: (el('controlador') as HTMLSelectElement).value as NomeControlador,
    limiar_espera: Number(input('limiar-espera').value),
    prioridade_ambulancia: input('prioridade-ambulancia').checked,
    prioridade_onibus: input('prioridade-onibus').checked,
  });
  function atualizarDisponibilidade() {
    (el('aplicar-controlador') as HTMLButtonElement).disabled = !conectado || !disponivel || interrompido;
    const baseline = ler().controlador === 'baseline';
    (el('parametros-prioridade') as HTMLFieldSetElement).disabled = baseline;
    el('parametros-prioridade').hidden = baseline;
    el('nota-politica').textContent = baseline
      ? 'Os sinais seguem uma sequência fixa.'
      : 'Mesmas prioridades, quatro formas de programar (paradigmas).';
  }
  const editar = () => { alterado = true; revisao++; atualizarDisponibilidade(); el('resultado-controlador').textContent = 'Clique em Ativar regras para aplicar.'; };
  const aplicar = (evento: Event) => {
    evento.preventDefault();
    const comando: ComandoControlador = { command_id: crypto.randomUUID(), tipo: 'configurar_controlador', parametros: ler() };
    if (enviar(comando)) enviados.set(comando.command_id, revisao);
  };
  el('form-controlador').addEventListener('input', editar);
  el('form-controlador').addEventListener('submit', aplicar);
  return {
    definirConexao(valor: boolean) { conectado = valor; atualizarDisponibilidade(); },
    confirmar(id: string, aplicado: boolean) {
      if (aplicado && enviados.get(id) === revisao) { alterado = false; assinatura = ''; }
      enviados.delete(id);
    },
    atualizar(controle: Controle | undefined, execucao: string, pausado: boolean) {
      const config = controle?.configuracao_controlador;
      disponivel = !!config; interrompido = pausado;
      if (config && (runId !== execucao || (!alterado && assinatura !== JSON.stringify(config)))) {
        if (runId !== execucao) enviados.clear();
        runId = execucao; assinatura = JSON.stringify(config); alterado = false;
        (el('controlador') as HTMLSelectElement).value = config.controlador;
        input('limiar-espera').value = String(config.limiar_espera);
        input('prioridade-ambulancia').checked = config.prioridade_ambulancia;
        input('prioridade-onibus').checked = config.prioridade_onibus;
        if (el('resultado-controlador').textContent === 'Aguardando conexão.') el('resultado-controlador').textContent = '';
      }
      atualizarDisponibilidade();
    },
    descartar() {
      el('form-controlador').removeEventListener('input', editar);
      el('form-controlador').removeEventListener('submit', aplicar);
    },
  };
}
