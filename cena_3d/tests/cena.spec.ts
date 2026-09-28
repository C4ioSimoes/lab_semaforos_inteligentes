import { expect, test, type WebSocketRoute } from '@playwright/test';

const instantaneo = (step: number, run_id = 'execucao-teste') => JSON.stringify({
  run_id, step, simulation_time: step / 10, fase: null, estado_transicao: 'nao_iniciado',
  ocupacoes: {}, filas: {}, solicitacoes: [], versao_configuracao: '1.2', participantes: [],
  semaforos: { N: 'vermelho', S: 'vermelho', L: 'vermelho', O: 'vermelho' },
});

test('mostra somente tempo do motor e rejeita estados antigos ou inválidos', async ({ page }) => {
  let socket: WebSocketRoute;
  const enviados: unknown[] = [];
  await page.routeWebSocket('**/ws', (ws) => {
    socket = ws;
    ws.onMessage((mensagem) => enviados.push(mensagem));
    ws.send(instantaneo(20));
  });
  await page.goto('/');
  await expect(page.locator('#passo')).toHaveText('20');
  await expect(page.locator('#tempo')).toHaveText('2,0');
  await expect(page.locator('.etiqueta-rua, .etiqueta-carro, .etiqueta-semaforo, .rotulos')).toHaveCount(0);
  socket!.send(instantaneo(19));
  socket!.send('{invalido');
  await expect(page.locator('#status')).toHaveAttribute('data-estado', 'erro');
  await expect(page.locator('#passo')).toHaveText('20');
  socket!.send(instantaneo(23));
  await expect(page.locator('#passo')).toHaveText('23');
  await expect(page.locator('#status')).toHaveAttribute('data-estado', 'desatualizado', { timeout: 6000 });
  await expect(page.locator('#tempo')).toHaveText('2,3');
  expect(enviados).toEqual([]);
});

test('ressincroniza após desconexão e aceita nova execução sem retornar à antiga', async ({ page }) => {
  let socket: WebSocketRoute;
  let conexoes = 0;
  await page.routeWebSocket('**/ws', (ws) => {
    socket = ws;
    conexoes++;
    ws.send(instantaneo(conexoes === 1 ? 50 : 55));
  });
  await page.goto('/');
  await expect(page.locator('#passo')).toHaveText('50');
  socket!.close();
  await expect(page.locator('#status')).toHaveAttribute('data-estado', 'desconectado');
  await expect(page.locator('#passo')).toHaveText('50');
  await expect(page.locator('#passo')).toHaveText('55');
  socket!.send(instantaneo(0, 'nova-execucao'));
  await expect(page.locator('#passo')).toHaveText('0');
  socket!.send(instantaneo(90));
  socket!.send(instantaneo(1, 'nova-execucao'));
  await expect(page.locator('#passo')).toHaveText('1');
  await expect(page.locator('#execucao')).toHaveText('nova-execucao');
});

test('câmera preserva centro, limita zoom e inclinação e restaura a vista', async ({ page }) => {
  await page.routeWebSocket('**/ws', (ws) => ws.send(instantaneo(0)));
  await page.goto('/');
  const resultado = await page.evaluate(async () => {
    // Exercita a mesma fábrica da aplicação em um canvas controlado pelo teste.
    const { criarCena } = await import('/src/cena.ts');
    const container = document.createElement('div');
    container.style.cssText = 'position:fixed;inset:0;width:800px;height:600px';
    document.body.append(container);
    const cena = criarCena(container);
    const { camera, controles } = cena;
    const inicial = camera.position.toArray();
    const canvas = container.querySelector('canvas')!;
    canvas.dispatchEvent(new WheelEvent('wheel', { deltaY: -100000, cancelable: true }));
    controles.update();
    const zoom = controles.getDistance();
    // Mesmo uma posição abaixo do solo é limitada na atualização orbital.
    camera.position.set(0, -20, 10);
    controles.update();
    const alturaMinima = camera.position.y;
    controles.target.set(8, 0, 8);
    controles.update();
    const alvo = controles.target.toArray();
    cena.vistaSuperior();
    const superior = camera.position.toArray();
    cena.restaurar();
    const restaurada = camera.position.toArray();
    const semPan = !controles.enablePan && !controles.zoomToCursor;
    cena.descartar();
    container.remove();
    return { inicial, restaurada, alvo, zoom, alturaMinima, superior, semPan };
  });
  expect(resultado.alvo).toEqual([0, 0, 0]);
  expect(resultado.semPan).toBe(true);
  expect(resultado.zoom).toBeGreaterThanOrEqual(25);
  expect(resultado.zoom).toBeLessThanOrEqual(110);
  expect(resultado.alturaMinima).toBeGreaterThan(0);
  expect(resultado.superior[1]).toBeCloseTo(85);
  expect(resultado.superior[0]).toBeCloseTo(0);
  expect(resultado.superior[2]).toBeCloseTo(0, 3);
  resultado.restaurada.forEach((valor, i) => expect(valor).toBeCloseTo(resultado.inicial[i]));
  await page.getByRole('button', { name: 'Vista superior' }).click();
  await page.getByRole('button', { name: 'Restaurar vista' }).click();
  await expect(page.locator('#erro-cena')).toBeHidden();
});

test('redimensiona a cena em tela estreita sem rolagem horizontal', async ({ page }) => {
  const erros: string[] = [];
  page.on('pageerror', (erro) => erros.push(erro.message));
  await page.routeWebSocket('**/ws', (ws) => ws.send(instantaneo(7)));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('#passo')).toHaveText('7');
  await expect(page.locator('#cena canvas')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Vista superior' }).click();
  expect(erros).toEqual([]);
});

test('separadores preservam rascunhos, funcionam por teclado e não enviam comandos', async ({ page }) => {
  const enviados: unknown[] = [];
  await page.routeWebSocket('**/ws', (ws) => {
    ws.send(instantaneo(0));
    ws.onMessage((mensagem) => enviados.push(mensagem));
  });
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  const paradigmas = page.getByRole('tab', { name: 'Paradigmas', exact: true });
  const neurais = page.getByRole('tab', { name: 'Redes neurais', exact: true });
  await page.getByLabel('Controlador', { exact: true }).selectOption('funcional');
  await page.getByLabel('Limiar de espera (s simulados)').fill('42');
  await neurais.click();
  await expect(neurais).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#painel-paradigmas')).toBeHidden();
  await expect(page.getByRole('tabpanel', { name: 'Redes neurais' })).toBeVisible();
  await expect(page.getByLabel('Modelo neural')).toBeDisabled();
  await expect(page.locator('#painel-neurais')).toContainText('Aguardando validação dos pesos pelo motor');
  await neurais.press('ArrowLeft');
  await expect(paradigmas).toBeFocused();
  await expect(page.locator('#limiar-espera')).toHaveValue('42');
  await expect(page.locator('#controlador')).toHaveValue('funcional');
  await expect(page.locator('#painel-neurais')).toBeHidden();
  await paradigmas.press('End');
  await expect(neurais).toBeFocused();
  await neurais.press('Home');
  await expect(paradigmas).toBeFocused();
  expect(enviados).toEqual([]);
});

test('canvas ocupa a maior parte do desktop e não gera rótulos ou erros gráficos', async ({ page }) => {
  const erros: string[] = [];
  page.on('pageerror', (erro) => erros.push(erro.message));
  page.on('console', (mensagem) => { if (mensagem.type() === 'error') erros.push(mensagem.text()); });
  await page.routeWebSocket('**/ws', (ws) => ws.send(instantaneo(0)));
  await page.goto('/');
  await expect(page.locator('#passo')).toHaveText('0');
  const canvas = await page.locator('#cena canvas').boundingBox();
  expect(canvas!.width).toBeGreaterThan(page.viewportSize()!.width * .65);
  expect(canvas!.height).toBeGreaterThan(page.viewportSize()!.height * .6);
  await expect(page.locator('.rotulos, .etiqueta-rua, .etiqueta-carro, .etiqueta-semaforo')).toHaveCount(0);
  await page.getByRole('button', { name: 'Vista superior' }).click();
  await page.getByRole('button', { name: 'Restaurar vista' }).click();
  expect(erros).toEqual([]);
});
