import { lerMensagem, type ComandoCliente, type Instantaneo, type RespostaComando } from './contratos';

export type EstadoConexao = 'conectando' | 'aguardando' | 'conectado' | 'desatualizado' | 'desconectado' | 'erro';

/** Transporta comandos e estados. Os temporizadores nunca avançam a simulação. */
export function conectarMotor(
  endereco: string,
  aoReceber: (estado: Instantaneo) => void,
  aoMudar: (estado: EstadoConexao, mensagem: string) => void,
  aoConfirmar: (resposta: RespostaComando) => void,
) {
  let socket: WebSocket | undefined;
  let encerrado = false;
  let tentativa = 0;
  let reconexao: ReturnType<typeof setTimeout> | undefined;
  let inatividade: ReturnType<typeof setTimeout> | undefined;
  let ultimo: Instantaneo | undefined;
  let sincronizado = false;
  const execucoesAnteriores = new Set<string>();

  function mudar(estado: EstadoConexao, mensagem: string) {
    sincronizado = estado === 'conectado';
    aoMudar(estado, mensagem);
  }

  function aguardarDados() {
    clearTimeout(inatividade);
    inatividade = setTimeout(() => mudar('desatualizado', 'Sem novos instantâneos há 3 s. Último estado preservado.'), 3000);
  }

  function abrir() {
    if (encerrado) return;
    mudar('conectando', ultimo ? 'Reconectando. Último estado preservado.' : 'Conectando ao servidor Python.');
    try {
      const url = new URL(endereco);
      if (!['ws:', 'wss:'].includes(url.protocol)) throw new Error('Protocolo inválido');
      socket = new WebSocket(url);
    } catch {
      mudar('erro', 'Endereço WebSocket inválido. Verifique VITE_WS_URL.');
      return;
    }
    const atual = socket;
    atual.onopen = () => {
      if (encerrado || socket !== atual) return;
      mudar('aguardando', 'Conexão aberta. Aguardando sincronização com o motor.');
      aguardarDados();
    };
    atual.onmessage = (evento) => {
      if (encerrado || socket !== atual) return;
      let recebido: Instantaneo;
      try {
        if (typeof evento.data !== 'string') throw new Error('Esperado JSON textual');
        const mensagem = lerMensagem(evento.data);
        if ('tipo' in mensagem) {
          aoConfirmar(mensagem);
          return;
        }
        recebido = mensagem;
      } catch {
        mudar('erro', 'Mensagem inválida recebida. Último estado válido preservado.');
        return;
      }
      if (execucoesAnteriores.has(recebido.run_id)) return;
      if (ultimo?.run_id === recebido.run_id &&
          (recebido.step < ultimo.step || recebido.simulation_time < ultimo.simulation_time)) return;
      // Um instantâneo igual permite sincronização após reconectar, sem avançar a tela.
      if (!ultimo || recebido.run_id !== ultimo.run_id || recebido.step > ultimo.step) {
        if (ultimo && recebido.run_id !== ultimo.run_id) execucoesAnteriores.add(ultimo.run_id);
        ultimo = recebido;
        aoReceber(recebido);
      }
      tentativa = 0;
      mudar('conectado', 'Instantâneos recebidos do motor Python.');
      aguardarDados();
    };
    atual.onerror = () => {
      if (!encerrado && socket === atual) mudar('erro', 'Falha na conexão com o motor. Aguardando reconexão.');
    };
    atual.onclose = () => {
      if (encerrado || socket !== atual) return;
      clearTimeout(inatividade);
      const espera = Math.min(1000 * 2 ** tentativa++, 8000);
      mudar('desconectado', `Conexão perdida; estado desatualizado. Nova tentativa em ${espera / 1000} s.`);
      reconexao = setTimeout(abrir, espera);
    };
  }
  abrir();
  return {
    enviar(comando: ComandoCliente): boolean {
      if (encerrado || !sincronizado || socket?.readyState !== WebSocket.OPEN) return false;
      try {
        socket.send(JSON.stringify(comando));
        return true;
      } catch {
        mudar('erro', 'Não foi possível enviar o comando. Aguarde a conexão.');
        return false;
      }
    },
    desconectar() {
      encerrado = true;
      clearTimeout(reconexao);
      clearTimeout(inatividade);
      socket?.close();
    },
  };
}
