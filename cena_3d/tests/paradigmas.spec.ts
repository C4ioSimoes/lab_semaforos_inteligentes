import { expect, test, type WebSocketRoute } from '@playwright/test';
import { execFileSync } from 'node:child_process';

// Um instantâneo real evita duplicar o contrato de diagnóstico neste teste.
const inicial = JSON.parse(execFileSync('.venv/bin/python', ['-c',
  'from motor_python.motor import Motor; print(Motor().instantaneo().model_dump_json())'],
  { cwd: '..', encoding: 'utf8' }).toString());
const configuracao = inicial.controle.configuracao_controlador;
const estado = (step: number, config = configuracao) => JSON.stringify({ ...inicial, step, simulation_time: step / 10,
  controle: { ...inicial.controle, configuracao_controlador: config } });

test('seletor envia comando e não altera diagnóstico antes da confirmação oficial', async ({ page }) => {
  const comandos: any[] = [];
  let socket: WebSocketRoute;
  await page.routeWebSocket('**/ws', (ws) => {
    socket = ws; ws.send(estado(1));
    ws.onMessage((msg) => comandos.push(JSON.parse(String(msg))));
  });
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await expect(page.locator('#aplicar-controlador')).toBeEnabled();
  await expect(page.locator('#limiar-espera')).toBeDisabled();
  await page.getByLabel('Controlador', { exact: true }).selectOption('funcional');
  await page.getByLabel('Limiar de espera (s simulados)').fill('25');
  await page.getByLabel('Atender emergências').uncheck();
  await page.getByLabel('Priorizar ônibus').check();
  socket!.send(estado(2));
  await expect(page.locator('#passo')).toHaveText('2');
  await expect(page.locator('#limiar-espera')).toHaveValue('25');
  await page.getByRole('button', { name: 'Aplicar controlador' }).click();
  await expect.poll(() => comandos.length).toBe(1);
  expect(comandos[0].tipo).toBe('configurar_controlador');
  expect(comandos[0].parametros).toEqual({ controlador: 'funcional', limiar_espera: 25, prioridade_ambulancia: false, prioridade_onibus: true });
  await expect(page.locator('#estado-controle')).toContainText('Política fixa');
  socket!.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comandos[0].command_id,
    confirmacao: { status: 'aplicado', passo_aplicacao: 3, erro: null } }));
  socket!.send(estado(3, comandos[0].parametros));
  await expect(page.locator('#estado-controle')).toContainText('Funcional');
  socket!.close();
  await expect(page.locator('#aplicar-controlador')).toBeDisabled();
});

test('confirmação atrasada preserva edição posterior e rejeição exibe motivo', async ({ page }) => {
  let socket: WebSocketRoute;
  const comandos: any[] = [];
  await page.routeWebSocket('**/ws', (ws) => {
    socket = ws; ws.send(estado(1));
    ws.onMessage((msg) => comandos.push(JSON.parse(String(msg))));
  });
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.getByLabel('Controlador', { exact: true }).selectOption('imperativo');
  await page.getByRole('button', { name: 'Aplicar controlador' }).click();
  await expect.poll(() => comandos.length).toBe(1);
  await page.locator('#limiar-espera').fill('45');
  socket!.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comandos[0].command_id,
    confirmacao: { status: 'aplicado', passo_aplicacao: 2, erro: null } }));
  socket!.send(estado(2, comandos[0].parametros));
  await expect(page.locator('#passo')).toHaveText('2');
  await expect(page.locator('#limiar-espera')).toHaveValue('45');
  await page.getByRole('button', { name: 'Aplicar controlador' }).click();
  await expect.poll(() => comandos.length).toBe(2);
  socket!.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comandos[1].command_id,
    confirmacao: { status: 'rejeitado', passo_aplicacao: null, erro: 'Configuração inválida.' } }));
  await expect(page.locator('#resultado-controlador')).toContainText('Configuração inválida');
  socket!.send(estado(3, { ...configuracao, controlador: 'desconhecido' }));
  await expect(page.locator('#status')).toHaveAttribute('data-estado', 'erro');
  await expect(page.locator('#passo')).toHaveText('2');
  const bloqueado = JSON.parse(estado(4, comandos[0].parametros));
  bloqueado.controle.validacao = { aceita: false, motivo: 'Proposta desconhecida ou fase não prevista.' };
  bloqueado.controle.decisao = { step: 4, controlador: 'imperativo', motivos: ['Proposta inválida'],
    proposta: { acao: 'acao_desconhecida', fase: 'F-LO', motivo: 'Teste de validação do motor' }, avaliacoes: [] };
  socket!.send(JSON.stringify(bloqueado));
  await expect(page.locator('#status')).toHaveAttribute('data-estado', 'conectado');
  await expect(page.locator('#validacao-controle')).toContainText('Proposta desconhecida');
  await expect(page.locator('#decisao-controlador')).toContainText('acao_desconhecida');
});

test('Prolog confirma seleção e mostra falha oficial sem substituir controlador', async ({ page }) => {
  let socket: WebSocketRoute;
  const comandos: any[] = [];
  await page.routeWebSocket('**/ws', (ws) => {
    socket = ws; ws.send(estado(1));
    ws.onMessage((msg) => comandos.push(JSON.parse(String(msg))));
  });
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.getByLabel('Controlador', { exact: true }).selectOption('logico');
  await page.getByRole('button', { name: 'Aplicar controlador' }).click();
  await expect.poll(() => comandos.length).toBe(1);
  expect(comandos[0].parametros.controlador).toBe('logico');
  await expect(page.locator('#estado-controle')).toContainText('Política fixa');
  socket!.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comandos[0].command_id,
    confirmacao: { status: 'aplicado', passo_aplicacao: 2, erro: null } }));
  socket!.send(estado(2, comandos[0].parametros));
  await expect(page.locator('#estado-controle')).toContainText('Lógico (Prolog)');
  const falha = JSON.parse(estado(3, comandos[0].parametros));
  falha.controle.falha_controlador = 'Falha SWI-Prolog/MQI. Execução interrompida; reinicie o motor.';
  falha.demanda.motivo_interrupcao = falha.controle.falha_controlador;
  falha.controle.decisao = null;
  socket!.send(JSON.stringify(falha));
  await expect(page.locator('#falha-controlador')).toBeVisible();
  await expect(page.locator('#falha-controlador')).toContainText('SWI-Prolog/MQI');
  await expect(page.locator('#controlador')).toHaveValue('logico');
  await expect(page.locator('#aplicar-controlador')).toBeDisabled();
  await expect(page.getByRole('switch')).toBeDisabled();
  await expect(page.locator('#estado-controle')).toContainText('Lógico (Prolog)');
  await expect(page.locator('#decisao-controlador')).toBeEmpty();
});

test('ativação Prolog rejeitada mantém identificação do controlador ativo', async ({ page }) => {
  await page.routeWebSocket('**/ws', (ws) => {
    ws.send(estado(1));
    ws.onMessage((msg) => {
      const comando = JSON.parse(String(msg));
      const erro = 'Falha ao iniciar SWI-Prolog/MQI. Seleção rejeitada; controlador ativo permanece baseline.';
      ws.send(JSON.stringify({ tipo: 'confirmacao_comando', command_id: comando.command_id,
        confirmacao: { status: 'rejeitado', passo_aplicacao: null, erro } }));
      const rejeitado = JSON.parse(estado(2));
      rejeitado.controle.falha_controlador = erro;
      ws.send(JSON.stringify(rejeitado));
    });
  });
  await page.goto('/');
  await page.locator('#configuracoes-experimento > summary').click();
  await page.getByLabel('Controlador', { exact: true }).selectOption('logico');
  await page.getByRole('button', { name: 'Aplicar controlador' }).click();
  await expect(page.locator('#resultado-controlador')).toContainText('Seleção rejeitada');
  await expect(page.locator('#falha-controlador')).toContainText('ativo permanece baseline');
  await expect(page.locator('#estado-controle')).toContainText('Política fixa');
  await expect(page.locator('#aplicar-controlador')).toBeEnabled();
});
