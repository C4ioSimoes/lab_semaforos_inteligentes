"""Transporte WebSocket e ciclo de vida do motor único por processo."""

import asyncio
import json
from contextlib import asynccontextmanager, suppress

from anyio import create_task_group
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .motor import Motor
from .exportacao import metricas_csv


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.motor = Motor()
    tarefa = asyncio.create_task(app.state.motor.executar(), name="relogio-oficial")
    try:
        yield
    finally:
        tarefa.cancel()
        try:
            with suppress(asyncio.CancelledError):
                await tarefa
        finally:
            app.state.motor.fechar()


app = FastAPI(title="Motor do Laboratório de Semáforos", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["GET"], expose_headers=["Content-Disposition"])


@app.get("/exportar/eventos")
async def exportar_eventos():
    dados = app.state.motor.exportar_experimento()
    return Response(json.dumps(dados, ensure_ascii=False, allow_nan=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="eventos-{dados["run_id"]}-passo-{dados["passo_exportacao"]}.json"'})


@app.get("/exportar/metricas")
async def exportar_metricas():
    dados = app.state.motor.exportar_experimento()
    return Response(metricas_csv(dados), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="metricas-{dados["run_id"]}-passo-{dados["passo_exportacao"]}.csv"'})


@app.websocket("/ws")
async def instantaneos(websocket: WebSocket) -> None:
    await websocket.accept()
    motor: Motor = websocket.app.state.motor
    fila = motor.assinar()

    async def enviar() -> None:
        while True:
            estado = await fila.get()
            if estado is None:
                await websocket.close(code=1013, reason="Cliente atrasado; reconecte para sincronizar")
                return
            await websocket.send_json(estado.model_dump(mode="json"))

    async def receber() -> None:
        while True:
            mensagem = await websocket.receive()
            if mensagem["type"] == "websocket.disconnect":
                return
            try:
                dados = json.loads(mensagem.get("text", ""))
            except (ValueError, TypeError):
                dados = None
            # Respostas e instantâneos compartilham uma fila e um único escritor.
            motor.receber_comando(dados, lambda resposta: motor.enfileirar(fila, resposta))

    try:
        async with create_task_group() as tarefas:
            async def enviar_ate_encerrar() -> None:
                try:
                    await enviar()
                except WebSocketDisconnect:
                    pass
                finally:
                    tarefas.cancel_scope.cancel()

            tarefas.start_soon(enviar_ate_encerrar)
            try:
                await receber()
            except WebSocketDisconnect:
                pass
            finally:
                tarefas.cancel_scope.cancel()
    finally:
        motor.desassinar(fila)
