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
  await page.getByRole('tab', {name:'Semáforo urbano',exact:true}).click();
  expect(comandos).toHaveLength(0);
  await expect(page.locator('#modo-ativo')).toContainText('Modo ativo: Paradigmas');
  await page.getByRole('button',{name:'Ativar semáforo urbano',exact:true}).click();
  await expect.poll(() => comandos.length).toBe(1);
  expect(comandos[0].parametros).toEqual({modo:'urbano'});
  await expect(page.locator('#modo-ativo')).toContainText('Modo ativo: Paradigmas');
  const estado=structuredClone(inicial); estado.step++; estado.controle.operacao.modo='urbano';
  socket.send(JSON.stringify(estado));
  await expect(page.locator('#modo-ativo')).toContainText('Modo ativo: Semáforo urbano');
  socket.close();
  await expect(page.locator('#ativar-urbano')).toBeDisabled();
});

test('aplicação real alterna os dois modelos e volta aos paradigmas', async ({ page }) => {
  test.setTimeout(60000);
  const erros: string[]=[]; page.on('pageerror',e=>erros.push(e.message));
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await expect(page.locator('#status')).toHaveText('Conectado');
  await page.getByRole('tab',{name:'Redes neurais',exact:true}).click();
  for(const modelo of ['perceptron','adaline']) {
    await page.getByLabel('Rede aplicada ao trânsito').selectOption(modelo);
    await page.getByRole('button',{name:'Ativar rede no trânsito',exact:true}).click();
    await expect(page.locator('#resultado-neural-transito')).toContainText('Pedido aplicado');
    await expect(page.locator('#modo-ativo')).toContainText(`Rede aplicada — ${modelo}`);
    await expect(page.locator('#treinamento-transito')).toContainText('preferências sintéticas');
  }
  await page.getByRole('tab',{name:'Semáforo urbano',exact:true}).click();
  await page.getByRole('button',{name:'Ativar semáforo urbano',exact:true}).click();
  await expect(page.locator('#modo-ativo')).toContainText('Modo ativo: Semáforo urbano');
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('tab',{name:'Paradigmas',exact:true}).click();
  await page.getByLabel('Controlador',{exact:true}).selectOption('imperativo');
  await page.getByRole('button',{name:'Aplicar controlador',exact:true}).click();
  await expect(page.locator('#modo-ativo')).toContainText('Modo ativo: Paradigmas');
  expect(erros).toEqual([]);
});

test('comparação mostra métricas medidas e explica horizonte da espera', async ({ page }) => {
  await page.routeWebSocket('**/ws', ws => ws.send(JSON.stringify(inicial)));
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.getByRole('tab',{name:'Semáforo urbano',exact:true}).click();
  await page.getByRole('button',{name:'Ver comparação medida',exact:true}).click();
  await expect(page.locator('#comparacao-transito table tbody tr')).toHaveCount(15);
  await expect(page.locator('#comparacao-transito')).toContainText('Médias de 3 sementes');
  await expect(page.locator('#comparacao-transito')).toContainText('Não inclui espera futura');
});
