// Code node: "Horário de atendimento (com feriados)"
// Modo: Run Once for Each Item
// Requisito 6. Mesma regra do exercício 2.2 (seg-sex, 8h-18h, America/Recife) + feriados do nó
// "Config: feriados". Fora do horário, calcula quando a equipe volta, pulando fim de semana e feriado
// (ex.: sexta 09/10 às 19h -> segunda 12/10 é feriado -> volta terça, 13/10, às 8h).

const FUSO = 'America/Recife';
const ABRE = 8;   // 08:00
const FECHA = 18; // 18:00 (exclusive)
const DIAS = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];
const feriados = new Set($json.feriados ?? []);

// Data e hora de Recife a partir de um instante (Intl é nativo do JS; continua certo se o fuso mudar de regra).
const formatador = new Intl.DateTimeFormat('en-CA', {
  timeZone: FUSO, year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23', weekday: 'short',
});
const SEMANA = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };

function emRecife(instante) {
  const p = Object.fromEntries(formatador.formatToParts(instante).map(x => [x.type, x.value]));
  return {
    data: `${p.year}-${p.month}-${p.day}`,
    diaSemana: SEMANA[p.weekday],
    minutos: Number(p.hour) * 60 + Number(p.minute),
  };
}

const diaUtil = r => r.diaSemana >= 1 && r.diaSemana <= 5 && !feriados.has(r.data);

// Momento da mensagem (o Chatwoot pode mandar ISO ou timestamp em segundos); sem data válida, agora.
function instanteDaMensagem(valor) {
  const data = typeof valor === 'number' ? new Date(valor * 1000) : new Date(valor ?? NaN);
  return Number.isNaN(data.getTime()) ? new Date() : data;
}

const agora = instanteDaMensagem($json.created_at);
const hoje = emRecife(agora);
const dentro_do_horario = diaUtil(hoje) && hoje.minutos >= ABRE * 60 && hoje.minutos < FECHA * 60;

let motivo = null;
let proxima_abertura = null;
if (!dentro_do_horario) {
  motivo = feriados.has(hoje.data) ? 'feriado' : !diaUtil(hoje) ? 'fim_de_semana' : 'fora_do_horario';

  // Hoje ainda abre (dia útil, antes das 8h)? Senão, procura o próximo dia útil.
  let dia = hoje;
  let diasAFrente = 0;
  if (!(diaUtil(hoje) && hoje.minutos < ABRE * 60)) {
    do {
      diasAFrente += 1;
      dia = emRecife(new Date(agora.getTime() + diasAFrente * 24 * 60 * 60 * 1000));
    } while (!diaUtil(dia) && diasAFrente < 15);
  }
  const [, mes, diaMes] = dia.data.split('-');
  const quando = diasAFrente === 0 ? 'hoje' : diasAFrente === 1 ? 'amanhã' : DIAS[dia.diaSemana];
  proxima_abertura = `${quando}, ${diaMes}/${mes}, às ${ABRE}h`;
}

return {
  json: { ...$json, dentro_do_horario, motivo_fora_do_horario: motivo, proxima_abertura },
};
