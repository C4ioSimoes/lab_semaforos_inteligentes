import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { criarCruzamento } from './cruzamento';
import { criarCamadaParticipantes } from './participantes';
import { criarSemaforos } from './semaforos';

export function criarCena(container: HTMLElement) {
  const cena = new THREE.Scene();
  cena.background = new THREE.Color('#bcbcbc');
  // A distância radial é fornecida por materialCurvo: desvanece todas as bordas.
  cena.fog = new THREE.Fog(cena.background, 45, 85);
  cena.add(criarCruzamento());
  const participantes = criarCamadaParticipantes();
  cena.add(participantes.grupo);
  const semaforos = criarSemaforos();
  cena.add(semaforos.grupo);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 250);
  const inicial = new THREE.Vector3(36, 52, 36);
  camera.position.copy(inicial);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.domElement.setAttribute('aria-label', 'Cruzamento 3D: arraste para orbitar e role para ampliar');
  renderer.domElement.tabIndex = 0;
  container.append(renderer.domElement);
  const controles = new OrbitControls(camera, renderer.domElement);
  controles.target.set(0, 0, 0);
  controles.cursor.set(0, 0, 0);
  controles.maxTargetRadius = 0;
  controles.enablePan = false;
  controles.zoomToCursor = false;
  controles.enableDamping = true;
  controles.dampingFactor = 0.08;
  controles.minDistance = 25;
  controles.maxDistance = 110;
  controles.minPolarAngle = 0;
  controles.maxPolarAngle = Math.PI / 2 - 0.15;
  controles.touches.TWO = THREE.TOUCH.DOLLY_ROTATE;
  controles.update();
  controles.saveState();

  function redimensionar() {
    const largura = container.clientWidth;
    const altura = container.clientHeight;
    if (!largura || !altura) return;
    camera.aspect = largura / altura;
    // Preserva o enquadramento horizontal em celulares e janelas estreitas.
    camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(
      Math.tan(THREE.MathUtils.degToRad(45 / 2)) / Math.min(1, camera.aspect),
    ));
    camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(largura, altura);
  }
  const observador = new ResizeObserver(redimensionar);
  observador.observe(container);
  redimensionar();

  // Este loop atualiza exclusivamente a apresentação, sem relógio de simulação.
  renderer.setAnimationLoop(() => {
    controles.update();
    renderer.render(cena, camera);
  });

  function limparInercia() {
    controles.enableDamping = false;
    controles.update();
    controles.enableDamping = true;
  }
  return {
    camera,
    controles,
    atualizarParticipantes: participantes.atualizar,
    atualizarSemaforos: semaforos.atualizar,
    vistaSuperior() {
      limparInercia();
      camera.position.set(0, 85, 0);
      controles.target.set(0, 0, 0);
      controles.update();
    },
    restaurar() {
      limparInercia();
      controles.reset();
    },
    descartar() {
      renderer.setAnimationLoop(null);
      observador.disconnect();
      controles.dispose();
      participantes.descartar();
      const materiais = new Set<THREE.Material>();
      cena.traverse((objeto) => {
        if (objeto instanceof THREE.Mesh) {
          objeto.geometry.dispose();
          const lista = Array.isArray(objeto.material) ? objeto.material : [objeto.material];
          lista.forEach((material) => materiais.add(material));
        }
      });
      materiais.forEach((material) => material.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
