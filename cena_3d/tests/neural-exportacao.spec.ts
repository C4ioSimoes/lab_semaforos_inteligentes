import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';

const inicial = JSON.parse(execFileSync('.venv/bin/python', ['-c',
  'from motor_python.motor import Motor; m=Motor(); print(m.avancar().model_dump_json())'],
  { cwd: '..', encoding: 'utf8' }).toString());

test('seleção neural usa confirmação oficial e mostra divergências de modelos inválidos', async ({ page }) => {
  let socket: any;
  const comandos: any[] = [];
  const estado = structuredClone(inicial);
  estado.controle.modelos_neurais.adaline.disponivel = false;
  estado.controle.modelos_neurais.adaline.erro = 'Os pesos divergem da AND; ativação impedida.';
  estado.controle.modelos_neurais.adaline.verificacao_and[2].divergencia = true;
  await page.routeWebSocket('**/ws', ws => {
    socket = ws; ws.send(JSON.stringify(estado)); ws.onMessage(m => comandos.push(JSON.parse(String(m))));
  });
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.locator('#estudo-and > summary').click();
  await expect(page.getByLabel('Modelo do exercício AND')).toBeEnabled();
  await expect(page.locator('#modelo-neural option[value="adaline"]')).toBeDisabled();
  await expect(page.locator('#validacao-neural')).toContainText('Divergência: x=[1, 0]');
  await page.getByLabel('Modelo do exercício AND').selectOption('perceptron');
  await page.getByRole('button', { name: 'Aplicar ao exercício' }).click();
  await expect.poll(() => comandos.length).toBe(1);
  expect(comandos[0].parametros).toEqual({ modelo: 'perceptron' });
  await expect(page.locator('#avaliador-atual')).toHaveText('AND de referência');
  socket.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comandos[0].command_id,
    confirmacao: { status: 'rejeitado', passo_aplicacao: null, erro: 'Pesos inválidos no motor.' } }));
  await expect(page.locator('#resultado-neural')).toContainText('Pesos inválidos');
  await expect(page.locator('#avaliador-atual')).toHaveText('AND de referência');
  socket.close();
  await expect(page.locator('#aplicar-neural')).toBeDisabled();
  await expect(page.locator('#exportar-eventos')).toBeDisabled();
});

test('integração real seleciona modelos, exibe cálculos e baixa JSON e CSV', async ({ page }) => {
  test.setTimeout(60000);
  const erros: string[] = [];
  page.on('pageerror', erro => erros.push(erro.message));
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await expect(page.locator('#status')).toHaveText('Conectado');
  await page.locator('#estudo-and > summary').click();
  for (const [modelo, nome] of [['perceptron', 'Perceptron'], ['adaline', 'Adaline'], ['AND_referencia', 'AND de referência']]) {
    await page.getByLabel('Modelo do exercício AND').selectOption(modelo);
    await page.getByRole('button', { name: 'Aplicar ao exercício' }).click();
    await expect(page.locator('#resultado-neural')).toContainText('Configuração aplicada.');
    await expect(page.locator('#avaliador-atual')).toHaveText(nome);
    await expect(page.locator('#neural-instante')).toContainText(nome);
    await expect(page.locator('.calculo-neural')).toHaveCount(3);
    await expect(page.locator('#diagnostico-neural')).toContainText('AND de referência');
    if (modelo !== 'AND_referencia') await expect(page.locator('#diagnostico-neural')).toContainText('w0=');
  }
  await page.locator('#salvar-resultados > summary').click();
  const jsonDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Baixar histórico (JSON)' }).click();
  const json = await jsonDownload;
  const dados = JSON.parse(await readFile((await json.path())!, 'utf8'));
  expect(dados.configuracao_atual.modelo_neural).toBe('AND_referencia');
  expect(dados.eventos.some((e: any) => e.tipo === 'modelo_neural_configurado')).toBe(true);
  expect(dados.pesos_treinados.perceptron.pesos).toHaveLength(3);
  const csvDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Baixar planilha (CSV)' }).click();
  const csv = await csvDownload;
  const texto = await readFile((await csv.path())!, 'utf8');
  expect(texto).toContain('espera_pendentes_externa_total');
  expect(texto).toContain('vazao_por_minuto');
  expect(texto).toContain(dados.run_id);
  await expect(page.locator('#resultado-exportacao')).toContainText('Métricas exportadas');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(erros).toEqual([]);
});

test('falha de download permite tentar novamente', async ({ page }) => {
  await page.routeWebSocket('**/ws', ws => ws.send(JSON.stringify(inicial)));
  await page.route('**/exportar/eventos', route => route.fulfill({ status: 500, body: 'falha', headers: { 'Access-Control-Allow-Origin': '*' } }));
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.locator('#salvar-resultados > summary').click();
  await page.getByRole('button', { name: 'Baixar histórico (JSON)' }).click();
  await expect(page.locator('#resultado-exportacao')).toContainText('HTTP 500');
  await expect(page.locator('#exportar-eventos')).toBeEnabled();
});
