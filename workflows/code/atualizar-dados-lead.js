// Code node: "Atualizar dados do lead"
// Modo: Run Once for Each Item
// Requisito 5: junta o que já foi coletado (Postgres) com o que a IA extraiu desta mensagem
// e decide o próximo passo:
//   perguntar  -> ainda falta nome, e-mail ou curso (pergunta um por vez, nessa ordem)
//   cadastrar  -> tem os três: segue para o Pipedrive
// Quem já virou lead (stage "concluido") também passa pelo Pipedrive: o cadastro não duplica
// pessoa nem negócio aberto, e se alguém apagou o lead no CRM, ele é recriado.

// Dados do cenário (PDF). O valor do negócio no Pipedrive é a previsão do contrato:
// matrícula + mensalidade × duração. A atendente ajusta se houver desconto.
const MATRICULA = 120;
const CURSOS = {
  'Inglês': { mensalidade: 389, meses: 18 },
  'Espanhol': { mensalidade: 349, meses: 12 },
};
const valorContrato = curso => (CURSOS[curso] ? MATRICULA + CURSOS[curso].mensalidade * CURSOS[curso].meses : null);

const estado = $json.estado ?? {};
const ia = $json.ia ?? {};

// Dado novo desta mensagem vale mais que o salvo (permite corrigir o e-mail, por exemplo).
const lead = {
  nome: ia.nome ?? estado.nome ?? null,
  email: ia.email ?? estado.email ?? null,
  curso: ia.curso ?? estado.curso ?? null,
};
const primeiroNome = lead.nome ? lead.nome.split(' ')[0] : '';
const perguntouAntes = campo => estado.stage === 'coletando' && estado.campo_pendente === campo;

function pergunta(campo) {
  if (campo === 'nome') {
    return perguntouAntes('nome')
      ? 'Não consegui pegar seu nome. Pode me dizer como você se chama?'
      : 'Que ótimo que você quer estudar com a gente! Para fazer sua pré-matrícula, qual é o seu nome completo?';
  }
  if (campo === 'email') {
    if (perguntouAntes('email')) {
      return $json.texto.includes('@')
        ? 'Esse e-mail parece incompleto. Pode conferir e mandar de novo? (ex.: nome@gmail.com)'
        : 'Qual é o seu e-mail? (ex.: nome@gmail.com)';
    }
    return ia.nome && !estado.nome ? `Prazer, ${primeiroNome}! Qual é o seu e-mail?` : 'Qual é o seu e-mail?';
  }
  return perguntouAntes('curso')
    ? 'Temos Inglês e Espanhol. Qual dos dois você prefere?'
    : 'E qual curso te interessa: Inglês ou Espanhol?';
}

let acao;
let resposta = null;
let campo_pendente = null;
let novo_stage;

const ja_era_lead = estado.stage === 'concluido';
const faltando = ['nome', 'email', 'curso'].filter(campo => !lead[campo]);

if (faltando.length) {
  acao = 'perguntar';
  novo_stage = 'coletando';
  campo_pendente = faltando[0];
  resposta = pergunta(campo_pendente);
} else {
  acao = 'cadastrar';
  // Só vira (ou continua) "concluido" depois que o Pipedrive confirmar.
  novo_stage = ja_era_lead ? 'concluido' : 'coletando';
}

return {
  json: {
    ...$json,
    lead: { ...lead, valor_contrato: valorContrato(lead.curso) },
    ja_era_lead,
    acao,
    campo_pendente,
    novo_stage,
    resposta,
  },
};
