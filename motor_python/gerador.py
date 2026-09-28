"""Poisson por fonte e passo, independente da mobilidade e dos controladores."""
from math import exp, isfinite
from random import Random

from pydantic import Field, model_validator

from .modelos import Contrato, ParametrosInsercao, ParametrosPedestre
from .movimento import PERFIS, TRAJETORIAS
from .pedestres import TRAVESSIAS

LIMITE_TAXA_EFETIVA = 6000.0


class ConfiguracaoGerador(Contrato):
    semente: int = Field(default=42, strict=True, ge=0, le=4294967295)
    taxas_veiculares: dict[str, dict[str, float]] = Field(default_factory=lambda: {
        origem: {categoria: 0.0 for categoria in PERFIS} for origem in TRAJETORIAS
    })
    taxas_pedestres: dict[str, float] = Field(default_factory=lambda: {t: 0.0 for t in TRAVESSIAS})
    fator_global: float = Field(default=1, ge=0, le=10)
    fatores_locais: dict[str, float] = Field(default_factory=lambda: {o: 1.0 for o in TRAJETORIAS})
    fator_pedestres: float = Field(default=1, ge=0, le=10)

    @model_validator(mode="after")
    def validar(self):
        if set(self.taxas_veiculares) != set(TRAJETORIAS) or set(self.fatores_locais) != set(TRAJETORIAS):
            raise ValueError("Informe exatamente as aproximações N, S, L e O.")
        if set(self.taxas_pedestres) != set(TRAVESSIAS):
            raise ValueError("Informe as quatro travessias N-TR, S-TR, L-TR e O-TR.")
        for origem, taxas in self.taxas_veiculares.items():
            if set(taxas) != set(PERFIS):
                raise ValueError("Informe carro, moto, onibus e ambulancia para cada aproximação.")
            fator = self.fatores_locais[origem]
            if not isfinite(fator) or not 0 <= fator <= 10:
                raise ValueError("Fatores locais devem estar entre 0 e 10.")
            for taxa in taxas.values():
                if not isfinite(taxa) or not 0 <= taxa <= LIMITE_TAXA_EFETIVA or taxa * fator * self.fator_global > LIMITE_TAXA_EFETIVA:
                    raise ValueError("Taxa base e efetiva devem estar entre 0 e 6000 participantes/min.")
        for taxa in self.taxas_pedestres.values():
            if not isfinite(taxa) or not 0 <= taxa <= LIMITE_TAXA_EFETIVA or taxa * self.fator_pedestres > LIMITE_TAXA_EFETIVA:
                raise ValueError("Taxa de pedestres base e efetiva deve estar entre 0 e 6000/min.")
        return self


def poisson(rng: Random, media: float) -> int:
    """Método do produto; soma de blocos Poisson evita underflow em médias grandes."""
    total = 0
    while media > 0:
        bloco = min(media, 20.0)
        limite, produto, quantidade = exp(-bloco), 1.0, 0
        while produto > limite:
            produto *= rng.random()
            quantidade += 1
        total += quantidade - 1
        media -= bloco
    return total


class GeradorDemanda:
    def __init__(self):
        self.configuracao = ConfiguracaoGerador()
        self._fontes: dict[str, Random] = {}
        self.inicio_janela = 0.0
        self.contagens: dict[str, int] = {}
        self.configurar(self.configuracao, 0)

    def configurar(self, configuracao: ConfiguracaoGerador, tempo: float):
        mudou_semente = configuracao.semente != self.configuracao.semente
        self.configuracao = configuracao.model_copy(deep=True)
        if mudou_semente or not self._fontes:
            self._fontes = {chave: Random(f"{configuracao.semente}:{chave}") for chave, _, _ in self.fontes()}
        self.inicio_janela = tempo
        self.contagens = {chave: 0 for chave in self._fontes}

    def fontes(self):
        c = self.configuracao
        for origem in TRAJETORIAS:
            for categoria in PERFIS:
                taxa = c.taxas_veiculares[origem][categoria] * c.fator_global * c.fatores_locais[origem]
                yield f"{origem}:{categoria}", taxa, dict(categoria=categoria, origem=origem, movimento="seguir_em_frente", quantidade=1,
                                                        solicitacao_prioritaria=categoria == "ambulancia")
        for travessia in TRAVESSIAS:
            for lado in ("A", "B"):
                # Taxa por travessia dividida igualmente entre seus dois acessos.
                taxa = c.taxas_pedestres[travessia] * c.fator_pedestres / 2
                yield f"{travessia}:{lado}:pedestre", taxa, dict(categoria="pedestre", travessia=travessia, lado=lado, quantidade=1)

    def gerar(self, dt: float):
        for chave, taxa, dados in self.fontes():
            quantidade = poisson(self._fontes[chave], taxa * dt / 60)
            self.contagens[chave] += quantidade
            if quantidade:
                classe = ParametrosPedestre if dados["categoria"] == "pedestre" else ParametrosInsercao
                yield chave, classe.model_validate(dados), quantidade

    def diagnostico(self, tempo: float):
        duracao = max(0, tempo - self.inicio_janela)
        taxas = {chave: taxa for chave, taxa, _ in self.fontes()}
        return {
            "configuracao": self.configuracao.model_dump(),
            "inicio_janela": self.inicio_janela, "duracao_janela": duracao,
            "taxas_efetivas": taxas,
            "taxas_observadas": {chave: (n * 60 / duracao if duracao else 0) for chave, n in self.contagens.items()},
            "gerados_janela": dict(self.contagens),
        }
