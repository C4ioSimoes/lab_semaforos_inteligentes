import type { ComandoReset } from './contratos';

export function criarReset(enviar: (comando: ComandoReset) => boolean) {
  const botao = document.getElementById('resetar-simulacao') as HTMLButtonElement;
  let conectado = false, execucao = '', pendente: string | undefined;
  function atualizarBotao() {
    botao.disabled = !conectado || !execucao || !!pendente;
    botao.setAttribute('aria-busy', String(!!pendente));
  }
  const resetar = () => {
    if (botao.disabled) return;
    const id = crypto.randomUUID();
    pendente = id;
    atualizarBotao();
    if (!enviar({command_id: id, tipo: 'resetar_simulacao', parametros: {}})) {
      pendente = undefined;
      atualizarBotao();
    }
  };
  botao.addEventListener('click', resetar);
  return {
    definirConexao(valor: boolean) {
      conectado = valor;
      if (!valor) pendente = undefined;
      atualizarBotao();
    },
    atualizar(runId: string) {
      if (execucao !== runId) { execucao = runId; pendente = undefined; }
      atualizarBotao();
    },
    confirmar(id: string, aplicado: boolean) {
      if (pendente === id && !aplicado) pendente = undefined;
      atualizarBotao();
    },
    descartar() { botao.removeEventListener('click', resetar); },
  };
}
