let chat, input;

function initChat(){
    chat = document.getElementById("chat");
    input = document.getElementById("input");

    input.addEventListener("keypress", e=>{
        if(e.key==="Enter") sendMessage();
    });
}

function addMessage(text,type){
    const bubble=document.createElement("div");
    bubble.className="bubble "+type;
    bubble.innerText=text;

    chat.appendChild(bubble);

    const meta=document.createElement("div");
    meta.className="meta";
    meta.innerText=new Date().toLocaleTimeString();

    chat.appendChild(meta);

    chat.scrollTop=chat.scrollHeight;
    document.getElementById("logo").style.opacity=0;
}

async function sendMessage(){
    const msg=input.value.trim();
    if(!msg) return;

    addMessage(msg,"user");
    input.value="";

    const res=await fetch("/chat",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({message:msg})
    });

    const data=await res.json();
    addMessage(data.reply,"bot");
}
