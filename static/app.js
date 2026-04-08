// CENTRAL INIT
document.addEventListener("DOMContentLoaded", () => {
    console.log("ROR SYSTEM READY");

    initChat();
    initTrade();
    initMic();
    initReminder();
});            body: JSON.stringify({message})
        });

        const data = await res.json();
        addMessage(data.reply, "bot");

    }catch(err){
        addMessage("Server error", "bot");
    }
}

// ---------------- ENTER KEY ----------------
input.addEventListener("keypress", function(e){
    if(e.key === "Enter"){
        sendMessage();
    }
});

// ---------------- JARVIS MODE COMMAND FILTER ----------------
// Only activates for important commands
function handleJarvisCommand(text){
    const t = text.toLowerCase();

    if(t.includes("check market") || t.includes("btc")){
        getTrade();
        return true;
    }

    if(t.includes("show reminders")){
        sendMessage();
        return true;
    }

    return false;
}

// ---------------- TRADING ----------------
async function getTrade(){
    tradeResult.innerText = "Checking market...";

    try{
        const res = await fetch("/ror-trade");
        const data = await res.json();

        let text = "";

        if(data.error){
            text = "❌ Error: " + data.error;
        }
        else if(!data.price){
            text = "⚠ No market data";
        }
        else{
            text =
`Price: $${data.price}
Decision: ${data.analysis?.decision || "N/A"}
Confidence: ${data.analysis?.confidence || "0"}%
Reason: ${data.analysis?.reason || "No reason"}`;
        }

        tradeResult.innerText = text;

    }catch(err){
        tradeResult.innerText = "Error fetching market";
    }
}

// ---------------- BUTTON FIX ----------------
if(tradeBtn){
    tradeBtn.addEventListener("click", getTrade);
}

// ---------------- AUTO BTC REFRESH ----------------
setInterval(async ()=>{
    try{
        const res = await fetch("/ror-trade");
        const data = await res.json();

        if(!data.price) return;

        tradeResult.innerText =
`LIVE BTC: $${data.price}
Decision: ${data.analysis?.decision || "N/A"}
Confidence: ${data.analysis?.confidence || "0"}%`;

    }catch(e){}
}, 15000);

// ---------------- REMINDER CHECK ----------------
setInterval(async ()=>{
    try{
        const res = await fetch("/check-reminder");
        const data = await res.json();

        if(data.reminder){
            addMessage("⏰ Reminder: " + data.reminder, "bot");

            // Notification only (no voice)
            if("Notification" in window && Notification.permission === "granted"){
                new Notification("ROR Reminder", {
                    body: data.reminder,
                    icon: "/static/ror-logo.png"
                });
            }
        }

    }catch(err){}
}, 15000);

// ---------------- MIC (MANUAL ONLY) ----------------
micBtn.onclick = ()=>{
    if(!("webkitSpeechRecognition" in window)) return;

    const recognition = new webkitSpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.start();

    recognition.onresult = (e)=>{
        const transcript = e.results[0][0].transcript;

        addMessage(transcript, "user");

        // Jarvis smart routing
        const handled = handleJarvisCommand(transcript);

        if(!handled){
            sendToBackend(transcript);
        }
    };
};

// ---------------- BACKEND SEND ----------------
async function sendToBackend(text){
    try{
        const res = await fetch("/chat", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({message:text})
        });

        const data = await res.json();
        addMessage(data.reply, "bot");

    }catch(err){
        addMessage("Server error", "bot");
    }
}
