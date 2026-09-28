/** Troca de painéis local: preserva formulários e nunca envia comandos. */
export function criarSeparadores(container: HTMLElement) {
  const abas = [...container.querySelectorAll<HTMLButtonElement>('[role="tab"]')];
  const eventos = new AbortController();
  function selecionar(ativa: HTMLButtonElement) {
    for (const aba of abas) {
      const selecionada = aba === ativa;
      aba.setAttribute('aria-selected', String(selecionada));
      aba.tabIndex = selecionada ? 0 : -1;
      const painel = document.getElementById(aba.getAttribute('aria-controls')!);
      if (painel) painel.hidden = !selecionada;
    }
  }
  for (const [indice, aba] of abas.entries()) {
    aba.addEventListener('click', () => selecionar(aba), { signal: eventos.signal });
    aba.addEventListener('keydown', (evento) => {
      let destino: number;
      switch (evento.key) {
        case 'ArrowRight': destino = (indice + 1) % abas.length; break;
        case 'ArrowLeft': destino = (indice + abas.length - 1) % abas.length; break;
        case 'Home': destino = 0; break;
        case 'End': destino = abas.length - 1; break;
        default: return;
      }
      evento.preventDefault();
      selecionar(abas[destino]);
      abas[destino].focus();
    }, { signal: eventos.signal });
  }
  return { descartar: () => eventos.abort() };
}
