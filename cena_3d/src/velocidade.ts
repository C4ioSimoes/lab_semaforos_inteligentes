import type { ComandoVelocidade } from './contratos';

export function criarVelocidade(enviar: (comando: ComandoVelocidade) => boolean) {
  const slider = document.getElementById('velocidade-simulacao') as HTMLInputElement;
  const valor = document.getElementById('valor-velocidade')!;
  const status = document.getElementById('resultado-velocidade')!;
  let conectado = false, interrompido = false, execucao = '';
  let oficial: number | undefined, escolha = 1, alterado = false;
  let pendente: { id: string; multiplicador: number; confirmado: boolean } | undefined;
  let temporizador: ReturnType<typeof setTimeout> | undefined;
  function mostrar() {
    slider.disabled = !conectado || oficial === undefined || interrompido;
    slider.value = String(escolha);
    slider.setAttribute('aria-valuetext', `${escolha} vezes a velocidade normal`);
    slider.setAttribute('aria-busy', String(!!pendente));
    slider.style.setProperty('--progresso', `${(escolha - 1) / 23 * 100}%`);
    valor.textContent = `${escolha}×`;
  }
  function aplicar() {
    clearTimeout(temporizador);
    if (!alterado || pendente || slider.disabled) return;
    if (escolha === oficial) { alterado = false; status.textContent = `Ativa: ${oficial}×`; return; }
    const id = crypto.randomUUID();
    pendente = { id, multiplicador: escolha, confirmado: false };
    alterado = false;
    if (enviar({command_id: id, tipo: 'configurar_velocidade', parametros: {multiplicador: escolha}})) {
      status.textContent = `Aplicando ${escolha}×…`;
    } else {
      pendente = undefined; escolha = oficial ?? 1;
    }
    mostrar();
  }
  const ajustar = () => {
    escolha = Number(slider.value); alterado = true; mostrar();
    status.textContent = `Ativa: ${oficial}× · ajustando…`;
    clearTimeout(temporizador);
    temporizador = setTimeout(aplicar, 180);
  };
  slider.addEventListener('input', ajustar);
  slider.addEventListener('change', aplicar);
  return {
    definirConexao(valor: boolean) {
      conectado = valor;
      if (!valor) {
        clearTimeout(temporizador); pendente = undefined; alterado = false; escolha = oficial ?? 1;
      }
      mostrar();
    },
    confirmar(id: string, aplicado: boolean, erro: string | null) {
      if (pendente?.id !== id) return;
      if (aplicado) pendente.confirmado = true;
      else {
        clearTimeout(temporizador); pendente = undefined; alterado = false; escolha = oficial ?? 1;
        status.textContent = erro ?? 'Não foi possível alterar a velocidade.';
      }
      mostrar();
    },
    atualizar(multiplicador: number | undefined, runId: string, pausado: boolean) {
      const mudou = oficial !== multiplicador || execucao !== runId;
      oficial = multiplicador; interrompido = pausado;
      if (execucao !== runId) {
        execucao = runId; clearTimeout(temporizador); pendente = undefined; alterado = false;
      }
      if (pendente?.confirmado && oficial === pendente.multiplicador) {
        pendente = undefined;
        status.textContent = `Ativa: ${oficial}×`;
      }
      if (!pendente && !alterado) {
        escolha = oficial ?? 1;
        if (mudou) status.textContent = oficial === undefined ? 'Disponível após atualizar o motor.' : `Ativa: ${oficial}×`;
      }
      mostrar();
      if (alterado && !pendente) queueMicrotask(aplicar);
    },
    descartar() {
      clearTimeout(temporizador);
      slider.removeEventListener('input', ajustar); slider.removeEventListener('change', aplicar);
    },
  };
}
