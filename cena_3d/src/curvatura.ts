import * as THREE from 'three';

/** Deformação exclusivamente visual, em coordenadas de mundo.
 * O mesmo shader curva piso, marcações, sinais e participantes sem modificar
 * as posições oficiais das malhas. Raio aproximado do globo: 125 unidades.
 */
export function materialCurvo(color: string): THREE.MeshBasicMaterial {
  const material = new THREE.MeshBasicMaterial({ color });
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader.replace('#include <project_vertex>', `
      vec4 mundoCurvo = modelMatrix * vec4(transformed, 1.0);
      mundoCurvo.y -= dot(mundoCurvo.xz, mundoCurvo.xz) * 0.004;
      vec4 mvPosition = viewMatrix * mundoCurvo;
      gl_Position = projectionMatrix * mvPosition;
    `).replace('#include <fog_vertex>', `
      #ifdef USE_FOG
        vFogDepth = length(mundoCurvo.xz);
      #endif
    `);
  };
  material.customProgramCacheKey = () => 'curvatura-mundo-fog-radial-v2';
  return material;
}
