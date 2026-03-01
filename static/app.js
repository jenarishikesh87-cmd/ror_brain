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
