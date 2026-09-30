import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
const inicial = JSON.parse(execFileSync('.venv/bin/python', ['-c',
  'from motor_python.motor import Motor; m=Motor(); print(m.avancar().model_dump_json())'],
  { cwd: '..', encoding: 'utf8' }).toString());

test('reset aguarda nova execução, trata rejeição e não envia cliques duplicados', async ({page}) => {
  let socket: any;
  const comandos: any[]=[];
  await page.routeWebSocket('**/ws', ws=>{socket=ws; ws.send(JSON.stringify(inicial));ws.onMessage(m=>comandos.push(JSON.parse(String(m))));});
  await page.goto('/');
  const botao=page.getByRole('button',{name:'Recomeçar simulação',exact:true});
  await expect(botao).toBeEnabled();
  await botao.click();
  await expect(botao).toBeDisabled();
  await expect.poll(()=>comandos.length).toBe(1);
  expect(comandos[0]).toMatchObject({tipo:'resetar_simulacao',parametros:{}});
  socket.send(JSON.stringify({tipo:'confirmacao_comando',command_id:comandos[0].command_id,confirmacao:{status:'rejeitado',passo_aplicacao:null,erro:'Falha no controlador'}}));
  await expect(page.locator('#resultado-reset')).toContainText('Falha no controlador');
  await expect(botao).toBeEnabled();
  await botao.click();
  await expect.poll(()=>comandos.length).toBe(2);
  socket.send(JSON.stringify({tipo:'confirmacao_comando',command_id:comandos[1].command_id,confirmacao:{status:'aplicado',passo_aplicacao:0,erro:null}}));
  await expect(botao).toBeDisabled();
  const novo=structuredClone(inicial);novo.run_id='apos-reset';novo.step=0;novo.simulation_time=0;
  socket.send(JSON.stringify(novo));
  await expect(page.locator('#tempo')).toHaveText('0,0');
  await expect(botao).toBeEnabled();
  socket.close();
  await expect(botao).toBeDisabled();
});

test('reset real mantém modo urbano e reinicia o relógio sem recarregar a página', async ({page}) => {
  await page.goto('/');
  await expect(page.locator('#status')).toHaveText('Conectado');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.getByRole('tab',{name:'Automático',exact:true}).click();
  await page.getByRole('button',{name:'Ativar automático',exact:true}).click();
  await expect(page.locator('#modo-ativo')).toContainText('Controle: Automático');
  const run=await page.locator('#execucao').textContent();
  await page.evaluate(()=>{(window as any).__marcadorReset='preservado';});
  await page.getByRole('button',{name:'Recomeçar simulação',exact:true}).click();
  await expect(page.locator('#resultado-reset')).toContainText('Simulação reiniciada');
  await expect(page.locator('#execucao')).not.toHaveText(run!);
  expect(Number(await page.locator('#passo').textContent())).toBeLessThan(20);
  await expect(page.locator('#modo-ativo')).toContainText('Controle: Automático');
  expect(await page.evaluate(()=>(window as any).__marcadorReset)).toBe('preservado');
  await expect(page.locator('#resetar-simulacao')).toBeEnabled();
  // Deixa a política padrão para outros testes do mesmo servidor.
  await page.getByRole('tab',{name:'Regras',exact:true}).click();
  await page.getByLabel('Tipo de regra',{exact:true}).selectOption('baseline');
  await page.getByRole('button',{name:'Ativar regras',exact:true}).click();
  await expect(page.locator('#modo-ativo')).toContainText('Controle: Regras');
});
