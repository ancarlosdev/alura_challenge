const chatWindow = document.getElementById("chat");
const form = document.getElementById("chat-form");
const input = document.getElementById("question-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");

// Historial de la conversación, solo en memoria del navegador (se pierde al
// recargar la página). No se usa localStorage/sessionStorage.
let conversationHistory = [];

resetBtn.addEventListener("click", () => {
  conversationHistory = [];
  chatWindow.innerHTML = "";
});

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function addSources(container, sources) {
  if (!sources || sources.length === 0) return;
  const sourcesDiv = document.createElement("div");
  sourcesDiv.className = "sources";
  sourcesDiv.textContent = "Fuentes: " + sources.join(", ");
  container.appendChild(sourcesDiv);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;

  addMessage(question, "user");
  input.value = "";
  sendBtn.disabled = true;

  const botDiv = addMessage("", "bot");
  const textNode = document.createElement("span");
  botDiv.appendChild(textNode);

  let fullAnswer = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        history: conversationHistory,
      }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";
    let metaParsed = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      if (!metaParsed) {
        const match = buffer.match(/^__META__(.*?)__END_META__/);
        if (match) {
          metaParsed = true;
          try {
            const meta = JSON.parse(match[1]);
            addSources(botDiv, meta.sources);
          } catch (err) {
            // ignore malformed meta
          }
          buffer = buffer.slice(match[0].length);
        } else {
          continue;
        }
      }

      textNode.textContent += buffer;
      fullAnswer += buffer;
      buffer = "";
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Actualiza el historial solo si la respuesta se generó con éxito.
    conversationHistory.push({ role: "user", content: question });
    conversationHistory.push({ role: "assistant", content: fullAnswer });
  } catch (err) {
    textNode.textContent = "Ocurrió un error al conectar con el agente.";
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});
