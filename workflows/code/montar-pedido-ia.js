// Code node: "Montar pedido para a IA"
// Modo: Run Once for Each Item
// Monta o corpo da chamada à OpenAI. A resposta vem em JSON com schema fixo (structured output):
// a intenção só pode ser um dos 4 valores e nome/e-mail/curso vêm null quando não aparecem.

// O modelo é escolhido no nó Config (config.openai_model).
const MODELO = $json.config?.openai_model || 'gpt-4.1-nano';
// Modelos de raciocínio (gpt-5*, o1, o3...) não aceitam temperature; os demais usam 0 (resposta estável).
const ACEITA_TEMPERATURA = !/^(gpt-5|o\d)/.test(MODELO);

const INSTRUCOES = `Você classifica mensagens de WhatsApp recebidas pela Escola Fale Bem, que vende cursos de inglês e espanhol.

Escolha UMA intenção:
- interesse_matricula: quer se matricular, se inscrever, começar um curso, OU está respondendo dados pedidos para a matrícula (nome, e-mail, curso).
- duvida: pergunta sobre preço, mensalidade, matrícula, duração, turmas, horários, aula experimental ou qualquer informação sobre a escola.
- falar_com_humano: pede para falar com uma pessoa, atendente ou humano.
- outro: saudação sozinha, agradecimento, assunto sem relação com a escola, ou não dá para saber.

Extraia também, SOMENTE se estiverem escritos na mensagem:
- nome: o nome que a pessoa disse ser o dela; senão null.
- email: o endereço de e-mail escrito; senão null.
- curso: "Inglês" se a mensagem cita inglês (ou english); "Espanhol" se cita espanhol (ou spanish); "nenhum" se não cita nenhum dos dois.
Nunca invente dados.`;

const estado = $json.estado;
let contexto = 'Contexto: conversa sem matrícula em andamento.';
if (estado?.stage === 'coletando') {
  contexto = `Contexto: o bot está coletando dados de matrícula e acabou de pedir: ${estado.campo_pendente ?? 'dados'}. ` +
    `Já coletado: nome=${estado.nome ?? 'falta'}, e-mail=${estado.email ?? 'falta'}, curso=${estado.curso ?? 'falta'}. ` +
    'Se a mensagem responde a esse pedido, a intenção é interesse_matricula.';
}
// O "sim" depois de o bot oferecer atendente é tratado em código (Validar resposta da IA), não aqui:
// avisar o modelo fazia o gpt-4.1-nano classificar qualquer mensagem seguinte (até um e-mail) como falar_com_humano.

const pedido = {
  model: MODELO,
  ...(ACEITA_TEMPERATURA && { temperature: 0 }),
  messages: [
    { role: 'system', content: INSTRUCOES },
    { role: 'system', content: contexto },
    { role: 'user', content: $json.texto },
  ],
  response_format: {
    type: 'json_schema',
    json_schema: {
      name: 'classificacao',
      strict: true,
      schema: {
        type: 'object',
        additionalProperties: false,
        required: ['intencao', 'nome', 'email', 'curso'],
        properties: {
          intencao: { type: 'string', enum: ['interesse_matricula', 'duvida', 'falar_com_humano', 'outro'] },
          nome: { type: ['string', 'null'] },
          email: { type: ['string', 'null'] },
          curso: { type: 'string', enum: ['Inglês', 'Espanhol', 'nenhum'] },
        },
      },
    },
  },
};

return { json: { ...$json, pedido_ia: pedido } };
