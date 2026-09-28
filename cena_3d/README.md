# Observatório do cruzamento 3D

Interface TypeScript, HTML, CSS e Three.js. O Python mantém o relógio, as posições,
as filas e as permissões; o navegador apresenta os instantâneos oficiais.

## Executar

Com o motor em `ws://127.0.0.1:8000/ws`:

```bash
cd cena_3d
npm ci
npm run dev
```

Abra o endereço informado pelo Vite. Para outro servidor, configure `VITE_WS_URL`
em `.env.local`. Use `wss://` quando servido por HTTPS.

```bash
npm run build
npm run preview
npx playwright install chromium
npm test
```

Playwright inicia FastAPI na porta 8001 e Vite na 5174, usando a `.venv` da raiz.
Todos os recursos são locais, sem dependências visuais de CDN.

## 1. UI/UX: monitoramento e geração

O painel esquerdo exibe conexão, tempo, fase, veículos, pedestres, fila externa,
vazão e espera média dos percursos concluídos. A inserção manual foi removida da
interface; o comando de inserção permanece disponível no protocolo para ensaios.

Na barra acima da cena, **Geração aleatória** liga/desliga veículos e pedestres
juntos. O slider **Intensidade do trânsito** ajusta as taxas sem botão Aplicar.
Desligar zera ambos os multiplicadores; participantes presentes e pedidos já
aceitos continuam sendo atendidos. Mover o slider desligado prepara a próxima ativação.

`src/geracao.ts` traduz 0–100 em um fator de 0,4–2,0. Por aproximação, as taxas
base por minuto são 12 carros, 3 motos, 1 ônibus e 0,2 ambulância; por travessia,
8 pedestres, divididos entre A/B. A semente recebida do motor é preservada.
São taxas médias Poisson, não quantidades garantidas. Comandos em andamento
preservam a última edição; rejeição e reconexão restauram o estado oficial.

**Configurações do experimento** mantém paradigmas, prioridades, redes neurais,
diagnósticos e exportações JSON/CSV recolhidos. Os separadores aceitam setas,
Home e End. Switch e slider têm rótulos acessíveis, foco visível e controle por
teclado; em telas estreitas a cena aparece primeiro, sem rolagem horizontal.

O layout usa duas colunas e espaçamento consistente:

```css
main {
  display: grid;
  grid-template-columns: 252px minmax(0, 1fr);
  gap: 20px;
}
.painel-dados {
  padding: 22px 18px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
}
```

Veja `index.html` e `src/style.css` para os componentes e regras responsivas.

## 2. Pedestres: liberação coletiva

`Motor._mover_pedestres`, em `../motor_python/motor.py`, autoriza todo o lote
admitido nas travessias verdes **antes** de avançar qualquer participante:

```python
permissoes = self.controle.permissoes()
for p in pedestres:
    if p.id not in self._autorizados and p.trajetoria in permissoes:
        self._percursos_pedestres[p.id] = percurso(p)
        self._autorizar(p)
        p.instante_inicio_espera = None
```

Cada ID tem seu próprio percurso. O estado passa a `em_travessia`, retirando-o
da fila de espera sem remover a entidade da simulação. A conclusão limpa somente
seu percurso. Chegadas durante o verde também recebem autorização. No vermelho,
novas autorizações param, enquanto as existentes seguem protegidas pela ocupação.

`../motor_python/pedestres.py` organiza 16 posições por acesso em filas alinhadas
a dois sentidos separados da faixa. Todos começam a caminhar na abertura; folga
mínima de 0,8 e preferência local nas esquinas compartilhadas podem limitar o
avanço individual. Isso evita sobreposição sem serializar a travessia inteira.
Pedidos ainda externos aguardam espaço para admissão. O modelo é didático, sem
calibração de dinâmica de multidões.

## 3. Vias extensas e névoa

`BORDA_VIA = 90` em `src/cruzamento.ts` e `../motor_python/movimento.py` amplia
a extensão anterior de ±30 para ±90. Geometria, marcações, calçadas, admissão e
saída usam essa extensão. A retenção e a proteção do cruzamento continuam nas
mesmas coordenadas. Atualize ambas as constantes se mudar novamente a extensão.

`src/cena.ts` configura a mesma cor para fundo e névoa:

```ts
cena.background = new THREE.Color('#bcbcbc');
cena.fog = new THREE.Fog(cena.background, 45, 85);
```

O Fog padrão depende da profundidade em relação à câmera. Para este cenário
orbital, `src/curvatura.ts` fornece a distância radial ao centro no shader:

```glsl
#ifdef USE_FOG
  vFogDepth = length(mundoCurvo.xz);
#endif
```

O trecho substitui `#include <fog_vertex>` dentro de `onBeforeCompile`.
Todos os materiais usam a mesma curva e névoa: ruas, sinalização e participantes
somem gradualmente entre 45 e 85 unidades, antes da borda física em 90. O centro
permanece legível ao girar, aproximar ou usar a vista superior. A posição inicial,
o alvo, os limites e o comportamento da câmera orbital foram preservados.

Referência: [Three.js Fog](https://threejs.org/docs/pages/Fog.html).

## Verificação

Os testes de navegador cobrem sincronização, geração real, slider com alterações
rápidas, rejeição, reconexão, nova execução, câmera, layout móvel e exportações.
Os testes Python incluem liberação simultânea de 30 pessoas por travessia, quatro
travessias concorrentes (120 pessoas), distância física, conclusão, bloqueio de
veículos durante a ocupação e filas veiculares na malha ampliada.
