// Code node: "Normalizar telefone (2.1)"
// Modo: Run Once for Each Item
// Entrada: $json.telefone (qualquer formato). Saída: o mesmo item + telefone_normalizado
// no formato +55DDDNÚMERO, ou null quando não dá para garantir um celular brasileiro válido.

// DDDs em uso no Brasil (Anatel). Combinações como 20, 23, 25, 26, 30, 36... não existem.
const DDDS_VALIDOS = new Set([
  11, 12, 13, 14, 15, 16, 17, 18, 19,
  21, 22, 24, 27, 28,
  31, 32, 33, 34, 35, 37, 38,
  41, 42, 43, 44, 45, 46, 47, 48, 49,
  51, 53, 54, 55,
  61, 62, 63, 64, 65, 66, 67, 68, 69,
  71, 73, 74, 75, 77, 79,
  81, 82, 83, 84, 85, 86, 87, 88, 89,
  91, 92, 93, 94, 95, 96, 97, 98, 99,
]);

function normalizarTelefone(valor) {
  if (valor === null || valor === undefined) return null;
  const texto = String(valor).trim();
  let digitos = texto.replace(/\D/g, '');

  // Veio com "+" mas não é +55: número estrangeiro, não é celular brasileiro.
  if (texto.startsWith('+') && !digitos.startsWith('55')) return null;

  // Com código do país: 55 + DDD(2) + 9 dígitos = 13.
  // Só removemos o 55 quando o tamanho bate, porque 55 também é um DDD (RS).
  if (digitos.length === 13 && digitos.startsWith('55')) {
    digitos = digitos.slice(2);
  } else if (digitos.length === 12 && digitos.startsWith('0')) {
    // Prefixo de discagem interurbana: 0 + DDD + número.
    digitos = digitos.slice(1);
  }

  // Celular nacional: DDD(2) + 9 + 8 dígitos = 11.
  if (digitos.length !== 11) return null;
  if (!DDDS_VALIDOS.has(Number(digitos.slice(0, 2)))) return null;
  if (digitos[2] !== '9') return null;

  return '+55' + digitos;
}

return {
  json: {
    ...$json,
    telefone_normalizado: normalizarTelefone($json.telefone),
  },
};
