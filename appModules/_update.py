# -*- coding: UTF-8 -*-
import wx
import urllib.request
import urllib.error
import tempfile
import json
import os
import threading
import ui
import gui

def _(msg):
	return msg

class ReadOnlyTextDialog(wx.Dialog):
	def __init__(self, parent, title, message, btn1_label="OK", btn2_label=None):
		super().__init__(parent, title=title, size=(500, 400), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		
		self.textCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
		self.textCtrl.SetValue(message)
		mainSizer.Add(self.textCtrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
		
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.btn1 = wx.Button(self, label=btn1_label)
		self.btn1.Bind(wx.EVT_BUTTON, self.onBtn1)
		btnSizer.Add(self.btn1, flag=wx.ALL, border=5)
		
		if btn2_label:
			self.btn2 = wx.Button(self, label=btn2_label)
			self.btn2.Bind(wx.EVT_BUTTON, self.onBtn2)
			btnSizer.Add(self.btn2, flag=wx.ALL, border=5)
			
		mainSizer.Add(btnSizer, flag=wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, border=10)
		self.SetSizer(mainSizer)
		self.result = False
		self.textCtrl.SetFocus()

	def onBtn1(self, evt):
		self.result = True
		self.EndModal(wx.ID_OK)

	def onBtn2(self, evt):
		self.result = False
		self.EndModal(wx.ID_CANCEL)

def _download_and_install_update(url):
	def _run():
		try:
			wx.CallAfter(ui.message, _("Mengunduh pembaruan, mohon tunggu..."))
			temp_dir = tempfile.gettempdir()
			addon_path = os.path.join(temp_dir, "TaklukkanWhatsApp_update.nvda-addon")
			
			req = urllib.request.Request(url, headers={'User-Agent': 'NVDA-TaklukkanWhatsApp'})
			with urllib.request.urlopen(req, timeout=30) as response, open(addon_path, 'wb') as out_file:
				out_file.write(response.read())
			
			wx.CallAfter(ui.message, _("Unduhan selesai. Membuka penginstal NVDA..."))
			os.startfile(addon_path)
		except Exception as e:
			wx.CallAfter(ui.message, _("Gagal mengunduh pembaruan."))
	threading.Thread(target=_run, daemon=True).start()

def check_for_updates():
	def _run():
		try:
			wx.CallAfter(ui.message, _("Memeriksa pembaruan Taklukkan WhatsApp..."))
			url = "https://api.github.com/repos/nyamancenter1804-collab/taklukkan_WhatsApp/releases/latest"
			req = urllib.request.Request(url, headers={'User-Agent': 'NVDA-TaklukkanWhatsApp'})
			with urllib.request.urlopen(req, timeout=10) as response:
				data = json.loads(response.read().decode('utf-8'))
				
			latest_version = data.get("tag_name", "").replace("v", "")
			manifest_path = os.path.join(os.path.dirname(__file__), "..", "manifest.ini")
			current_version = "5.4.7"
			try:
				with open(manifest_path, "r", encoding="utf-8") as f:
					for line in f:
						if line.startswith("version = "):
							current_version = line.split("=")[1].strip()
							break
			except Exception: pass
			
			if latest_version and latest_version != current_version:
				download_url = ""
				for asset in data.get("assets", []):
					if asset.get("name", "").endswith(".nvda-addon"):
						download_url = asset.get("browser_download_url")
						break
				
				if download_url:
					release_notes = data.get("body", "")
					message = _("Versi terbaru Taklukkan WhatsApp ({}) tersedia!\nVersi Anda: {}\n\nCatatan Rilis:\n{}\n\nApakah Anda ingin mengunduh dan menginstalnya sekarang?").format(latest_version, current_version, release_notes)
					def show_prompt():
						dlg = ReadOnlyTextDialog(gui.mainFrame, _("Pembaruan Tersedia"), message, btn1_label="Update", btn2_label="Batal")
						dlg.Raise()
						res = dlg.ShowModal()
						if res == wx.ID_OK and dlg.result:
							_download_and_install_update(download_url)
						dlg.Destroy()
					wx.CallAfter(show_prompt)
				else:
					wx.CallAfter(ui.message, _("Pembaruan ditemukan, tetapi file add-on tidak tersedia di rilis GitHub."))
			else:
				wx.CallAfter(ui.message, _("Taklukkan WhatsApp sudah dalam versi terbaru."))
		except urllib.error.HTTPError as e:
			if e.code == 403:
				wx.CallAfter(ui.message, _("Pengecekan gagal karena limit GitHub tercapai. Silakan coba lagi nanti."))
			else:
				wx.CallAfter(ui.message, _("Gagal memeriksa pembaruan. Pastikan Anda terhubung ke internet."))
		except Exception as e:
			wx.CallAfter(ui.message, _("Gagal memeriksa pembaruan. Pastikan Anda terhubung ke internet."))
	threading.Thread(target=_run, daemon=True).start()
