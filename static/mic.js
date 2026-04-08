let micBtn;

function initMic(){
    micBtn = document.getElementById("micBtn");

    micBtn.onclick=()=>{
        if(!("webkitSpeechRecognition" in window)) return;

        const r=new webkitSpeechRecognition();
        r.lang="en-IN";

        r.start();

        r.onresult=e=>{
            let t=e.results[0][0].transcript;
            addMessage(t,"user");
            sendToBackend(t);
        };
    };
}

async function sendToBackend(text){
    const res=await fetch("/chat",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({message:text})
    });

    const data=await res.json();
    addMessage(data.reply,"bot");
}
