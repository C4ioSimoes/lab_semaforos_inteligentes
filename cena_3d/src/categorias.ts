export const nomesCategorias = {
  carro: 'Carro', moto: 'Moto', onibus: 'Ônibus', ambulancia: 'Ambulância',
  pedestre: 'Pedestre',
} as const;
export type CategoriaVeiculo = keyof typeof nomesCategorias;

export function categoriaValida(valor: unknown): valor is CategoriaVeiculo {
  return typeof valor === 'string' && Object.hasOwn(nomesCategorias, valor);
}

// Cores apenas visuais; dimensões e posição vêm do motor.
export const coresCategorias: Record<CategoriaVeiculo, string[]> = {
  carro: ['#cf793f', '#b96a38', '#f2b975', '#8c512e', '#e59854', '#bf6c39'],
  moto: ['#15998f', '#117e77', '#65e1d2', '#174b48', '#24b6a8', '#147a71'],
  onibus: ['#3974b4', '#2b5c99', '#81b5e8', '#203d61', '#4b8acb', '#305b90'],
  ambulancia: ['#e9edef', '#d6dfe4', '#ffffff', '#8d9ea6', '#d34245', '#b82f3c'],
  pedestre: ['#505050'],
};
