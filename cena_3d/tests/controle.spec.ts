import { expect, test, type WebSocketRoute } from '@playwright/test';

const resumo = {
  concluidos: 2, ativos: 3, pendentes: 1, vazao_por_minuto: 6,
  espera_concluidos_interna_media: 3, espera_concluidos_externa_media: 1,
  espera_concluidos_total_media: 4, espera_ativos_interna_total: 12,
  espera_ativos_externa_total: 2, espera_pendentes_externa_total: 8,
  espera_pedestres_ate_autorizacao_total: 3,
};
const estado = (step: number, cor = 'verde') => ({
  run_id: 'controle', step, simulation_time: step / 10, fase: 'F-NS',
  estado_transicao: cor === 'verde' ? 'atendimento' : 'encerramento',
  ocupacoes: {}, filas: {}, solicitacoes: [], versao_configuracao: '1.4', participantes: [],
  semaforos: { N: cor, S: cor, L: 'vermelho', O: 'vermelho' },
  semaforos_pedestres: { 'N-TR': 'vermelho', 'S-TR': 'vermelho', 'L-TR': 'vermelho', 'O-TR': 'vermelho' },
  controle: {
    politica: 'fixa_referencia', estado: 'atendimento', inicio_passo: 10, decorrido_segundos: 9,
    sequencia: ['F-NS', 'F-LO', 'F-PED'], permissoes: ['N-seguir_em_frente', 'S-seguir_em_frente'], bloqueios: 0,
    tempos: { verde: 10, amarelo: 3, liberacao_minima: 1 }, validacao: { aceita: true, motivo: 'Tempo fixo de atendimento.' },
  },
  metricas: { intervalo_segundos: 20, chegadas_solicitadas: 6, limiar_velocidade_espera: 0.1,
    total: resumo, por_origem: { N: resumo }, por_categoria: { carro: resumo } },
});

test('sinais e métricas copiam o motor e permanecem estáveis sem ticks', async ({ page }) => {
  let socket: WebSocketRoute;
  await page.routeWebSocket('**/ws', (ws) => { socket = ws; ws.send(JSON.stringify(estado(100))); });
  await page.goto('/');
  const sinaisAcessiveis = page.locator('#situacao-cruzamento');
  await expect(sinaisAcessiveis).toContainText('N: verde');
  await expect(page.locator('#vazao')).toHaveText('6,0');
  await expect(page.locator('#espera-concluidos')).toHaveText('4,0 s');
  socket!.send(JSON.stringify(estado(110, 'amarelo')));
  await expect(sinaisAcessiveis).toContainText('N: amarelo');
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect(sinaisAcessiveis).toContainText('N: amarelo');
  await expect(page.locator('#tempo')).toHaveText('11,0');
  socket!.send(JSON.stringify(estado(111, 'azul')));
  await expect(page.locator('#status')).toHaveAttribute('data-estado', 'erro');
  await expect(sinaisAcessiveis).toContainText('N: amarelo');
  socket!.send(JSON.stringify({ ...estado(120), metricas: { ...estado(120).metricas, total: { ...resumo, vazao_por_minuto: null } } }));
  await expect(page.locator('#vazao')).toHaveText('6,0');
});

test('modelo do semáforo acende somente a lâmpada da cor oficial', async ({ page }) => {
  await page.routeWebSocket('**/ws', (ws) => ws.send(JSON.stringify(estado(100))));
  await page.goto('/');
  const materiais = await page.evaluate(async () => {
    const { criarSemaforos } = await import('/src/semaforos.ts');
    const camada = criarSemaforos();
    camada.atualizar({ semaforos: { N: 'amarelo', S: 'verde', L: 'vermelho', O: 'vermelho' } });
    const cores = ['vermelho', 'amarelo', 'verde'].map((c) => (camada.grupo.getObjectByName(`N-${c}`) as any).material.color.getHexString());
    camada.grupo.traverse((objeto: any) => { objeto.geometry?.dispose(); objeto.material?.dispose(); objeto.element?.remove(); });
    return cores;
  });
  expect(materiais).toEqual(['343434', 'ffce52', '343434']);
});
