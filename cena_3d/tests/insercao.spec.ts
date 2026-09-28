import { expect, test, type WebSocketRoute } from '@playwright/test';

const carro = (id = 'carro-1') => ({
  id, categoria: 'carro', origem: 'L', destino: 'O', trajetoria: 'L-seguir_em_frente',
  posicao: { x: 28, y: 0.65, z: -4.5, rotacao_y: -Math.PI / 2 },
  estado: 'em_movimento', instante_solicitado: 0.1, instante_inserido: 0.1,
  solicitacao_prioritaria: false,
  dimensoes: { comprimento: 4, largura: 1.8, altura: 1.3 }, instante_inicio_espera: null,
});
const instantaneo = (step: number, participantes: ReturnType<typeof carro>[] = []) => JSON.stringify({
  run_id: 'teste', step, simulation_time: step / 10, fase: null,
  estado_transicao: 'nao_iniciado', ocupacoes: {}, filas: {}, solicitacoes: [],
  versao_configuracao: '1.2', participantes,
  semaforos: { N: 'vermelho', S: 'vermelho', L: 'vermelho', O: 'vermelho' },
});

test('copia coordenadas exatas, mantém posição entre ticks e substitui a execução', async ({ page }) => {
  await page.routeWebSocket('**/ws', (ws) => ws.send(instantaneo(0)));
  await page.goto('/');
  const resultado = await page.evaluate(async (participante) => {
    const { criarCamadaParticipantes } = await import('/src/participantes.ts');
    const camada = criarCamadaParticipantes();
    camada.atualizar('a', [participante]);
    const modelo = camada.grupo.getObjectByName(participante.id)!;
    const inicial = modelo.position.toArray();
    await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
    const entreTicks = modelo.position.toArray();
    camada.atualizar('a', [{ ...participante, posicao: { ...participante.posicao, x: 19.123456 } }]);
    const proxima = modelo.position.toArray();
    const rotacao = modelo.rotation.y;
    camada.atualizar('b', []);
    const restantes = camada.grupo.children.length;
    camada.descartar();
    return { inicial, entreTicks, proxima, rotacao, restantes };
  }, carro());
  expect(resultado.inicial).toEqual([28, 0.65, -4.5]);
  expect(resultado.entreTicks).toEqual(resultado.inicial);
  expect(resultado.proxima).toEqual([19.123456, 0.65, -4.5]);
  expect(resultado.rotacao).toBe(-Math.PI / 2);
  expect(resultado.restantes).toBe(0);
});

