"""Baseline e validação comum de integridade, sem dependências gráficas."""
from dataclasses import dataclass
from itertools import combinations
from types import MappingProxyType
from typing import Literal

from pydantic import Field, model_validator

from .modelos import Contrato

VEICULARES = tuple(f"{o}-seguir_em_frente" for o in "NSLO")
PEDESTRES = tuple(f"{o}-TR" for o in "NSLO")
MOVIMENTOS = VEICULARES + PEDESTRES


def conflitos_iniciais():
    matriz = {a: {b: False for b in MOVIMENTOS} for a in MOVIMENTOS}
    for a, b in combinations(MOVIMENTOS, 2):
        if a in VEICULARES and b in VEICULARES:
            conflito = (a[0] in "NS") != (b[0] in "NS")
        elif (a in VEICULARES) != (b in VEICULARES):
            veiculo, pedestre = (a, b) if a in VEICULARES else (b, a)
            conflito = (veiculo[0] in "NS") == (pedestre[0] in "NS")
        else:
            conflito = False
        matriz[a][b] = matriz[b][a] = conflito
    return matriz


class ConfiguracaoControle(Contrato):
    conflitos: dict[str, dict[str, bool]] = Field(default_factory=conflitos_iniciais)
    fases: dict[str, list[str]] = Field(default_factory=lambda: {
        "F-NS": list(VEICULARES[:2]), "F-LO": list(VEICULARES[2:]), "F-PED": list(PEDESTRES),
    })
    sequencia: list[str] = Field(default_factory=lambda: ["F-NS", "F-LO", "F-PED"])
    verde_passos: int = Field(default=100, strict=True, gt=0)
    amarelo_passos: int = Field(default=30, strict=True, gt=0)
    liberacao_passos: int = Field(default=10, strict=True, gt=0)

    @model_validator(mode="after")
    def validar(self):
        esperada = conflitos_iniciais()
        if set(self.conflitos) != set(MOVIMENTOS):
            raise ValueError("A matriz deve conter os oito movimentos habilitados.")
        for a, linha in self.conflitos.items():
            if set(linha) != set(MOVIMENTOS) or linha[a]:
                raise ValueError("Matriz incompleta ou diagonal com conflito.")
        for a, b in combinations(MOVIMENTOS, 2):
            if self.conflitos[a][b] != self.conflitos[b][a]:
                raise ValueError("A matriz de conflitos deve ser simétrica.")
            if esperada[a][b] and not self.conflitos[a][b]:
                raise ValueError("A matriz não pode omitir conflitos da geometria habilitada.")
        if not self.fases or not self.sequencia or set(self.sequencia) != set(self.fases) or len(set(self.sequencia)) != len(self.sequencia):
            raise ValueError("A sequência deve listar cada fase exatamente uma vez.")
        for fase, movimentos in self.fases.items():
            if not fase or not movimentos or len(set(movimentos)) != len(movimentos) or not set(movimentos) <= set(MOVIMENTOS):
                raise ValueError("Fase vazia, duplicada ou com movimento desconhecido.")
            if any(self.conflitos[a][b] for a, b in combinations(movimentos, 2)):
                raise ValueError(f"Fase {fase} contém movimentos conflitantes.")
        if set().union(*map(set, self.fases.values())) != set(MOVIMENTOS):
            raise ValueError("Todos os movimentos habilitados precisam de atendimento.")
        return self


@dataclass(frozen=True)
class EstadoControle:
    fase: str | None
    estado: str
    decorrido_passos: int
    ocupados: tuple[str, ...]


@dataclass(frozen=True)
class Proposta:
    acao: Literal["manter", "transicionar", "aguardar"]
    fase: str | None
    motivo: str


class PoliticaFixa:
    """Recebe estado imutável; propõe sem alterar permissões do motor."""
    def __init__(self, configuracao: ConfiguracaoControle):
        self.sequencia = tuple(configuracao.sequencia)
        self.verde_passos = configuracao.verde_passos

    def propor(self, estado: EstadoControle) -> Proposta:
        indice = self.sequencia.index(estado.fase) if estado.fase in self.sequencia else -1
        if estado.fase is None or estado.estado != "atendimento" or estado.decorrido_passos >= self.verde_passos:
            return Proposta("transicionar", self.sequencia[(indice + 1) % len(self.sequencia)], "Sequência fixa, sem prioridade adaptativa.")
        return Proposta("manter", estado.fase, "Tempo fixo de atendimento ainda não concluído.")


class MaquinaSemaforica:
    def __init__(self, configuracao: ConfiguracaoControle, registrar):
        # Revalida mesmo modelos alterados pelo chamador após sua construção.
        c = ConfiguracaoControle.model_validate(configuracao.model_dump())
        self.configuracao = c
        self.fases = MappingProxyType({k: tuple(v) for k, v in c.fases.items()})
        self.conflitos = MappingProxyType({k: MappingProxyType(v.copy()) for k, v in c.conflitos.items()})
        self.fase: str | None = None
        self.estado = "liberacao"
        self.inicio_passo = 0
        self.registrar = registrar
        self.ultima_validacao = {"aceita": True, "motivo": "Liberação inicial."}
        self.bloqueios = 0
        self._ultimo_bloqueio = None
        self.adaptativo = False

    @property
    def verde_minimo(self):
        return 30 if self.adaptativo else self.configuracao.verde_passos

    @property
    def verde_maximo(self):
        return float('inf') if self.adaptativo else self.configuracao.verde_passos

    def leitura(self, passo: int, ocupados: tuple[str, ...]) -> EstadoControle:
        return EstadoControle(self.fase, self.estado, passo - self.inicio_passo, ocupados)

    def permissoes(self) -> tuple[str, ...]:
        return self.fases[self.fase] if self.fase and self.estado == "atendimento" else ()

    def sinais(self):
        sinais = {m: "vermelho" for m in MOVIMENTOS}
        if self.fase:
            for m in self.fases[self.fase]:
                if self.estado == "atendimento":
                    sinais[m] = "verde"
                elif self.estado == "encerramento" and m in VEICULARES:
                    sinais[m] = "amarelo"
        return sinais

    def _mudar(self, estado, fase, passo):
        anterior = {"estado": self.estado, "fase": self.fase}
        self.estado, self.fase, self.inicio_passo = estado, fase, passo
        self.registrar("transicao_semaforica", "motor", anterior, {"estado": estado, "fase": fase})

    def aplicar(self, proposta: Proposta, passo: int, ocupados: tuple[str, ...], *, elegivel: bool = True):
        decorrido = passo - self.inicio_passo
        motivo = None
        if proposta.acao not in ("manter", "transicionar", "aguardar") or (proposta.acao != "aguardar" and proposta.fase not in self.fases):
            motivo = "Proposta desconhecida ou fase não prevista."
        elif proposta.acao == "aguardar":
            if proposta.fase is not None:
                motivo = "Espera sem demanda não pode indicar fase."
            elif self.estado == "atendimento":
                if decorrido < self.verde_minimo:
                    motivo = "Tempo mínimo de atendimento não cumprido."
                else:
                    self._mudar("encerramento" if any(m in VEICULARES for m in self.fases[self.fase]) else "liberacao", self.fase, passo)
            elif self.estado == "encerramento":
                if decorrido < self.configuracao.amarelo_passos:
                    motivo = "Amarelo veicular em andamento."
                else:
                    self._mudar("liberacao", self.fase, passo)
        elif proposta.acao == "manter":
            if self.estado != "atendimento" or proposta.fase != self.fase:
                motivo = "Manutenção incompatível com o estado atual."
            elif decorrido >= self.verde_maximo:
                motivo = "Tempo máximo de atendimento atingido."
        elif self.estado == "atendimento":
            if decorrido < self.verde_minimo:
                motivo = "Tempo mínimo de atendimento não cumprido."
            else:
                proximo = "encerramento" if any(m in VEICULARES for m in self.fases[self.fase]) else "liberacao"
                self._mudar(proximo, self.fase, passo)
        elif self.estado == "encerramento":
            if decorrido < self.configuracao.amarelo_passos:
                motivo = "Amarelo veicular em andamento."
            else:
                self._mudar("liberacao", self.fase, passo)
        elif self.estado == "liberacao":
            if decorrido < self.configuracao.liberacao_passos:
                motivo = "Intervalo mínimo de liberação em andamento."
            elif any(self.conflitos[a][b] for a in self.fases[proposta.fase] for b in ocupados):
                motivo = "Trajetória conflitante ainda ocupada."
            elif not elegivel:
                motivo = "Avaliador de elegibilidade não autorizou a abertura da fase."
            else:
                self._mudar("atendimento", proposta.fase, passo)
        if motivo and self.estado == "atendimento" and decorrido >= self.verde_maximo:
            # Uma proposta inválida não pode prolongar o verde além do máximo.
            proximo = "encerramento" if any(m in VEICULARES for m in self.fases[self.fase]) else "liberacao"
            self._mudar(proximo, self.fase, passo)
        self.ultima_validacao = {"aceita": motivo is None, "motivo": motivo or proposta.motivo,
                                 "proposta": {"acao": proposta.acao, "fase": proposta.fase}}
        # Registra cada bloqueio novo; a repetição permanece visível no diagnóstico.
        chave = (self.estado, proposta.acao, proposta.fase, motivo)
        if motivo and chave != self._ultimo_bloqueio:
            self.bloqueios += 1
            self.registrar("proposta_bloqueada", "motor", self.ultima_validacao["proposta"], {"motivo": motivo})
        self._ultimo_bloqueio = chave if motivo else None

    def admissibilidade(self, fase, passo, ocupados):
        """Autorizar agora é distinto de escolher um destino para transição."""
        decorrido = passo - self.inicio_passo
        if self.estado == "atendimento":
            if self.fase == fase and decorrido < self.verde_maximo:
                return True, None
            return False, "É necessário encerrar atendimento e cumprir a transição."
        if self.estado == "encerramento":
            return False, "Amarelo veicular em andamento."
        if decorrido < self.configuracao.liberacao_passos:
            return False, "Intervalo mínimo de liberação em andamento."
        if any(self.conflitos[a][b] for a in self.fases[fase] for b in ocupados):
            return False, "Trajetória conflitante ainda ocupada."
        return True, None

    def diagnostico(self, passo):
        return {"politica": "fixa_referencia", "sequencia": list(self.configuracao.sequencia),
                "estado": self.estado, "inicio_passo": self.inicio_passo,
                "decorrido_segundos": (passo - self.inicio_passo) / 10,
                "verde_variavel": self.adaptativo,
                "verde_minimo_segundos": self.verde_minimo / 10,
                "verde_maximo_segundos": None if self.adaptativo else self.verde_maximo / 10,
                "tempos": {"verde": self.configuracao.verde_passos / 10,
                           "amarelo": self.configuracao.amarelo_passos / 10,
                           "liberacao_minima": self.configuracao.liberacao_passos / 10},
                "permissoes": list(self.permissoes()), "validacao": self.ultima_validacao.copy(),
                "bloqueios": self.bloqueios}
