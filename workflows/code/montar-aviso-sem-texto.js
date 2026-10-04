// Code node: "Montar aviso (mensagem sem texto)"
// Modo: Run Once for Each Item
// "?", "......", emoji solto, foto/documento sem legenda, áudio sem transcrição, visualização única, figurinha.
// Nada disso vai para a IA. Quem manda várias seguidas está com dificuldade, então o bot escala:
//   1ª -> aviso   2ª -> oferece atendente   3ª -> transfere (faixa humano)   4ª+ -> silêncio
// Figurinha é exceção (rajada de figurinhas é brincadeira, não pedido de ajuda): só o 1º aviso.
// "Seguidas" = dentro de 10 minutos do último aviso. No meio da matrícula, o aviso lembra o dado que falta.

const JANELA = 10 * 60 * 1000;

const estado = $json.estado ?? {};
const tipo = $json.tipo;
const recente = estado.ultimo_aviso_em && Date.now() - Date.parse(estado.ultimo_aviso_em) < JANELA;
const qtd_sem_texto = recente ? (estado.qtd_sem_texto ?? 0) + 1 : 1;

const LEMBRETES = {
  nome: 'Para continuar sua pré-matrícula, qual é o seu nome completo?',
  email: 'Para continuar sua pré-matrícula, qual é o seu e-mail?',
  curso: 'Para continuar sua pré-matrícula, qual curso te interessa: Inglês ou Espanhol?',
};
const lembrete = estado.stage === 'coletando' ? LEMBRETES[estado.campo_pendente] ?? '' : '';
const comLembrete = texto => (lembrete ? `${texto} ${lembrete}` : texto);

const PRIMEIRO_AVISO = {
  audio: comLembrete('Ainda não consigo ouvir áudios. Pode me escrever o que você precisa?'),
  midia: comLembrete('Ainda não consigo ver imagens, vídeos ou figurinhas. Pode me escrever o que você precisa?'),
  nao_suportado: comLembrete('Não consegui abrir essa mensagem (mensagens de visualização única não chegam para mim). Pode me escrever o que você precisa?'),
  vazio: lembrete
    ? `Não entendi sua mensagem. ${lembrete}`
    : 'Não entendi sua mensagem. Posso te ajudar com informações sobre cursos e preços, fazer sua pré-matrícula ou chamar uma atendente. O que você precisa?',
};

// acao: avisar | transferir | silenciar
let acao = 'silenciar';
let resposta = null;
let ofereceu_atendente = false;

if (qtd_sem_texto === 1) {
  acao = 'avisar';
  resposta = PRIMEIRO_AVISO[tipo] ?? PRIMEIRO_AVISO.vazio;
} else if ($json.eh_figurinha) {
  acao = 'silenciar';
} else if (qtd_sem_texto === 2) {
  acao = 'avisar';
  ofereceu_atendente = true;
  resposta = tipo === 'audio'
    ? 'Ainda não consigo ouvir áudios. Se preferir, posso te passar para uma atendente. Quer?'
    : 'Parece que não estou conseguindo te entender por aqui. Quer que eu chame uma atendente?';
} else if (qtd_sem_texto === 3) {
  acao = 'transferir';
}

return {
  json: { ...$json, acao_sem_texto: acao, resposta, ultimo_aviso: tipo, qtd_sem_texto, ofereceu_atendente },
};
