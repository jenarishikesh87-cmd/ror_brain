function initReminder(){

    setInterval(async ()=>{
        const res=await fetch("/check-reminder");
        const data=await res.json();

        if(data.reminder){
            addMessage("⏰ "+data.reminder,"bot");
        }
    },15000);
}
