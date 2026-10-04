-- Banco separado do n8n, só com os dados do bot.
CREATE DATABASE falebem;
\connect falebem

-- Estado da conversa (Parte 1, item 5): uma linha por conversa do Chatwoot.
CREATE TABLE conversation_state (
  conversation_id BIGINT PRIMARY KEY,
  phone           TEXT,
  stage           TEXT NOT NULL DEFAULT 'inicio',     -- inicio | coletando | concluido
  nome            TEXT,
  email           TEXT,
  curso           TEXT,                               -- Inglês | Espanhol
  campo_pendente  TEXT,                               -- dado que o bot pediu por último: nome | email | curso
  ultimo_aviso    TEXT,                               -- último aviso de mensagem sem texto (vazio | midia | audio | nao_suportado)
  ultimo_aviso_em TIMESTAMPTZ,                        -- quando foi enviado (não repetir o mesmo aviso em seguida)
  qtd_sem_texto   INT NOT NULL DEFAULT 0,             -- mensagens sem texto seguidas (2ª oferece atendente, 3ª transfere)
  ofereceu_atendente_em TIMESTAMPTZ,                  -- bot perguntou "quer falar com uma atendente?" (para entender o "sim")
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Log de falhas (Parte 1, item 7): para alguém descobrir o erro depois.
CREATE TABLE error_log (
  id              BIGSERIAL PRIMARY KEY,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  execution_id    TEXT,
  node            TEXT,
  message         TEXT,
  conversation_id BIGINT,
  payload         JSONB
);
