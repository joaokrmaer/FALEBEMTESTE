// Code node: "Dentro do horário de atendimento (2.2)"
// Modo: Run Once for Each Item
// Entrada: $json.data (ISO 8601 em UTC). Saída: o mesmo item + dentro_do_horario (boolean).
// Regra: segunda a sexta, das 8h00 (inclusive) às 18h00 (exclusive), fuso America/Recife.

const FUSO = 'America/Recife';
const DIAS_UTEIS = new Set(['Mon', 'Tue', 'Wed', 'Thu', 'Fri']);
const ABRE = 8 * 60;   // 08:00 em minutos
const FECHA = 18 * 60; // 18:00 em minutos

// Usa o Intl (nativo do JS) para ler dia da semana e hora no fuso de Recife,
// em vez de subtrair 3h na mão: continua certo se o fuso mudar de regra.
const formatador = new Intl.DateTimeFormat('en-US', {
  timeZone: FUSO,
  weekday: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

function dentroDoHorario(iso) {
  const data = new Date(iso);
  // Data inválida conta como fora do horário: na dúvida, não prometemos atendente.
  if (!iso || Number.isNaN(data.getTime())) return false;

  const partes = Object.fromEntries(
    formatador.formatToParts(data).map(p => [p.type, p.value]),
  );
  const minutos = Number(partes.hour) * 60 + Number(partes.minute);

  return DIAS_UTEIS.has(partes.weekday) && minutos >= ABRE && minutos < FECHA;
}

return {
  json: {
    ...$json,
    dentro_do_horario: dentroDoHorario($json.data),
  },
};
