"""
Servicio encargado de llamar a la API de Gemini:
- condense_question(): reformula una pregunta de seguimiento como una pregunta
  autocontenida, usando el historial de la conversación (necesario para que la
  búsqueda semántica funcione bien con preguntas como "¿y en ese caso qué pasa?").
- generate_answer_stream(): genera la respuesta final en streaming, considerando
  el contexto recuperado y el historial reciente de la conversación.
"""

import google.generativeai as genai

from app import config

genai.configure(api_key=config.GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Eres un asistente corporativo que responde preguntas de colaboradores "
    "de una empresa basándote ÚNICAMENTE en el contexto de documentos internos "
    "que se te proporciona a continuación. Reglas:\n"
    "1. Responde solo con base en el contexto entregado, nunca con conocimiento externo.\n"
    "2. Si la respuesta no está en el contexto, dilo explícitamente: "
    "'No encontré esta información en los documentos disponibles.' No inventes nada.\n"
    "3. Sé claro, directo y en español, salvo que te pregunten en otro idioma.\n"
    "4. Cuando puedas, menciona de qué documento proviene la información.\n"
    "5. Puedes usar el historial de la conversación para entender preguntas de "
    "seguimiento, pero la respuesta debe seguir basándose solo en el contexto entregado."
)

_model = genai.GenerativeModel(
    model_name=config.CHAT_MODEL,
    system_instruction=SYSTEM_INSTRUCTION,
)

# Modelo aparte, sin la "personalidad" corporativa, para la tarea de
# reformular preguntas (no debe negarse a responder ni citar fuentes).
_condense_model = genai.GenerativeModel(model_name=config.CHAT_MODEL)

MAX_HISTORY_TURNS = 6  # cuántos pares pregunta/respuesta recientes se conservan


def _format_history(history):
    """history: lista de {"role": "user"|"assistant", "content": str}."""
    if not history:
        return ""
    trimmed = history[-(MAX_HISTORY_TURNS * 2):]
    lines = []
    for turn in trimmed:
        speaker = "Colaborador" if turn.get("role") == "user" else "Agente"
        lines.append(f"{speaker}: {turn.get('content', '').strip()}")
    return "\n".join(lines)


def condense_question(question: str, history) -> str:
    """
    Reformula la pregunta actual como una pregunta autocontenida (standalone),
    resolviendo referencias al historial ("eso", "ese caso", "y el otro"), para
    usarla en la búsqueda semántica. Si no hay historial, devuelve la pregunta tal cual.
    """
    if not history:
        return question

    history_text = _format_history(history)
    prompt = (
        "Dado el siguiente historial de conversación y una pregunta de seguimiento, "
        "reformula la pregunta de seguimiento como una pregunta autocontenida y clara, "
        "en español, que se pueda entender sin necesidad de leer el historial. "
        "No la respondas, solo reformúlala. Si ya es autocontenida, devuélvela igual.\n\n"
        f"Historial:\n{history_text}\n\n"
        f"Pregunta de seguimiento: {question}\n\n"
        "Pregunta autocontenida:"
    )
    try:
        response = _condense_model.generate_content(prompt)
        condensed = (response.text or "").strip()
        return condensed if condensed else question
    except Exception:
        return question


def build_prompt(question: str, context: str, history=None) -> str:
    history_text = _format_history(history or [])
    history_block = f"Historial reciente de la conversación:\n{history_text}\n\n" if history_text else ""

    if not context:
        return (
            f"{history_block}"
            f"Pregunta del colaborador: {question}\n\n"
            "No hay documentos indexados todavía, informa que no puedes responder aún."
        )
    return (
        f"{history_block}"
        f"Contexto recuperado de los documentos internos:\n\n{context}\n\n"
        f"Pregunta del colaborador: {question}\n\n"
        "Responde siguiendo las reglas indicadas."
    )


def generate_answer_stream(question: str, context: str, history=None):
    """Generador que produce la respuesta de Gemini en fragmentos de texto (streaming)."""
    prompt = build_prompt(question, context, history)
    try:
        response = _model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"\n\n[Error al consultar el modelo: {e}]"
