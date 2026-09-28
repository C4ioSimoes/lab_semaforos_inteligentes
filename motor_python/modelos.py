"""Contratos da Seção 13; estruturas internas ainda não definidas ficam em JSON."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

Identificador = Annotated[str, Field(min_length=1)]
Passo = Annotated[int, Field(ge=0, strict=True)]
Tempo = Annotated[float, Field(ge=0)]
ObjetoJSON = dict[str, JsonValue]
CategoriaVeiculo = Literal["carro", "moto", "onibus", "ambulancia"]


class Contrato(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Cenario(Contrato):
    schema_version: Identificador
    scenario_id: Identificador
    geometria: ObjetoJSON
    movimentos: list[ObjetoJSON]
    conflitos: ObjetoJSON
    fases: list[ObjetoJSON]
    tempos: ObjetoJSON
    parametros_participantes: ObjetoJSON
    taxas: ObjetoJSON
    semente: int
    passo: float = Field(gt=0)


class Posicao(Contrato):
    x: float
    y: float
    z: float
    rotacao_y: float


class Dimensoes(Contrato):
    comprimento: float = Field(gt=0)
    largura: float = Field(gt=0)
    altura: float = Field(gt=0)


class Participante(Contrato):
    id: Identificador
    categoria: Identificador
    origem: Identificador
    destino: Identificador
    trajetoria: Identificador
    posicao: Posicao
    estado: Identificador
    instante_solicitado: Tempo
    instante_inserido: Tempo | None
    solicitacao_prioritaria: bool
    dimensoes: Dimensoes
    instante_inicio_espera: Tempo | None = None
    fonte: Literal["manual", "automatico"] = "manual"
    espera_interna: Tempo = 0
    instante_autorizacao: Tempo | None = None


class Instantaneo(Contrato):
    run_id: Identificador
    step: Passo
    simulation_time: Tempo
    fase: Identificador | None
    estado_transicao: Identificador
    ocupacoes: ObjetoJSON
    filas: ObjetoJSON
    solicitacoes: list[ObjetoJSON]
    versao_configuracao: Identificador
    participantes: list[Participante] = Field(default_factory=list)
    semaforos: dict[str, Literal["verde", "amarelo", "vermelho"]]
    semaforos_pedestres: dict[str, Literal["verde", "vermelho"]] = Field(default_factory=dict)
    controle: ObjetoJSON = Field(default_factory=dict)
    metricas: ObjetoJSON = Field(default_factory=dict)
    demanda: ObjetoJSON = Field(default_factory=dict)


class Comando(Contrato):
    command_id: Identificador
    tipo: Identificador
    parametros: ObjetoJSON
    passo_solicitado: Passo | None = None
    confirmacao: ObjetoJSON | None = None


class ParametrosInsercao(Contrato):
    categoria: CategoriaVeiculo
    origem: Literal["N", "S", "L", "O"]
    movimento: Literal["seguir_em_frente"]
    quantidade: int = Field(strict=True, ge=1, le=1)
    solicitacao_prioritaria: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validar_emergencia(self):
        if self.solicitacao_prioritaria and self.categoria != "ambulancia":
            raise ValueError("Somente ambulâncias podem solicitar prioridade de emergência.")
        return self


class ConfiguracaoControlador(Contrato):
    controlador: Literal["baseline", "imperativo", "orientado_objetos", "funcional", "logico"] = "baseline"
    limiar_espera: float = Field(default=30, strict=True, gt=0, le=3600)
    prioridade_ambulancia: bool = Field(default=True, strict=True)
    prioridade_onibus: bool = Field(default=False, strict=True)


class ConfiguracaoNeural(Contrato):
    modelo: Literal["AND_referencia", "perceptron", "adaline"]


class ParametrosPedestre(Contrato):
    categoria: Literal["pedestre"]
    travessia: Literal["N-TR", "S-TR", "L-TR", "O-TR"]
    lado: Literal["A", "B"]
    quantidade: int = Field(strict=True, ge=1, le=100)


class ConfirmacaoComando(Contrato):
    status: Literal["aplicado", "rejeitado"]
    passo_aplicacao: Passo | None = None
    erro: str | None = None


class RespostaComando(Contrato):
    tipo: Literal["confirmacao_comando"] = "confirmacao_comando"
    command_id: Identificador | None
    confirmacao: ConfirmacaoComando


class Decisao(Contrato):
    decision_id: Identificador
    step: Passo
    controlador: Identificador
    politica: Identificador
    modelo: Identificador
    candidatas: list[Identificador]
    avaliacoes: list[ObjetoJSON]
    motivos: list[str]
    proposta: ObjetoJSON
    resultado_validacao: ObjetoJSON


class Evento(Contrato):
    event_id: Identificador
    ordem: Passo
    passo: Passo
    tempo_simulado: Tempo
    tipo: Identificador
    origem: Identificador
    parametros: ObjetoJSON
    resultado: ObjetoJSON


class Resultado(Contrato):
    versoes: ObjetoJSON
    configuracao: ObjetoJSON
    demanda_solicitada: ObjetoJSON
    demanda_admitida: ObjetoJSON
    metricas: ObjetoJSON
    motivo_termino: Identificador
    limites_atingidos: list[str]
