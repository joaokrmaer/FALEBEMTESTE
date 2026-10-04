// Code node: "Juntar mensagens picadas (2.3)"
// Modo: Run Once for All Items
// Entrada: itens com { conversation_id, content, created_at }, em qualquer ordem.
// Saída: um item por conversa, com os textos em ordem cronológica unidos por espaço.

const conversas = new Map();

for (const [indice, item] of $input.all().entries()) {
  const { conversation_id, content, created_at } = item.json;
  const texto = String(content ?? '').trim();
  if (!texto) continue; // anexo/figurinha sem texto não entra na frase

  const quando = Date.parse(created_at);
  if (!conversas.has(conversation_id)) conversas.set(conversation_id, []);
  conversas.get(conversation_id).push({
    texto,
    created_at,
    quando: Number.isNaN(quando) ? Infinity : quando, // data inválida vai para o fim
    indice, // desempate: mesmo instante, mantém a ordem em que chegaram
  });
}

const resultado = [...conversas.entries()].map(([conversation_id, mensagens]) => {
  mensagens.sort((a, b) => a.quando - b.quando || a.indice - b.indice);
  return {
    conversation_id,
    content: mensagens.map(m => m.texto).join(' '),
    quantidade_mensagens: mensagens.length,
    primeira_mensagem_em: mensagens[0].created_at,
    ultima_mensagem_em: mensagens[mensagens.length - 1].created_at,
    _inicio: mensagens[0].quando,
  };
});

// Conversa que começou primeiro sai primeiro.
resultado.sort((a, b) => a._inicio - b._inicio);

return resultado.map(({ _inicio, ...json }) => ({ json }));
