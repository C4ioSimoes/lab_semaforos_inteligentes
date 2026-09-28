"""Acessos e percursos pedestres; a autorização pertence ao motor semafórico."""
from math import hypot
from .modelos import Dimensoes, Posicao

DIMENSOES_PEDESTRE = Dimensoes(comprimento=0.6, largura=0.6, altura=1.7)
TRAVESSIAS = ("N-TR", "S-TR", "L-TR", "O-TR")
ACESSOS = tuple(f"{travessia}:{lado}" for travessia in TRAVESSIAS for lado in ("A", "B"))


def posicoes_acesso(acesso: str) -> list[Posicao]:
    """16 posições em cada sentido, alinhadas à faixa de travessia.

    A fila ocupa a calçada externa. Separar sentidos evita que o lote liberado
    convirja para um único ponto ou encontre a fila oposta de frente.
    """
    travessia, lado = acesso.split(":")
    faixa = -7.65 if lado == "A" else -8.75
    return [Posicao(x=x, y=0.85, z=z, rotacao_y=0)
            for coluna in range(16)
            for x, z in [local(travessia, (-1 if lado == "A" else 1) * (12 + coluna), faixa)]]


VELOCIDADE_PEDESTRE = 1.4
FOLGA_PEDESTRE = 0.8


def local(travessia, x, z):
    if travessia == "S-TR":
        return -x, -z
    if travessia == "L-TR":
        return -z, x
    if travessia == "O-TR":
        return z, -x
    return x, z


def percurso(p):
    lado_a = p.origem.endswith(":A")
    destino = 6.4 if lado_a else -6.4
    faixa = -7.65 if lado_a else -8.75
    return [(p.posicao.x, p.posicao.z), local(p.trajetoria, destino, faixa)]


def passo_livre(p, destino, distancia_maxima, pedestres):
    """Avança em paralelo, preservando folga e a passagem nas esquinas.

    Somente a pequena esquina compartilhada tem preferência de passagem.
    A reserva não bloqueia outras travessias nem a autorização do lote.
    """
    x, z = p.posicao.x, p.posicao.z
    dx, dz = destino[0] - x, destino[1] - z
    distancia = hypot(dx, dz)
    if distancia < 1e-9:
        return destino
    passo = min(distancia_maxima, distancia)
    candidato = (x + dx / distancia * passo, z + dz / distancia * passo)
    def na_esquina(x, z):
        return 6.4 < abs(x) <= 10.8 and 6.4 < abs(z) <= 10.8
    for outro in pedestres:
        if outro.id == p.id:
            continue
        ox, oz = outro.posicao.x, outro.posicao.z
        if (outro.origem != p.origem and na_esquina(*candidato) and na_esquina(ox, oz)
                and candidato[0] * ox > 0 and candidato[1] * oz > 0):
            return x, z
        if distancia_segmento(ox, oz, (x, z), candidato) < FOLGA_PEDESTRE - 1e-9:
            return x, z
    return candidato


def distancia_segmento(x, z, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    comprimento2 = dx * dx + dz * dz
    t = min(1, max(0, ((x - a[0]) * dx + (z - a[1]) * dz) / comprimento2)) if comprimento2 else 0
    return ((x - a[0] - t * dx) ** 2 + (z - a[1] - t * dz) ** 2) ** 0.5


def perto_percurso(posicao, pontos):
    return any(distancia_segmento(posicao.x, posicao.z, a, b) < FOLGA_PEDESTRE - 1e-9
               for a, b in zip(pontos, pontos[1:]))
