"""Monta workflows/bot-fale-bem.json a partir dos Code nodes em workflows/code e parte2.

Uso: python tools/gerar_workflow.py
O JSON gerado pode ser colado no canvas do n8n (Ctrl+V) ou importado (Import from File).
Credenciais entram só por id/nome; nenhum segredo vai no arquivo.

Layout em faixas: a faixa de cima entende a mensagem; cada intenção tem a sua faixa embaixo,
lida da esquerda para a direita e terminando no próprio envio ao Chatwoot.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ler = lambda p: (RAIZ / p).read_text(encoding="utf-8")

CRED_OPENAI = {"openAiApi": {"id": "LBsr7lTD2wajHV7U", "name": "OpenAi Growth Hub"}}
CRED_PIPEDRIVE = {"pipedriveApi": {"id": "8M6jVYTL6blpUZfd", "name": "Pipedrive API"}}
CRED_POSTGRES = {"postgres": {"id": "2kaRKTIHEWBpLG2K", "name": "Postgres - falebem"}}
CRED_CHATWOOT = {"httpHeaderAuth": {"id": "u1bzi4Eqo27GTZj9", "name": "chatwoot api token"}}

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
PIPEDRIVE = "https://api.pipedrive.com/api/v2"
CTX_LEAD = "$('Atualizar dados do lead').item.json"
CTX_CONFIRMACAO = "$('Confirmar matrícula').item.json"

nodes, connections = [], {}


# ---------------------------------------------------------------- helpers
def node(name, type_, params, pos, version=1, **extra):
    nodes.append({"parameters": params, "id": name, "name": name, "type": type_,
                  "typeVersion": version, "position": list(pos), **extra})


def nota(name, texto, pos, w, h, cor=7):
    node(name, "n8n-nodes-base.stickyNote", {"content": texto, "height": h, "width": w, "color": cor}, pos)


def code(name, arquivo, pos, por_item=True, saida_de_erro=False):
    """Code node. Erro no código para a execução, e a faixa de falhas (Error Trigger) assume."""
    params = {"jsCode": ler(arquivo) if arquivo.endswith(".js") else arquivo}
    if por_item:
        params = {"mode": "runOnceForEachItem", **params}
    extra = {"onError": "continueErrorOutput"} if saida_de_erro else {}
    node(name, "n8n-nodes-base.code", params, pos, 2, **extra)


def http(name, pos, metodo, url, cred, corpo=None, query=None, retry=3, on_error=None, timeout=20000):
    """HTTP Request. Sem on_error, uma falha (depois das tentativas) para a execução e o Error Workflow assume."""
    params = {"method": metodo, "url": url, "options": {"timeout": timeout}}
    if "openAiApi" in cred:
        params.update(authentication="predefinedCredentialType", nodeCredentialType="openAiApi")
    elif "pipedriveApi" in cred:
        params.update(authentication="predefinedCredentialType", nodeCredentialType="pipedriveApi")
    else:
        params.update(authentication="genericCredentialType", genericAuthType="httpHeaderAuth")
    if query:
        params.update(sendQuery=True, queryParameters={"parameters": [{"name": k, "value": v} for k, v in query]})
    if corpo:
        params.update(sendBody=True, specifyBody="json", jsonBody=corpo)
    extra = {"onError": on_error} if on_error else {}
    node(name, "n8n-nodes-base.httpRequest", params, pos, 4.2, retryOnFail=retry > 1, maxTries=retry,
         waitBetweenTries=2000, credentials=cred, **extra)


def condicao(id_, esquerda, valor=None, tipo="string", op="equals"):
    c = {"id": id_, "leftValue": esquerda, "rightValue": valor if valor is not None else "",
         "operator": {"type": tipo, "operation": op}}
    if valor is None:
        c["operator"]["singleValue"] = True
    return c


def grupo(conds, validacao="strict"):
    return {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": validacao, "version": 2},
            "conditions": conds, "combinator": "and"}


def switch(name, campo, saidas, pos):
    regras = [{"conditions": grupo([condicao(f"{name}-{s}", f"={{{{ $json.{campo} }}}}", s)]),
               "renameOutput": True, "outputKey": s} for s in saidas]
    node(name, "n8n-nodes-base.switch", {"rules": {"values": regras}, "options": {}}, pos, 3.2)


def postgres(name, sql, valores, pos, on_error=None, **extra):
    if on_error:
        extra["onError"] = on_error
    node(name, "n8n-nodes-base.postgres",
         {"operation": "executeQuery", "query": sql, "options": {"queryReplacement": valores}},
         pos, 2.6, credentials=CRED_POSTGRES, **extra)


def enviar(name, pos, ctx="$json", on_error=None):
    """POST /messages no Chatwoot com o texto em <ctx>.resposta (URL base em config.chatwoot_url)."""
    url = (f"={{{{ {ctx}.config.chatwoot_url }}}}/api/v1/accounts/{{{{ {ctx}.account_id }}}}"
           f"/conversations/{{{{ {ctx}.conversation_id }}}}/messages")
    corpo = f"={{{{ JSON.stringify({{ content: {ctx}.resposta, message_type: 'outgoing', private: false }}) }}}}"
    http(name, pos, "POST", url, CRED_CHATWOOT, corpo=corpo, timeout=15000, on_error=on_error)


# Os dados vão como UM parâmetro JSON: null continua NULL no banco (com parâmetros soltos o n8n
# grava o texto "null") e vírgula dentro de um nome não quebra a lista de parâmetros.
SQL_SALVAR_ESTADO = (
    "INSERT INTO conversation_state (conversation_id, phone, stage, nome, email, curso, campo_pendente, ultimo_aviso, qtd_sem_texto, updated_at)\n"
    "SELECT (d->>'conversation_id')::bigint, d->>'phone', d->>'stage', d->>'nome', d->>'email', d->>'curso', d->>'campo_pendente', NULL, 0, now()\n"
    "FROM (SELECT $1::jsonb AS d) AS dados\n"
    "ON CONFLICT (conversation_id) DO UPDATE SET\n"
    "  phone = EXCLUDED.phone, stage = EXCLUDED.stage, nome = EXCLUDED.nome, email = EXCLUDED.email,\n"
    "  curso = EXCLUDED.curso, campo_pendente = EXCLUDED.campo_pendente,\n"
    "  ultimo_aviso = NULL, qtd_sem_texto = 0, updated_at = now();")


def salvar_estado(name, pos, ctx="$json"):
    """Upsert da conversa em conversation_state (uma linha por conversa)."""
    valores = (f"={{{{ JSON.stringify({{ conversation_id: {ctx}.conversation_id, phone: {ctx}.telefone_normalizado, "
               f"stage: {ctx}.novo_stage, nome: {ctx}.lead.nome, email: {ctx}.lead.email, curso: {ctx}.lead.curso, "
               f"campo_pendente: {ctx}.campo_pendente }}) }}}}")
    postgres(name, SQL_SALVAR_ESTADO, valores, pos)


def liga(origem, destino, saida=0):
    saidas = connections.setdefault(origem, {"main": []})["main"]
    while len(saidas) <= saida:
        saidas.append([])
    saidas[saida].append({"node": destino, "type": "main", "index": 0})


def corrente(*nomes):
    for a, b in zip(nomes, nomes[1:]):
        liga(a, b)


X = lambda i: i * 220          # coluna i do grid
FAIXA_DUVIDA, FAIXA_LEAD = 560, 1440
X_RAMOS = X(12)                # onde começam as faixas das intenções

# ================================================================ FAIXA PRINCIPAL: entender a mensagem
nota("Nota: 1. Entrada e filtro",
     "## 1. Entrada e filtro\nO Chatwoot chama este Webhook a cada `message_created`.\n\n"
     "O bot só segue se **todas** forem verdade:\n- evento é `message_created`\n"
     "- mensagem `incoming` (do contato), não privada\n"
     "- remetente é `contact` (evita loop: respostas do próprio bot chegam como `outgoing`)\n"
     "- conversa `pending` **e** sem atendente (`assignee`). Quando o bot transfere, a conversa vira `open` e ele fica em silêncio.\n\n"
     "**Config** guarda a URL do Chatwoot e o modelo da OpenAI.",
     (X(0) - 60, -520), X(3) - 20, 680)
node("Chatwoot: mensagem recebida", "n8n-nodes-base.webhook",
     {"httpMethod": "POST", "path": "chatwoot-falebem", "options": {}}, (X(0), 0), 2,
     webhookId="6f0c2b8e-3d4a-4c1e-9b7a-2f5d8e1c4a90")
node("Deve responder?", "n8n-nodes-base.filter", {"conditions": grupo([
    condicao("f1-evento", "={{ $json.body.event }}", "message_created"),
    condicao("f2-incoming", "={{ $json.body.message_type }}", "incoming"),
    condicao("f3-nao-privada", "={{ $json.body.private !== true }}", None, "boolean", "true"),
    condicao("f4-contato", "={{ $json.body.sender?.type }}", "contact"),
    condicao("f5-pendente", "={{ $json.body.conversation?.status }}", "pending"),
    condicao("f6-sem-atendente", "={{ !$json.body.conversation?.meta?.assignee }}", None, "boolean", "true"),
], "loose"), "options": {}}, (X(1), 0), 2.2)
node("Config", "n8n-nodes-base.set", {"assignments": {"assignments": [
    {"id": "cfg-chatwoot-url", "name": "config.chatwoot_url",
     "value": "https://webhook.site/6911d878-b057-4dba-b99f-a03ff679a435", "type": "string"},
    {"id": "cfg-openai-model", "name": "config.openai_model", "value": "gpt-4.1-nano", "type": "string"},
]}, "includeOtherFields": True, "options": {}}, (X(2), 0), 3.4)

nota("Nota: 2. Preparar mensagem e estado",
     "## 2. Preparar mensagem e estado\n**Preparar mensagem** limpa o texto (\"oi......  quanto custa???\" vira \"oi. quanto custa?\") "
     "e classifica o tipo. Só `texto` vai para a IA: figurinha, emoji solto, foto sem legenda e áudio sem transcrição "
     "recebem resposta fixa, sem gastar chamada de IA.\n\nÁudio transcrito pelo Chatwoot (`transcribed_text`) e legenda de foto contam como texto.\n\n"
     "**Buscar estado** lê a conversa no Postgres (banco `falebem`): o que já foi coletado do lead e quais avisos já foram enviados.",
     (X(3) - 60, -520), X(5) - 20, 680)
code("Preparar mensagem", "workflows/code/preparar-mensagem.js", (X(3), 0))
code("Normalizar telefone (2.1)", "parte2/2.1-normalizar-telefone.js", (X(4), 0))
postgres("Buscar estado da conversa", "SELECT * FROM conversation_state WHERE conversation_id = $1;",
         "={{ $json.conversation_id }}", (X(5), 0), alwaysOutputData=True)
code("Montar contexto", "// Junta a mensagem preparada com o estado salvo da conversa (null se é a primeira vez).\n"
     "const msg = $('Normalizar telefone (2.1)').item.json;\nconst estado = $json.conversation_id ? $json : null;\n\n"
     "return { json: { ...msg, estado } };\n", (X(6), 0))
switch("Tipo de mensagem", "tipo", ["texto", "vazio", "midia", "audio", "nao_suportado"], (X(7), 0))

nota("Nota: 3. Intenção (IA)",
     "## 3. Intenção (IA)\nA OpenAI responde em **JSON com schema fixo** (structured output): a intenção só pode ser "
     "`interesse_matricula`, `duvida`, `falar_com_humano` ou `outro`. Na mesma chamada ela extrai nome, e-mail e curso, se aparecerem.\n\n"
     "Se o bot está no meio da matrícula, o pedido avisa a IA o que foi perguntado por último (assim \"Mariana\" é entendido como o nome).\n\n"
     "**Falha da IA** (erro, timeout, 429 após 3 tentativas, resposta fora da lista) → intenção vira `outro` e o erro vai em `ia.erro` para o log.",
     (X(8) - 60, -520), X(4) - 20, 680)
code("Montar pedido para a IA", "workflows/code/montar-pedido-ia.js", (X(8), 0))
http("Classificar intenção (OpenAI)", (X(9), 0), "POST", OPENAI_URL, CRED_OPENAI,
     corpo="={{ JSON.stringify($json.pedido_ia) }}", on_error="continueRegularOutput")
code("Validar resposta da IA", "workflows/code/validar-resposta-ia.js", (X(10), 0))
switch("Intenção", "ia.intencao", ["interesse_matricula", "duvida", "falar_com_humano", "outro"], (X(11), 0))

corrente("Chatwoot: mensagem recebida", "Deve responder?", "Config", "Preparar mensagem", "Normalizar telefone (2.1)",
         "Buscar estado da conversa", "Montar contexto", "Tipo de mensagem")
liga("Tipo de mensagem", "Montar pedido para a IA", 0)
corrente("Montar pedido para a IA", "Classificar intenção (OpenAI)", "Validar resposta da IA", "Intenção")

SQL_REGISTRAR_OFERTA = (
    "INSERT INTO conversation_state (conversation_id, phone, ofereceu_atendente_em, updated_at)\n"
    "SELECT (d->>'conversation_id')::bigint, d->>'phone', now(), now()\n"
    "FROM (SELECT $1::jsonb AS d) AS dados\n"
    "ON CONFLICT (conversation_id) DO UPDATE SET ofereceu_atendente_em = now(), updated_at = now();")
VALORES_CONVERSA = "={{ JSON.stringify({ conversation_id: $json.conversation_id, phone: $json.telefone_normalizado }) }}"

# ================================================================ FAIXA: MENSAGEM SEM TEXTO
S = FAIXA_DUVIDA
CTX_AVISO = "$('Montar aviso (mensagem sem texto)').item.json"
nota("Nota: Faixa Sem texto",
     "## Faixa: mensagem sem texto\n\"?\", \"......\", emoji solto, foto/documento sem legenda, áudio sem transcrição, visualização única, "
     "figurinha. **Não vai para a IA** (economiza chamada e evita 429).\n\n"
     "Várias seguidas (10 min) = dificuldade, então o bot escala:\n"
     "**1ª** aviso → **2ª** oferece atendente → **3ª** transfere pela faixa humano (respeita horário e feriado) → **4ª+** silêncio.\n\n"
     "Figurinha é exceção: rajada de figurinhas é brincadeira, então só o 1º aviso.\n\n"
     "No meio da matrícula, o aviso lembra o dado que falta. *Salvar aviso* não mexe nos dados do lead.",
     (X(7) - 60, S - 360), X(4) - 20, 640, 6)
code("Montar aviso (mensagem sem texto)", "workflows/code/montar-aviso-sem-texto.js", (X(7), S))
switch("Avisar ou transferir?", "acao_sem_texto", ["avisar", "transferir"], (X(8), S))
SQL_SALVAR_AVISO = (
    "INSERT INTO conversation_state (conversation_id, phone, ultimo_aviso, ultimo_aviso_em, qtd_sem_texto, ofereceu_atendente_em, updated_at)\n"
    "SELECT (d->>'conversation_id')::bigint, d->>'phone', d->>'ultimo_aviso', now(), (d->>'qtd_sem_texto')::int,\n"
    "       CASE WHEN (d->>'ofereceu_atendente')::boolean THEN now() END, now()\n"
    "FROM (SELECT $1::jsonb AS d) AS dados\n"
    "ON CONFLICT (conversation_id) DO UPDATE SET\n"
    "  ultimo_aviso = EXCLUDED.ultimo_aviso, ultimo_aviso_em = now(), qtd_sem_texto = EXCLUDED.qtd_sem_texto,\n"
    "  ofereceu_atendente_em = COALESCE(EXCLUDED.ofereceu_atendente_em, conversation_state.ofereceu_atendente_em),\n"
    "  updated_at = now();")
VALORES_AVISO = ("={{ JSON.stringify({ conversation_id: $json.conversation_id, phone: $json.telefone_normalizado, "
                 "ultimo_aviso: $json.ultimo_aviso, qtd_sem_texto: $json.qtd_sem_texto, ofereceu_atendente: $json.ofereceu_atendente }) }}")
postgres("Salvar aviso", SQL_SALVAR_AVISO, VALORES_AVISO, (X(9), S - 80))
enviar("Enviar aviso", (X(10), S - 80), CTX_AVISO)
postgres("Salvar aviso (transferência)", SQL_SALVAR_AVISO, VALORES_AVISO, (X(9), S + 120))
for saida in (1, 2, 3, 4):  # vazio, midia, audio, nao_suportado
    liga("Tipo de mensagem", "Montar aviso (mensagem sem texto)", saida)
corrente("Montar aviso (mensagem sem texto)", "Avisar ou transferir?")
liga("Avisar ou transferir?", "Salvar aviso", 0)
corrente("Salvar aviso", "Enviar aviso")
# transferir: anota a contagem (para a 4ª ficar em silêncio) e segue para a faixa humano com o contexto intacto
liga("Avisar ou transferir?", "Salvar aviso (transferência)", 1)
liga("Avisar ou transferir?", "Config: feriados", 1)

# ================================================================ FAIXA: DÚVIDA
D = FAIXA_DUVIDA
CTX_DUVIDA = "$('Conferir resposta da dúvida').item.json"
nota("Nota: Faixa Dúvida",
     "## Faixa: dúvida\nA OpenAI recebe **só os dados oficiais do PDF** e é instruída a dizer que não sabe quando a resposta não está ali.\n\n"
     "**Trava anti-invenção** (*Conferir resposta da dúvida*): todo `R$` e todo horário citado precisa existir nos dados oficiais "
     "(389, 349, 120 / 8h, 18h). Se não existir, a resposta é descartada e o bot diz que não tem a informação e oferece uma atendente. "
     "Inventar preço é o pior erro deste bot, então não confiamos só no prompt.\n\n"
     "Quando oferece atendente, anota no Postgres: se a pessoa responder \"sim\", a IA entende como pedido de atendimento.\n\n"
     "Se a OpenAI falhar, o contato recebe a mensagem de contingência e o erro segue em `erros` para o log.",
     (X_RAMOS - 60, D - 340), X(6) - 20, 680, 5)
code("Montar pedido de resposta (dúvida)", "workflows/code/montar-pedido-duvida.js", (X_RAMOS, D))
http("Responder dúvida (OpenAI)", (X_RAMOS + X(1), D), "POST", OPENAI_URL, CRED_OPENAI,
     corpo="={{ JSON.stringify($json.pedido_ia) }}", on_error="continueRegularOutput")
code("Conferir resposta da dúvida", "workflows/code/validar-resposta-duvida.js", (X_RAMOS + X(2), D))
node("Ofereceu atendente?", "n8n-nodes-base.if", {"conditions": grupo([
    condicao("ofereceu", "={{ $json.oferece_atendente }}", None, "boolean", "true")], "loose"),
    "options": {}}, (X_RAMOS + X(3), D), 2.2)
postgres("Registrar oferta de atendente (dúvida)", SQL_REGISTRAR_OFERTA, VALORES_CONVERSA, (X_RAMOS + X(4), D - 120))
enviar("Enviar resposta da dúvida", (X_RAMOS + X(5), D), CTX_DUVIDA)
liga("Intenção", "Montar pedido de resposta (dúvida)", 1)
corrente("Montar pedido de resposta (dúvida)", "Responder dúvida (OpenAI)", "Conferir resposta da dúvida",
         "Ofereceu atendente?")
liga("Ofereceu atendente?", "Registrar oferta de atendente (dúvida)", 0)
liga("Ofereceu atendente?", "Enviar resposta da dúvida", 1)
corrente("Registrar oferta de atendente (dúvida)", "Enviar resposta da dúvida")

# ================================================================ FAIXA: MATRÍCULA
L = FAIXA_LEAD
nota("Nota: Faixa Matrícula",
     "## Faixa: matrícula (captura de lead)\n**Atualizar dados do lead** junta o que está salvo no Postgres com o que a IA extraiu agora e decide:\n"
     "- **perguntar**: falta nome, e-mail ou curso → salva o estado e pergunta (um dado por vez)\n"
     "- **cadastrar**: tem os três → Pipedrive. Quem já era lead também passa por aqui: o cadastro não duplica nada e, "
     "se alguém apagou o lead no Pipedrive, ele é recriado.\n\n"
     "Estado em `conversation_state` (Postgres): cada mensagem é uma execução nova do n8n. Salva **antes** de enviar, "
     "para o bot nunca fazer uma pergunta e esquecer que fez.\n\n"
     "**Sem duplicar no Pipedrive (API v2):** busca por trecho do telefone; *Encontrar pessoa pelo telefone* normaliza cada resultado "
     "com a função do 2.1 e só considera a mesma pessoa se o número ficar idêntico. Achou → atualiza; não achou → cria.\n\n"
     "**Negócio** `Matrícula <curso>` com valor previsto (matrícula + mensalidade × duração, em BRL). Se a pessoa já tem um negócio "
     "**aberto** com o mesmo título (lead que volta numa conversa nova), não cria outro.\n\n"
     "Etiqueta `lead-qualificado`: o endpoint **substitui** as etiquetas, então mandamos as antigas + a nova. "
     "A conversa só vira `concluido` depois disso tudo dar certo.",
     (X_RAMOS - 60, L - 520), X(15) - 20, 1040, 4)
code("Atualizar dados do lead", "workflows/code/atualizar-dados-lead.js", (X_RAMOS, L))
switch("Próximo passo do lead", "acao", ["perguntar", "cadastrar"], (X_RAMOS + X(1), L))
# perguntar: linha de cima da faixa
salvar_estado("Salvar estado (coletando)", (X_RAMOS + X(3), L - 180))
enviar("Enviar pergunta do lead", (X_RAMOS + X(4), L - 180), CTX_LEAD)
# cadastrar: linha do meio
http("Pipedrive: buscar pessoa pelo telefone", (X_RAMOS + X(2), L + 40), "GET", f"{PIPEDRIVE}/persons/search", CRED_PIPEDRIVE,
     query=[("term", "={{ ($json.telefone_normalizado || $json.telefone || '').replace(/\\D/g, '').slice(-8) || '00000000' }}"),
            ("fields", "phone")])
code("Encontrar pessoa pelo telefone", "workflows/code/encontrar-pessoa-telefone.js", (X_RAMOS + X(3), L + 40))
node("Já existe no Pipedrive?", "n8n-nodes-base.if", {"conditions": grupo([
    condicao("existe", "={{ $json.pipedrive_person_id !== null }}", None, "boolean", "true")], "loose"),
    "options": {}}, (X_RAMOS + X(4), L + 40), 2.2)
corpo_pessoa = ("={{ JSON.stringify({ name: $json.lead.nome, "
                "emails: [{ value: $json.lead.email, primary: true, label: 'work' }], "
                "phones: [{ value: $json.telefone_normalizado || $json.telefone, primary: true, label: 'mobile' }] }) }}")
http("Pipedrive: atualizar pessoa", (X_RAMOS + X(5), L - 40), "PATCH",
     f"={PIPEDRIVE}/persons/{{{{ $json.pipedrive_person_id }}}}", CRED_PIPEDRIVE, corpo=corpo_pessoa, retry=2)
http("Pipedrive: criar pessoa", (X_RAMOS + X(5), L + 120), "POST", f"{PIPEDRIVE}/persons", CRED_PIPEDRIVE,
     corpo=corpo_pessoa, retry=2)
code("Guardar id da pessoa", "// Atualizar ou criar: os dois devolvem a pessoa em data.id. Guarda junto com o contexto do lead.\n"
     "const contexto = $('Encontrar pessoa pelo telefone').item.json;\n\n"
     "return { json: { ...contexto, pipedrive_person_id: $json.data.id } };\n", (X_RAMOS + X(6), L + 40))
http("Pipedrive: negócios abertos da pessoa", (X_RAMOS + X(7), L + 40), "GET", f"{PIPEDRIVE}/deals", CRED_PIPEDRIVE,
     query=[("person_id", "={{ $json.pipedrive_person_id }}"), ("status", "open")])
code("Verificar negócio aberto", "workflows/code/verificar-negocio-aberto.js", (X_RAMOS + X(8), L + 40))
node("Já tem negócio aberto?", "n8n-nodes-base.if", {"conditions": grupo([
    condicao("tem-negocio", "={{ $json.negocio_existente_id !== null }}", None, "boolean", "true")], "loose"),
    "options": {}}, (X_RAMOS + X(9), L + 40), 2.2)
http("Pipedrive: criar negócio", (X_RAMOS + X(10), L + 180), "POST", f"{PIPEDRIVE}/deals", CRED_PIPEDRIVE, retry=2,
     corpo=("={{ JSON.stringify({ title: $json.titulo_negocio, person_id: $json.pipedrive_person_id, "
            "value: $json.lead.valor_contrato, currency: 'BRL' }) }}"))
http("Chatwoot: etiqueta lead-qualificado", (X_RAMOS + X(11), L + 40), "POST",
     f"={{{{ {CTX_LEAD}.config.chatwoot_url }}}}/api/v1/accounts/{{{{ {CTX_LEAD}.account_id }}}}"
     f"/conversations/{{{{ {CTX_LEAD}.conversation_id }}}}/labels", CRED_CHATWOOT, timeout=15000,
     corpo="={{ JSON.stringify({ labels: [...new Set([...($('Chatwoot: mensagem recebida').item.json.body.conversation?.labels ?? []), 'lead-qualificado'])] }) }}")
code("Confirmar matrícula", "workflows/code/confirmar-matricula.js", (X_RAMOS + X(12), L + 40))
salvar_estado("Salvar estado (concluído)", (X_RAMOS + X(13), L + 40))
enviar("Enviar confirmação da matrícula", (X_RAMOS + X(14), L + 40), CTX_CONFIRMACAO)

liga("Intenção", "Atualizar dados do lead", 0)
corrente("Atualizar dados do lead", "Próximo passo do lead")
liga("Próximo passo do lead", "Salvar estado (coletando)", 0)
corrente("Salvar estado (coletando)", "Enviar pergunta do lead")
liga("Próximo passo do lead", "Pipedrive: buscar pessoa pelo telefone", 1)
corrente("Pipedrive: buscar pessoa pelo telefone", "Encontrar pessoa pelo telefone", "Já existe no Pipedrive?")
liga("Já existe no Pipedrive?", "Pipedrive: atualizar pessoa", 0)
liga("Já existe no Pipedrive?", "Pipedrive: criar pessoa", 1)
liga("Pipedrive: atualizar pessoa", "Guardar id da pessoa")
liga("Pipedrive: criar pessoa", "Guardar id da pessoa")
corrente("Guardar id da pessoa", "Pipedrive: negócios abertos da pessoa", "Verificar negócio aberto", "Já tem negócio aberto?")
liga("Já tem negócio aberto?", "Chatwoot: etiqueta lead-qualificado", 0)
liga("Já tem negócio aberto?", "Pipedrive: criar negócio", 1)
corrente("Pipedrive: criar negócio", "Chatwoot: etiqueta lead-qualificado", "Confirmar matrícula",
         "Salvar estado (concluído)", "Enviar confirmação da matrícula")

# ================================================================ FAIXA: FALAR COM HUMANO
H = FAIXA_LEAD + 940
CTX_TRANSFERENCIA = "$('Mensagem: transferindo').item.json"
nota("Nota: Faixa Humano",
     "## Faixa: falar com humano\nHorário: seg-sex, 8h-18h, America/Recife (mesma regra do exercício 2.2), **menos os feriados** de "
     "*Config: feriados* (nacionais + PE + Recife, 2026-2027; **revisar todo ano**).\n\n"
     "- **Dentro do horário**: avisa o contato e abre a conversa para a equipe (`toggle_status` → `open`). "
     "A partir daí o filtro da entrada deixa o bot em silêncio.\n"
     "- **Fora do horário**: diz quando a equipe volta, pulando fim de semana e feriado "
     "(sexta 19h com segunda feriado → \"terça, 13/10, às 8h\"), e mantém a conversa `pending`.\n\n"
     "O horário considerado é o da mensagem (`created_at`), o que permite testar sábado/feriado pelo pin data.",
     (X_RAMOS - 60, H - 380), X(7) - 20, 700, 3)
code("Config: feriados", "workflows/code/config-feriados.js", (X_RAMOS, H))
code("Horário de atendimento (com feriados)", "workflows/code/horario-atendimento-feriados.js", (X_RAMOS + X(1), H))
node("Dentro do horário?", "n8n-nodes-base.if", {"conditions": grupo([
    condicao("dentro", "={{ $json.dentro_do_horario }}", None, "boolean", "true")], "loose"),
    "options": {}}, (X_RAMOS + X(2), H), 2.2)


def mensagem(name, texto, pos):
    """Set node com o texto da resposta: fica visível e editável sem mexer em código."""
    node(name, "n8n-nodes-base.set", {"assignments": {"assignments": [
        {"id": f"{name}-resposta", "name": "resposta", "value": texto, "type": "string"}]},
        "includeOtherFields": True, "options": {}}, pos, 3.4)


mensagem("Mensagem: transferindo",
         "Vou chamar uma das nossas atendentes para te ajudar. Em instantes alguém continua a conversa com você por aqui.",
         (X_RAMOS + X(3), H - 100))
enviar("Enviar aviso de transferência", (X_RAMOS + X(4), H - 100))
http("Chatwoot: abrir conversa para a equipe", (X_RAMOS + X(5), H - 100), "POST",
     f"={{{{ {CTX_TRANSFERENCIA}.config.chatwoot_url }}}}/api/v1/accounts/{{{{ {CTX_TRANSFERENCIA}.account_id }}}}"
     f"/conversations/{{{{ {CTX_TRANSFERENCIA}.conversation_id }}}}/toggle_status", CRED_CHATWOOT, timeout=15000,
     corpo="={{ JSON.stringify({ status: 'open' }) }}")
mensagem("Mensagem: fora do horário",
         "=No momento nossa equipe não está disponível. Retornamos {{ $json.proxima_abertura }}, "
         "e uma atendente vai te responder assim que voltarmos. "
         "Enquanto isso, posso tirar dúvidas sobre cursos e preços por aqui!",
         (X_RAMOS + X(3), H + 120))
enviar("Enviar aviso de fora do horário", (X_RAMOS + X(4), H + 120))

liga("Intenção", "Config: feriados", 2)
corrente("Config: feriados", "Horário de atendimento (com feriados)", "Dentro do horário?")
liga("Dentro do horário?", "Mensagem: transferindo", 0)
liga("Dentro do horário?", "Mensagem: fora do horário", 1)
corrente("Mensagem: transferindo", "Enviar aviso de transferência", "Chatwoot: abrir conversa para a equipe")
corrente("Mensagem: fora do horário", "Enviar aviso de fora do horário")

# ================================================================ FAIXA: OUTRO
O = H + 760
nota("Nota: Faixa Outro",
     "## Faixa: outro\nSaudação, agradecimento, assunto sem relação com a escola **ou falha da IA** (requisito 3: falhou → `outro`).\n\n"
     "No meio da matrícula, lembra o dado que falta. Fora disso, apresenta o que o bot sabe fazer.",
     (X_RAMOS - 60, O - 300), X(3) - 20, 460, 2)
code("Montar resposta (outro)", "workflows/code/montar-resposta-outro.js", (X_RAMOS, O))
enviar("Enviar resposta (outro)", (X_RAMOS + X(1), O))
liga("Intenção", "Montar resposta (outro)", 3)
corrente("Montar resposta (outro)", "Enviar resposta (outro)")

# ================================================================ Falhas da OpenAI (log local)
# Falha de Pipedrive, Chatwoot, Postgres ou de código para a execução e quem assume é a faixa de falhas
# (Error Trigger, mais abaixo). A OpenAI é diferente: o fluxo segue (classificação -> "outro";
# dúvida -> contingência própria), então o erro é registrado aqui mesmo, ao lado de onde acontece.
SQL_LOG_IA = ("INSERT INTO error_log (execution_id, node, message, conversation_id, payload)\n"
              "SELECT d->>'execution_id', d->>'node', d->>'message', (d->>'conversation_id')::bigint, d->'payload'\n"
              "FROM (SELECT $1::jsonb AS d) AS dados;")


def log_ia(name, no_origem, mensagem, pos):
    valores = ("={{ JSON.stringify({ execution_id: String($execution.id), node: '" + no_origem + "', message: " + mensagem +
               ", conversation_id: $json.conversation_id, payload: { mensagem_do_contato: $json.texto } }) }}")
    postgres(name, SQL_LOG_IA, valores, pos, on_error="continueRegularOutput")


node("Falha na IA?", "n8n-nodes-base.if", {"conditions": grupo([
    condicao("falha-ia", "={{ !!$json.ia.erro }}", None, "boolean", "true")], "loose"),
    "options": {}}, (X(10), -200), 2.2)
log_ia("Registrar falha da IA", "Classificar intenção (OpenAI)", "$json.ia.erro", (X(11), -200))
liga("Validar resposta da IA", "Falha na IA?")
liga("Falha na IA?", "Registrar falha da IA", 0)
node("Falha na IA (dúvida)?", "n8n-nodes-base.if", {"conditions": grupo([
    condicao("falha-ia-duvida", "={{ $json.erros.length > 0 }}", None, "boolean", "true")], "loose"),
    "options": {}}, (X_RAMOS + X(3), D + 180), 2.2)
log_ia("Registrar falha da IA (dúvida)", "Responder dúvida (OpenAI)", "$json.erros.join(' | ')", (X_RAMOS + X(4), D + 180))
liga("Conferir resposta da dúvida", "Falha na IA (dúvida)?")
liga("Falha na IA (dúvida)?", "Registrar falha da IA (dúvida)", 0)

# ================================================================ FAIXA: FALHAS (Error Trigger)
# Um workflow que tem Error Trigger é o próprio Error Workflow: quando uma execução do bot falha, o n8n roda
# esta faixa como uma execução nova. Nenhuma linha liga o resto do bot aqui. Só dispara em execuções reais
# (Webhook ativo); testes manuais no editor não disparam o Error Trigger.
F = O + 760
CRED_N8N_API = {"httpHeaderAuth": {"id": "UIRyenBXIi4CfS7a", "name": "Header Auth account"}}
nota("Nota: Falhas",
     "## Faixa: falhas (requisito 7)\nComeça no **Error Trigger**, sem linhas vindo do resto do bot. O n8n roda esta faixa quando uma execução falha: "
     "Pipedrive, Chatwoot ou Postgres fora do ar (depois das tentativas) ou erro de código.\n\n"
     "1. **Buscar a execução que falhou** pela API do n8n, para descobrir a conversa (funciona mesmo com o banco do bot fora do ar).\n"
     "2. **Registrar falha** na tabela `error_log` (banco `falebem`): nó, mensagem, execução, conversa. "
     "Para descobrir depois: `SELECT * FROM error_log ORDER BY created_at DESC;`\n"
     "3. **Contingência**: \"Desculpe, tive um problema...\" para o contato não ficar sem resposta.\n\n"
     "2 e 3 saem em paralelo: se o banco estiver fora, a mensagem ao contato sai mesmo assim.\n\n"
     "Falhas da OpenAI não chegam aqui: o bot segue sozinho e registra o erro no próprio workflow.",
     (X_RAMOS - 60, F - 480), X(5) - 20, 760, 1)
node("Quando o bot falhar", "n8n-nodes-base.errorTrigger", {}, (X_RAMOS, F), 1)
http("Buscar execução que falhou (API n8n)", (X_RAMOS + X(1), F), "GET",
     "=http://localhost:5678/api/v1/executions/{{ $json.execution.id }}", CRED_N8N_API,
     query=[("includeData", "true")], retry=2, on_error="continueRegularOutput", timeout=15000)
code("Montar registro de falha", "workflows/code/montar-registro-falha.js", (X_RAMOS + X(2), F))
postgres("Registrar falha (error_log)",
         "INSERT INTO error_log (execution_id, node, message, conversation_id, payload)\n"
         "SELECT d->>'execution_id', d->>'node', d->>'message', (d->>'conversation_id')::bigint, d->'payload'\n"
         "FROM (SELECT $1::jsonb AS d) AS dados;",
         "={{ JSON.stringify($json.registro) }}", (X_RAMOS + X(3), F - 120), on_error="continueRegularOutput")
node("Precisa de contingência?", "n8n-nodes-base.if", {"conditions": grupo([
    condicao("contingencia", "={{ $json.enviar_contingencia }}", None, "boolean", "true")], "loose"),
    "options": {}}, (X_RAMOS + X(3), F + 100), 2.2)
enviar("Enviar mensagem de contingência", (X_RAMOS + X(4), F + 100))
corrente("Quando o bot falhar", "Buscar execução que falhou (API n8n)", "Montar registro de falha")
liga("Montar registro de falha", "Registrar falha (error_log)")
liga("Montar registro de falha", "Precisa de contingência?")
liga("Precisa de contingência?", "Enviar mensagem de contingência", 0)

# ================================================================ PARTE 2: exercícios de Code node
P2 = F + 760
nota("Nota: Parte 2",
     "## Parte 2: JavaScript no Code node\nOs três exercícios, cada um em um Code node próprio, sem bibliotecas externas. "
     "Rode pelo botão **Test workflow → Testar Parte 2**.\n\n"
     "Cada exercício recebe os casos do PDF de um nó *Casos de teste*. O 2.1 também é usado no bot "
     "(*Normalizar telefone (2.1)* e na busca do Pipedrive).",
     (X(0) - 60, P2 - 340), X(4) - 20, 1100, 6)
node("Testar Parte 2", "n8n-nodes-base.manualTrigger", {}, (X(0), P2 + 220), 1)
code("Casos de teste 2.1", "return [\n  '(81) 99876-5432',\n  '+55 81 9 9876-5432',\n  '5581998765432',\n  '81998765432',\n"
     "  '998765432',\n  'abc',\n].map(telefone => ({ json: { telefone } }));\n", (X(1), P2), por_item=False, saida_de_erro=False)
code("Exercício 2.1: normalizar telefone", "parte2/2.1-normalizar-telefone.js", (X(2), P2), saida_de_erro=False)
code("Casos de teste 2.2", "return [\n  '2026-10-05T11:00:00Z',\n  '2026-10-06T10:59:00Z',\n  '2026-10-05T21:00:00Z',\n"
     "  '2026-10-10T14:00:00Z',\n].map(data => ({ json: { data } }));\n", (X(1), P2 + 220), por_item=False, saida_de_erro=False)
code("Exercício 2.2: horário de atendimento", "parte2/2.2-horario-atendimento.js", (X(2), P2 + 220), saida_de_erro=False)
code("Casos de teste 2.3", "return [\n"
     "  { json: { conversation_id: 42, content: 'do curso de inglês', created_at: '2026-10-05T12:00:09Z' } },\n"
     "  { json: { conversation_id: 77, content: 'boa tarde', created_at: '2026-10-05T12:00:03Z' } },\n"
     "  { json: { conversation_id: 42, content: 'oi', created_at: '2026-10-05T12:00:01Z' } },\n"
     "  { json: { conversation_id: 42, content: 'queria saber o valor', created_at: '2026-10-05T12:00:05Z' } },\n"
     "];\n", (X(1), P2 + 440), por_item=False, saida_de_erro=False)
code("Exercício 2.3: juntar mensagens picadas", "parte2/2.3-juntar-mensagens.js", (X(2), P2 + 440), por_item=False, saida_de_erro=False)
for n in ("1", "2", "3"):
    liga("Testar Parte 2", f"Casos de teste 2.{n}")
corrente("Casos de teste 2.1", "Exercício 2.1: normalizar telefone")
corrente("Casos de teste 2.2", "Exercício 2.2: horário de atendimento")
corrente("Casos de teste 2.3", "Exercício 2.3: juntar mensagens picadas")

# ================================================================ Pin data (payload do PDF)
PAYLOAD = {
    "event": "message_created", "id": 90871, "content": "Oi, quanto custa o curso de inglês?",
    "message_type": "incoming", "private": False, "created_at": "2026-10-05T12:00:01Z",
    "account": {"id": 3, "name": "Escola Fale Bem"}, "inbox": {"id": 11, "name": "WhatsApp Fale Bem"},
    "sender": {"id": 5521, "name": "Mariana Souza", "phone_number": "+5581998765432", "type": "contact"},
    "conversation": {"id": 42, "status": "pending", "labels": [], "custom_attributes": {},
                     "meta": {"sender": {"id": 5521, "name": "Mariana Souza", "phone_number": "+5581998765432"},
                              "assignee": None}},
}
pin = {"Chatwoot: mensagem recebida": [{"json": {"headers": {"content-type": "application/json"},
                                                 "params": {}, "query": {}, "body": PAYLOAD}}]}

def gravar(arquivo, nome, pin_data=None):
    """Confere as ligações, grava o workflow e zera as listas para o próximo."""
    nomes = {n["name"] for n in nodes}
    for origem, c in connections.items():
        assert origem in nomes, origem
        for saida in c["main"]:
            for d in saida:
                assert d["node"] in nomes, d["node"]
    destino = RAIZ / "workflows" / arquivo
    destino.write_text(json.dumps({"name": nome, "nodes": nodes, "connections": connections,
                                   "pinData": pin_data or {}, "settings": {"executionOrder": "v1"}},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(nodes)} nos -> {destino.relative_to(RAIZ)}")
    nodes.clear()
    connections.clear()


gravar("bot-fale-bem.json", "Bot Fale Bem - Atendimento", pin)

