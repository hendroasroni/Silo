// ==========================================
// AI SILO BRIDGE - GOOGLE FLOW CONTENT SCRIPT
// ==========================================

const BRIDGE_API_BASE = "http://localhost:7860";
let currentTask = null;
let queueStats = { total: 0, completed: 0, pending: 0, skipped: 0, current_index: 0 };
let isConnected = false;
let autoFillEnabled = true;
let pollInterval = null;

// ==========================================
// 1. DOCK UI INJECTION
// ==========================================
function injectDock() {
  if (document.getElementById("silo-bridge-dock")) return;

  const dock = document.createElement("div");
  dock.id = "silo-bridge-dock";
  dock.innerHTML = `
    <div class="silo-dock-header" id="silo-dock-header">
      <div class="silo-dock-title">
        <span class="silo-status-dot" id="silo-status-dot"></span>
        <span>AI Silo Bridge</span>
      </div>
      <div class="silo-dock-controls">
        <button class="silo-btn-icon" id="silo-btn-refresh" title="Refresh Task">🔄</button>
        <button class="silo-btn-icon" id="silo-btn-minimize" title="Minimize">➖</button>
      </div>
    </div>
    <div class="silo-dock-body" id="silo-dock-body">
      <!-- Task Content will be rendered dynamically -->
      <div id="silo-task-container">
        <div class="silo-offline-box">
          Menghubungkan ke Silo CLI (<code>localhost:7860</code>)...<br>
          Pastikan Anda sudah memilih menu <b>Google Flow Bridge</b> di CLI.
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(dock);

  // Event Listeners for Header Controls
  document.getElementById("silo-btn-minimize").addEventListener("click", (e) => {
    e.stopPropagation();
    dock.classList.toggle("minimized");
  });

  document.getElementById("silo-dock-header").addEventListener("click", () => {
    if (dock.classList.contains("minimized")) {
      dock.classList.remove("minimized");
    }
  });

  document.getElementById("silo-btn-refresh").addEventListener("click", (e) => {
    e.stopPropagation();
    fetchCurrentTask();
  });
}

// ==========================================
// 2. RENDER DOCK CONTENT
// ==========================================
function renderTaskUI() {
  const container = document.getElementById("silo-task-container");
  if (!container) return;

  const dot = document.getElementById("silo-status-dot");
  if (dot) {
    dot.className = isConnected ? "silo-status-dot online" : "silo-status-dot";
  }

  if (!isConnected) {
    container.innerHTML = `
      <div class="silo-offline-box">
        ⚠️ <b>Silo CLI Belum Terhubung</b><br>
        Jalankan menu Google Flow di Silo CLI (<code>localhost:7860</code>).
      </div>
      <button class="silo-btn silo-btn-secondary" id="silo-btn-retry" style="width: 100%;">
        🔄 Coba Hubungkan Ulang
      </button>
    `;
    const retryBtn = document.getElementById("silo-btn-retry");
    if (retryBtn) retryBtn.addEventListener("click", fetchCurrentTask);
    return;
  }

  if (!currentTask) {
    container.innerHTML = `
      <div style="text-align: center; padding: 12px 6px;">
        <div style="font-size: 24px; margin-bottom: 6px;">🎉</div>
        <div style="font-weight: 700; color: #38bdf8; margin-bottom: 4px;">Semua Task Selesai!</div>
        <div style="font-size: 11px; color: #94a3b8;">
          Total ${queueStats.completed} gambar berhasil dibuat & disimpan ke artikel Silo.
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="silo-task-meta">
      <div class="silo-meta-row">
        <span class="silo-meta-label">Progress:</span>
        <span class="silo-meta-val badge">#${queueStats.current_index} dari ${queueStats.total} Artikel</span>
      </div>
      <div class="silo-meta-row">
        <span class="silo-meta-label">Keyword:</span>
        <span class="silo-meta-val" title="${currentTask.keyword}">${currentTask.keyword}</span>
      </div>
      <div class="silo-meta-row">
        <span class="silo-meta-label">Artikel:</span>
        <span class="silo-meta-val" title="${currentTask.title}">${currentTask.title}</span>
      </div>
    </div>

    <div class="silo-prompt-container">
      <div class="silo-prompt-header">
        <span>Prompt Imagen / Flow:</span>
        <span style="font-size: 10px; color: #38bdf8;">Siap di-generate</span>
      </div>
      <div class="silo-prompt-box" id="silo-prompt-text">${escapeHtml(currentTask.prompt)}</div>
    </div>

    <div class="silo-actions-row">
      <button class="silo-btn silo-btn-primary" id="silo-btn-autofill">
        ⚡ Auto-Fill & Paste
      </button>
      <button class="silo-btn silo-btn-secondary" id="silo-btn-copy">
        📋 Copy Prompt
      </button>
    </div>

    <div class="silo-nav-row">
      <button class="silo-btn silo-btn-outline" id="silo-btn-prev">
        ⏮️ Prev
      </button>
      <span style="font-size: 11px; color: #64748b;">
        Selesai: <b>${queueStats.completed}</b> | Sisa: <b>${queueStats.pending}</b>
      </span>
      <button class="silo-btn silo-btn-outline" id="silo-btn-skip">
        ⏭️ Skip
      </button>
    </div>
  `;

  // Attach Action Listeners
  document.getElementById("silo-btn-autofill").addEventListener("click", () => {
    autoFillPrompt(currentTask.prompt);
  });

  document.getElementById("silo-btn-copy").addEventListener("click", () => {
    navigator.clipboard.writeText(currentTask.prompt).then(() => {
      showToast("📋 Prompt berhasil disalin ke clipboard!");
    });
  });

  document.getElementById("silo-btn-skip").addEventListener("click", () => {
    skipCurrentTask();
  });

  document.getElementById("silo-btn-prev").addEventListener("click", () => {
    prevTask();
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ==========================================
// 3. API CLIENT (COMMUNICATION WITH PYTHON CLI)
// ==========================================
async function fetchCurrentTask() {
  try {
    const res = await fetch(`${BRIDGE_API_BASE}/api/current`, { method: "GET" });
    if (res.ok) {
      const data = await res.json();
      isConnected = true;
      currentTask = data.task;
      queueStats = data.stats || queueStats;
      renderTaskUI();
    } else {
      isConnected = false;
      renderTaskUI();
    }
  } catch (err) {
    isConnected = false;
    renderTaskUI();
  }
}

async function skipCurrentTask() {
  try {
    const res = await fetch(`${BRIDGE_API_BASE}/api/skip`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      currentTask = data.current_task;
      queueStats = data.stats || queueStats;
      showToast("⏭️ Task artikel dilewati.");
      renderTaskUI();
    }
  } catch (err) {
    showToast("⚠️ Gagal melewati task.", true);
  }
}

async function prevTask() {
  try {
    const res = await fetch(`${BRIDGE_API_BASE}/api/prev`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      currentTask = data.current_task;
      queueStats = data.stats || queueStats;
      renderTaskUI();
    }
  } catch (err) {
    showToast("⚠️ Gagal ke task sebelumnya.", true);
  }
}

async function uploadSelectedImage(imageBlobOrUrl, btnElement) {
  if (!currentTask) {
    showToast("⚠️ Tidak ada task artikel yang sedang aktif.", true);
    return;
  }

  if (btnElement) {
    btnElement.classList.add("uploading");
    btnElement.innerHTML = "⏳ Mengirim...";
  }

  try {
    let base64Data = "";

    if (typeof imageBlobOrUrl === "string") {
      // It's a URL
      const response = await fetch(imageBlobOrUrl);
      const blob = await response.blob();
      base64Data = await blobToBase64(blob);
    } else if (imageBlobOrUrl instanceof Blob) {
      base64Data = await blobToBase64(imageBlobOrUrl);
    }

    if (!base64Data) {
      throw new Error("Gagal mengekstrak data gambar.");
    }

    const payload = {
      task_id: currentTask.task_id,
      image_base64: base64Data
    };

    const res = await fetch(`${BRIDGE_API_BASE}/api/upload`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      if (btnElement) {
        btnElement.classList.remove("uploading");
        btnElement.classList.add("success");
        btnElement.innerHTML = "✓ Terkirim!";
      }

      showToast(`✓ Gambar tersimpan untuk "${currentTask.keyword}"!`);
      
      // Auto-load next task
      currentTask = data.next_task;
      queueStats = data.stats || queueStats;
      renderTaskUI();

      // Optional auto-fill next prompt
      if (currentTask && autoFillEnabled) {
        setTimeout(() => {
          autoFillPrompt(currentTask.prompt);
        }, 800);
      }
    } else {
      const errData = await res.json();
      throw new Error(errData.error || "Gagal upload.");
    }
  } catch (err) {
    if (btnElement) {
      btnElement.classList.remove("uploading");
      btnElement.innerHTML = "📸 Kirim ke Silo";
    }
    showToast(`⚠️ Error: ${err.message}`, true);
  }
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// ==========================================
// 4. AUTO-FILL PROMPT TO FLOW INPUT
// ==========================================
function autoFillPrompt(promptText) {
  if (!promptText) return;

  // Search possible textarea / input / contenteditable on flow.google.com / labs.google
  const selectors = [
    'textarea[placeholder*="prompt" i]',
    'textarea[placeholder*="describe" i]',
    'textarea[aria-label*="prompt" i]',
    'textarea',
    'div[contenteditable="true"]',
    'input[type="text"][placeholder*="prompt" i]'
  ];

  let targetInput = null;
  for (const sel of selectors) {
    const els = document.querySelectorAll(sel);
    for (const el of els) {
      // Pastikan bukan elemen di dalam floating dock kita
      if (!el.closest("#silo-bridge-dock") && el.offsetParent !== null) {
        targetInput = el;
        break;
      }
    }
    if (targetInput) break;
  }

  if (targetInput) {
    if (targetInput.tagName === "TEXTAREA" || targetInput.tagName === "INPUT") {
      targetInput.value = promptText;
      targetInput.dispatchEvent(new Event("input", { bubbles: true }));
      targetInput.dispatchEvent(new Event("change", { bubbles: true }));
      targetInput.focus();
    } else if (targetInput.isContentEditable) {
      targetInput.innerText = promptText;
      targetInput.dispatchEvent(new Event("input", { bubbles: true }));
      targetInput.focus();
    }
    showToast("⚡ Prompt berhasil di-paste ke kolom Flow!");
  } else {
    // Fallback copy to clipboard
    navigator.clipboard.writeText(promptText);
    showToast("📋 Kolom input tidak ditemukan. Prompt telah disalin ke clipboard!");
  }
}

// ==========================================
// 5. DOM OBSERVER: INJECT 1-CLICK SELECTOR ON IMAGES
// ==========================================
function setupImageObserver() {
  const observer = new MutationObserver(() => {
    attachButtonsToImages();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  // Initial check
  attachButtonsToImages();
}

function attachButtonsToImages() {
  // Cari semua elemen <img> di halaman
  const images = document.querySelectorAll("img");

  images.forEach((img) => {
    // Abaikan gambar di dalam dock, avatar, logo, atau icon kecil (< 150px)
    if (img.closest("#silo-bridge-dock")) return;
    if (img.width < 120 || img.height < 120) return;
    if (!img.src || img.src.startsWith("data:image/svg")) return;

    // Cari container kartu terdekat
    let container = img.parentElement;
    if (!container) return;

    // Pastikan container memiliki position relative agar button absolute bisa menempel
    if (window.getComputedStyle(container).position === "static") {
      container.style.position = "relative";
    }

    // Jika sudah ada button di container ini, lewati
    if (container.querySelector(".silo-image-selector-btn")) return;

    // Buat tombol selector
    const btn = document.createElement("button");
    btn.className = "silo-image-selector-btn";
    btn.innerHTML = "📸 Kirim ke Silo";
    btn.title = "Klik untuk menyimpan gambar ini sebagai Featured Image artikel aktif di Silo";

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      uploadSelectedImage(img.src, btn);
    });

    container.appendChild(btn);
  });
}

// ==========================================
// 6. TOAST NOTIFICATION HELPER
// ==========================================
function showToast(message, isError = false) {
  const existing = document.querySelector(".silo-toast-notification");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = "silo-toast-notification";
  if (isError) {
    toast.style.background = "rgba(239, 68, 68, 0.95)";
    toast.style.boxShadow = "0 10px 30px rgba(0, 0, 0, 0.4), 0 0 20px rgba(239, 68, 68, 0.35)";
  }
  toast.innerText = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ==========================================
// 7. INITIALIZATION
// ==========================================
function init() {
  injectDock();
  setupImageObserver();
  fetchCurrentTask();

  // Polling status setiap 3 detik jika belum terhubung atau queue berubah
  pollInterval = setInterval(fetchCurrentTask, 3000);
}

// Run after page load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
