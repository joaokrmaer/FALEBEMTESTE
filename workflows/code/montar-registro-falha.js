// Code node: "Montar registro de falha" (workflow Bot Fale Bem - Falhas)
// Modo: Run Once for Each Item
// Requisito 7. O n8n roda este workflow quando uma execução do bot falha (Pipedrive, Chatwoot,
// Postgres ou erro de código). A execução que falhou é lida pela API do n8n para descobrir a conversa:
// isso funciona mesmo com o banco do bot fora do ar. Monta:
//   - o registro para a tabela error_log (alguém descobre depois: SELECT * FROM error_log)
//   - a mensagem de contingência, para o contato não ficar sem resposta

const CONTINGENCIA = 'Desculpe, tive um problema para responder agora. Já deixei sua mensagem registrada ' +
  'e uma atendente vai te responder assim que possível.';

const gatilho = $('Quando o bot falhar').item.json;
const execucao = $json; // resposta de GET /api/v1/executions/{id}?includeData=true

const runData = execucao.data?.resultData?.runData ?? {};
const saidaDo = nome => runData[nome]?.[0]?.data?.main?.[0]?.[0]?.json;
const corpo = saidaDo('Chatwoot: mensagem recebida')?.body ?? {};
const config = saidaDo('Config')?.config ?? {};

const conversation_id = corpo.conversation?.id ?? null;
const account_id = corpo.account?.id ?? null;
const leuExecucao = !execucao.error && Boolean(execucao.data);

return {
  json: {
    conversation_id,
    account_id,
    config,
    resposta: CONTINGENCIA,
    enviar_contingencia: Boolean(conversation_id && account_id && config.chatwoot_url),
    registro: {
      execution_id: String(gatilho.execution?.id ?? ''),
      node: gatilho.execution?.lastNodeExecuted ?? 'desconhecido',
      message: String(gatilho.execution?.error?.message ?? 'Erro sem mensagem').slice(0, 2000),
      conversation_id,
      payload: {
        workflow: gatilho.workflow?.name ?? null,
        execucao_url: gatilho.execution?.url ?? null,
        mensagem_do_contato: corpo.content ?? null,
        message_id: corpo.id ?? null,
        aviso: leuExecucao ? null : 'Não foi possível ler a execução pela API do n8n; contingência não enviada.',
      },
    },
  },
};
