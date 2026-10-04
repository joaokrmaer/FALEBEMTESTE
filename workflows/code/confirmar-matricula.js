// Code node: "Confirmar matrícula"
// Modo: Run Once for Each Item
// Pipedrive e etiqueta deram certo: marca a conversa como concluída e monta a confirmação.
// Quem já era lead recebe um "seus dados já estão com a equipe" em vez da confirmação nova.

const contexto = $('Atualizar dados do lead').item.json;
const primeiroNome = contexto.lead.nome.split(' ')[0];

const resposta = contexto.ja_era_lead
  ? `Seus dados já estão com a nossa equipe, ${primeiroNome}! Uma atendente vai falar com você para finalizar ` +
    'a matrícula. Se quiser falar com ela agora, é só pedir.'
  : `Prontinho, ${primeiroNome}! Sua pré-matrícula no curso de ${contexto.lead.curso} foi registrada. ` +
    'Uma atendente vai entrar em contato para finalizar. Ah, e a aula experimental é gratuita!';

return {
  json: {
    ...contexto,
    novo_stage: 'concluido',
    campo_pendente: null,
    resposta,
  },
};
