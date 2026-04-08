async function sendMessage() {
    const input = document.getElementById("message");
    const message = input.value;
    if (!message) return;

    addMessage(message, "user");
    input.value = "";

    const response = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: message })
    });

    const data = await response.json();
    addMessage(data.reply, "ror");
}

function addMessage(text, sender) {
    const chat = document.getElementById("chat");
    const div = document.createElement("div");
    div.className = "message " + sender;
    div.innerText = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
      }

async function getTrade() {
  const res = await fetch("/ror-trade");
  const data = await res.json();

  let html = "";

  if (data.error) {
  html = "❌ Error: " + data.error;
} else if (!data.price) {
  html = "⚠️ No market data received";
} else {
  html = `
    <p><b>Price:</b> $${data.price}</p>
    <p><b>Decision:</b> ${data.analysis?.decision || "N/A"}</p>
    <p><b>Confidence:</b> ${data.analysis?.confidence || "0"}%</p>
    <p><b>Reason:</b> ${data.analysis?.reason || "No reason"}</p>
  `;
  }
