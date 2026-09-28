"""Fábrica de adaptadores; a política é implementada em cada paradigma."""
from motor_python.controle import PoliticaFixa
from .imperativo import ControladorImperativo
from .orientado_objetos import ControladorOrientadoObjetos
from .funcional import ControladorFuncional


def criar_controlador(nome, configuracao_controle):
    if nome == 'baseline':
        return PoliticaFixa(configuracao_controle)
    if nome == 'logico':
        from .adaptador_prolog import AdaptadorProlog
        return AdaptadorProlog()
    return {'imperativo': ControladorImperativo, 'orientado_objetos': ControladorOrientadoObjetos,
            'funcional': ControladorFuncional}[nome]()
