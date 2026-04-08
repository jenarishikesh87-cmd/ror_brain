// ================= TRADE MODULE =================

let currentAsset = "bitcoin"; // default

function initTrade(){

    const tradeBtn = document.getElementById("trade-btn");
    const tradeResult = document.getElementById("trade-result");

    // Asset buttons (optional if you add UI later)
    window.setAsset = function(asset){
        currentAsset = asset;
        getTrade();
    }

    tradeBtn.addEventListener("click", getTrade);

    // Auto refresh
    setInterval(getTrade, 15000);

    async function getTrade(){
        tradeResult.innerHTML = "Loading...";

        try{
            const res = await fetch(`/ror-trade/${currentAsset}`);
            const data = await res.json();

            const a = data.analysis;

            tradeResult.innerHTML = `
<div class="card">

<div class="row">
  <span>Session</span>
  <b>${a.session}</b>
</div>

<div class="price">$${data.price}</div>

<div class="decision ${a.decision}">
  ${a.decision}
</div>

<div class="confidence">
  Confidence: ${a.confidence}%
</div>

<div class="levels">
  <div>Entry: ${a.entry}</div>
  <div>TP: ${a.tp}</div>
  <div>SL: ${a.sl}</div>
</div>

<div class="signals">
  ${a.signals.join(" • ")}
</div>

<div class="reason">
  ${a.reason}
</div>

</div>
            `;

        }catch(e){
            tradeResult.innerHTML = "Error loading market";
        }
    }
}
