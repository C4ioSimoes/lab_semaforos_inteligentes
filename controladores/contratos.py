"""Somente contratos imutáveis; nenhuma seleção de fases compartilhada."""
from dataclasses import dataclass
from motor_python.controle import EstadoControle, Proposta


@dataclass(frozen=True)
class Solicitacao:
    id: str
    movimento: str
    categoria: str
    instante: float
    prioritaria: bool = False


@dataclass(frozen=True)
class Fase:
    id: str
    movimentos: tuple[str, ...]
    admissivel: bool
    bloqueio: str | None = None


@dataclass(frozen=True)
class Estado:
    relogio: EstadoControle
    tempo: float
    fases: tuple[Fase, ...]
    solicitacoes: tuple[Solicitacao, ...]
    verde_passos: int
    limiar_espera: float
    prioridade_ambulancia: bool
    prioridade_onibus: bool
    conflitos: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Avaliacao:
    fase: str
    demanda: int
    maior_espera: float
    criterio: str
    chave: tuple[int, float, float, str]
    admissivel: bool
    bloqueio: str | None


@dataclass(frozen=True)
class Decisao:
    proposta: Proposta
    avaliacoes: tuple[Avaliacao, ...]
    criterio: str
