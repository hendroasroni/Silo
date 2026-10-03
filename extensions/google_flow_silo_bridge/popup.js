const BRIDGE_URL = "http://localhost:7860";

async function checkStatus() {
  const statusEl = document.getElementById("server-status");
  const queueEl = document.getElementById("queue-count");

  try {
    const res = await fetch(`${BRIDGE_URL}/api/status`);
    if (res.ok) {
      const data = await res.json();
      statusEl.className = "badge-online";
      statusEl.innerText = "🟢 Terhubung (Port 7860)";
      
      const stats = data.stats || {};
      queueEl.innerText = `${stats.completed || 0} / ${stats.total || 0} Selesai (${stats.pending || 0} Tersisa)`;
    } else {
      statusEl.className = "badge-offline";
      statusEl.innerText = "🔴 Offline";
      queueEl.innerText = "-";
    }
  } catch (err) {
    statusEl.className = "badge-offline";
    statusEl.innerText = "🔴 Offline (Silo CLI Belum Jalan)";
    queueEl.innerText = "-";
  }
}

document.getElementById("btn-open-flow").addEventListener("click", () => {
  chrome.tabs.create({ url: "https://flow.google.com/" });
});

document.addEventListener("DOMContentLoaded", checkStatus);
