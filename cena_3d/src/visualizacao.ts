/** Painéis sobre a cena: não mudam o relógio nem as configurações do motor. */
export function criarVisualizacao() {
  const eventos = new AbortController();
  const pequeno = window.matchMedia('(max-width: 760px)');
  const pares = [
    ['alternar-dados', 'painel-dados'], ['alternar-controles', 'painel-geracao'],
  ].map(([botao, painel]) => ({
    botao: document.getElementById(botao) as HTMLButtonElement,
    painel: document.getElementById(painel)!,
  }));
  function mostrar(indice: number, aberto: boolean) {
    pares[indice].painel.hidden = !aberto;
    pares[indice].botao.setAttribute('aria-expanded', String(aberto));
  }
  function adaptar() {
    for (let i = 0; i < pares.length; i++) mostrar(i, !pequeno.matches);
  }
  for (const [i, par] of pares.entries()) {
    par.botao.addEventListener('click', () => {
      const abrir = par.painel.hidden;
      if (pequeno.matches) pares.forEach((_, outro) => mostrar(outro, false));
      mostrar(i, abrir);
    }, { signal: eventos.signal });
  }
  pequeno.addEventListener('change', adaptar, { signal: eventos.signal });
  adaptar();

  const telaCheia = document.getElementById('tela-cheia') as HTMLButtonElement;
  const status = document.getElementById('resultado-visualizacao')!;
  telaCheia.hidden = !document.fullscreenEnabled;
  function sincronizar() {
    const nome = document.fullscreenElement ? 'Sair da tela cheia' : 'Entrar em tela cheia';
    telaCheia.setAttribute('aria-label', nome); telaCheia.title = nome;
  }
  telaCheia.addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
      status.textContent = '';
    } catch {
      status.textContent = 'Tela cheia indisponível neste navegador.';
    }
  }, { signal: eventos.signal });
  document.addEventListener('fullscreenchange', sincronizar, { signal: eventos.signal });
  sincronizar();
  return { descartar() { eventos.abort(); } };
}
