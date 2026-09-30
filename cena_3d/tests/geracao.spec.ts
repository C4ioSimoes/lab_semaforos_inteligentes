import { expect, test, type Page, type WebSocketRoute } from '@playwright/test';
import { execFileSync } from 'node:child_process';

const inicial = JSON.parse(execFileSync('.venv/bin/python', ['-c',
  'from motor_python.motor import Motor; print(Motor().instantaneo().model_dump_json())'],
  { cwd: '..', encoding: 'utf8' }).toString());
async function preparar(page: Page) {
  let socket: WebSocketRoute;
  const comandos: any[] = [];
  let estado = structuredClone(inicial);
  let passo = 1;
  await page.routeWebSocket('**/ws', ws => {
    socket = ws; ws.send(JSON.stringify({ ...estado, step: passo, simulation_time: passo / 10 }));
    ws.onMessage(m => comandos.push(JSON.parse(String(m))));
  });
  await page.goto('/');
  await expect(page.getByRole('switch')).toBeEnabled();
  return {
    comandos,
    tick() { passo++; socket!.send(JSON.stringify({ ...estado, step: passo, simulation_time: passo / 10 })); },
    confirmar(i: number, aplicado = true) {
      const comando = comandos[i];
      socket!.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comando.command_id,
        confirmacao: { status: aplicado ? 'aplicado' : 'rejeitado', passo_aplicacao: aplicado ? passo + 1 : null, erro: aplicado ? null : 'Configuração rejeitada.' } }));
      if (aplicado) estado.demanda.configuracao = comando.parametros;
      this.tick();
    },
    desconectar() { socket!.close(); },
    reiniciar() { estado = structuredClone(inicial); estado.run_id = 'nova-execucao'; passo = 0; this.tick(); },
  };
}
async function intensidade(page: Page, valor: number) {
  await page.getByRole('slider', { name: 'Quantidade de trânsito', exact: true }).fill(String(valor));
  await page.getByRole('slider', { name: 'Quantidade de trânsito', exact: true }).dispatchEvent('change');
}

test('layout essencial e toggle controlam simultaneamente todas as fontes', async ({ page }) => {
  const motor = await preparar(page);
  await expect(page.locator('#form-insercao, #form-geracao, #taxas-origens')).toHaveCount(0);
  await expect(page.locator('#configuracoes-experimento')).not.toHaveAttribute('open');
  await expect(page.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
  await intensidade(page, 80);
  expect(motor.comandos).toHaveLength(0);
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(1);
  const c = motor.comandos[0].parametros;
  expect(c.fator_global).toBeCloseTo(1.68);
  expect(c.fator_pedestres).toBe(c.fator_global);
  for (const o of ['N', 'S', 'L', 'O']) {
    expect(Object.values(c.taxas_veiculares[o]).every(t => Number(t) > 0)).toBe(true);
    expect(c.taxas_pedestres[`${o}-TR`]).toBeGreaterThan(0);
  }
  motor.confirmar(0);
  await expect(page.getByRole('switch')).toHaveAttribute('aria-busy', 'false');
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(2);
  expect(motor.comandos[1].parametros.fator_global).toBe(0);
  expect(motor.comandos[1].parametros.fator_pedestres).toBe(0);
});

test('edições rápidas preservam a última intensidade e desligamento durante confirmação', async ({ page }) => {
  const motor = await preparar(page);
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(1);
  await intensidade(page, 70);
  await intensidade(page, 100);
  motor.tick();
  await expect(page.getByRole('slider', { name: 'Quantidade de trânsito', exact: true })).toHaveValue('100');
  motor.confirmar(0);
  await expect.poll(() => motor.comandos.length).toBe(2);
  expect(motor.comandos[1].parametros.fator_global).toBe(2);
  await page.getByRole('switch').click();
  motor.confirmar(1);
  await expect.poll(() => motor.comandos.length).toBe(3);
  expect(motor.comandos[2].parametros.fator_global).toBe(0);
  motor.confirmar(2);
  await expect(page.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
});

test('rejeição, desconexão e nova execução restauram o estado oficial', async ({ page }) => {
  const motor = await preparar(page);
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(1);
  motor.confirmar(0, false);
  await expect(page.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
  await expect(page.locator('#resultado-geracao')).toContainText('rejeitada');
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(2);
  motor.desconectar();
  await expect(page.getByRole('switch')).toBeDisabled();
  await expect(page.getByRole('switch')).toBeEnabled({ timeout: 5000 });
  await expect(page.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
  expect(motor.comandos).toHaveLength(2);
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(3);
  motor.confirmar(2);
  await expect(page.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
  motor.reiniciar();
  await expect(page.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
});

test('geração real muda intensidade e para novas chegadas sem apagar participantes', async ({ page }) => {
  const estados: any[] = [];
  page.on('websocket', ws => ws.on('framereceived', ({ payload }) => {
    const e = JSON.parse(String(payload)); if (e.participantes) estados.push(e);
  }));
  const ultimo = () => estados.at(-1);
  await page.goto('/');
  await expect(page.getByRole('switch')).toBeEnabled();
  await intensidade(page, 100);
  await page.getByRole('switch').click();
  await expect.poll(() => ultimo()?.demanda.configuracao.fator_global).toBe(2);
  await expect.poll(() => ultimo()?.demanda.solicitados.automatico, { timeout: 15000 }).toBeGreaterThan(3);
  await intensidade(page, 20);
  await expect.poll(() => ultimo()?.demanda.configuracao.fator_global).toBeCloseTo(.72);
  await page.screenshot({ path: '/tmp/transito-desktop.png' });
  await page.getByRole('switch').click();
  await expect.poll(() => ultimo()?.demanda.configuracao.fator_global).toBe(0);
  const parado = ultimo();
  expect(parado.participantes.length).toBeGreaterThan(0);
  await expect.poll(() => ultimo()?.step).toBeGreaterThan(parado.step + 5);
  expect(ultimo().demanda.solicitados.automatico).toBe(parado.demanda.solicitados.automatico);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '/tmp/transito-mobile.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('desligar pedestres mantém veículos e a escolha sobrevive a ajustes e reconexão', async ({ page }) => {
  const motor = await preparar(page);
  const pedestres = page.getByRole('checkbox', {name:'Incluir pedestres'});
  await expect(pedestres).toBeChecked();
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(1);
  motor.confirmar(0);
  await pedestres.uncheck();
  await expect.poll(() => motor.comandos.length).toBe(2);
  const anterior = motor.comandos[0].parametros, depois = motor.comandos[1].parametros;
  expect(depois.taxas_veiculares).toEqual(anterior.taxas_veiculares);
  expect(depois.fatores_locais).toEqual(anterior.fatores_locais);
  expect(depois.fator_global).toBe(anterior.fator_global);
  expect(depois.semente).toBe(anterior.semente);
  expect(depois.fator_pedestres).toBe(0);
  expect(Object.values(depois.taxas_pedestres)).toEqual([0,0,0,0]);
  motor.confirmar(1);
  await intensidade(page, 80);
  await expect.poll(() => motor.comandos.length).toBe(3);
  expect(motor.comandos[2].parametros.fator_global).toBeCloseTo(1.68);
  expect(motor.comandos[2].parametros.fator_pedestres).toBe(0);
  motor.confirmar(2);
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(4);
  motor.confirmar(3);
  await page.getByRole('switch').click();
  await expect.poll(() => motor.comandos.length).toBe(5);
  expect(motor.comandos[4].parametros.fator_pedestres).toBe(0);
  motor.confirmar(4);
  motor.desconectar();
  await expect(pedestres).toBeDisabled();
  await expect(pedestres).toBeEnabled();
  await expect(pedestres).not.toBeChecked();
  await pedestres.check();
  await expect.poll(() => motor.comandos.length).toBe(6);
  expect(motor.comandos[5].parametros.fator_pedestres).toBeCloseTo(1.68);
  expect(motor.comandos[5].parametros.taxas_veiculares).toEqual(anterior.taxas_veiculares);
  motor.confirmar(5);
  await expect(pedestres).toBeChecked();
});

test('pedestres desligados deixam de chegar no motor real e continuam desligados após reset', async ({ page }) => {
  const estados: any[] = [];
  page.on('websocket', ws => ws.on('framereceived', ({payload}) => {
    const e=JSON.parse(String(payload)); if(e.participantes) estados.push(e);
  }));
  const ultimo=()=>estados.at(-1);
  await page.goto('/');
  await expect(page.getByRole('switch')).toBeEnabled();
  await page.getByRole('button',{name:'Recomeçar simulação'}).click();
  await expect(page.locator('#resultado-reset')).toContainText('reiniciada');
  const velocidade=page.getByRole('slider',{name:'Velocidade da simulação'});
  await velocidade.fill('24'); await velocidade.dispatchEvent('change');
  await expect.poll(()=>ultimo()?.velocidade_simulacao).toBe(24);
  await intensidade(page,100);
  await page.getByRole('switch').click();
  await expect.poll(()=>ultimo()?.participantes.some((p:any)=>p.categoria==='pedestre')).toBe(true);
  await page.getByRole('checkbox',{name:'Incluir pedestres'}).uncheck();
  await expect.poll(()=>ultimo()?.demanda.configuracao.fator_pedestres).toBe(0);
  const corte=ultimo().step;
  expect(ultimo().demanda.configuracao.fator_global).toBe(2);
  await expect.poll(()=>ultimo()?.step,{timeout:5000}).toBeGreaterThan(corte+80);
  const dados=await (await page.request.get('http://127.0.0.1:8001/exportar/eventos')).json();
  expect(dados.eventos.some((e:any)=>e.tipo==='travessia_solicitada')).toBe(true);
  expect(dados.eventos.filter((e:any)=>e.tipo==='travessia_solicitada' && e.passo>corte)).toHaveLength(0);
  expect(dados.eventos.some((e:any)=>e.tipo==='insercao_solicitada' && e.passo>corte)).toBe(true);
  const execucao = ultimo().run_id;
  await page.getByRole('button',{name:'Recomeçar simulação'}).click();
  await expect.poll(()=>ultimo()?.run_id).not.toBe(execucao);
  await expect(page.getByRole('checkbox',{name:'Incluir pedestres'})).not.toBeChecked();
  // Restabelece o perfil padrão do servidor compartilhado pelos testes.
  await page.getByRole('checkbox',{name:'Incluir pedestres'}).check();
  await expect.poll(()=>ultimo()?.demanda.configuracao.fator_pedestres).toBe(2);
  await page.getByRole('switch').click();
  await expect.poll(()=>ultimo()?.demanda.configuracao.fator_global).toBe(0);
  await velocidade.fill('1'); await velocidade.dispatchEvent('change');
  await expect.poll(()=>ultimo()?.velocidade_simulacao).toBe(1);
});
