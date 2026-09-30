/** Nomes de apresentação; os identificadores do protocolo permanecem iguais. */
export const nomesRedes: Record<string, string> = { perceptron: 'Perceptron', adaline: 'Adaline' };
export function nomeFase(fase: string | null | undefined): string {
  return ({ 'F-NS': 'Norte ↔ Sul', 'F-LO': 'Leste ↔ Oeste', 'F-PED': 'Pedestres' } as Record<string, string>)[fase ?? ''] ?? fase ?? 'Aguardando';
}
