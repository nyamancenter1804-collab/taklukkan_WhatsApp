# 🤖 Panduan AI dan Developer: Taklukkan WhatsApp

Halo rekan AI atau programmer manusia! Jika Anda sedang bertugas memodifikasi, menambah fitur, atau memperbaiki *Add-on* Taklukkan WhatsApp ini, **BERHENTILAH SEJENAK DAN BACA PANDUAN INI!**

Add-on ini memiliki arsitektur modular yang dirancang secara khusus untuk menjaga kestabilan sistem *screen reader* NVDA dan mencegah tabrakan dengan fungsi mengetik pada WhatsApp. Ikuti panduan arsitektur berikut:

## 1. Arsitektur File (Modularitas)

File sumber Add-on tidak lagi berada di dalam satu file raksasa. Kami membaginya menjadi tiga komponen utama di dalam folder `appModules/`:

*   **`whatsapp_root.py` (Mesin Utama)**
    Ini adalah file utama yang dibaca otomatis oleh NVDA. File ini HANYA bertugas sebagai sakelar (pengaktif mode), pengikat `__gestures` utama, pengelola rute pintasan (`getScript`), dan _event handler_ (`_onBrowseModeStateChange`). **JANGAN PERNAH** menambahkan logika F3, menu bantuan, atau skrip aksi baru di sini!
*   **`_gestures.py` (Daftar Aksi)**
    File ini adalah *Mixin Class* (`GesturesMixin`) yang berisi semua fungsi yang berawalan `script_...` (seperti memutar pesan suara, menyalin teks, dll). Jika Anda ingin menambah fitur baru, tambahkan fungsinya di dalam kelas `GesturesMixin` ini.
*   **`_update.py` (Pengecek Versi F3)**
    Logika yang melibatkan internet, unduhan, penguraian JSON GitHub, dan kotak dialog teks baca (`ReadOnlyTextDialog`) diletakkan di file ini. Ini memisahkan fungsi internet dari logika pembaca layar dasar.

> [!TIP]
> Mengapa memakai awalan garis bawah (`_`) untuk file tambahan seperti `_gestures.py` dan `_update.py`? 
> Jika file *Python* di dalam folder `appModules` tidak diawali garis bawah, NVDA akan mengira file tersebut adalah modul aplikasi target (seolah-olah ada aplikasi bernama `update.exe` atau `gestures.exe`). Selalu gunakan `_` jika membuat modul pustaka/library baru!

## 2. Aturan Input Gestures NVDA

Add-on ini menggunakan *layer mode* khusus (Mode Skrip) untuk mencegah pintasan bertabrakan dengan pengetikan tombol normal.

> [!IMPORTANT]
> **ATURAN DOCSTRING:** 
> Setiap fungsi `script_...` di dalam `_gestures.py` **WAJIB** menggunakan dekorator `@scriptHandler.script(description=_("Deskripsi aksi"))`. 
> Hal ini dilakukan agar fungsi tersebut muncul di daftar *Input Gestures* bawaan NVDA dalam status **Not Set** (kosong).

> [!WARNING]
> **JANGAN MENAMBAH PINTASAN KEYBOARD KE `__gestures` SECARA GLOBAL!**
> Di dalam `whatsapp_root.py`, atribut `__gestures` hanya boleh berisi:
> ```python
> __gestures = {
>     "kb:NVDA+control+w": "waPrefix"
> }
> ```
> Biarkan pengguna mengatur pintasan internal mereka melalui fitur Pengelola Pintasan bawaan (`KeyManagerDialog`) kita. Jangan mengisinya dengan huruf seperti `m` atau `c` secara global, karena itu akan merusak kemampuan pengguna untuk mengetik obrolan di WhatsApp!

## 3. Keamanan Threading dan Fokus Dialog

Jika Anda membuat fungsi yang membutuhkan waktu lama (seperti `check_for_updates` atau memuat data panjang), Anda **WAJIB** membungkusnya di dalam `threading.Thread`! NVDA adalah aplikasi berbasis *single-thread* untuk interaksi UI. Jika Anda memblokir *thread* utama, NVDA akan diam (*freeze*) atau hancur karena *watchdog error*.

> [!CAUTION]
> **Aturan Memanggil UI dari Thread:**
> Saat berada di dalam *thread* belakang layar, Anda **TIDAK BOLEH** langsung memanggil fungsi *User Interface* (seperti `ui.message` atau membuka dialog). Anda wajib menggunakan `wx.CallAfter()` untuk mengembalikannya ke *thread* utama.
> Contoh: `wx.CallAfter(ui.message, _("Pesan Anda"))`

> [!TIP]
> **Fokus Dialog Windows:**
> Jika membuat *Custom Dialog* berbasis `wx.Dialog`, dialog sering kali bersembunyi di belakang jendela utama WhatsApp, dan NVDA akan memberikan pesan log `Foreground took too long to change`.
> **Solusi Saktinya:**
> 1. Gunakan parameter `style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP` pada inisialisasi super class.
> 2. Panggil `dlg.Raise()` sebelum menjalankan `dlg.ShowModal()`.

Terima kasih telah membaca. Silakan lanjutkan memprogram dengan aman! 🚀
