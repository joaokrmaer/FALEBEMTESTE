// Code node: "Verificar negócio aberto"
// Modo: Run Once for Each Item
// Lead que volta numa conversa nova não gera negócio repetido: se a pessoa já tem um negócio
// ABERTO com o mesmo título, reaproveitamos. Ganho ou perdido não conta (aí é uma nova venda).

const contexto = $('Guardar id da pessoa').item.json;
const titulo = `Matrícula ${contexto.lead.curso}`;
const negocios = Array.isArray($json.data) ? $json.data : [];
const aberto = negocios.find(n => n.title === titulo && n.status === 'open');

return {
  json: {
    ...contexto,
    titulo_negocio: titulo,
    negocio_existente_id: aberto?.id ?? null,
  },
};
