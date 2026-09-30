import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
const inicial = JSON.parse(execFileSync('.venv/bin/python', ['-c',
  'from motor_python.motor import Motor; print(Motor().instantaneo().model_dump_json())'],
  { cwd: '..', encoding: 'utf8' }).toString());

test('velocidade acompanha o motor, preserva a última edição e trata rejeição e reconexão', async ({ page }) => {
  let socket: any;
  const comandos: any[] = [];
  const estado = structuredClone(inicial);
  await page.routeWebSocket('**/ws', ws => {
    socket = ws; ws.send(JSON.stringify(estado)); ws.onMessage(m => comandos.push(JSON.parse(String(m))));
  });
  await page.goto('/');
  const slider = page.getByRole('slider', { name: 'Velocidade da simulação', exact: true });
  const alterar = async (v: string) => { await slider.fill(v); await slider.dispatchEvent('change'); };
  const confirmar = (i: number, aplicado = true) => {
    socket.send(JSON.stringify({tipo:'confirmacao_comando',command_id:comandos[i].command_id,
      confirmacao:{status:aplicado?'aplicado':'rejeitado',passo_aplicacao:aplicado?estado.step+1:null,erro:aplicado?null:'Velocidade rejeitada.'}}));
    if(aplicado) estado.velocidade_simulacao = comandos[i].parametros.multiplicador;
    estado.step++; estado.simulation_time = estado.step / 10;
    socket.send(JSON.stringify(estado));
  };
  await expect(slider).toHaveValue('1');
  const quantidade = await page.getByRole('slider', { name: 'Quantidade de trânsito' }).boundingBox();
  const velocidade = await slider.boundingBox();
  expect(velocidade!.y).toBeGreaterThan(quantidade!.y);
  await alterar('24');
  await expect.poll(() => comandos.length).toBe(1);
  expect(comandos[0]).toMatchObject({tipo:'configurar_velocidade',parametros:{multiplicador:24}});
  await alterar('12');
  confirmar(0);
  await expect.poll(() => comandos.length).toBe(2);
  expect(comandos[1].parametros.multiplicador).toBe(12);
  confirmar(1);
  await expect(slider).toHaveValue('12');
  await expect(page.locator('#resultado-velocidade')).toHaveText('Ativa: 12×');
  await alterar('2');
  await expect.poll(() => comandos.length).toBe(3);
  confirmar(2, false);
  await expect(slider).toHaveValue('12');
  await expect(page.locator('#resultado-velocidade')).toContainText('rejeitada');
  socket.close();
  await expect(slider).toBeDisabled();
  await expect(slider).toBeEnabled();
  await expect(slider).toHaveValue('12');
  estado.run_id = 'nova-execucao'; estado.step = 0; estado.simulation_time = 0; estado.velocidade_simulacao = 1;
  socket.send(JSON.stringify(estado));
  await expect(slider).toHaveValue('1');
  expect(comandos).toHaveLength(3);
});

test('24× acelera o relógio real, mantém a conexão e o reset preserva a velocidade', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#status')).toHaveText('Conectado');
  const slider = page.getByRole('slider', { name: 'Velocidade da simulação' });
  await slider.fill('24'); await slider.dispatchEvent('change');
  await expect(page.locator('#resultado-velocidade')).toHaveText('Ativa: 24×');
  const passo = Number(await page.locator('#passo').textContent());
  await expect.poll(async () => Number(await page.locator('#passo').textContent()), {timeout: 3000}).toBeGreaterThan(passo + 24);
  await page.getByRole('button', { name: 'Recomeçar simulação' }).click();
  await expect(page.locator('#resultado-reset')).toContainText('reiniciada');
  await expect(slider).toHaveValue('24');
  await expect(page.locator('#status')).toHaveText('Conectado');
  await slider.fill('1'); await slider.dispatchEvent('change');
  await expect(page.locator('#resultado-velocidade')).toHaveText('Ativa: 1×');
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
