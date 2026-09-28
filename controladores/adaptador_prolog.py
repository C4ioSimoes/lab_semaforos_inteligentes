"""Transporte MQI persistente e conversão de contratos, sem política em Python."""
from contextlib import contextmanager, suppress
from dataclasses import asdict
import json
import os
from pathlib import Path
from threading import Event, Timer
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contratos import Avaliacao, Decisao, Estado, Proposta


class FalhaProlog(RuntimeError):
    """Falha explícita de dependência, sessão, consulta ou contrato Prolog."""


class _Contrato(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class _Proposta(_Contrato):
    acao: Literal['manter', 'transicionar', 'aguardar']
    fase: str | None
    motivo: str


class _Avaliacao(_Contrato):
    fase: str
    demanda: int = Field(ge=0)
    maior_espera: float = Field(ge=0)
    criterio: Literal['emergencia', 'limiar_espera', 'onibus', 'maior_demanda', 'sem_demanda']
    chave: tuple[int, float, float, str]
    admissivel: bool
    bloqueio: str | None


class _Decisao(_Contrato):
    proposta: _Proposta
    avaliacoes: list[_Avaliacao]
    criterio: Literal['emergencia', 'limiar_espera', 'onibus', 'maior_demanda', 'sem_demanda']


class AdaptadorProlog:
    """Uma instância SWI e uma conexão por controlador, até troca ou shutdown.

    A consulta tem limite no SWI; o watchdog cobre também travamento do processo
    e do transporte, que query_timeout_seconds sozinho não interrompe.
    Uma sessão que falhou nunca reconecta ou muda de algoritmo implicitamente.
    """
    def __init__(self, *, timeout_consulta: float = 1.0, timeout_comunicacao: float = 3.0,
                 timeout_inicio: float = 5.0):
        self._mqi = None
        self._thread = None
        self._fechado = False
        self.timeout_consulta = timeout_consulta
        self.timeout_comunicacao = timeout_comunicacao
        try:
            from swiplserver import PrologMQI
            self._mqi = PrologMQI(query_timeout_seconds=timeout_consulta,
                                  unix_domain_socket='' if os.name == 'posix' else None)
            with self._prazo(timeout_inicio):
                self._mqi.start()
                self._thread = self._mqi.create_thread()
                self._thread.start()
                arquivo = str(Path(__file__).with_name('logico.pl').resolve())
                # String Prolog escapada, inclusive aspas e barras; nunca código
                # vindo de IDs, caminhos ou parâmetros fornecidos pelo cliente.
                if self._thread.query(f'load_files({json.dumps(arquivo, ensure_ascii=False)}, [silent(true)])') is not True:
                    raise ValueError('Não foi possível carregar logico.pl.')
                if self._thread.query('current_predicate(logico:decidir_json/2)') is not True:
                    raise ValueError('Predicado decidir_json/2 ausente.')
        except Exception as erro:
            self.fechar()
            raise FalhaProlog(f'Falha ao iniciar SWI-Prolog/MQI ({type(erro).__name__}): {erro}') from erro

    @contextmanager
    def _prazo(self, segundos):
        expirou = Event()

        def interromper():
            expirou.set()
            if self._mqi:
                self._mqi.stop(kill=True)

        timer = Timer(segundos, interromper)
        timer.daemon = True
        timer.start()
        try:
            yield
        finally:
            timer.cancel()
            timer.join()
            if expirou.is_set():
                raise TimeoutError(f'MQI não respondeu em {segundos:g} s de tempo real.')

    def propor(self, estado: Estado) -> Decisao:
        if self._fechado:
            raise FalhaProlog('Sessão MQI encerrada; não houve reconexão nem troca de paradigma.')
        try:
            serializado = json.dumps(asdict(estado), ensure_ascii=False, allow_nan=False)
            consulta = f'logico:decidir_json({json.dumps(serializado, ensure_ascii=False)}, Resposta)'
            with self._prazo(self.timeout_comunicacao):
                respostas = self._thread.query(consulta, query_timeout_seconds=self.timeout_consulta)
            if not isinstance(respostas, list) or len(respostas) != 1 or not isinstance(respostas[0], dict):
                raise ValueError('A consulta deve retornar exatamente uma decisão.')
            resposta = _Decisao.model_validate_json(respostas[0]['Resposta'])
            if [a.fase for a in resposta.avaliacoes] != [f.id for f in estado.fases]:
                raise ValueError('Avaliações não correspondem às fases e à ordem de entrada.')
            if any(a.chave[3] != a.fase for a in resposta.avaliacoes):
                raise ValueError('Identificador de desempate inconsistente.')
            return Decisao(Proposta(**resposta.proposta.model_dump()),
                           tuple(Avaliacao(**a.model_dump()) for a in resposta.avaliacoes), resposta.criterio)
        except Exception as erro:
            self.fechar()
            raise FalhaProlog(f'Falha na decisão SWI-Prolog/MQI ({type(erro).__name__}): {erro}') from erro

    def fechar(self):
        if self._fechado:
            return
        self._fechado = True
        if self._mqi:
            # kill é deliberado: não depender de uma nova conexão para encerrar
            # um processo possivelmente indisponível. Não cancela estado do motor.
            self._mqi.stop(kill=True)
            self._mqi.connection_failed = True
        if self._thread:
            with suppress(Exception):
                self._thread.stop()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechar()
