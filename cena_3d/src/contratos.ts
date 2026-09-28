/** Espelho de Instantaneo em motor_python/modelos.py (Seção 13). */
import { categoriaValida, type CategoriaVeiculo } from './categorias';
export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type ObjetoJson = { [key: string]: Json };
export type CorSemaforo = 'vermelho' | 'amarelo' | 'verde';
export type NomeControlador = 'baseline' | 'imperativo' | 'orientado_objetos' | 'funcional' | 'logico';
export type ModeloNeural = 'AND_referencia' | 'perceptron' | 'adaline';
export interface CalculoNeural {
  modelo: ModeloNeural; entradas: [number, number]; pesos: [number, number, number] | null;
  bias: number; peso_bias: number | null; soma_ponderada: number | null;
  saida: number; and_referencia: number; elegivel: boolean; divergencia: boolean;
}
export interface DisponibilidadeNeural {
  disponivel: boolean; erro: string | null; verificacao_and: CalculoNeural[];
  epocas?: number; motivo_parada?: string; versao?: string;
}
export interface ConfiguracaoControlador {
  controlador: NomeControlador; limiar_espera: number; prioridade_ambulancia: boolean; prioridade_onibus: boolean;
}
export interface DecisaoControlador {
  step: number; controlador: NomeControlador; modelo?: ModeloNeural; motivos: string[];
  proposta: { acao: string; fase: string | null; motivo: string };
  avaliacoes: { fase: string; demanda: number; maior_espera: number; criterio: string; admissivel: boolean; elegivel: boolean; bloqueio: string | null; neural?: CalculoNeural; origem_solicitacao?: string }[];
}

export interface ResumoMetricas {
  concluidos: number; ativos: number; pendentes: number; vazao_por_minuto: number;
  espera_concluidos_interna_media: number; espera_concluidos_externa_media: number;
  espera_concluidos_total_media: number; espera_ativos_interna_total: number;
  espera_ativos_externa_total: number; espera_pendentes_externa_total: number;
  espera_pedestres_ate_autorizacao_total: number;
}
export interface Metricas {
  intervalo_segundos: number; chegadas_solicitadas: number; limiar_velocidade_espera: number;
  total: ResumoMetricas; por_origem: Record<string, ResumoMetricas>; por_categoria: Record<string, ResumoMetricas>;
}
export interface Controle {
  politica: string; estado: string; inicio_passo: number; decorrido_segundos: number;
  sequencia: string[]; permissoes: string[]; bloqueios: number;
  tempos: { verde: number; amarelo: number; liberacao_minima: number };
  validacao: { aceita: boolean; motivo: string };
  configuracao_controlador?: ConfiguracaoControlador;
  decisao?: DecisaoControlador | null;
  falha_controlador?: string | null;
  modelo_neural?: ModeloNeural;
  modelos_neurais?: Record<ModeloNeural, DisponibilidadeNeural>;
}

export interface Participante {
  readonly id: string;
  readonly categoria: CategoriaVeiculo;
  readonly origem: string;
  readonly destino: string;
  readonly trajetoria: string;
  readonly posicao: { readonly x: number; readonly y: number; readonly z: number; readonly rotacao_y: number };
  readonly estado: string;
  readonly instante_solicitado: number;
  readonly instante_inserido: number | null;
  readonly solicitacao_prioritaria: boolean;
  readonly dimensoes: { readonly comprimento: number; readonly largura: number; readonly altura: number };
  readonly instante_inicio_espera: number | null;
  readonly fonte?: 'manual' | 'automatico';
}

export interface ComandoInsercao {
  command_id: string;
  tipo: 'inserir_participante';
  parametros: { categoria: Exclude<CategoriaVeiculo, 'pedestre'>; origem: string; movimento: 'seguir_em_frente'; quantidade: 1; solicitacao_prioritaria?: boolean }
    | { categoria: 'pedestre'; travessia: string; lado: 'A' | 'B'; quantidade: number };
}

export interface ConfiguracaoGerador {
  semente: number;
  taxas_veiculares: Record<string, Record<string, number>>;
  taxas_pedestres: Record<string, number>;
  fator_global: number;
  fatores_locais: Record<string, number>;
  fator_pedestres: number;
}
export interface DiagnosticoDemanda {
  configuracao: ConfiguracaoGerador;
  inicio_janela: number; duracao_janela: number;
  taxas_efetivas: Record<string, number>; taxas_observadas: Record<string, number>;
  gerados_janela: Record<string, number>;
  solicitados: Record<'manual' | 'automatico', number>;
  admitidos: Record<'manual' | 'automatico', number>;
  recusados: Record<'manual' | 'automatico', number>;
  motivo_interrupcao: string | null;
  limites: { ativos: number; pendentes: number; taxa_efetiva: number };
}
export interface ComandoGerador {
  command_id: string; tipo: 'configurar_gerador'; parametros: ConfiguracaoGerador;
}
export interface ComandoControlador {
  command_id: string; tipo: 'configurar_controlador'; parametros: ConfiguracaoControlador;
}
export interface ComandoNeural {
  command_id: string; tipo: 'configurar_modelo_neural'; parametros: { modelo: ModeloNeural };
}
export type ComandoCliente = ComandoInsercao | ComandoGerador | ComandoControlador | ComandoNeural;

export interface RespostaComando {
  readonly tipo: 'confirmacao_comando';
  readonly command_id: string | null;
  readonly confirmacao: {
    readonly status: 'aplicado' | 'rejeitado';
    readonly passo_aplicacao: number | null;
    readonly erro: string | null;
  };
}

export interface Instantaneo {
  readonly run_id: string;
  readonly step: number;
  readonly simulation_time: number;
  readonly fase: string | null;
  readonly estado_transicao: string;
  readonly ocupacoes: ObjetoJson;
  readonly filas: ObjetoJson;
  readonly solicitacoes: ObjetoJson[];
  readonly versao_configuracao: string;
  readonly participantes: Participante[];
  readonly semaforos: Record<'N' | 'S' | 'L' | 'O', CorSemaforo>;
  readonly semaforos_pedestres?: Record<string, 'verde' | 'vermelho'>;
  readonly controle?: Controle;
  readonly metricas?: Metricas;
  readonly demanda?: DiagnosticoDemanda;
}

const objeto = (v: unknown): v is ObjetoJson => typeof v === 'object' && v !== null && !Array.isArray(v);
const texto = (v: unknown): v is string => typeof v === 'string' && v.length > 0;
const finito = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const naoNegativo = (v: unknown): v is number => finito(v) && v >= 0;

const modelosNeurais = ['AND_referencia', 'perceptron', 'adaline'];
function calculoNeuralValido(v: unknown): boolean {
  if (!objeto(v) || !modelosNeurais.includes(v.modelo as string) || v.bias !== 1 ||
      !Array.isArray(v.entradas) || v.entradas.length !== 2 || !v.entradas.every(x => x === 0 || x === 1) ||
      ![-1, 1].includes(v.saida as number) || ![-1, 1].includes(v.and_referencia as number) ||
      typeof v.elegivel !== 'boolean' || typeof v.divergencia !== 'boolean') return false;
  return v.modelo === 'AND_referencia'
    ? v.pesos === null && v.peso_bias === null && v.soma_ponderada === null
    : Array.isArray(v.pesos) && v.pesos.length === 3 && v.pesos.every(finito) && finito(v.peso_bias) && finito(v.soma_ponderada);
}
function disponibilidadeNeuralValida(v: unknown): boolean {
  return objeto(v) && modelosNeurais.every(nome => {
    const m = v[nome];
    return objeto(m) && typeof m.disponivel === 'boolean' && (m.erro === null || texto(m.erro)) &&
      Array.isArray(m.verificacao_and) && m.verificacao_and.every(calculoNeuralValido);
  });
}
function metricasValidas(v: unknown): boolean {
  const resumo = (r: unknown) => objeto(r) && ['concluidos', 'ativos', 'pendentes', 'vazao_por_minuto',
    'espera_concluidos_interna_media', 'espera_concluidos_externa_media', 'espera_concluidos_total_media',
    'espera_ativos_interna_total', 'espera_ativos_externa_total', 'espera_pendentes_externa_total',
    'espera_pedestres_ate_autorizacao_total'].every((k) => naoNegativo(r[k]));
  return objeto(v) && naoNegativo(v.intervalo_segundos) && naoNegativo(v.chegadas_solicitadas) &&
    naoNegativo(v.limiar_velocidade_espera) && resumo(v.total) && objeto(v.por_origem) &&
    objeto(v.por_categoria) && Object.values(v.por_origem).every(resumo) && Object.values(v.por_categoria).every(resumo);
}
function controleValido(v: unknown): boolean {
  return objeto(v) && texto(v.politica) && texto(v.estado) && naoNegativo(v.inicio_passo) &&
    naoNegativo(v.decorrido_segundos) && naoNegativo(v.bloqueios) && Array.isArray(v.sequencia) &&
    v.sequencia.every(texto) && Array.isArray(v.permissoes) && v.permissoes.every(texto) &&
    objeto(v.tempos) && ['verde', 'amarelo', 'liberacao_minima'].every((k) => naoNegativo((v.tempos as ObjetoJson)[k])) &&
    objeto(v.validacao) && typeof v.validacao.aceita === 'boolean' && texto(v.validacao.motivo) &&
    (v.configuracao_controlador === undefined || configuracaoControladorValida(v.configuracao_controlador)) &&
    (v.falha_controlador === undefined || v.falha_controlador === null || texto(v.falha_controlador)) &&
    (v.modelo_neural === undefined || modelosNeurais.includes(v.modelo_neural as string)) &&
    (v.modelos_neurais === undefined || disponibilidadeNeuralValida(v.modelos_neurais)) &&
    (v.decisao === undefined || v.decisao === null || decisaoValida(v.decisao));
}
function configuracaoControladorValida(v: unknown): boolean {
  return objeto(v) && ['baseline', 'imperativo', 'orientado_objetos', 'funcional', 'logico'].includes(v.controlador as string) &&
    finito(v.limiar_espera) && v.limiar_espera > 0 && v.limiar_espera <= 3600 &&
    typeof v.prioridade_ambulancia === 'boolean' && typeof v.prioridade_onibus === 'boolean';
}
function decisaoValida(v: unknown): boolean {
  return objeto(v) && Number.isSafeInteger(v.step) && naoNegativo(v.step) &&
    ['baseline', 'imperativo', 'orientado_objetos', 'funcional', 'logico'].includes(v.controlador as string) &&
    Array.isArray(v.motivos) && v.motivos.every(texto) && objeto(v.proposta) &&
    texto(v.proposta.acao) &&
    (v.proposta.fase === null || texto(v.proposta.fase)) && texto(v.proposta.motivo) && Array.isArray(v.avaliacoes) &&
    v.avaliacoes.every((a) => objeto(a) && texto(a.fase) && naoNegativo(a.demanda) && naoNegativo(a.maior_espera) &&
      texto(a.criterio) && typeof a.admissivel === 'boolean' && typeof a.elegivel === 'boolean' && (a.bloqueio === null || texto(a.bloqueio)) && (a.neural === undefined || calculoNeuralValido(a.neural)));
}

function participante(v: unknown): boolean {
  if (!objeto(v) || !objeto(v.posicao) || !objeto(v.dimensoes)) return false;
  const posicao = v.posicao;
  const dimensoes = v.dimensoes;
  return texto(v.id) && categoriaValida(v.categoria) && texto(v.origem) &&
    texto(v.destino) && texto(v.trajetoria) && texto(v.estado) &&
    ['x', 'y', 'z', 'rotacao_y'].every((eixo) => finito(posicao[eixo])) &&
    ['comprimento', 'largura', 'altura'].every((eixo) => finito(dimensoes[eixo]) && (dimensoes[eixo] as number) > 0) &&
    finito(v.instante_solicitado) && v.instante_solicitado >= 0 &&
    (v.instante_inserido === null || (finito(v.instante_inserido) && v.instante_inserido >= 0)) &&
    typeof v.solicitacao_prioritaria === 'boolean' &&
    (v.fonte === undefined || v.fonte === 'manual' || v.fonte === 'automatico') &&
    (v.instante_inicio_espera === null || (finito(v.instante_inicio_espera) && v.instante_inicio_espera >= 0));
}

function demandaValida(v: unknown): boolean {
  if (!objeto(v) || !objeto(v.configuracao) || !objeto(v.limites)) return false;
  const mapa = (m: unknown) => objeto(m) && Object.values(m).every((n) => finito(n) && n >= 0);
  const c = v.configuracao;
  return ['inicio_janela', 'duracao_janela'].every((k) => finito(v[k]) && (v[k] as number) >= 0) &&
    ['taxas_efetivas', 'taxas_observadas', 'gerados_janela', 'solicitados', 'admitidos', 'recusados'].every((k) => mapa(v[k])) &&
    [v.solicitados, v.admitidos, v.recusados].every((m) => objeto(m) && finito(m.manual) && finito(m.automatico)) &&
    (v.motivo_interrupcao === null || texto(v.motivo_interrupcao)) && mapa(v.limites) &&
    ['ativos', 'pendentes', 'taxa_efetiva'].every((k) => finito((v.limites as ObjetoJson)[k])) &&
    Number.isSafeInteger(c.semente) && finito(c.fator_global) && finito(c.fator_pedestres) &&
    mapa(c.taxas_pedestres) && mapa(c.fatores_locais) && objeto(c.taxas_veiculares) &&
    ['N', 'S', 'L', 'O'].every((o) => {
      const taxas = (c.taxas_veiculares as ObjetoJson)[o];
      return finito((c.fatores_locais as ObjetoJson)[o]) && finito((c.taxas_pedestres as ObjetoJson)[`${o}-TR`]) &&
        mapa(taxas) && objeto(taxas) && ['carro', 'moto', 'onibus', 'ambulancia'].every((k) => finito(taxas[k]));
    });
}

export function lerInstantaneo(mensagem: string): Instantaneo {
  const v: unknown = JSON.parse(mensagem);
  if (!objeto(v) || !texto(v.run_id) || !Number.isSafeInteger(v.step) ||
      typeof v.step !== 'number' || v.step < 0 ||
      typeof v.simulation_time !== 'number' || !Number.isFinite(v.simulation_time) || v.simulation_time < 0 ||
      !(v.fase === null || texto(v.fase)) || !texto(v.estado_transicao) ||
      !objeto(v.ocupacoes) || !objeto(v.filas) || !Array.isArray(v.solicitacoes) ||
      !v.solicitacoes.every(objeto) || !texto(v.versao_configuracao) ||
      (v.demanda !== undefined && !demandaValida(v.demanda)) ||
      (v.metricas !== undefined && !metricasValidas(v.metricas)) ||
      (v.controle !== undefined && !controleValido(v.controle)) ||
      (['1.4', '1.5', '1.6', '1.7'].includes(v.versao_configuracao as string) && (v.controle === undefined || v.metricas === undefined || v.semaforos_pedestres === undefined)) ||
      (['1.5', '1.6', '1.7'].includes(v.versao_configuracao as string) && (!objeto(v.controle) || !configuracaoControladorValida(v.controle.configuracao_controlador))) ||
      (['1.6', '1.7'].includes(v.versao_configuracao as string) && (!objeto(v.controle) || !(v.controle.falha_controlador === null || texto(v.controle.falha_controlador)))) ||
      (v.versao_configuracao === '1.7' && (!objeto(v.controle) || !modelosNeurais.includes(v.controle.modelo_neural as string) || !disponibilidadeNeuralValida(v.controle.modelos_neurais))) ||
      (v.semaforos_pedestres !== undefined && (!objeto(v.semaforos_pedestres) || !['N-TR', 'S-TR', 'L-TR', 'O-TR'].every((m) => ['verde', 'vermelho'].includes((v.semaforos_pedestres as ObjetoJson)[m] as string)))) ||
      !objeto(v.semaforos) || !['N', 'S', 'L', 'O'].every((origem) => ['vermelho', 'amarelo', 'verde'].includes((v.semaforos as ObjetoJson)[origem] as string)) ||
      !Array.isArray(v.participantes) || !v.participantes.every(participante) ||
      new Set(v.participantes.map((p) => (p as ObjetoJson).id)).size !== v.participantes.length) {
    throw new Error('Instantâneo incompatível com o contrato da Seção 13.');
  }
  return v as unknown as Instantaneo;
}

export function lerMensagem(mensagem: string): Instantaneo | RespostaComando {
  const v: unknown = JSON.parse(mensagem);
  if (!objeto(v) || v.tipo !== 'confirmacao_comando') return lerInstantaneo(mensagem);
  const c = v.confirmacao;
  if (!(v.command_id === null || texto(v.command_id)) || !objeto(c) ||
      !(c.erro === null || texto(c.erro)) ||
      !((c.status === 'aplicado' && Number.isSafeInteger(c.passo_aplicacao) &&
        typeof c.passo_aplicacao === 'number' && c.passo_aplicacao >= 0 && c.erro === null) ||
        (c.status === 'rejeitado' && c.passo_aplicacao === null && texto(c.erro)))) {
    throw new Error('Confirmação de comando inválida.');
  }
  return v as unknown as RespostaComando;
}
