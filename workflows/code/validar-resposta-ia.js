// Code node: "Validar resposta da IA"
// Modo: Run Once for Each Item
// Requisito 3: se a IA falhar ou devolver algo fora da lista, a intenção vira "outro".
// A falha fica registrada em ia.erro para o bloco de falhas gravar no error_log.

const INTENCOES = ['interesse_matricula', 'duvida', 'falar_com_humano', 'outro'];
const contexto = $('Montar pedido para a IA').item.json;
const { pedido_ia, ...msg } = contexto;

function lerResposta(resposta) {
  if (resposta.error) {
    return { erro: `OpenAI: ${resposta.error.message ?? JSON.stringify(resposta.error)}` };
  }
  const conteudo = resposta.choices?.[0]?.message?.content;
  try {
    return { dados: JSON.parse(conteudo) };
  } catch {
    return { erro: `Resposta da IA não é JSON: ${String(conteudo).slice(0, 200)}` };
  }
}

const textoOuNull = v => (typeof v === 'string' && v.trim() ? v.trim().slice(0, 120) : null);
const emailValido = v => (typeof v === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) ? v.trim().toLowerCase() : null);
const cursoValido = v => (v === 'Inglês' || v === 'Espanhol' ? v : null);

// Rede de segurança para modelos pequenos: e-mail e curso dá para achar no texto sem IA.
const texto = msg.texto ?? '';
const emailNoTexto = texto.match(/[^\s@]+@[^\s@]+\.[^\s@]{2,}/)?.[0]?.replace(/[.,;!?)]+$/, '');
function cursoNoTexto() {
  const ingles = /ingl[eê]s|english/i.test(texto);
  const espanhol = /espanhol|spanish/i.test(texto);
  if (ingles === espanhol) return null; // nenhum ou os dois: não dá para decidir
  return ingles ? 'Inglês' : 'Espanhol';
}

const { dados = {}, erro = null } = lerResposta($json);

let intencao = INTENCOES.includes(dados.intencao) ? dados.intencao : 'outro';
const extraido = {
  nome: textoOuNull(dados.nome),
  email: emailValido(dados.email) ?? emailValido(emailNoTexto),
  curso: cursoNoTexto() ?? cursoValido(dados.curso), // texto sem ambiguidade vence a IA
};

// Rede de segurança: no meio da matrícula, uma resposta curta ("Mariana") que trouxe dado
// continua sendo matrícula, mesmo que a IA tenha classificado como "outro".
const trouxeDado = extraido.nome || extraido.email || extraido.curso;
if (msg.estado?.stage === 'coletando' && intencao === 'outro' && trouxeDado) {
  intencao = 'interesse_matricula';
}

// Rede de segurança: o bot ofereceu atendente há pouco e a resposta é um "sim" curto.
const ofereceuHaPouco = msg.estado?.ofereceu_atendente_em &&
  Date.now() - Date.parse(msg.estado.ofereceu_atendente_em) < 30 * 60 * 1000;
const respostaAfirmativa = /^(sim|s|quero|pode|pode ser|claro|ok|por favor|isso)\b/i.test(texto.trim());
if (ofereceuHaPouco && intencao === 'outro' && respostaAfirmativa) {
  intencao = 'falar_com_humano';
}

return {
  json: {
    ...msg,
    ia: {
      intencao,
      ...extraido,
      erro: erro ?? (dados.intencao && !INTENCOES.includes(dados.intencao) ? `Intenção fora da lista: ${dados.intencao}` : null),
    },
  },
};
