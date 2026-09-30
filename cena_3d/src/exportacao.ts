/** Downloads consultam o mesmo motor usado pela conexão WebSocket. */
export function criarExportacoes(websocket: string) {
  const status = document.getElementById('resultado-exportacao')!;
  const registros: { botao: HTMLButtonElement; clicar: () => Promise<void> }[] = [];
  let conectado = false;
  const emCurso = new Set<HTMLButtonElement>();
  for (const [tipo, extensao] of [['eventos', 'json'], ['metricas', 'csv']]) {
    const botao = document.getElementById(`exportar-${tipo}`) as HTMLButtonElement;
    const clicar = async () => {
      botao.disabled = true; emCurso.add(botao);
      status.textContent = 'Preparando arquivo…';
      try {
        const url = new URL(websocket);
        url.protocol = url.protocol === 'wss:' ? 'https:' : 'http:';
        url.pathname = `/exportar/${tipo}`; url.search = ''; url.hash = '';
        const resposta = await fetch(url, { signal: AbortSignal.timeout(30000) });
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        const arquivo = await resposta.blob();
        const link = document.createElement('a');
        const destino = URL.createObjectURL(arquivo);
        link.href = destino;
        link.download = resposta.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1] ?? `${tipo}.${extensao}`;
        document.body.append(link); link.click(); link.remove();
        setTimeout(() => URL.revokeObjectURL(destino), 1000);
        status.textContent = `${tipo === 'eventos' ? 'Eventos exportados' : 'Métricas exportadas'}.`;
      } catch (erro) {
        status.textContent = `Não foi possível exportar: ${erro instanceof Error ? erro.message : 'falha na conexão'}. Tente novamente.`;
      } finally { emCurso.delete(botao); botao.disabled = !conectado; }
    };
    botao.addEventListener('click', clicar);
    registros.push({ botao, clicar });
  }
  return {
    definirConexao(valor: boolean) {
      conectado = valor;
      if (valor && status.textContent === 'Aguardando conexão.') status.textContent = 'A simulação continua durante o download.';
      for (const { botao } of registros) botao.disabled = !valor || emCurso.has(botao);
    },
    descartar() { for (const { botao, clicar } of registros) botao.removeEventListener('click', clicar); },
  };
}
