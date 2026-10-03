# Google Flow to AI Silo Bridge (Chrome Extension)

Chrome Extension pembantu untuk menghubungkan antrean artikel di **AI Silo Builder** dengan **flow.google.com** (Google Imagen 3).

---

## 🚀 Cara Pasang Ekstensi di Google Chrome (1 Menit):

1. Buka browser **Google Chrome**.
2. Ketik `chrome://extensions` di address bar dan tekan Enter.
3. Aktifkan sakelar **Developer mode** (Mode Pengembang) di pojok kanan atas.
4. Klik tombol **Load unpacked** (Muat yang belum dibongkar) di pojok kiri atas.
5. Pilih folder:
   ```
   C:\Users\Hendro\Silo\extensions\google_flow_silo_bridge
   ```
6. Ekstensi **"Google Flow to AI Silo Bridge"** berhasil terpasang! 🎉

---

## 🎯 Cara Penggunaan:

1. Di **Silo CLI**, buka menu **Generate Thumbnail via Google Flow (Extension Bridge)**.
2. Silo CLI akan otomatis menyalakan server lokal di `http://localhost:7860` dan membuka `flow.google.com`.
3. Di halaman **flow.google.com**:
   - Widget mini **AI Silo Bridge** akan muncul di pojok kanan bawah.
   - Klik tombol **`[⚡ Auto-Fill & Paste]`** untuk memasukkan prompt artikel aktif.
   - Klik **Generate** di Google Flow.
   - Pada hasil 2-4 variasi gambar yang muncul, klik tombol **`[📸 Kirim ke Silo]`** pada variasi gambar favorit Anda!
4. Gambar akan langsung otomatis tersimpan dalam format `.webp` di folder artikel Silo dan frontmatter artikel terupdate!
