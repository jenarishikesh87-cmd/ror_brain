// ---------------- SEND MESSAGE ----------------
async function sendMessage(){
    const input = document.getElementById("input"); // FIXED ID
    const message = input.value.trim();

    if(!message) return;

    addMessage(message, "user");
    input.value = "";

    try{
        const res = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({message})
        });

        const data = await res.json();
        addMessage(data.reply, "bot"); // FIXED TYPE

    }catch(err){
        addMessage("Error connecting to server", "bot");
    }
}

// ---------------- ADD MESSAGE ----------------
function addMessage(text, type){
    const chat = document.getElementById("chat");

    const bubble = document.createElement("div");
    bubble.className = "bubble " + type;
    bubble.innerText = text;

    chat.appendChild(bubble);

    const meta = document.createElement("div");
    meta.className = "meta " + (type==="user" ? "user-meta":"bot-meta");
    meta.innerText = "Sent · " + new Date().toLocaleTimeString();

    chat.appendChild(meta);

    chat.scrollTop = chat.scrollHeight;
}

// ---------------- TRADING ----------------
async function getTrade(){
    const tradeResult = document.getElementById("trade-result");

    tradeResult.innerText = "Checking market...";

    try{
        const res = await fetch("/ror-trade");
        const data = await res.json();

        let html = "";

        if(data.error){
            html = "❌ Error: " + data.error;
        }
        else if(!data.price){
            html = "⚠ No market data";
        }
        else{
            html = `
<b>Price:</b> $${data.price}
<b>Decision:</b> ${data.analysis?.decision || "N/A"}
<b>Confidence:</b> ${data.analysis?.confidence || "0"}%
<b>Reason:</b> ${data.analysis?.reason || "No reason"}
            `;
        }

        tradeResult.innerText = html;

    }catch(err){
        tradeResult.innerText = "Error fetching market";
    }
}

// ---------------- BUTTON BIND ----------------
document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("trade-btn");

    if(btn){
        btn.addEventListener("click", getTrade);
    }

    console.log("JS READY ✅");
});

// ---------------- REMINDER CHECK ----------------
setInterval(async ()=>{
    try{
        const res = await fetch("/check-reminder");
        const data = await res.json();

        if(data.reminder){
            addMessage("⏰ Reminder: " + data.reminder, "bot");
            alert("Reminder: " + data.reminder);
        }

    }catch(err){}
}, 15000);
