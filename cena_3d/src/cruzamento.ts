import * as THREE from 'three';
import { materialCurvo } from './curvatura';

export const BORDA_VIA = 90; // Espelho da extensão física em motor_python/movimento.py.

/** Convenção gráfica provisória: norte = -Z, leste = +X, solo no plano XZ. */
export const aproximacoes = [
  { id: 'N', nome: 'Norte', rotacao: 0 },
  { id: 'S', nome: 'Sul', rotacao: Math.PI },
  { id: 'L', nome: 'Leste', rotacao: -Math.PI / 2 },
  { id: 'O', nome: 'Oeste', rotacao: Math.PI / 2 },
] as const;

export function criarCruzamento(): THREE.Group {
  const grupo = new THREE.Group();
  grupo.name = 'cruzamento-central';
  const materiais = {
    solo: materialCurvo('#bcbcbc'),
    pista: materialCurvo('#383838'),
    calcada: materialCurvo('#d5d5d5'),
    jardim: materialCurvo('#adadad'),
    branco: materialCurvo('#f3f3f3'),
    eixo: materialCurvo('#999999'),
  };
  function plano(pai: THREE.Group, id: string, largura: number, comprimento: number,
    x: number, z: number, y: number, material: THREE.Material) {
    const malha = new THREE.Mesh(new THREE.PlaneGeometry(largura, comprimento, Math.ceil(largura / 2), Math.ceil(comprimento / 2)), material);
    malha.rotation.x = -Math.PI / 2;
    malha.position.set(x, y, z);
    malha.name = id;
    malha.userData.id = id;
    pai.add(malha);
    return malha;
  }
  // Folga entre superfícies evita interseções entre triângulos após a curvatura.
  plano(grupo, 'solo', BORDA_VIA * 2 + 12, BORDA_VIA * 2 + 12, 0, 0, -0.12, materiais.solo);
  plano(grupo, 'intersecao', 12, 12, 0, 0, 0, materiais.pista);
  // Os quatro terrenos acompanham as vias até além do fim da neblina (85).
  // O mesmo material curvo mantém piso, calçadas e horizonte contínuos.
  const inicioCalcada = 6.1;
  const inicioTerreno = 11;
  for (const x of [-1, 1]) for (const z of [-1, 1]) {
    const centroCalcada = (BORDA_VIA + inicioCalcada) / 2;
    const centroTerreno = (BORDA_VIA + inicioTerreno) / 2;
    plano(grupo, `calcada-${x}-${z}`, BORDA_VIA - inicioCalcada, BORDA_VIA - inicioCalcada,
      x * centroCalcada, z * centroCalcada, 0.06, materiais.calcada);
    plano(grupo, `jardim-${x}-${z}`, BORDA_VIA - inicioTerreno, BORDA_VIA - inicioTerreno,
      x * centroTerreno, z * centroTerreno, 0.12, materiais.jardim);
  }
  for (const via of aproximacoes) {
    const rua = new THREE.Group();
    rua.name = `rua-${via.id}`;
    rua.userData.id = rua.name;
    rua.rotation.y = via.rotacao;
    grupo.add(rua);
    // Quatro faixas planas: duas de entrada e duas de saída em cada braço.
    [-4.5, -1.5, 1.5, 4.5].forEach((x, indice) => {
      plano(rua, `${via.id}-F${indice + 1}`, 3, BORDA_VIA - 6, x, -(BORDA_VIA + 6) / 2, 0, materiais.pista);
    });
    for (const x of [-0.12, 0.12]) plano(rua, `${via.id}-eixo-${x}`, 0.1, BORDA_VIA - 10, x, -(BORDA_VIA + 10) / 2, 0.04, materiais.eixo);
    for (const x of [-3, 3]) for (let z = -14; z >= -BORDA_VIA; z -= 3) {
      plano(rua, `${via.id}-divisoria-${x}-${z}`, 0.12, 1.5, x, z, 0.04, materiais.branco);
    }
    plano(rua, `${via.id}-RET`, 5.8, 0.45, -3, -11, 0.045, materiais.branco);
    const travessia = new THREE.Group();
    travessia.name = `${via.id}-TR`;
    travessia.userData.id = travessia.name;
    rua.add(travessia);
    for (let i = 0; i < 12; i++) {
      plano(travessia, `${via.id}-TR-${i}`, 0.55, 2.2, -5.5 + i, -8.2, 0.045, materiais.branco);
    }

  }
  return grupo;
}
