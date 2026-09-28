"""Métricas oficiais em segundos e participantes por minuto simulado."""
from collections import defaultdict


def espera_externa(p, tempo):
    return max(0, (p.instante_inserido if p.instante_inserido is not None else tempo) - p.instante_solicitado)


class Metricas:
    def __init__(self):
        self._concluidos = defaultdict(lambda: {"quantidade": 0, "interna": 0.0, "externa": 0.0, "pedestre": 0.0,
                                               "emergencias": 0, "emergencia_atendimento": 0.0, "emergencia_conclusao": 0.0})
        self._filas = defaultdict(lambda: {"interna_area": 0.0, "externa_area": 0.0, "interna_max": 0, "externa_max": 0})

    def registrar_filas(self, ativos, pendentes, dt):
        """Integral discreta: comprimento ao fim de cada passo, ponderado por Δt."""
        contagens = defaultdict(lambda: [0, 0])
        for indice, participantes in enumerate((ativos, pendentes)):
            for p in participantes:
                if indice == 0 and not p.estado.startswith('aguardando_'):
                    continue
                for chave in ((None, None), (p.origem, None), (None, p.categoria), (p.origem, p.categoria)):
                    contagens[chave][indice] += 1
        for chave, (interna, externa) in contagens.items():
            dados = self._filas[chave]
            dados['interna_area'] += interna * dt
            dados['externa_area'] += externa * dt
            dados['interna_max'] = max(dados['interna_max'], interna)
            dados['externa_max'] = max(dados['externa_max'], externa)

    def concluir(self, p, tempo):
        dados = self._concluidos[(p.origem, p.categoria)]
        dados["quantidade"] += 1
        dados["interna"] += p.espera_interna
        dados["externa"] += espera_externa(p, tempo)
        if p.categoria == "pedestre":
            dados["pedestre"] += p.instante_autorizacao - p.instante_solicitado
        if p.solicitacao_prioritaria:
            dados['emergencias'] += 1
            dados['emergencia_atendimento'] += p.instante_autorizacao - p.instante_solicitado
            dados['emergencia_conclusao'] += tempo - p.instante_solicitado

    def instantaneo(self, tempo, ativos, pendentes, chegadas):
        def grupo(origem=None, categoria=None):
            def corresponde(o, c):
                return (origem is None or origem == o) and (categoria is None or categoria == c)
            presentes = [p for p in ativos if corresponde(p.origem, p.categoria)]
            externos = [p for p in pendentes if corresponde(p.origem, p.categoria)]
            concluidos = [v for (o, c), v in self._concluidos.items() if corresponde(o, c)]
            n = sum(v["quantidade"] for v in concluidos)
            interna = sum(v["interna"] for v in concluidos)
            externa = sum(v["externa"] for v in concluidos)
            filas = self._filas.get((origem, categoria), {})
            emergencias_concluidas = sum(v['emergencias'] for v in concluidos)
            atendidas = [p for p in presentes if p.solicitacao_prioritaria and p.instante_autorizacao is not None]
            nao_atendidas = [p for p in (*presentes, *externos) if p.solicitacao_prioritaria and p.instante_autorizacao is None]
            total_atendidas = emergencias_concluidas + len(atendidas)
            tempo_atendimento = sum(v['emergencia_atendimento'] for v in concluidos) + sum(p.instante_autorizacao - p.instante_solicitado for p in atendidas)
            return {
                "concluidos": n, "ativos": len(presentes), "pendentes": len(externos),
                "vazao_por_minuto": n * 60 / tempo if tempo else 0,
                "espera_concluidos_interna_media": interna / n if n else 0,
                "espera_concluidos_externa_media": externa / n if n else 0,
                "espera_concluidos_total_media": (interna + externa) / n if n else 0,
                "espera_ativos_interna_total": sum(p.espera_interna for p in presentes),
                "espera_ativos_externa_total": sum(espera_externa(p, tempo) for p in presentes),
                "espera_pendentes_externa_total": sum(espera_externa(p, tempo) for p in externos),
                "fila_interna_media": filas.get('interna_area', 0) / tempo if tempo else 0,
                "fila_externa_media": filas.get('externa_area', 0) / tempo if tempo else 0,
                "fila_interna_max": filas.get('interna_max', 0), "fila_externa_max": filas.get('externa_max', 0),
                "emergencias_atendidas": total_atendidas, "emergencias_concluidas": emergencias_concluidas,
                "emergencias_nao_atendidas": len(nao_atendidas),
                "emergencia_tempo_ate_atendimento_medio": tempo_atendimento / total_atendidas if total_atendidas else 0,
                "emergencia_tempo_ate_conclusao_medio": sum(v['emergencia_conclusao'] for v in concluidos) / emergencias_concluidas if emergencias_concluidas else 0,
                "emergencia_espera_nao_atendidos_total": sum(tempo - p.instante_solicitado for p in nao_atendidas),
                "espera_pedestres_ate_autorizacao_total": sum(v["pedestre"] for v in concluidos) + sum(
                    (p.instante_autorizacao if p.instante_autorizacao is not None else tempo) - p.instante_solicitado
                    for p in (*presentes, *externos) if p.categoria == "pedestre"),
            }
        origens = sorted({'N', 'S', 'L', 'O', 'N-TR', 'S-TR', 'L-TR', 'O-TR'} |
                         {p.origem for p in (*ativos, *pendentes)} | {o for o, _ in self._concluidos})
        return {"intervalo_segundos": tempo, "chegadas_solicitadas": chegadas, "limiar_velocidade_espera": 0.1,
                "total": grupo(), "por_origem": {o: grupo(origem=o) for o in origens},
                "por_categoria": {c: grupo(categoria=c) for c in ("carro", "moto", "onibus", "ambulancia", "pedestre")},
                "por_origem_categoria": {o: {c: grupo(origem=o, categoria=c) for c in
                    (("pedestre",) if o.endswith('-TR') else ("carro", "moto", "onibus", "ambulancia"))} for o in origens}}
