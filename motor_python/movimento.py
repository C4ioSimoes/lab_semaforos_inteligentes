"""Geometria longitudinal e parâmetros didáticos por categoria."""

from dataclasses import dataclass
from math import pi

from .modelos import Dimensoes, Posicao

# A barra desenhada está a 11 unidades do centro e tem espessura 0,45.
# Em relação à origem da trajetória (±28), sua borda de aproximação está em 16,775.
BORDA_VIA = 90  # Espelho de BORDA_VIA em cena_3d/src/cruzamento.ts.
ORIGEM_TRAJETORIA = 28
DISTANCIA_RETENCAO = ORIGEM_TRAJETORIA - 11 - 0.45 / 2
FOLGA_RETENCAO = 0.5


@dataclass(frozen=True)
class PerfilVeiculo:
    dimensoes: Dimensoes
    velocidade: float
    distancia_minima: float

    @property
    def distancia_inicial(self) -> float:
        # Mantém o referencial longitudinal e amplia a área de aproximação.
        return self.dimensoes.comprimento / 2 + ORIGEM_TRAJETORIA - BORDA_VIA


PERFIS = {
    "carro": PerfilVeiculo(Dimensoes(comprimento=4, largura=1.8, altura=1.3), 6, 2),
    "moto": PerfilVeiculo(Dimensoes(comprimento=2, largura=0.8, altura=1.2), 7, 1.5),
    "onibus": PerfilVeiculo(Dimensoes(comprimento=10, largura=2.5, altura=3), 4, 2.5),
    "ambulancia": PerfilVeiculo(Dimensoes(comprimento=5, largura=2, altura=2.4), 6, 2),
}


@dataclass(frozen=True)
class Trajetoria:
    x: float
    z: float
    dx: float
    dz: float
    rotacao_y: float
    destino: str

    def posicao(self, distancia: float, altura: float = 1.3) -> Posicao:
        return Posicao(
            x=round(self.x + self.dx * distancia, 6),
            y=altura / 2,
            z=round(self.z + self.dz * distancia, 6),
            rotacao_y=self.rotacao_y,
        )


# Faixa externa de entrada de cada braço, correspondente à geometria do M1.
TRAJETORIAS = {
    "N": Trajetoria(-4.5, -28, 0, 1, 0, "S"),
    "S": Trajetoria(4.5, 28, 0, -1, pi, "N"),
    "L": Trajetoria(28, -4.5, -1, 0, -pi / 2, "O"),
    "O": Trajetoria(-28, 4.5, 1, 0, pi / 2, "L"),
}
