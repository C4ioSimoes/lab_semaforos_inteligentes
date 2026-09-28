import * as THREE from 'three';
import { materialCurvo } from './curvatura';
import type { Participante } from './contratos';
import { coresCategorias, type CategoriaVeiculo } from './categorias';

/** A sincronização somente copia os dados oficiais. Não há velocidade ou integração local. */
export function criarCamadaParticipantes() {
  const grupo = new THREE.Group();
  grupo.name = 'participantes';
  const geometria = new THREE.BoxGeometry(1, 1, 1, 2, 1, 4);
  const geometriaPedestre = new THREE.CapsuleGeometry(0.5, 1, 4, 8);
  const materiais = Object.fromEntries(Object.entries(coresCategorias).map(([categoria, cores]) =>
    [categoria, cores.map(materialCurvo)],
  )) as Record<CategoriaVeiculo, THREE.MeshBasicMaterial[]>;
  const modelos = new Map<string, THREE.Group>();
  let execucao: string | undefined;

  function remover(id: string) {
    const modelo = modelos.get(id);
    modelo?.removeFromParent();
    modelos.delete(id);
  }

  return {
    grupo,
    atualizar(runId: string, participantes: readonly Participante[]) {
      if (execucao !== runId) {
        for (const id of modelos.keys()) remover(id);
        execucao = runId;
      }
      const presentes = new Set(participantes.map((p) => p.id));
      for (const id of modelos.keys()) if (!presentes.has(id)) remover(id);
      for (const participante of participantes) {
        let modelo = modelos.get(participante.id);
        if (!modelo) {
          modelo = new THREE.Group();
          modelo.name = participante.id;
          modelo.userData.id = participante.id;
          const pedestre = participante.categoria === 'pedestre';
          const corpo = new THREE.Mesh(pedestre ? geometriaPedestre : geometria,
            pedestre ? materiais.pedestre[0] : materiais[participante.categoria]);
          corpo.name = 'corpo';
          modelo.add(corpo);
          modelos.set(participante.id, modelo);
          grupo.add(modelo);
        }
        const corpo = modelo.getObjectByName('corpo') as THREE.Mesh;
        const { largura, altura, comprimento } = participante.dimensoes;
        const pedestre = participante.categoria === 'pedestre';
        corpo.scale.set(largura, pedestre ? altura / 2 : altura, comprimento);
        corpo.material = pedestre ? materiais.pedestre[0] : materiais[participante.categoria];
        const { x, y, z, rotacao_y } = participante.posicao;
        modelo.position.set(x, y, z);
        modelo.rotation.y = rotacao_y;
      }
    },
    descartar() {
      for (const id of modelos.keys()) remover(id);
      grupo.removeFromParent();
      geometria.dispose();
      geometriaPedestre.dispose();
      Object.values(materiais).flat().forEach((material) => material.dispose());
    },
  };
}
