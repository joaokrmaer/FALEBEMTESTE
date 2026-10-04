// Code node: "Montar resposta (outro)"
// Modo: Run Once for Each Item
// Saudação, agradecimento, assunto sem relação ou falha da IA (requisito 3: falhou -> "outro").
// No meio da matrícula, lembra o dado que falta; senão, apresenta o que o bot sabe fazer.

const estado = $json.estado ?? {};

const LEMBRETES = {
  nome: 'Para continuar sua pré-matrícula, qual é o seu nome completo?',
  email: 'Para continuar sua pré-matrícula, qual é o seu e-mail?',
  curso: 'Para continuar sua pré-matrícula, qual curso te interessa: Inglês ou Espanhol?',
};
const lembrete = estado.stage === 'coletando' ? LEMBRETES[estado.campo_pendente] : null;

const resposta = lembrete ??
  'Oi! Sou o assistente virtual da Escola Fale Bem. Posso te ajudar com informações sobre os cursos de inglês e espanhol, ' +
  'fazer sua pré-matrícula ou chamar uma atendente. Como posso ajudar?';

return { json: { ...$json, resposta } };
