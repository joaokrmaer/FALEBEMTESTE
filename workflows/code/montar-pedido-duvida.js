// Code node: "Montar pedido de resposta (dúvida)"
// Modo: Run Once for Each Item
// Requisito 4: responder SOMENTE com os dados do cenário. Sem resposta ali -> diz que não sabe
// e oferece uma atendente. A trava contra preço/horário inventado fica no nó seguinte.

const MODELO = $json.config?.openai_model || 'gpt-4.1-nano';
const ACEITA_TEMPERATURA = !/^(gpt-5|o\d)/.test(MODELO);

const DADOS_DA_ESCOLA = `Escola Fale Bem — dados oficiais (única fonte permitida):
- Inglês: duração de 18 meses, mensalidade de R$ 389, turmas de manhã, à noite e aos sábados.
- Espanhol: duração de 12 meses, mensalidade de R$ 349, turmas à noite e aos sábados.
- Matrícula: R$ 120.
- Aula experimental: gratuita.
- Atendimento humano: de segunda a sexta, das 8h às 18h, horário de Recife.`;

const INSTRUCOES = `Você é o assistente de WhatsApp da Escola Fale Bem. Responda à dúvida do contato em português, de forma curta e simpática (no máximo 3 frases).

Regras obrigatórias:
1. Use SOMENTE os dados oficiais abaixo. Não use conhecimento próprio.
2. Nunca invente preço, desconto, forma de pagamento, horário de aula, endereço, professor ou qualquer dado que não esteja abaixo.
3. Se a pergunta não puder ser respondida só com esses dados, diga que não tem essa informação e pergunte se a pessoa quer falar com uma atendente. Nesse caso, marque respondida_com_dados = false.

${DADOS_DA_ESCOLA}`;

const pedido = {
  model: MODELO,
  ...(ACEITA_TEMPERATURA && { temperature: 0 }),
  messages: [
    { role: 'system', content: INSTRUCOES },
    { role: 'user', content: $json.texto },
  ],
  response_format: {
    type: 'json_schema',
    json_schema: {
      name: 'resposta_duvida',
      strict: true,
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['resposta', 'respondida_com_dados'],
        properties: {
          resposta: { type: 'string' },
          respondida_com_dados: { type: 'boolean' },
        },
      },
    },
  },
};

return { json: { ...$json, pedido_ia: pedido } };
