# Roteiro de testes

Cada arquivo `.json` desta pasta é uma mensagem do Chatwoot. Para usar: nó **Chatwoot: mensagem recebida** → lápis (Edit) no painel OUTPUT → Ctrl+A → Delete → cole o conteúdo do arquivo → Save → setinha do **Test workflow** → **Chatwoot: mensagem recebida**.

As respostas do bot aparecem no webhook.site. Os testes usam a conversa 42; o estado dela fica na tabela `conversation_state`.

**🔄 = zerar o estado antes** (apagar a linha da conversa 42: `DELETE FROM conversation_state WHERE conversation_id = 42;`).

## 1. Quando responder (requisito 2)
| Arquivo | Esperado |
|---|---|
| 16-atendente-ja-assumiu | Para no **Deve responder?** (atendente assumiu). Nada no webhook.site |
| 17-mensagem-do-proprio-bot | Para no **Deve responder?** (mensagem `outgoing`, evita loop). Nada no webhook.site |

## 2. Dúvidas (requisito 4) 🔄
| Arquivo | Esperado |
|---|---|
| 01-duvida-preco | Resposta com R$ 389 (inglês) |
| 14-duvida-sem-resposta | "Essa informação eu não tenho aqui. Quer que eu chame uma atendente?" |
| 15-sim-depois-da-oferta | Vai para a faixa humano: "Vou chamar uma das nossas atendentes..." + `toggle_status` open |

## 3. Outro 🔄
| Arquivo | Esperado |
|---|---|
| 10-outro-oi | Menu: "Oi! Sou o assistente virtual da Escola Fale Bem..." |

## 4. Matrícula (requisito 5) 🔄
| Arquivo | Esperado |
|---|---|
| 02-matricula-inicio | Pergunta o nome |
| 03-matricula-nome | "Prazer, Mariana! Qual é o seu e-mail?" |
| 04-matricula-email | Pergunta o curso |
| 05-matricula-curso | Pipedrive: pessoa + negócio "Matrícula Inglês" (R$ 7.122) + etiqueta `lead-qualificado` + "Prontinho, Mariana!..." |
| 06-matricula-tudo-de-uma-vez | Já era lead: **não** duplica pessoa nem negócio. "Seus dados já estão com a nossa equipe..." |

## 5. Mensagem sem texto 🔄
| Arquivo | Esperado |
|---|---|
| 13-velhinho-so-pontos (4x seguidas) | 1ª aviso → 2ª oferece atendente → 3ª transfere → 4ª nada |

## 6. Figurinha 🔄
| Arquivo | Esperado |
|---|---|
| 11-figurinha (3x seguidas) | Só a 1ª responde |

## 7. Áudio 🔄
| Arquivo | Esperado |
|---|---|
| 12-audio-sem-transcricao (2x) | 1ª "Ainda não consigo ouvir áudios..." → 2ª oferece atendente |

## 8. Falar com humano (requisito 6)
| Arquivo | Esperado |
|---|---|
| 07-humano-dentro-do-horario | "Vou chamar uma das nossas atendentes..." + `toggle_status` open |
| 08-humano-sabado | "No momento nossa equipe não está disponível. Retornamos terça, 13/10, às 8h..." |
| 09-humano-sexta-noite-antes-do-feriado | Igual ao 08 (segunda 12/10 é feriado) |

## 9. Falhas (requisito 7)
| Teste | Esperado |
|---|---|
| A. `config.openai_model` = `modelo-que-nao-existe` + 01-duvida-preco | Menu (falha da IA vira "outro") + linha nova em `error_log` + nota privada para a equipe (`"private": true`). **Voltar o modelo depois.** |
| B. Banco indisponível (tabela `conversation_state` renomeada) + 01-duvida-preco | "Desculpe, tive um problema para responder agora..." + linha em `error_log` + nota privada para a equipe. Só funciona com o workflow ativo (Error Trigger) |

Para ver os erros: `SELECT * FROM error_log ORDER BY created_at DESC;`
