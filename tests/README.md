# Testes do back-end

Execute na raiz, com as dependências de `motor_python/requirements-dev.txt` e SWI-Prolog instalados:

```bash
.venv/bin/python -m pytest -q
```

| Assunto | Arquivos |
| --- | --- |
| Quatro paradigmas e integração Prolog | [test_paradigmas.py](test_paradigmas.py), [test_prolog.py](test_prolog.py) |
| AND, validação dos pesos e exportações | [test_neural_exportacao.py](test_neural_exportacao.py) |
| Modos Rede neural e Automático | [test_transito.py](test_transito.py) |
| Relógio, contratos e comunicação | [test_motor.py](test_motor.py) |
| Sinais, conflitos e retenção | [test_controle.py](test_controle.py), [test_retencao.py](test_retencao.py) |
| Geração e inserção de participantes | [test_demanda.py](test_demanda.py), [test_insercao.py](test_insercao.py) |
| Duas faixas por sentido | [test_faixas.py](test_faixas.py) |
| Travessia de pedestres | [test_travessia_coletiva.py](test_travessia_coletiva.py) |
| Reinício e aceleração | [test_reset.py](test_reset.py), [test_velocidade.py](test_velocidade.py) |

Os testes do treinamento AND ficam em [verificar_experimento.py](../experimento_neural/verificar_experimento.py) e usam o ambiente do experimento. Os testes de interface ficam em `cena_3d/tests`.

Os testes de paradigmas comparam decisões para as mesmas entradas. Os ensaios de [experimento_transito](../experimento_transito/README.md) medem resultados de políticas distintas. São verificações com objetivos diferentes.
