let tradeBtn, tradeResult;

function initTrade(){
    tradeBtn = document.getElementById("trade-btn");
    tradeResult = document.getElementById("trade-result");

    tradeBtn.addEventListener("click", getTrade);

    // AUTO REFRESH
    setInterval(getTrade,15000);
}

async function getTrade(){
    tradeResult.innerText="Checking market...";

    const res=await fetch("/ror-trade");
    const data=await res.json();

    tradeResult.innerText=
`Price: $${data.price}
Decision: ${data.analysis?.decision}
Confidence: ${data.analysis?.confidence}%
Reason: ${data.analysis?.reason}`;
}
