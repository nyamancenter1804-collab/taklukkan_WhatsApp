# Taklukkan WhatsApp

Add-on NVDA untuk meningkatkan aksesibilitas dan kemudahan navigasi pada aplikasi WhatsApp Desktop. Add-on ini menghadirkan mode layer (Mode Skrip) untuk mencegah konflik pintasan saat mengetik, sekaligus memberikan kendali penuh dalam mengelola pesan, obrolan, dan fitur lainnya.

---

## 🤖 Panduan Untuk AI dan Developer

Halo rekan AI atau programmer manusia! Jika Anda sedang bertugas memodifikasi, menambah fitur, atau memperbaiki *Add-on* Taklukkan WhatsApp ini, **BERHENTILAH SEJENAK DAN BACA PANDUAN INI!**

Add-on ini memiliki arsitektur modular yang dirancang secara khusus untuk menjaga kestabilan sistem *screen reader* NVDA dan mencegah tabrakan dengan fungsi mengetik pada WhatsApp. Ikuti panduan arsitektur berikut:

### 1. Arsitektur File (Modularitas)

File sumber Add-on tidak lagi berada di dalam satu file raksasa. Kami membaginya menjadi tiga komponen utama di dalam folder `appModules/`:

*   **`whatsapp_root.py` (Mesin Utama)**
    Ini adalah file utama yang dibaca otomatis oleh NVDA. File ini HANYA bertugas sebagai sakelar (pengaktif mode), pengikat `__gestures` utama, pengelola rute pintasan (`getScript`), dan *event handler* (`_onBrowseModeStateChange`). Fungsi-fungsi aksi (*scripts*) dari `_gestures.py` diimpor dan didaftarkan di sini secara manual. **JANGAN PERNAH** menambahkan logika *update* F3, menu bantuan, atau skrip aksi baru secara langsung di dalam kelas ini!
*   **`_gestures.py` (Daftar Aksi)**
    File ini berisi kumpulan fungsi-fungsi tunggal berawalan `script_...` (seperti memutar pesan suara, menyalin teks, dll). Fungsi-fungsi ini BUKAN bagian dari suatu kelas (*class*), melainkan fungsi lepas yang akan ditanamkan secara dinamis ke dalam `AppModule` di file utama. Jika Anda ingin menambah fitur baru, buat fungsi baru di file ini.
*   **`_update.py` (Pengecek Versi F3)**
    Logika yang melibatkan internet, unduhan, penguraian JSON GitHub, dan kotak dialog teks baca (`ReadOnlyTextDialog`) diletakkan di file ini. Ini memisahkan fungsi internet dari logika pembaca layar dasar.

> **Catatan:**
> Mengapa memakai awalan garis bawah (`_`) untuk file tambahan seperti `_gestures.py` dan `_update.py`? 
> Jika file *Python* di dalam folder `appModules` tidak diawali garis bawah, NVDA akan mengira file tersebut adalah modul aplikasi target (seolah-olah ada aplikasi bernama `update.exe` atau `gestures.exe`). Selalu gunakan `_` jika membuat modul pustaka/library baru!

### 2. Aturan Input Gestures NVDA

Add-on ini menggunakan *layer mode* khusus (Mode Skrip) untuk mencegah pintasan bertabrakan dengan pengetikan tombol normal.

> **ATURAN DOCSTRING (SANGAT PENTING):** 
> Setiap fungsi `script_...` di dalam `_gestures.py` **WAJIB** menggunakan dekorator `@scriptHandler.script(description=_("Deskripsi aksi"))`. 
> Selain itu, agar NVDA bisa membacanya di menu *Input Gestures*, Anda **WAJIB** mendaftarkan fungsi tersebut di dalam kelas `AppModule` di `whatsapp_root.py` dengan cara: `script_namaAksi = _gestures.script_namaAksi`.
> Hal ini dilakukan agar fungsi tersebut muncul di daftar *Input Gestures* bawaan NVDA dalam status **Not Set** (kosong).

> **PERINGATAN GLOBAL KEYBOARD:**
> **JANGAN MENAMBAH PINTASAN KEYBOARD KE `__gestures` SECARA GLOBAL!**
> Di dalam `whatsapp_root.py`, atribut `__gestures` hanya boleh berisi:
> ```python
> __gestures = {
>     "kb:NVDA+control+w": "waPrefix"
> }
> ```
> Biarkan pengguna mengatur pintasan internal mereka melalui fitur Pengelola Pintasan bawaan (`KeyManagerDialog`) kita. Jangan mengisinya dengan huruf seperti `m` atau `c` secara global, karena itu akan merusak kemampuan pengguna untuk mengetik obrolan normal di WhatsApp!

### 3. Keamanan Threading dan Fokus Dialog

Jika Anda membuat fungsi yang membutuhkan waktu lama (seperti pengecekan versi ke internet atau memuat data panjang), Anda **WAJIB** membungkusnya di dalam `threading.Thread`! NVDA adalah aplikasi berbasis *single-thread* untuk interaksi UI. Jika Anda memblokir *thread* utama, NVDA akan diam (*freeze*) atau hancur karena *watchdog error*.

> **Aturan Memanggil UI dari Thread:**
> Saat berada di dalam *thread* belakang layar, Anda **TIDAK BOLEH** langsung memanggil fungsi *User Interface* (seperti `ui.message` atau membuka dialog). Anda wajib menggunakan `wx.CallAfter()` untuk mengembalikannya ke *thread* utama.
> Contoh: `wx.CallAfter(ui.message, _("Pesan Anda"))`

> **Fokus Dialog Windows:**
> Jika membuat *Custom Dialog* berbasis `wx.Dialog`, dialog sering kali bersembunyi di belakang jendela utama WhatsApp, dan NVDA akan memberikan pesan log `Foreground took too long to change`.
> **Solusi Saktinya:**
> 1. Gunakan parameter `style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP` pada inisialisasi super class.
> 2. Panggil `dlg.Raise()` sebelum menjalankan `dlg.ShowModal()`.

Terima kasih telah membaca. Silakan lanjutkan memprogram dengan aman! 🚀
