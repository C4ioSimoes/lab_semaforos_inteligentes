"""Relógio oficial: um passo inteiro corresponde a 0,1 segundo simulado."""

import asyncio
import json
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from uuid import uuid4
from math import atan2, hypot

from pydantic import ValidationError

from .modelos import (
    Comando, ConfirmacaoComando, Evento, Instantaneo, ParametrosInsercao,
    Participante, RespostaComando, ParametrosPedestre, ConfiguracaoControlador, ConfiguracaoNeural, ConfiguracaoOperacao, ConfiguracaoVelocidade, ParametrosReset, Decisao,
)
from .movimento import DISTANCIA_RETENCAO, FOLGA_RETENCAO, PERFIS, TRAJETORIAS, BORDA_VIA, ORIGEM_TRAJETORIA, FAIXAS, TRAJETORIAS_POR_FAIXA
from .gerador import ConfiguracaoGerador, GeradorDemanda
from .pedestres import ACESSOS, DIMENSOES_PEDESTRE, posicoes_acesso
from .pedestres import VELOCIDADE_PEDESTRE, percurso, perto_percurso, passo_livre
from .controle import ConfiguracaoControle, MaquinaSemaforica, Proposta, MOVIMENTOS, PEDESTRES
from .metricas import Metricas
from .neural import AvaliadoresNeurais, ARQUIVO_PESOS
from .transito import ControleTransito
from controladores import criar_controlador
from controladores.adaptador_prolog import FalhaProlog
from controladores.contratos import Estado as EstadoDecisao, Fase, Solicitacao, Avaliacao

PASSO_SEGUNDOS = 0.1
INTERVALO_PUBLICACAO = 1 / 20  # Limite de 20 atualizações/s reais na execução acelerada.
LIMITE_INSTANTANEOS_PENDENTES = 100
MensagemMotor = Instantaneo | RespostaComando
Responder = Callable[[RespostaComando], None]


@dataclass
class RegistroComando:
    comando: Comando
    parametros: ParametrosInsercao | ParametrosPedestre | ConfiguracaoGerador | ConfiguracaoControlador | ConfiguracaoNeural | ConfiguracaoOperacao | ConfiguracaoVelocidade | ParametrosReset
    respostas: list[Responder] = field(default_factory=list)
    resultado: RespostaComando | None = None


class Motor:
    def __init__(self, *, limite_ativos: int = 200, limite_pendentes: int = 2000,
                 configuracao_controle: ConfiguracaoControle | None = None, arquivo_pesos=ARQUIVO_PESOS) -> None:
        if limite_ativos < 1 or limite_pendentes < 1:
            raise ValueError("Limites de capacidade devem ser positivos.")
        self._run_id = str(uuid4())
        self._step = 0
        self.velocidade_simulacao = 1
        self._assinantes: set[asyncio.Queue[MensagemMotor | None]] = set()
        self._comandos: dict[str, RegistroComando] = {}
        self._resets_confirmados: dict[str, RegistroComando] = {}
        self._pendentes: deque[str] = deque()
        self._entradas: dict[str, deque[Participante]] = {origem: deque() for origem in (*TRAJETORIAS, *ACESSOS)}
        self._participantes: dict[str, Participante] = {}
        self._passos_insercao: dict[str, int] = {}
        self._distancias: dict[str, float] = {}
        self._proxima_faixa = {origem: FAIXAS[0] for origem in TRAJETORIAS}
        self._eventos: list[Evento] = []
        self._sequencia_participante = 0
        self.gerador = GeradorDemanda()
        self._solicitados = {"manual": 0, "automatico": 0}
        self._admitidos = {"manual": 0, "automatico": 0}
        self._recusados = {"manual": 0, "automatico": 0}
        self._limite_ativos, self._limite_pendentes = limite_ativos, limite_pendentes
        self._motivo_interrupcao: str | None = None
        self.controle = MaquinaSemaforica(configuracao_controle or ConfiguracaoControle(), self._registrar)
        self.configuracao_controlador = ConfiguracaoControlador()
        self.controlador = criar_controlador("baseline", self.controle.configuracao)
        self.neurais = AvaliadoresNeurais(arquivo_pesos)
        self.modelo_neural = "AND_referencia"
        self.operacao = ConfiguracaoOperacao()
        self.transito = ControleTransito()
        self._diagnostico_transito = None
        self._ultima_decisao: Decisao | None = None
        self._falha_controlador: str | None = None
        self._assinatura_decisao = None
        self._alertas_espera: set[str] = set()
        self.metricas = Metricas()
        self._autorizados: set[str] = set()
        self._percursos_pedestres: dict[str, list[tuple[float, float]]] = {}
        self._configuracao_inicial = self.configuracao_experimento()
        self._historico_metricas = [self._amostra_metricas(self.instantaneo())]

    def instantaneo(self) -> Instantaneo:
        return Instantaneo(
            run_id=self._run_id,
            step=self._step,
            simulation_time=self._step / 10,
            velocidade_simulacao=self.velocidade_simulacao,
            fase=self.controle.fase,
            estado_transicao=self.controle.estado,
            ocupacoes=self._ocupacoes(),
            filas={
                "externas": {origem: len(fila) for origem, fila in self._entradas.items()},
                "internas": {origem: sum(
                    p.origem == origem and p.estado.startswith("aguardando_")
                    for p in self._participantes.values()
                ) for origem in self._entradas},
            },
            solicitacoes=[
                {"id": p.id, "categoria": p.categoria, "origem": p.origem,
                 "instante_solicitado": p.instante_solicitado, "estado": p.estado, "fonte": p.fonte,
                 "solicitacao_prioritaria": p.solicitacao_prioritaria}
                for fila in self._entradas.values() for p in fila
            ],
            versao_configuracao="1.8",
            participantes=[p.model_copy(deep=True) for p in self._participantes.values()],
            semaforos={origem: self.controle.sinais()[f"{origem}-seguir_em_frente"] for origem in TRAJETORIAS},
            semaforos_pedestres={m: self.controle.sinais()[m] for m in PEDESTRES},
            controle={**self.controle.diagnostico(self._step),
                "politica": (f"transito_{self.operacao.modelo if self.operacao.modo == 'neural' else 'urbano'}_v1" if self.operacao.modo != "paradigmas" else "fixa_referencia" if self.configuracao_controlador.controlador == "baseline" else "prioridades_demanda_v1"),
                "configuracao_controlador": self.configuracao_controlador.model_dump(),
                "operacao": self.operacao.model_dump(),
                "transito": self._diagnostico_transito,
                "erro_neural_transito": self.transito.erro,
                "treinamento_transito": {nome: {k: v for k, v in modelo.items() if k != "historico"}
                    for nome, modelo in self.transito.documento["modelos"].items()} if self.transito.documento else None,
                "falha_controlador": self._falha_controlador,
                "modelo_neural": self.modelo_neural,
                "modelos_neurais": self.neurais.disponibilidade(),
                "decisao": self._ultima_decisao.model_dump(mode="json") if self._ultima_decisao else None},
            metricas=self.metricas.instantaneo(self._step / 10, list(self._participantes.values()),
                [p for fila in self._entradas.values() for p in fila], sum(self._solicitados.values())),
            demanda={
                **self.gerador.diagnostico(self._step / 10),
                "solicitados": dict(self._solicitados), "admitidos": dict(self._admitidos),
                "recusados": dict(self._recusados), "motivo_interrupcao": self._motivo_interrupcao,
                "limites": {"ativos": self._limite_ativos, "pendentes": self._limite_pendentes, "taxa_efetiva": 6000},
            },
        )

    def assinar(self) -> asyncio.Queue[MensagemMotor | None]:
        fila: asyncio.Queue[MensagemMotor | None] = asyncio.Queue(
            maxsize=LIMITE_INSTANTANEOS_PENDENTES
        )
        # Sem await: inscrição e sincronização inicial acontecem no mesmo turno.
        fila.put_nowait(self.instantaneo())
        self._assinantes.add(fila)
        return fila

    def desassinar(self, fila: asyncio.Queue[MensagemMotor | None]) -> None:
        self._assinantes.discard(fila)

    def enfileirar(self, fila: asyncio.Queue[MensagemMotor | None], mensagem: MensagemMotor) -> None:
        if fila not in self._assinantes:
            return
        if fila.full():
            self.desassinar(fila)
            while not fila.empty():
                fila.get_nowait()
            fila.put_nowait(None)
        else:
            fila.put_nowait(mensagem.model_copy(deep=True))

    def _registrar(self, tipo: str, origem: str, parametros: dict, resultado: dict) -> None:
        ordem = len(self._eventos)
        self._eventos.append(Evento(
            event_id=f"{self._run_id}:evento:{ordem}", ordem=ordem,
            passo=self._step, tempo_simulado=self._step / 10, tipo=tipo,
            origem=origem, parametros=parametros, resultado=resultado,
        ))

    def receber_comando(self, dados: object, responder: Responder) -> None:
        """Valida e agenda; nenhuma posição muda durante o recebimento."""
        command_id = dados.get("command_id") if isinstance(dados, dict) else None
        command_id = command_id if isinstance(command_id, str) and command_id else None

        def rejeitar(motivo: str) -> None:
            resposta = RespostaComando(command_id=command_id, confirmacao=ConfirmacaoComando(
                status="rejeitado", erro=motivo,
            ))
            self._registrar("comando_rejeitado", "manual", {"command_id": command_id}, {"erro": motivo})
            responder(resposta)

        try:
            comando = Comando.model_validate(dados)
        except ValidationError:
            rejeitar("Comando inválido: informe command_id, tipo e parametros, sem campos extras.")
            return
        if comando.tipo not in {"inserir_participante", "configurar_gerador", "configurar_controlador", "configurar_modelo_neural", "configurar_operacao", "configurar_velocidade", "resetar_simulacao"}:
            rejeitar("Tipo de comando não suportado.")
            return
        if comando.confirmacao is not None or comando.passo_solicitado is not None:
            rejeitar("O motor define a confirmação e o passo de aplicação neste incremento.")
            return
        try:
            classe = (ParametrosReset if comando.tipo == "resetar_simulacao" else
                      ConfiguracaoVelocidade if comando.tipo == "configurar_velocidade" else
                      ConfiguracaoOperacao if comando.tipo == "configurar_operacao" else
                      ConfiguracaoNeural if comando.tipo == "configurar_modelo_neural" else
                      ConfiguracaoControlador if comando.tipo == "configurar_controlador" else
                      ConfiguracaoGerador if comando.tipo == "configurar_gerador" else
                      ParametrosPedestre if comando.parametros.get("categoria") == "pedestre" else ParametrosInsercao)
            parametros = classe.model_validate(comando.parametros)
        except ValidationError as erro:
            detalhe = erro.errors()[0]
            if comando.tipo == "configurar_velocidade":
                rejeitar("Velocidade inválida. Use um multiplicador inteiro de 1 a 24, sem campos extras.")
                return
            if comando.tipo in {"configurar_controlador", "configurar_modelo_neural", "configurar_operacao"}:
                rejeitar(f"Configuração de controlador inválida: {detalhe['msg']}")
                return
            if comando.tipo == "configurar_gerador":
                rejeitar(f"Configuração de geração inválida: {detalhe['msg']}")
                return
            if not detalhe["loc"]:
                rejeitar(detalhe["msg"])
                return
            campo = str(detalhe["loc"][0])
            motivos = {
                "categoria": "Categoria inválida. Use carro, moto, onibus, ambulancia ou pedestre.",
                "origem": "Rua de origem inválida. Use N, S, L ou O.",
                "movimento": "Movimento inválido. Use seguir_em_frente.",
                "quantidade": "Quantidade inválida. Use 1 para veículos ou um inteiro entre 1 e 100 para pedestres.",
                "travessia": "Travessia inválida. Use N-TR, S-TR, L-TR ou O-TR.",
                "lado": "Lado inválido. Use A ou B na travessia escolhida.",
                "solicitacao_prioritaria": "Solicitação prioritária deve ser booleana e exclusiva de ambulâncias.",
            }
            rejeitar(motivos.get(campo, f"Parâmetro não permitido: {campo}."))
            return
        anterior = self._comandos.get(comando.command_id) or self._resets_confirmados.get(comando.command_id)
        if anterior:
            if anterior.comando != comando:
                rejeitar("command_id já utilizado com outros parâmetros.")
            elif anterior.resultado:
                responder(anterior.resultado.model_copy(deep=True))
            else:
                anterior.respostas.append(responder)
            return
        if self._motivo_interrupcao and comando.tipo != "resetar_simulacao":
            rejeitar(f"Execução interrompida: {self._motivo_interrupcao}. Reinicie o motor para um novo ensaio.")
            return
        self._comandos[comando.command_id] = RegistroComando(comando, parametros, [responder])
        self._pendentes.append(comando.command_id)

    def _reiniciar(self, registro: RegistroComando) -> None:
        """Nova execução no mesmo objeto: mantém sockets e reinicia o RNG da semente."""
        novo = Motor(limite_ativos=self._limite_ativos, limite_pendentes=self._limite_pendentes,
                     configuracao_controle=self.controle.configuracao)
        novo.configuracao_controlador = self.configuracao_controlador.model_copy(deep=True)
        novo.controlador = criar_controlador(novo.configuracao_controlador.controlador, novo.controle.configuracao)
        novo.operacao = self.operacao.model_copy(deep=True)
        novo.velocidade_simulacao = self.velocidade_simulacao
        novo.controle.adaptativo = novo.operacao.modo != "paradigmas"
        novo.modelo_neural, novo.neurais, novo.transito = self.modelo_neural, self.neurais, self.transito
        novo.gerador.configurar(self.gerador.configuracao, 0)
        novo._configuracao_inicial = novo.configuracao_experimento()
        novo._historico_metricas = [novo._amostra_metricas(novo.instantaneo())]
        # Comandos posteriores ao reset pertencem à execução descartada.
        for ident in self._pendentes:
            pendente = self._comandos[ident]
            resposta = RespostaComando(command_id=ident, confirmacao=ConfirmacaoComando(
                status="rejeitado", erro="Comando cancelado pelo reset da simulação."))
            for responder in pendente.respostas:
                responder(resposta.model_copy(deep=True))
        self.fechar()
        novo._assinantes = self._assinantes
        novo._resets_confirmados = self._resets_confirmados
        novo._comandos = {registro.comando.command_id: registro}
        # Remove estados antigos ainda não entregues, preservando confirmações.
        for fila in novo._assinantes:
            respostas = []
            while not fila.empty():
                mensagem = fila.get_nowait()
                if isinstance(mensagem, RespostaComando):
                    respostas.append(mensagem)
            for resposta in respostas:
                fila.put_nowait(resposta)
        anterior = self._run_id
        self.__dict__.update(novo.__dict__)
        self.controle.registrar = self._registrar
        self._registrar("simulacao_resetada", "manual", {"execucao_anterior": anterior}, {"configuracoes_preservadas": True})

    def _aplicar_comandos(self) -> bool:
        while self._pendentes:
            command_id = self._pendentes.popleft()
            registro = self._comandos[command_id]
            erro_comando = None
            if isinstance(registro.parametros, ParametrosReset):
                try:
                    self._reiniciar(registro)
                    aplicado = True
                except FalhaProlog as erro:
                    aplicado, erro_comando = False, f"Não foi possível reiniciar o controlador: {erro}"
            elif isinstance(registro.parametros, ConfiguracaoVelocidade):
                anterior = self.velocidade_simulacao
                self.velocidade_simulacao = registro.parametros.multiplicador
                self._registrar("velocidade_configurada", "manual", {"anterior": anterior},
                                {"multiplicador": self.velocidade_simulacao})
                aplicado = True
            elif isinstance(registro.parametros, ConfiguracaoOperacao):
                if registro.parametros.modo == "neural" and self.transito.erro:
                    aplicado, erro_comando = False, self.transito.erro
                else:
                    anterior = self.operacao.model_dump()
                    self.operacao = registro.parametros.model_copy(deep=True)
                    self.controle.adaptativo = self.operacao.modo != "paradigmas"
                    self._diagnostico_transito = None
                    self._assinatura_decisao = None
                    self._registrar("operacao_configurada", "manual", {"anterior": anterior}, self.operacao.model_dump())
                    aplicado = True
            elif isinstance(registro.parametros, ConfiguracaoControlador):
                anterior = self.configuracao_controlador.model_dump()
                try:
                    novo = (self.controlador if registro.parametros.controlador == self.configuracao_controlador.controlador
                            else criar_controlador(registro.parametros.controlador, self.controle.configuracao))
                except FalhaProlog as erro:
                    erro_comando = (f'{erro}. Seleção rejeitada; controlador ativo permanece '
                                    f'{self.configuracao_controlador.controlador}.')
                    self._falha_controlador = erro_comando
                    self._registrar("falha_controlador", "logico", {"command_id": command_id, "etapa": "ativacao"},
                                    {"erro": erro_comando})
                    aplicado = False
                else:
                    if novo is not self.controlador:
                        self.fechar()
                    self.controlador = novo
                    self.operacao.modo = "paradigmas"
                    self.controle.adaptativo = False
                    self._diagnostico_transito = None
                    self.configuracao_controlador = registro.parametros.model_copy(deep=True)
                    self._falha_controlador = None
                    self._assinatura_decisao = None
                    self._registrar("controlador_configurado", "manual", {"command_id": command_id, "anterior": anterior},
                                    {"nova": self.configuracao_controlador.model_dump(), "exploracao": True})
                    aplicado = True
            elif isinstance(registro.parametros, ConfiguracaoNeural):
                try:
                    self.neurais.validar_selecao(registro.parametros.modelo)
                except ValueError as erro:
                    aplicado, erro_comando = False, str(erro)
                    self._registrar("modelo_neural_rejeitado", "manual", registro.comando.model_dump(), {"erro": erro_comando})
                else:
                    anterior = self.modelo_neural
                    self.modelo_neural = registro.parametros.modelo
                    self._assinatura_decisao = None
                    self._registrar("modelo_neural_configurado", "manual", {"command_id": command_id, "anterior": anterior},
                                    {"modelo": self.modelo_neural, "exploracao": True})
                    aplicado = True
            elif isinstance(registro.parametros, ConfiguracaoGerador):
                anterior = self.gerador.configuracao.model_dump()
                self.gerador.configurar(registro.parametros, (self._step - 1) / 10)
                self._registrar("gerador_configurado", "manual", {"command_id": command_id, "anterior": anterior},
                                {"nova": registro.parametros.model_dump()})
                aplicado = True
            else:
                aplicado = self._solicitar(registro.parametros, "manual", registro.parametros.quantidade, command_id)
            registro.resultado = RespostaComando(command_id=command_id, confirmacao=ConfirmacaoComando(
                status="aplicado" if aplicado else "rejeitado", passo_aplicacao=self._step if aplicado else None,
                erro=None if aplicado else erro_comando or self._motivo_interrupcao,
            ))
            for responder in registro.respostas:
                responder(registro.resultado.model_copy(deep=True))
            registro.respostas.clear()
            if isinstance(registro.parametros, ParametrosReset) and aplicado:
                self._resets_confirmados[command_id] = registro
                return True
        return False

    def _interromper(self, motivo: str) -> None:
        if not self._motivo_interrupcao:
            self._motivo_interrupcao = motivo
            self._registrar("limite_atingido", "motor", {}, {"motivo": motivo})

    def _solicitar(self, parametros, fonte: str, quantidade: int, command_id: str | None = None) -> bool:
        self._solicitados[fonte] += quantidade
        vagas = max(0, self._limite_pendentes - sum(len(fila) for fila in self._entradas.values()))
        aceitos = min(quantidade, vagas) if not self._motivo_interrupcao else 0
        if fonte == "manual" and aceitos < quantidade:
            aceitos = 0  # lote manual atômico
        recusados = quantidade - aceitos
        if recusados:
            self._recusados[fonte] += recusados
            self._interromper("Limite técnico de pendências atingido")
            self._registrar("chegadas_recusadas", fonte, {"quantidade": recusados, **parametros.model_dump(exclude={"quantidade"})}, {})
        for _ in range(aceitos):
            categoria = parametros.categoria
            if isinstance(parametros, ParametrosPedestre):
                origem = f"{parametros.travessia}:{parametros.lado}"
                destino = f"{parametros.travessia}:{'B' if parametros.lado == 'A' else 'A'}"
                trajetoria = parametros.travessia
                dimensoes = DIMENSOES_PEDESTRE
                posicao = posicoes_acesso(origem)[0]
            else:
                origem = parametros.origem
                perfil = PERFIS[categoria]
                destino, trajetoria = TRAJETORIAS[origem].destino, f"{origem}-seguir_em_frente"
                dimensoes = perfil.dimensoes
                posicao = TRAJETORIAS[origem].posicao(perfil.distancia_inicial, dimensoes.altura)
            self._sequencia_participante += 1
            participante = Participante(
                id=f"{self._run_id}:{categoria}:{self._sequencia_participante}", categoria=categoria,
                origem=origem, destino=destino, trajetoria=trajetoria, posicao=posicao,
                estado="aguardando_entrada", instante_solicitado=self._step / 10, instante_inserido=None,
                solicitacao_prioritaria=getattr(parametros, "solicitacao_prioritaria", False),
                dimensoes=dimensoes.model_copy(deep=True), fonte=fonte,
            )
            self._entradas[origem].append(participante)
            self._registrar("travessia_solicitada" if categoria == "pedestre" else "insercao_solicitada", fonte,
                            {**parametros.model_dump(), "quantidade": 1, "command_id": command_id}, {"participante_id": participante.id})
            if participante.solicitacao_prioritaria:
                self._registrar("emergencia_solicitada", fonte, {"participante_id": participante.id, "origem": origem}, {})
        return aceitos == quantidade

    def _gerar_chegadas(self) -> None:
        for chave, parametros, quantidade in self.gerador.gerar(PASSO_SEGUNDOS):
            self._registrar("chegadas_automaticas", "automatico", {"fonte": chave, "quantidade": quantidade}, {})
            self._solicitar(parametros, "automatico", quantidade)

    def _admitir_participantes(self) -> None:
        for origem, fila in self._entradas.items():
            if not fila:
                continue
            if len(self._participantes) >= self._limite_ativos:
                self._interromper("Limite técnico de participantes ativos atingido")
                break
            candidato = fila[0]
            if candidato.categoria == "pedestre":
                livres = (posicao for posicao in posicoes_acesso(origem) if all(
                    (p.posicao.x - posicao.x) ** 2 + (p.posicao.z - posicao.z) ** 2 >= 1 - 1e-9
                    for p in self._participantes.values() if p.categoria == "pedestre"
                ) and not any(perto_percurso(posicao, pontos) for pontos in self._percursos_pedestres.values()))
                posicao = next(livres, None)
                if posicao is None:
                    continue
                participante = fila.popleft()
                participante.posicao = posicao
                participante.instante_inserido = participante.instante_inicio_espera = self._step / 10
                participante.estado = "aguardando_travessia"
                self._participantes[participante.id] = participante
                self._passos_insercao[participante.id] = self._step
                self._admitidos[participante.fonte] += 1
                self._registrar("participante_inserido", origem, {"participante_id": participante.id}, {})
                self._registrar("inicio_espera", origem, {"participante_id": participante.id, "motivo": "aguardando_travessia"}, {})
                continue
            # FIFO por origem, até uma admissão por faixa neste passo.
            for _ in FAIXAS:
                if not fila:
                    break
                if len(self._participantes) >= self._limite_ativos:
                    self._interromper("Limite técnico de participantes ativos atingido")
                    break
                candidato = fila[0]
                perfil = PERFIS[candidato.categoria]
                livres = []
                for faixa in FAIXAS:
                    veiculos = [p for p in self._participantes.values()
                                if p.origem == origem and p.faixa == faixa]
                    ocupada = any(
                        self._distancias[p.id] - perfil.distancia_inicial <
                        (p.dimensoes.comprimento + candidato.dimensoes.comprimento) / 2 + perfil.distancia_minima
                        for p in veiculos
                    )
                    if not ocupada:
                        # Extensão física da aproximação ocupada; sem sorteios extras.
                        carga = sum(p.dimensoes.comprimento + PERFIS[p.categoria].distancia_minima
                                    for p in veiculos if p.id not in self._autorizados)
                        livres.append((carga, faixa != self._proxima_faixa[origem], faixa))
                if not livres:
                    break
                faixa = min(livres)[2]
                self._proxima_faixa[origem] = FAIXAS[1] if faixa == FAIXAS[0] else FAIXAS[0]
                participante = fila.popleft()
                participante.faixa = faixa
                participante.posicao = TRAJETORIAS_POR_FAIXA[origem, faixa].posicao(
                    perfil.distancia_inicial, participante.dimensoes.altura)
                participante.instante_inserido = self._step / 10
                participante.estado = "em_movimento"
                self._participantes[participante.id] = participante
                self._admitidos[participante.fonte] += 1
                self._passos_insercao[participante.id] = self._step
                self._distancias[participante.id] = perfil.distancia_inicial
                self._registrar("participante_inserido", origem,
                                {"participante_id": participante.id, "faixa": faixa}, {})

    def _mover_participantes(self) -> None:
        # Atualiza da frente para trás. Cada seguidor usa a posição final do líder
        # neste tick, preservando ordem, comprimentos e a folga do próprio seguidor.
        for (origem, faixa_veicular), trajetoria in TRAJETORIAS_POR_FAIXA.items():
            fila = sorted(
                (p for p in self._participantes.values() if p.origem == origem and p.faixa == faixa_veicular),
                key=lambda p: (-self._distancias[p.id], p.id),
            )
            lider: Participante | None = None
            for participante in fila:
                perfil = PERFIS[participante.categoria]
                anterior = self._distancias[participante.id]
                retencao = DISTANCIA_RETENCAO - FOLGA_RETENCAO - participante.dimensoes.comprimento / 2
                permitido = participante.id in self._autorizados or participante.trajetoria in self.controle.permissoes()
                limite = float("inf") if permitido else retencao
                motivo = "aguardando_retencao"
                if lider:
                    limite_lider = self._distancias[lider.id] - (
                        lider.dimensoes.comprimento + participante.dimensoes.comprimento
                    ) / 2 - perfil.distancia_minima
                    if limite_lider < limite:
                        limite, motivo = limite_lider, "aguardando_fila"
                novo = self._passos_insercao[participante.id] == self._step
                desejada = anterior if novo else anterior + perfil.velocidade * PASSO_SEGUNDOS
                distancia = round(min(desejada, limite), 6)
                if permitido and distancia > retencao + 1e-6 and participante.id not in self._autorizados:
                    self._autorizar(participante)
                self._distancias[participante.id] = distancia
                participante.posicao = trajetoria.posicao(distancia, participante.dimensoes.altura)
                parado = not novo and abs(distancia - anterior) / PASSO_SEGUNDOS < 0.1
                if parado:
                    participante.espera_interna = round(participante.espera_interna + PASSO_SEGUNDOS, 6)
                estado = motivo if parado else "em_movimento"
                if parado and participante.instante_inicio_espera is None:
                    participante.instante_inicio_espera = self._step / 10
                    self._registrar("inicio_espera", origem, {
                        "participante_id": participante.id, "motivo": motivo,
                    }, {})
                elif not parado:
                    participante.instante_inicio_espera = None
                participante.estado = estado
                lider = participante
        # Retira somente quando toda a carroceria ultrapassou a borda de destino.
        for participante in tuple(self._participantes.values()):
            if participante.categoria != "pedestre" and self._distancias[participante.id] - participante.dimensoes.comprimento / 2 >= ORIGEM_TRAJETORIA + BORDA_VIA:
                self._concluir(participante)

    def _autorizar(self, participante):
        self._autorizados.add(participante.id)
        participante.instante_autorizacao = self._step / 10
        self._registrar("movimento_autorizado", "motor", {"participante_id": participante.id,
                        "trajetoria": participante.trajetoria}, {"fase": self.controle.fase})

    def _ocupacoes(self):
        ocupacoes = {m: [] for m in MOVIMENTOS}
        for p in self._participantes.values():
            if p.id not in self._autorizados:
                continue
            # Guarda conservadora: mantém ocupado até a traseira passar da
            # travessia oposta, mais a mesma margem usada na retenção.
            if p.categoria == "pedestre" or self._distancias[p.id] - p.dimensoes.comprimento / 2 <= 39.725:
                ocupacoes[p.trajetoria].append(p.id)
        return ocupacoes

    def _concluir(self, participante):
        self.metricas.concluir(participante, self._step / 10)
        self._registrar("percurso_concluido", participante.origem, {"participante_id": participante.id,
            "categoria": participante.categoria, "fonte": participante.fonte}, {
            "instante_solicitado": participante.instante_solicitado,
            "instante_inserido": participante.instante_inserido,
            "instante_autorizacao": participante.instante_autorizacao,
            "instante_concluido": self._step / 10, "espera_interna": participante.espera_interna,
        })
        del self._participantes[participante.id]
        self._distancias.pop(participante.id, None)
        self._passos_insercao.pop(participante.id, None)
        self._autorizados.discard(participante.id)
        self._percursos_pedestres.pop(participante.id, None)

    def _mover_pedestres(self):
        pedestres = [p for p in self._participantes.values() if p.categoria == "pedestre"]
        # Flush lógico da fila: autoriza todo o lote no mesmo tick, antes de mover.
        # Cada pessoa mantém seu percurso; quem iniciou termina mesmo no vermelho.
        permissoes = self.controle.permissoes()
        for p in pedestres:
            if p.id not in self._autorizados and p.trajetoria in permissoes:
                self._percursos_pedestres[p.id] = percurso(p)
                self._autorizar(p)
                p.instante_inicio_espera = None
        for p in pedestres:
            if p.id not in self._autorizados:
                if self._passos_insercao[p.id] != self._step:
                    p.espera_interna = round(p.espera_interna + PASSO_SEGUNDOS, 6)
                continue
            p.estado = "em_travessia"
            pontos = self._percursos_pedestres[p.id]
            destino = pontos[1]
            x, z = passo_livre(p, destino, VELOCIDADE_PEDESTRE * PASSO_SEGUNDOS, pedestres)
            dx, dz = x - p.posicao.x, z - p.posicao.z
            p.posicao.x, p.posicao.z = x, z
            if hypot(dx, dz) > 1e-9:
                p.posicao.rotacao_y = atan2(dx, dz)
            else:
                p.espera_interna = round(p.espera_interna + PASSO_SEGUNDOS, 6)
            pontos[0] = (x, z)
            if hypot(x - destino[0], z - destino[1]) < 1e-9:
                pontos.pop(0)
            if len(pontos) == 1:
                self._concluir(p)

    def _decidir_transito(self):
        proposta, avaliacoes, criterio, calculo, ocupados = self.transito.decidir(self)
        elegivel = next((a["elegivel"] for a in avaliacoes if a["fase"] == proposta.fase), False)
        self.controle.aplicar(proposta, self._step, ocupados, elegivel=elegivel,
                              prioridade_emergencia=self.operacao.modo == "neural" and criterio == "emergencia")
        nome = self.operacao.modelo if self.operacao.modo == "neural" else "urbano"
        self._diagnostico_transito = {"modo": self.operacao.modo, "modelo": nome,
            "criterio": criterio, "comparacao": calculo,
            "verde_minimo_segundos": self.controle.verde_minimo / 10,
            "verde_maximo_segundos": None}
        self._ultima_decisao = Decisao(decision_id=f"{self._run_id}:decisao:{self._step}",
            step=self._step, controlador=self.operacao.modo, politica=f"transito_{nome}_v1",
            modelo=nome, candidatas=[a["fase"] for a in avaliacoes], avaliacoes=avaliacoes,
            motivos=[criterio, proposta.motivo], proposta=asdict(proposta),
            resultado_validacao=self.controle.ultima_validacao.copy())
        assinatura = (self.operacao.modo, nome, proposta.acao, proposta.fase, criterio,
                     self.controle.estado, self.controle.fase)
        if assinatura != self._assinatura_decisao:
            self._registrar("decisao_controlador", self.operacao.modo,
                            {"transito": self._diagnostico_transito}, self._ultima_decisao.model_dump(mode="json"))
            self._assinatura_decisao = assinatura
        return True

    def _decidir(self):
        if self.operacao.modo != "paradigmas":
            return self._decidir_transito()
        ocupados = tuple(m for m, ids in self._ocupacoes().items() if ids)
        config = self.configuracao_controlador
        relogio = self.controle.leitura(self._step, ocupados)
        pedidos = tuple(Solicitacao(p.id, p.trajetoria, p.categoria, p.instante_solicitado, p.solicitacao_prioritaria)
                        for p in (*self._participantes.values(), *(p for fila in self._entradas.values() for p in fila))
                        if p.instante_autorizacao is None)
        fases = tuple(Fase(f, movimentos, *self.controle.admissibilidade(f, self._step, ocupados))
                      for f, movimentos in sorted(self.controle.fases.items()))
        entrada = EstadoDecisao(relogio, self._step / 10, fases, pedidos, self.controle.configuracao.verde_passos,
                               config.limiar_espera, config.prioridade_ambulancia, config.prioridade_onibus,
                               tuple((a, b) for a, linha in self.controle.conflitos.items() for b, conflito in linha.items() if conflito))
        if config.controlador == "baseline":
            proposta = self.controlador.propor(relogio)
            criterio = "sequencia_fixa"
            avaliacoes = tuple(Avaliacao(f.id, sum(p.movimento in f.movimentos for p in pedidos),
                max((self._step / 10 - p.instante for p in pedidos if p.movimento in f.movimentos), default=0),
                criterio, (0, 0., 0., f.id), f.admissivel, f.bloqueio) for f in fases)
        else:
            try:
                decisao = self.controlador.propor(entrada)
            except FalhaProlog as erro:
                # Congela toda a simulação antes de mover/autorizar participantes.
                # Fase, ocupações e autorizações existentes permanecem preservadas.
                self._falha_controlador = f'{erro}. Execução interrompida; reinicie o motor para um novo ensaio.'
                self._motivo_interrupcao = self._falha_controlador
                self._ultima_decisao = None
                self.controle.ultima_validacao = {"aceita": False, "motivo": self._falha_controlador}
                self._registrar("falha_controlador", "logico",
                                {"etapa": "decisao", "entrada": json.loads(json.dumps(asdict(entrada)))},
                                {"erro": self._falha_controlador, "interrompido": True})
                return False
            proposta, avaliacoes, criterio = decisao.proposta, decisao.avaliacoes, decisao.criterio
        avaliacoes_neurais = []
        for a in avaliacoes:
            # Na baseline a solicitação é programada pelo relógio (sequência
            # fixa); nos adaptativos ela vem da demanda pendente da fase.
            solicitado = proposta.fase == a.fase if config.controlador == "baseline" else a.demanda > 0
            calculo = self.neurais.avaliar(self.modelo_neural, int(solicitado), int(a.admissivel))
            avaliacoes_neurais.append({**asdict(a), "chave": list(a.chave),
                "elegivel": calculo["elegivel"], "neural": calculo,
                "origem_solicitacao": "sequencia_fixa" if config.controlador == "baseline" else "demanda"})
        elegivel = next((a["elegivel"] for a in avaliacoes_neurais if a["fase"] == proposta.fase), False)
        # A elegibilidade governa a abertura. Fechamento, amarelo e liberação
        # continuam avançando mesmo quando x2=0, sem encurtar as proteções.
        self.controle.aplicar(proposta, self._step, ocupados, elegivel=elegivel)
        self._ultima_decisao = Decisao(
            decision_id=f"{self._run_id}:decisao:{self._step}", step=self._step, controlador=config.controlador,
            politica="fixa_referencia" if config.controlador == "baseline" else "prioridades_demanda_v1",
            modelo=self.modelo_neural, candidatas=[a.fase for a in avaliacoes],
            avaliacoes=avaliacoes_neurais,
            motivos=[criterio, proposta.motivo], proposta=asdict(proposta),
            resultado_validacao=self.controle.ultima_validacao.copy())
        assinatura = (config.model_dump_json(), self.modelo_neural,
                      tuple((a["fase"], tuple(a["neural"]["entradas"])) for a in avaliacoes_neurais), proposta.acao, proposta.fase, criterio, self.controle.estado,
                      self.controle.fase, self.controle.ultima_validacao["aceita"], self.controle.ultima_validacao["motivo"])
        if assinatura != self._assinatura_decisao:
            self._registrar("decisao_controlador", config.controlador, {"entrada": json.loads(json.dumps(asdict(entrada)))},
                            self._ultima_decisao.model_dump(mode="json"))
            self._assinatura_decisao = assinatura
        alertas = {a.fase for a in avaliacoes if a.demanda and a.maior_espera > config.limiar_espera}
        for fase in sorted(alertas - self._alertas_espera):
            self._registrar("limiar_espera_excedido", "motor", {"fase": fase, "limiar": config.limiar_espera}, {})
        self._alertas_espera = alertas
        return True

    def avancar(self, *, publicar: bool = True) -> Instantaneo:
        estado = self._avancar(publicar=publicar, capturar=True)
        assert estado is not None
        return estado

    def _avancar(self, *, publicar: bool, capturar: bool = False) -> Instantaneo | None:
        reset_pendente = any(isinstance(self._comandos[c].parametros, ParametrosReset) for c in self._pendentes)
        if self._motivo_interrupcao and not reset_pendente:
            estado = self.instantaneo()
            if publicar:
                for fila in tuple(self._assinantes):
                    self.enfileirar(fila, estado)
            return estado
        self._step += 1
        reiniciado = self._aplicar_comandos()
        if reiniciado or (reset_pendente and self._motivo_interrupcao):
            estado = self.instantaneo()
            for fila in tuple(self._assinantes):
                self.enfileirar(fila, estado)
            return estado
        self._gerar_chegadas()
        self._admitir_participantes()
        if self._decidir():
            self._mover_participantes()
            self._mover_pedestres()
        self.metricas.registrar_filas(list(self._participantes.values()),
            [p for fila in self._entradas.values() for p in fila], PASSO_SEGUNDOS)
        # Os acumuladores acima sempre avançam. Montar cópias completas só é
        # necessário para a tela, a amostra histórica ou o chamador síncrono.
        if not (publicar or capturar or self._step % 10 == 0 or self._motivo_interrupcao):
            return None
        estado = self.instantaneo()
        if self._step % 10 == 0:
            self._historico_metricas.append(self._amostra_metricas(estado))
        if publicar or self._motivo_interrupcao:
            for fila in tuple(self._assinantes):
                self.enfileirar(fila, estado)
        return estado

    def configuracao_experimento(self):
        return {"controle": self.controle.configuracao.model_dump(mode="json"),
                "controlador": self.configuracao_controlador.model_dump(mode="json"),
                "operacao": self.operacao.model_dump(),
                "modelo_neural": self.modelo_neural, "gerador": self.gerador.configuracao.model_dump(mode="json"),
                "passo_segundos": PASSO_SEGUNDOS,
                "velocidade_simulacao": self.velocidade_simulacao,
                "limites": {"ativos": self._limite_ativos, "pendentes": self._limite_pendentes}}

    def _amostra_metricas(self, estado):
        return {"step": estado.step, "tempo_simulado": estado.simulation_time, "fase": estado.fase,
                "estado_transicao": estado.estado_transicao,
                "controlador": self.configuracao_controlador.controlador if self.operacao.modo == "paradigmas" else self.operacao.modo,
                "modelo": self.modelo_neural if self.operacao.modo == "paradigmas" else self.operacao.modelo if self.operacao.modo == "neural" else "urbano",
                "metricas": estado.metricas, "filas": estado.filas,
                "propostas_bloqueadas": self.controle.bloqueios,
                "solicitados": dict(self._solicitados), "admitidos": dict(self._admitidos), "recusados": dict(self._recusados)}

    def exportar_experimento(self):
        """Recorte coerente sem await; baixar não encerra nem reinicia o ensaio."""
        estado = self.instantaneo()
        amostras = list(self._historico_metricas)
        atual = self._amostra_metricas(estado)
        if amostras[-1]["step"] == self._step:
            amostras[-1] = atual
        else:
            amostras.append(atual)
        return {"schema_version": "1.0", "versao_motor": "1.8", "run_id": self._run_id,
                "intervalo_observado": {"inicio": 0, "fim": self._step / 10, "unidade": "segundos_simulados"},
                "passo_exportacao": self._step, "motivo_encerramento": self._motivo_interrupcao or "em_andamento",
                "configuracao_inicial": self._configuracao_inicial,
                "configuracao_atual": self.configuracao_experimento(),
                "modelos_neurais": self.neurais.disponibilidade(), "pesos_treinados": self.neurais.pesos_exportaveis(),
                "treinamento_transito": self.transito.documento,
                "eventos": [e.model_dump(mode="json") for e in self._eventos],
                "historico_fases": [e.model_dump(mode="json") for e in self._eventos if e.tipo == "transicao_semaforica"],
                "metricas": estado.metricas, "demanda": estado.demanda,
                "participantes_ativos": [p.model_dump(mode="json") for p in estado.participantes],
                "participantes_pendentes": [p.model_dump(mode="json") for fila in self._entradas.values() for p in fila],
                "amostragem_metricas_segundos": 1, "historico_metricas": amostras}

    def fechar(self) -> None:
        fechar = getattr(self.controlador, "fechar", None)
        if fechar:
            fechar()

    async def executar(self) -> None:
        loop = asyncio.get_running_loop()
        ultima_publicacao = loop.time()
        proximo_passo = ultima_publicacao + PASSO_SEGUNDOS / self.velocidade_simulacao
        while True:
            await asyncio.sleep(max(0, proximo_passo - loop.time()))
            agora = loop.time()
            # Só a transmissão visual é limitada. Cálculos e histórico continuam
            # em TODOS os passos; comandos e resets recebem estado imediato.
            publicar = (self.velocidade_simulacao == 1 or bool(self._pendentes)
                        or agora - ultima_publicacao >= INTERVALO_PUBLICACAO)
            self._avancar(publicar=publicar)
            if publicar:
                ultima_publicacao = agora
            fator = 1 if self._motivo_interrupcao else self.velocidade_simulacao
            # Sem dívida de tempo: sob carga, reduz o ritmo real, sem pular passos
            # nem aumentar Δt. sleep(0) também permite atender comandos e sockets.
            proximo_passo = max(proximo_passo + PASSO_SEGUNDOS / fator, loop.time())
