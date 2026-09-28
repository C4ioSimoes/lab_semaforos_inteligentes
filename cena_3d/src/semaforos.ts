import * as THREE from 'three';
import { materialCurvo } from './curvatura';
import { aproximacoes } from './cruzamento';
import type { CorSemaforo, Instantaneo } from './contratos';

/** Indicadores recebem cores prontas do motor. Não há temporizador ou decisão local. */
export function criarSemaforos() {
  const grupo = new THREE.Group();
  grupo.name = 'grupos-semaforicos';
  const cores = { vermelho: '#ff6b64', amarelo: '#ffce52', verde: '#68df9b' };
  const indicadores = new Map<string, { luzes: Map<CorSemaforo, THREE.MeshBasicMaterial> }>();
  for (const via of aproximacoes) {
    const braco = new THREE.Group();
    braco.rotation.y = via.rotacao;
    grupo.add(braco);
    for (const pedestre of [false, true]) {
      const id = pedestre ? `${via.id}-TR` : via.id;
      const modelo = new THREE.Group();
      modelo.name = `semaforo-${id}`;
      modelo.userData.id = modelo.name;
      modelo.position.set(pedestre ? 7.1 : -7.4, 0.5, pedestre ? -6.7 : -13.5);
      braco.add(modelo);
      const lampadas: CorSemaforo[] = pedestre ? ['vermelho', 'verde'] : ['vermelho', 'amarelo', 'verde'];
      const caixa = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.45, lampadas.length * 0.85 + 0.3), materialCurvo('#181818'));
      modelo.add(caixa);
      const luzes = new Map<CorSemaforo, THREE.MeshBasicMaterial>();
      lampadas.forEach((cor, i) => {
        const material = materialCurvo('#343434');
        luzes.set(cor, material);
        const luz = new THREE.Mesh(new THREE.SphereGeometry(0.32, 12, 8), material);
        luz.position.set(0, 0.3, (i - (lampadas.length - 1) / 2) * 0.85);
        luz.name = `${id}-${cor}`;
        modelo.add(luz);
      });
      indicadores.set(id, { luzes });
    }
  }
  return {
    grupo,
    atualizar(estado: Pick<Instantaneo, 'semaforos' | 'semaforos_pedestres'>) {
      for (const [id, indicador] of indicadores) {
        const cor = id.endsWith('-TR') ? estado.semaforos_pedestres?.[id] : estado.semaforos[id as keyof typeof estado.semaforos];
        for (const [luz, material] of indicador.luzes) material.color.set(luz === cor ? cores[luz] : '#343434');
      }
    },
  };
}
