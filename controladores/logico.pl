:- module(logico, [decidir_json/2]).
:- use_module(library(http/json)).
:- use_module(library(lists)).
:- use_module(library(apply)).

% Fatos da política prioridades_demanda_v1. O estado é um argumento local
% de cada consulta: nenhum assert/retract ou pedido persiste entre ticks.
precedencia(emergencia, 0).
precedencia(limiar_espera, 1).
precedencia(onibus, 2).
precedencia(maior_demanda, 3).
precedencia(sem_demanda, 4).

conflito(E, A, B) :- member([A, B], E.conflitos), !.
conflito(E, A, B) :- member([B, A], E.conflitos).
compativel(E, F) :-
    \+ (member(A, F.movimentos), member(B, F.movimentos), conflito(E, A, B)).
livre(E, F) :-
    \+ (member(A, F.movimentos), member(B, E.relogio.ocupados), conflito(E, A, B)).

% A guarda temporal comum é fornecida pelo motor. Esta regra também verifica
% conflitos declarados. Prioridade escolhe um destino; não concede permissão.
admissibilidade(E, F, true, null) :-
    F.admissivel == true, compativel(E, F), livre(E, F), !.
admissibilidade(_, F, false, Bloqueio) :- F.admissivel == false, !, Bloqueio = F.bloqueio.
admissibilidade(_, _, false, "Conflito entre movimentos ou ocupação existente.").

pedido_da_fase(F, P) :- memberchk(P.movimento, F.movimentos).
instante(P, T) :- T = P.instante.
emergencia(P) :- P.categoria == "ambulancia", P.prioritaria == true.
onibus(P) :- P.categoria == "onibus".
mais_antigo(Pedidos, T) :- maplist(instante, Pedidos, Tempos), min_list(Tempos, T).
espera(_, [], 0.0, 0.0) :- !.
espera(E, Pedidos, Antiga, Espera) :-
    mais_antigo(Pedidos, Antiga), Diferenca is E.tempo - Antiga,
    format(string(Decimal), '~6f', [Diferenca]), number_string(Arredondada, Decimal),
    Espera is max(0.0, Arredondada).

prioridade(_, [], _, _, sem_demanda, 0.0, 0.0) :- !.
prioridade(E, Pedidos, _, _, emergencia, T, 0.0) :-
    E.prioridade_ambulancia == true, include(emergencia, Pedidos, Emergencias),
    Emergencias \= [], mais_antigo(Emergencias, T), !.
prioridade(E, _, _, Espera, limiar_espera, Negativa, 0.0) :-
    Espera > E.limiar_espera, Negativa is -Espera, !.
prioridade(E, Pedidos, _, _, onibus, T, 0.0) :-
    E.prioridade_onibus == true, include(onibus, Pedidos, Onibus),
    Onibus \= [], mais_antigo(Onibus, T), !.
prioridade(_, Pedidos, Antiga, _, maior_demanda, Negativa, Antiga) :-
    length(Pedidos, N), Negativa is -N.

avaliar(E, F, Avaliacao) :-
    include(pedido_da_fase(F), E.solicitacoes, Pedidos), length(Pedidos, N),
    espera(E, Pedidos, Antiga, Espera),
    prioridade(E, Pedidos, Antiga, Espera, Criterio, Primeiro, Segundo),
    precedencia(Criterio, Ordem), admissibilidade(E, F, Admissivel, Bloqueio),
    PrimeiroNumero is float(Primeiro), SegundoNumero is float(Segundo),
    Avaliacao = _{fase:F.id, demanda:N, maior_espera:Espera, criterio:Criterio,
                  chave:[Ordem, PrimeiroNumero, SegundoNumero, F.id], admissivel:Admissivel, bloqueio:Bloqueio}.

escolher(Avaliacoes, Escolhida, Criterio) :-
    findall(Chave-A, (member(A, Avaliacoes), A.demanda > 0, Chave = A.chave), Pares),
    keysort(Pares, Ordenadas),
    ( Ordenadas = [_-Escolhida|_] -> Criterio = Escolhida.criterio
    ; Escolhida = nenhum, Criterio = sem_demanda ).

propor(E, _, _, _{acao:manter, fase:E.relogio.fase,
    motivo:"Preservar o tempo de atendimento e movimentos autorizados."}) :-
    E.relogio.estado == "atendimento", E.relogio.decorrido_passos < E.verde_passos, !.
propor(_, nenhum, _, _{acao:aguardar, fase:null,
    motivo:"Sem solicitações pendentes; encerrar permissões e aguardar em vermelho."}) :- !.
propor(_, Escolhida, Criterio, _{acao:transicionar, fase:Escolhida.fase, motivo:Motivo}) :-
    format(string(Motivo), 'Prioridade: ~w. Respeitar transição e ocupações.', [Criterio]).

decidir_json(Json, Resposta) :-
    atom_json_dict(Json, E, []),
    maplist(avaliar(E), E.fases, Avaliacoes),
    escolher(Avaliacoes, Escolhida, Criterio), propor(E, Escolhida, Criterio, Proposta),
    atom_json_dict(Resposta, _{proposta:Proposta, avaliacoes:Avaliacoes, criterio:Criterio}, []).
