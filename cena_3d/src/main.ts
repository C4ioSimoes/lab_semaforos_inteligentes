import './style.css';
import { criarReset } from './reset';
import { criarPainelTransito } from './transito';
import { criarPainelNeural } from './neural';
import { criarExportacoes } from './exportacao';
import { criarSeparadores } from './separadores';
import { criarCena } from './cena';
import { conectarMotor, type EstadoConexao } from './conexao';
import type { ComandoCliente } from './contratos';
import { criarPainelGeracao } from './geracao';
import { criarPainelControlador, nomesControladores } from './controladores';

function elemento(id: string): HTMLElement {
  const encontrado = document.getElementById(id);
  if (!encontrado) throw new Error(`Elemento ausente: ${id}`);
  return encontrado;
}
const separadores = criarSeparadores(elemento('separadores-controle'));
let cena: ReturnType<typeof criarCena> | undefined;
try {
  cena = criarCena(elemento('cena'));
} catch (erro) {
  console.error('Falha ao inicializar a cena', erro);
  elemento('erro-cena').hidden = false;
  elemento('erro-cena').textContent = 'Não foi possível iniciar o WebGL. Verifique o suporte gráfico do navegador.';
}
const superior = () => cena?.vistaSuperior();
const restaurar = () => cena?.restaurar();
elemento('vista-superior').addEventListener('click', superior);
elemento('restaurar-vista').addEventListener('click', restaurar);
const url = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws';
elemento('endpoint').textContent = url;
const titulos: Record<EstadoConexao, string> = {
  conectando: 'Conectando', aguardando: 'Sincronizando', conectado: 'Conectado',
  desatualizado: 'Estado desatualizado', desconectado: 'Desconectado', erro: 'Falha na conexão',
};
const formatador = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 3 });
type Destino = 'resultado-geracao' | 'resultado-controlador' | 'resultado-neural' | 'resultado-neural-transito' | 'resultado-urbano' | 'resultado-reset';
const pendentes = new Map<string, Destino>();
const painelGeracao = criarPainelGeracao(enviarComando);
const painelControlador = criarPainelControlador(enviarComando);
const painelNeural = criarPainelNeural(enviarComando);
const painelTransito = criarPainelTransito(enviarComando);
const exportacoes = criarExportacoes(url);
const painelReset = criarReset(enviarComando);
let ultimaExecucao: string | undefined;
const conexao = conectarMotor(url, (estado) => {
  if (ultimaExecucao !== estado.run_id) pendentes.clear();
  ultimaExecucao = estado.run_id;
  painelReset.atualizar(estado.run_id);
  elemento('tempo').textContent = formatador.format(estado.simulation_time);
  elemento('passo').textContent = String(estado.step);
  elemento('fase').textContent = estado.fase ?? 'Aguardando';
  elemento('execucao').textContent = estado.run_id;
  cena?.atualizarParticipantes(estado.run_id, estado.participantes);
  cena?.atualizarSemaforos(estado);
  const controle = estado.controle;
  const nome = controle?.configuracao_controlador?.controlador ?? 'baseline';
  elemento('estado-controle').textContent = controle
    ? `${controle.operacao?.modo === 'urbano' ? 'Semáforo urbano' : controle.operacao?.modo === 'neural' ? `Rede aplicada: ${controle.operacao.modelo}` : nome === 'baseline' ? 'Política fixa' : nomesControladores[nome]} · ${controle.estado} há ${formatador.format(controle.decorrido_segundos)} s.`
    : 'Aguardando política e transição.';
  elemento('validacao-controle').textContent = controle?.validacao.motivo ?? '';
  elemento('falha-controlador').hidden = !controle?.falha_controlador;
  elemento('falha-controlador').textContent = controle?.falha_controlador ?? '';
  elemento('decisao-controlador').textContent = controle?.decisao
    ? `Passo ${controle.decisao.step}: ${controle.decisao.proposta.acao} → ${controle.decisao.proposta.fase ?? 'aguardar demanda'}. ${controle.decisao.proposta.motivo}` : '';
  elemento('avaliacoes-fases').replaceChildren(...(controle?.decisao?.avaliacoes ?? []).map((a) => {
    const linha = document.createElement('p');
    linha.textContent = `${a.fase}: ${a.demanda} solicitações · maior espera ${formatador.format(a.maior_espera)} s · ${a.criterio}. ${a.admissivel ? 'Admissível agora.' : a.bloqueio}`;
    return linha;
  }));
  elemento('vazao').textContent = estado.metricas ? formatador.format(estado.metricas.total.vazao_por_minuto) : '—';
  elemento('espera-concluidos').textContent = estado.metricas ? `${formatador.format(estado.metricas.total.espera_concluidos_total_media)} s` : '—';
  const interrompido = !!estado.demanda?.motivo_interrupcao;
  painelControlador.atualizar(controle, estado.run_id, interrompido);
  painelNeural.atualizar(controle, estado.run_id, interrompido);
  painelTransito.atualizar(controle, interrompido);
  painelGeracao.atualizar(estado.demanda, estado.run_id);
  elemento('carros-ativos').textContent = String(estado.participantes.filter((p) => p.categoria !== 'pedestre').length);
  elemento('pedestres-ativos').textContent = String(estado.participantes.filter((p) => p.categoria === 'pedestre').length);
  elemento('entrada-pendente').textContent = String(estado.solicitacoes.length);
  elemento('situacao-cruzamento').textContent = Object.entries(estado.semaforos)
    .map(([origem, sinal]) => `${origem}: ${sinal}`).join(' · ');
}, (estado, mensagem) => {
  elemento('status').dataset.estado = estado;
  elemento('status').textContent = titulos[estado];
  elemento('mensagem-conexao').textContent = estado === 'conectado' ? 'Simulação sincronizada' : mensagem;
  painelGeracao.definirConexao(estado === 'conectado');
  painelControlador.definirConexao(estado === 'conectado');
  painelNeural.definirConexao(estado === 'conectado');
  painelTransito.definirConexao(estado === 'conectado');
  exportacoes.definirConexao(estado === 'conectado');
  painelReset.definirConexao(estado === 'conectado');
  if (estado !== 'conectado') {
    for (const destino of pendentes.values()) elemento(destino).textContent = 'Há pedidos sem confirmação. Aguardando sincronização com o motor.';
    pendentes.clear();
  }
}, (resposta) => {
  const destino = resposta.command_id ? pendentes.get(resposta.command_id) : undefined;
  if (!destino || !resposta.command_id) return;
  pendentes.delete(resposta.command_id);
  const confirmacao = resposta.confirmacao;
  if (destino === 'resultado-reset') painelReset.confirmar(resposta.command_id, confirmacao.status === 'aplicado');
  if (destino === 'resultado-geracao') painelGeracao.confirmar(resposta.command_id, confirmacao.status === 'aplicado');
  if (destino === 'resultado-neural') painelNeural.confirmar(resposta.command_id, confirmacao.status === 'aplicado');
  if (destino === 'resultado-controlador') painelControlador.confirmar(resposta.command_id, confirmacao.status === 'aplicado');
  elemento(destino).textContent = confirmacao.status === 'aplicado'
    ? destino === 'resultado-reset' ? 'Simulação reiniciada. Configurações mantidas.' : destino === 'resultado-geracao' ? 'Geração atualizada.' : `Pedido aplicado no passo ${confirmacao.passo_aplicacao}.`
    : `Pedido rejeitado: ${confirmacao.erro}`;
});
function enviarComando(comando: ComandoCliente) {
  const destino: Destino = comando.tipo === 'resetar_simulacao' ? 'resultado-reset' : comando.tipo === 'configurar_operacao' ? (comando.parametros.modo === 'urbano' ? 'resultado-urbano' : 'resultado-neural-transito') : comando.tipo === 'configurar_modelo_neural' ? 'resultado-neural' : comando.tipo === 'configurar_controlador' ? 'resultado-controlador' : 'resultado-geracao';
  pendentes.set(comando.command_id, destino);
  if (conexao.enviar(comando)) {
    elemento(destino).textContent = 'Atualizando…';
    return true;
  }
  pendentes.delete(comando.command_id);
  elemento(destino).textContent = 'Pedido não enviado. Aguarde a conexão com o motor.';
  return false;
}
function descartar() {
  separadores.descartar(); conexao.desconectar(); painelGeracao.descartar(); painelReset.descartar();
  painelControlador.descartar(); painelNeural.descartar(); painelTransito.descartar(); exportacoes.descartar(); cena?.descartar();
  elemento('vista-superior').removeEventListener('click', superior);
  elemento('restaurar-vista').removeEventListener('click', restaurar);
}
window.addEventListener('pagehide', descartar, { once: true });
if (import.meta.hot) import.meta.hot.dispose(() => {
  window.removeEventListener('pagehide', descartar); descartar();
});
