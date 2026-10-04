// Code node: "Conferir resposta da dúvida"
// Modo: Run Once for Each Item
// Trava contra invenção: toda quantia em R$ e todo horário citado precisam existir nos dados oficiais.
// Se a IA falhou ou citou algo fora da lista, a resposta é trocada por uma mensagem segura.

const PRECOS_OFICIAIS = new Set([389, 349, 120]);
const HORAS_OFICIAIS = new Set([8, 18]);

const SEM_RESPOSTA = 'Essa informação eu não tenho aqui. Quer que eu chame uma atendente para te ajudar?';
const CONTINGENCIA = 'Desculpe, tive um problema para responder agora. Já deixei sua mensagem registrada e uma atendente vai te responder assim que possível.';

const contexto = $('Montar pedido de resposta (dúvida)').item.json;
const { pedido_ia, ...msg } = contexto;
const erros = [msg.ia?.erro].filter(Boolean);

function lerResposta(resposta) {
  if (resposta.error) return { erro: `OpenAI (dúvida): ${resposta.error.message ?? JSON.stringify(resposta.error)}` };
  try {
    const dados = JSON.parse(resposta.choices?.[0]?.message?.content);
    if (typeof dados.resposta !== 'string' || !dados.resposta.trim()) throw new Error('vazia');
    return { dados };
  } catch {
    return { erro: 'Resposta da dúvida inválida' };
  }
}

// Lista o que a resposta afirma que não está nos dados oficiais.
function dadosInventados(texto) {
  const problemas = [];
  for (const [, valor] of texto.matchAll(/R\$\s*(\d+(?:[.,]\d+)?)/g)) {
    const numero = Number(valor.replace(/\.(?=\d{3})/g, '').replace(',', '.'));
    if (!PRECOS_OFICIAIS.has(numero)) problemas.push(`preço R$ ${valor}`);
  }
  for (const [, hora] of texto.matchAll(/\b(\d{1,2})\s*(?:h|horas?\b|:\d{2})/gi)) {
    if (!HORAS_OFICIAIS.has(Number(hora))) problemas.push(`horário ${hora}h`);
  }
  return problemas;
}

const { dados, erro } = lerResposta($json);
let resposta;
let trava = null;

if (erro) {
  erros.push(erro);
  resposta = CONTINGENCIA;
} else {
  const inventado = dadosInventados(dados.resposta);
  if (inventado.length) {
    trava = `Resposta descartada, citava ${inventado.join(', ')}: "${dados.resposta}"`;
    resposta = SEM_RESPOSTA;
  } else {
    resposta = dados.resposta.trim();
  }
}

return {
  json: {
    ...msg,
    resposta,
    oferece_atendente: Boolean(trava) || dados?.respondida_com_dados === false,
    trava_anti_invencao: trava,
    erros,
  },
};
