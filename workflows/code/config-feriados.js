// Code node: "Config: feriados"
// Modo: Run Once for Each Item
// Dias em que a equipe NÃO atende, além de sábado e domingo. REVISAR TODO ANO.
// Nacionais + Pernambuco + Recife. Carnaval e Corpus Christi são ponto facultativo:
// estão na lista por costume em Recife, mas a escola deve confirmar se fecha.

const FERIADOS = {
  // 2026
  '2026-01-01': 'Confraternização Universal',
  '2026-02-16': 'Carnaval (segunda)',
  '2026-02-17': 'Carnaval (terça)',
  '2026-03-06': 'Data Magna de Pernambuco',
  '2026-04-03': 'Sexta-feira Santa',
  '2026-04-21': 'Tiradentes',
  '2026-05-01': 'Dia do Trabalho',
  '2026-06-04': 'Corpus Christi',
  '2026-06-24': 'São João (Recife)',
  '2026-07-16': 'Nossa Senhora do Carmo (Recife)',
  '2026-09-07': 'Independência',
  '2026-10-12': 'Nossa Senhora Aparecida',
  '2026-11-02': 'Finados',
  '2026-11-15': 'Proclamação da República',
  '2026-11-20': 'Consciência Negra',
  '2026-12-08': 'Nossa Senhora da Conceição (Recife)',
  '2026-12-25': 'Natal',
  // 2027
  '2027-01-01': 'Confraternização Universal',
  '2027-02-08': 'Carnaval (segunda)',
  '2027-02-09': 'Carnaval (terça)',
  '2027-03-06': 'Data Magna de Pernambuco',
  '2027-03-26': 'Sexta-feira Santa',
  '2027-04-21': 'Tiradentes',
  '2027-05-01': 'Dia do Trabalho',
  '2027-05-27': 'Corpus Christi',
  '2027-06-24': 'São João (Recife)',
  '2027-07-16': 'Nossa Senhora do Carmo (Recife)',
  '2027-09-07': 'Independência',
  '2027-10-12': 'Nossa Senhora Aparecida',
  '2027-11-02': 'Finados',
  '2027-11-15': 'Proclamação da República',
  '2027-11-20': 'Consciência Negra',
  '2027-12-08': 'Nossa Senhora da Conceição (Recife)',
  '2027-12-25': 'Natal',
};

return { json: { ...$json, feriados: Object.keys(FERIADOS) } };
