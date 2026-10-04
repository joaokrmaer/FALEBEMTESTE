// Code node: "Preparar mensagem"
// Modo: Run Once for Each Item
// Achata o payload do Chatwoot no que o resto do fluxo usa e classifica o tipo da mensagem.
// Só o tipo "texto" vai para a IA; os outros recebem resposta fixa (economiza chamada e evita 429).
//
// tipo:
//   texto          -> tem texto útil (digitado, legenda de mídia ou áudio transcrito pelo Chatwoot)
//   vazio          -> só espaço, pontuação ou emoji
//   midia          -> foto, vídeo, figurinha, documento... sem legenda
//   audio          -> áudio sem transcrição
//   nao_suportado  -> o WhatsApp não entregou o conteúdo (ex.: visualização única)

const body = $json.body ?? {};
const anexos = Array.isArray(body.attachments) ? body.attachments : [];

// Limpa o que o contato digitou: junta espaços e reduz pontuação repetida ("oi......" -> "oi.").
function limparTexto(valor) {
  return String(valor ?? '')
    .replace(/\s+/g, ' ')
    .replace(/([.,;:!?])\1+/g, '$1')
    .replace(/^[\s.,;:!?]+/, '')
    .trim();
}

// Texto útil = tem pelo menos uma letra ou número (emoji e pontuação sozinhos não contam).
const temConteudo = texto => /[\p{L}\p{N}]/u.test(texto);

const textoDigitado = limparTexto(body.content);
const audio = anexos.find(a => a.file_type === 'audio');
const textoAudio = limparTexto(audio?.transcribed_text);

let tipo;
let texto = '';
let origem = null;

if (body.content_attributes?.is_unsupported) {
  tipo = 'nao_suportado';
} else if (temConteudo(textoDigitado)) {
  tipo = 'texto';
  texto = textoDigitado;
  origem = anexos.length ? 'legenda' : 'digitado';
} else if (audio && temConteudo(textoAudio)) {
  tipo = 'texto';
  texto = textoAudio;
  origem = 'audio_transcrito';
} else if (audio) {
  tipo = 'audio';
} else if (anexos.length || body.content_type === 'sticker') {
  tipo = 'midia';
} else {
  tipo = 'vazio';
}

// Figurinha: o Chatwoot marca content_type "sticker"; no WhatsApp ela também chega como imagem .webp.
const eh_figurinha = body.content_type === 'sticker' ||
  anexos.some(a => a.file_type === 'image' && String(a.extension ?? '').toLowerCase() === 'webp');

return {
  json: {
    eh_figurinha: tipo === 'midia' && eh_figurinha,
    message_id: body.id,
    account_id: body.account?.id,
    conversation_id: body.conversation?.id,
    contato_nome: body.sender?.name ?? null,
    telefone: body.sender?.phone_number ?? body.conversation?.meta?.sender?.phone_number ?? null,
    created_at: body.created_at,
    tipo,
    texto,
    origem,
    config: $json.config,
  },
};
