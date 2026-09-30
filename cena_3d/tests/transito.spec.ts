import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
const inicial = JSON.parse(execFileSync('.venv/bin/python', ['-c',
  'from motor_python.motor import Motor; m=Motor(); print(m.avancar().model_dump_json())'],
  { cwd: '..', encoding: 'utf8' }).toString());

test('abas não ativam políticas; ativação urbana é explícita e sincronizada', async ({ page }) => {
  let socket: any;
  const comandos: any[] = [];
  await page.routeWebSocket('**/ws', ws => {socket=ws; ws.send(JSON.stringify(inicial)); ws.onMessage(m => comandos.push(JSON.parse(String(m))));});
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.getByRole('tab', {name:'Automático',exact:true}).click();
  expect(comandos).toHaveLength(0);
  await expect(page.locator('#modo-ativo')).toContainText('Controle: Regras');
  await page.getByRole('button',{name:'Ativar automático',exact:true}).click();
  await expect.poll(() => comandos.length).toBe(1);
  expect(comandos[0].parametros).toEqual({modo:'urbano'});
  await expect(page.locator('#modo-ativo')).toContainText('Controle: Regras');
  const estado=structuredClone(inicial); estado.step++; estado.controle.operacao.modo='urbano';
  socket.send(JSON.stringify(estado));
  await expect(page.locator('#modo-ativo')).toContainText('Controle: Automático');
  socket.close();
  await expect(page.locator('#ativar-urbano')).toBeDisabled();
});

test('aplicação real alterna os dois modelos e volta aos paradigmas', async ({ page }) => {
  test.setTimeout(60000);
  const erros: string[]=[]; page.on('pageerror',e=>erros.push(e.message));
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await expect(page.locator('#status')).toHaveText('Conectado');
  await page.getByRole('tab',{name:'Rede neural',exact:true}).click();
  for(const modelo of ['perceptron','adaline']) {
    await page.getByLabel('Rede para controlar o trânsito').selectOption(modelo);
    await page.getByRole('button',{name:'Ativar rede neural',exact:true}).click();
    await expect(page.locator('#resultado-neural-transito')).toContainText('Configuração aplicada.');
    await expect(page.locator('#modo-ativo')).toContainText(`Rede neural · ${modelo === 'perceptron' ? 'Perceptron' : 'Adaline'}`);
    await expect(page.locator('#treinamento-transito')).toContainText('teste sintético');
  }
  await page.getByRole('tab',{name:'Automático',exact:true}).click();
  await page.getByRole('button',{name:'Ativar automático',exact:true}).click();
  await expect(page.locator('#modo-ativo')).toContainText('Controle: Automático');
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button', {name:'Dados', exact:true}).click();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('tab',{name:'Regras',exact:true}).click();
  await page.getByLabel('Tipo de regra',{exact:true}).selectOption('imperativo');
  await page.getByRole('button',{name:'Ativar regras',exact:true}).click();
  await expect(page.locator('#modo-ativo')).toContainText('Controle: Regras');
  expect(erros).toEqual([]);
});

test('comparação mostra métricas medidas e explica horizonte da espera', async ({ page }) => {
  await page.routeWebSocket('**/ws', ws => ws.send(JSON.stringify(inicial)));
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.getByRole('tab',{name:'Automático',exact:true}).click();
  await page.locator('#ensaios > summary').click();
  await page.getByRole('button',{name:'Carregar comparação',exact:true}).click();
  await expect(page.locator('#comparacao-transito table tbody tr')).toHaveCount(15);
  await expect(page.locator('#comparacao-transito')).toContainText('Média de 3 repetições');
  await expect(page.locator('#comparacao-transito')).toContainText('Não inclui espera futura');
});

test('rede ativa é sincronizada; rascunhos e exercício AND não se confundem', async ({ page }) => {
  let socket: any;
  const comandos: any[] = [];
  const estado = structuredClone(inicial);
  estado.controle.operacao = { modo: 'neural', modelo: 'adaline' };
  await page.routeWebSocket('**/ws', ws => {
    socket = ws; ws.send(JSON.stringify(estado));
    ws.onMessage(m => comandos.push(JSON.parse(String(m))));
  });
  await page.goto('/');
  // O modo ativo fica visível mesmo com as configurações recolhidas.
  await expect(page.locator('#modo-ativo')).toBeVisible();
  await expect(page.locator('#modo-ativo')).toHaveText('Controle: Rede neural · Adaline');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.getByRole('tab', { name: 'Rede neural', exact: true }).click();
  const seletor = page.getByLabel('Rede para controlar o trânsito');
  await expect(seletor).toHaveValue('adaline');
  await expect(page.locator('#painel-neurais select:visible')).toHaveCount(1);
  await expect(page.locator('#calculo-transito')).toBeHidden();
  await seletor.selectOption('perceptron');
  await expect(page.locator('#modo-ativo')).toHaveText('Controle: Rede neural · Adaline');
  expect(comandos).toHaveLength(0);
  await page.getByRole('button', { name: 'Ativar rede neural', exact: true }).click();
  await expect.poll(() => comandos.length).toBe(1);
  await expect(page.locator('#ativar-neural-transito')).toBeDisabled();
  await seletor.selectOption('adaline');
  socket.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comandos[0].command_id,
    confirmacao: { status: 'aplicado', passo_aplicacao: estado.step + 1, erro: null } }));
  estado.step++; estado.controle.operacao.modelo = 'perceptron';
  socket.send(JSON.stringify(estado));
  await expect(page.locator('#modo-ativo')).toHaveText('Controle: Rede neural · Perceptron');
  await expect(seletor).toHaveValue('adaline');
  await expect(page.locator('#resultado-neural-transito')).toContainText('Nova escolha pendente');
  await page.getByRole('button', { name: 'Ativar rede neural', exact: true }).click();
  await expect.poll(() => comandos.length).toBe(2);
  socket.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comandos[1].command_id,
    confirmacao: { status: 'rejeitado', passo_aplicacao: null, erro: 'Modelo indisponível.' } }));
  await expect(seletor).toHaveValue('perceptron');
  await expect(page.locator('#resultado-neural-transito')).toContainText('Modelo indisponível');
  await expect(page.locator('#ativar-neural-transito')).toBeEnabled();
  await page.getByRole('tab', { name: 'Regras', exact: true }).click();
  await page.locator('#estudo-and > summary').click();
  await expect(page.getByLabel('Modelo do exercício AND')).toBeDisabled();
  await expect(page.locator('#estado-and')).toContainText('Inativo');
  expect(comandos).toHaveLength(2);
  estado.step++; estado.controle.operacao.modo = 'paradigmas';
  socket.send(JSON.stringify(estado));
  await expect(page.getByLabel('Modelo do exercício AND')).toBeEnabled();
  await expect(page.locator('#estado-and')).toContainText('Usado apenas em Regras');
});
