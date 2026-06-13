# -*- coding: UTF-8 -*-
import appModuleHandler
import api
import ui
import scriptHandler
import controlTypes
import config
import re
import wx
import time
import threading
import json
import os
import treeInterceptorHandler
import speech
import urllib.request
import urllib.error
import tempfile
import gui

# --- TRANSLATOR ---
# Bahasa Indonesia
def _(msg):
	return msg

CONFIG_SECTION = "whatsappPhoneFilter"

SPEC = {
	'filterChatList': 'boolean(default=False)',
	'filterMessageList': 'boolean(default=True)',
	'autoFocusMode': 'boolean(default=True)',
	'filterUsageHints': 'boolean(default=True)',
}

MAYBE_RE = re.compile(r"\bTalvez\b\s*", re.IGNORECASE)
PHONE_RE = re.compile(r"\+\d[()\d\s-]{8,15}(?=[^\d]|$|\s)")
DURATION_RE = re.compile(r"\b\d+:\d{2}\b")
USAGE_HINT_RE = re.compile(
	r"(For more options|Untuk opsi|Para lebih|Para más|Pour plus|Per lebih|Per lebih banyak|"
	r"Per lebih lanjut|Per più|Für weitere|Para mais|Daha fazla|Voor meer|Untuk mengakses|"
	r"Untuk selengkapnya|Untuk bantuan|Untuk mendapatkan|Для получения|Để biết thêm|"
	r"สำหรับตัวเลือก|その他のオプション|更多选项|अधिक विकल्पों|추가 옵션|Avaa pikavalikko painamalla)",
	re.IGNORECASE
)

class ReadOnlyTextDialog(wx.Dialog):
	def __init__(self, parent, title, message, btn1_label="OK", btn2_label=None):
		super().__init__(parent, title=title, size=(500, 400))
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

class AppModule(appModuleHandler.AppModule):
	"""
	App Module for WhatsApp Desktop.
	"""

	scriptCategory = _("Taklukkan WhatsApp")

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)

		if CONFIG_SECTION not in config.conf:
			config.conf[CONFIG_SECTION] = {}
		config.conf.spec[CONFIG_SECTION] = SPEC

		self._config_cache = {
			'filterChatList': False,
			'filterMessageList': True,
			'autoFocusMode': True,
			'filterUsageHints': True,
		}
		self._loadConfigCache()

		self._toggling = False
		self._whatsapp_window = None
		self._conv_list_container = None
		self._conv_list_cell = None
		treeInterceptorHandler.post_browseModeStateChange.register(self._onBrowseModeStateChange)

		# Layer System Variables
		self.layer_active = False
		self.keys_file = os.path.join(os.path.dirname(__file__), "..", "TaklukkanWhatsApp_keys.json")
		self.load_keys()

	def load_keys(self):
		defaults = {"m": "goToMessageList", "c": "goToConversationList", "d": "focusComposer"}
		self.immutable_keys = {"k": "openKeyManager", "f": "toggleAutoFocusMode", "f3": "checkForUpdates"}
		
		self.custom_keys = defaults.copy()
		if os.path.exists(self.keys_file):
			try:
				with open(self.keys_file, "r") as f:
					data = json.load(f)
					loaded = data.get("keys", {})
					for k, v in loaded.items():
						if k not in self.immutable_keys:
							self.custom_keys[k] = v
			except Exception:
				pass

		self.active_keys = self.custom_keys.copy()
		self.active_keys.update(self.immutable_keys)

	def save_keys(self):
		try:
			with open(self.keys_file, "w") as f:
				json.dump({"keys": self.custom_keys}, f)
		except Exception:
			pass

	def _play_tone(self, tone_type="on"):
		try:
			import winsound
			sound_dir = os.path.join(os.path.dirname(__file__), "Sound")
			if tone_type == "on":
				winsound.PlaySound(os.path.join(sound_dir, "start_skrips.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
			elif tone_type == "off":
				winsound.PlaySound(os.path.join(sound_dir, "stop_skrips.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
		except Exception:
			def _beep():
				try:
					import tones
					if tone_type == "on":
						tones.beep(880, 50)
						time.sleep(0.05)
						tones.beep(1100, 50)
					elif tone_type == "off":
						tones.beep(1100, 50)
						time.sleep(0.05)
						tones.beep(880, 50)
				except Exception:
					pass
			threading.Thread(target=_beep, daemon=True).start()

	@scriptHandler.script(
		description=_("Awalan mode pintasan Taklukkan WhatsApp")
	)
	def script_waPrefix(self, gesture):
		self.layer_active = True
		self._play_tone("on")
		ui.message(_("Masuk ke mode Whats App Skrips. Tekan F1 untuk menampilkan bantuan."))

	@scriptHandler.script(
		description=_("Batal mode pintasan Taklukkan WhatsApp")
	)
	def script_cancelPrefix(self, gesture):
		ui.message(_("Dibatalkan"))

	def script_showHelp(self, gesture):
		help_text = _("Panduan Pintasan Taklukkan WhatsApp:\n\n")
		available_actions = {
			"goToMessageList": _("Pergi ke Daftar Pesan"),
			"goToConversationList": _("Pergi ke Daftar Obrolan"),
			"focusComposer": _("Fokus ke Kotak Ketik"),
			"openKeyManager": _("Buka Pengelola Pintasan"),
			"toggleAutoFocusMode": _("Matikan/Nyalakan Mode Fokus Otomatis"),
			"checkForUpdates": _("Cek Pembaruan Add-on via GitHub"),
			"copyMessage": _("Salin Pesan ke Clipboard"),
			"playAudio": _("Putar Pesan Suara"),
			"readCompleteMessage": _("Baca Pesan Secara Lengkap (Klik 'Baca Selengkapnya')"),
			"readCompleteMessageBrowse": _("Baca Pesan Lengkap dalam Mode Telusur"),
			"contextMenu": _("Buka Menu Konteks Pesan"),
			"reactMessage": _("Beri Reaksi pada Pesan"),
			"togglePhoneReadingInChatList": _("Sembunyikan/Tampilkan Nomor Telepon di Daftar Obrolan"),
			"togglePhoneReadingInMessageList": _("Sembunyikan/Tampilkan Nomor Telepon di Daftar Pesan"),
			"toggleUsageHints": _("Tampilkan/Sembunyikan Petunjuk Penggunaan")
		}
		for k, v in self.active_keys.items():
			help_text += f"Tombol '{k}': {available_actions.get(v, v)}\n"
		
		help_text += _("\nTekan Escape atau tekan awalan skrip lagi untuk membatalkan mode.")
		
		def show_help_dialog():
			dlg = ReadOnlyTextDialog(gui.mainFrame, _("Bantuan Taklukkan WhatsApp"), help_text, btn1_label="OK")
			dlg.ShowModal()
			dlg.Destroy()
		wx.CallAfter(show_help_dialog)

	def getScript(self, gesture):
		if getattr(self, "layer_active", False):
			script_name = None
			for identifier in gesture.identifiers:
				key = identifier.replace("kb:", "").lower()
				
				if key == "escape":
					script_name = "script_cancelPrefix"
					break
				if key == "f1":
					script_name = "script_showHelp"
					break
				if key in self.active_keys:
					action = self.active_keys[key]
					script_name = "script_" + action
					break
			
			if script_name:
				target_script = getattr(self, script_name, None)
				if target_script:
					def _layer_wrapper(g):
						self.layer_active = False
						if script_name != "script_cancelPrefix":
							self._play_tone("off")
						target_script(g)
					return _layer_wrapper
			
			self.layer_active = False
			self._play_tone("off")
			
			native_script = super(AppModule, self).getScript(gesture)
			if native_script and getattr(native_script, "__name__", "") == "script_waPrefix":
				def _cancel_toggle(g):
					ui.message(_("Dibatalkan"))
				return _cancel_toggle
			
			def _swallow(g):
				ui.message(_("Dibatalkan"))
			return _swallow
			
		return super(AppModule, self).getScript(gesture)

	def script_openKeyManager(self, gesture):
		def run():
			dlg = KeyManagerDialog(gui.mainFrame, self)
			dlg.ShowModal()
			dlg.Destroy()
		wx.CallAfter(run)

	def script_checkForUpdates(self, gesture):
		def _run():
			try:
				wx.CallAfter(ui.message, _("Memeriksa pembaruan Taklukkan WhatsApp..."))
				url = "https://api.github.com/repos/nyamancenter1804-collab/taklukkan_WhatsApp/releases/latest"
				req = urllib.request.Request(url, headers={'User-Agent': 'NVDA-TaklukkanWhatsApp'})
				with urllib.request.urlopen(req, timeout=10) as response:
					data = json.loads(response.read().decode('utf-8'))
					
				latest_version = data.get("tag_name", "").replace("v", "")
				manifest_path = os.path.join(os.path.dirname(__file__), "..", "manifest.ini")
				current_version = "5.4.2"
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
							res = dlg.ShowModal()
							if res == wx.ID_OK and dlg.result:
								self._download_and_install_update(download_url)
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

	def _download_and_install_update(self, url):
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

	def _loadConfigCache(self):
		try:
			section = config.conf.get(CONFIG_SECTION, {})
			for key in self._config_cache:
				val = section.get(key)
				if val is None: continue
				if isinstance(val, str):
					val = val.lower() == 'true'
				self._config_cache[key] = bool(val)
		except Exception:
			pass

	def _onBrowseModeStateChange(self, **kwargs):
		try:
			if not self._config_cache['autoFocusMode']:
				return
			focus = api.getFocusObject()
			if focus and focus.treeInterceptor:
				app = getattr(focus, "appModule", None)
				if app and hasattr(app, "appName") and app.appName in ("whatsapp", "whatsapp.root", "msedgewebview2", "applicationframehost"):
					focus_process_id = getattr(focus, "processID", None)
					if focus_process_id != self.processID:
						return
					focus.treeInterceptor.passThrough = True
		except:
			pass

	def _getConversationListContainer(self):
		if self._conv_list_container:
			try:
				_ = self._conv_list_container.children
				if _role(self._conv_list_container) == 28:
					return self._conv_list_container
				self._conv_list_container = None
			except Exception:
				self._conv_list_container = None
		return None

	def _setConversationListContainer(self, obj):
		try:
			if obj and _role(obj) == 28:
				self._conv_list_container = obj
				return True
		except Exception:
			pass
		return False

	def _getConversationListCell(self):
		if self._conv_list_cell:
			try:
				_ = self._conv_list_cell.children
				if _role(self._conv_list_cell) == 29:
					return self._conv_list_cell
				self._conv_list_cell = None
			except Exception:
				self._conv_list_cell = None
		return None

	def _setConversationListCell(self, obj):
		try:
			if obj and _role(obj) == 29:
				self._conv_list_cell = obj
				return True
		except Exception:
			pass
		return False

	def _findWhatsAppWindow(self):
		if self._whatsapp_window:
			try:
				_ = self._whatsapp_window.children
				return self._whatsapp_window
			except Exception:
				self._whatsapp_window = None

		try:
			focus = api.getFocusObject()
			ti = getattr(focus, "treeInterceptor", None)
			if not ti or not hasattr(ti, "rootNVDAObject"):
				return None
			root = ti.rootNVDAObject

			def search(obj, depth=0, max_depth=6):
				if depth > max_depth:
					return None
				if _role(obj) == 52:
					return obj
				for child in getattr(obj, "children", []) or []:
					result = search(child, depth + 1, max_depth)
					if result:
						return result
				return None

			found = search(root)
			if found:
				self._whatsapp_window = found
			return found
		except Exception:
			return None

	def _shouldFilterChatList(self):
		return self._config_cache.get('filterChatList', False)

	def _shouldFilterMessageList(self):
		return self._config_cache.get('filterMessageList', True)

	def _shouldAutoFocusMode(self):
		return self._config_cache.get('autoFocusMode', True)

	def _shouldFilterUsageHints(self):
		return self._config_cache.get('filterUsageHints', True)

	def _findButtons(self, obj):
		buttons = []
		if _role(obj) == controlTypes.Role.BUTTON:
			buttons.append(obj)
		for child in getattr(obj, "children", []):
			buttons.extend(self._findButtons(child))
		return buttons

	def _findSlider(self, obj):
		try:
			role = _role(obj)
			if role is None: return None
			if role == controlTypes.Role.SLIDER or role == controlTypes.Role.PROGRESSBAR:
				return obj
			for child in getattr(obj, "children", []):
				result = self._findSlider(child)
				if result: return result
		except Exception: pass
		return None

	def _collectButtonsUntil(self, obj, stop_obj):
		buttons = []
		if obj is stop_obj:
			return buttons, True
		if _role(obj) == controlTypes.Role.BUTTON:
			buttons.append(obj)
		for child in getattr(obj, "children", []):
			child_buttons, found = self._collectButtonsUntil(child, stop_obj)
			buttons.extend(child_buttons)
			if found:
				return buttons, True
		return buttons, False

	def _collectTexts(self, obj, min_length=20):
		texts = []
		try:
			role = _role(obj)
			if role is None: return texts
			if role == controlTypes.Role.STATICTEXT or role == 7:
				name = getattr(obj, "name", "") or ""
				if name:
					clean = name.strip()
					if clean and not clean.startswith("00:") and len(clean) > min_length:
						texts.append(clean)
			value = getattr(obj, "value", "") or ""
			if value:
				clean_v = str(value).strip()
				if len(clean_v) > min_length:
					texts.append(clean_v)
			for child in getattr(obj, "children", []):
				texts.extend(self._collectTexts(child, min_length))
		except Exception: pass
		return texts

	def _findCollapsed(self, obj):
		try:
			role = _role(obj)
			if role is None: return None
			if role == controlTypes.Role.BUTTON:
				states = getattr(obj, "states", set())
				if 512 in states:
					return obj
			for child in getattr(obj, "children", []):
				result = self._findCollapsed(child)
				if result: return result
		except Exception: pass
		return None

	def _findFirstButton(self, obj):
		if _role(obj) == controlTypes.Role.BUTTON:
			return obj
		for child in getattr(obj, "children", []):
			result = self._findFirstButton(child)
			if result: return result
		return None

	def _findFirstCell(self, obj, depth=0, max_depth=3):
		if depth > max_depth: return None
		try:
			if _role(obj) == controlTypes.Role.TABLECELL:
				return obj
			for child in getattr(obj, "children", []):
				result = self._findFirstCell(child, depth + 1, max_depth)
				if result: return result
		except Exception: pass
		return None

	def script_copyMessage(self, gesture):
		if not self._isMessageListFocus():
			gesture.send()
			return
		focus = api.getFocusObject()
		focus_name = getattr(focus, "name", "") or ""
		if not focus_name:
			gesture.send()
			return
		text, error = self._getMessageText(require_expanded=False)
		if text:
			api.copyToClip(text)
			ui.message(_("Pesan disalin"))
			return
		parent = getattr(focus, "parent", None)
		if parent:
			siblings = getattr(parent, "children", []) or []
			all_text_parts = []
			for sibling in siblings:
				all_text_parts.extend(self._collectTexts(sibling, 20))
			existing_text = " ".join(all_text_parts)
			if existing_text.strip():
				api.copyToClip(existing_text)
				ui.message(_("Pesan disalin"))
				return
		ui.message(_("Gagal menyalin pesan"))
		gesture.send()

	def script_playAudio(self, gesture):
		try:
			focus = api.getFocusObject()
			if not self._isMessageListFocus():
				if _role(focus) == controlTypes.Role.BUTTON:
					gesture.send()
					return
				gesture.send()
				return
			parent = getattr(focus, "parent", None)
			if not parent:
				ui.message(_("Pesan suara tidak ditemukan"))
				return
			if self._isVideoMessage(parent):
				self._clickFirstButton(focus)
				return
			siblings = getattr(parent, "children", []) or []
			for sibling in siblings:
				slider_obj = self._findSlider(sibling)
				if slider_obj:
					all_buttons, _found = self._collectButtonsUntil(sibling, slider_obj)
					if all_buttons:
						all_buttons[-1].doAction()
						return
			ui.message(_("Pesan suara tidak ditemukan"))
		except Exception:
			ui.message(_("Pesan suara tidak ditemukan"))

	def _getMessageText(self, require_expanded=True):
		if not self._isMessageListFocus():
			return None, _("Tidak berada di daftar pesan")
		focus = api.getFocusObject()
		focus_name = getattr(focus, "name", "") or ""
		if "…" not in focus_name:
			return None, _("Bukan pesan teks panjang")
		parent = getattr(focus, "parent", None)
		if not parent:
			return None, _("Pesan tidak ditemukan")
		siblings = getattr(parent, "children", []) or []
		all_text_parts = []
		for sibling in siblings:
			all_text_parts.extend(self._collectTexts(sibling, 20))
		existing_text = " ".join(all_text_parts)
		if len(existing_text) > 800:
			return existing_text, None
		if not require_expanded:
			return existing_text, None
		for sibling in siblings:
			collapsed_obj = self._findCollapsed(sibling)
			if collapsed_obj:
				all_buttons, _found = self._collectButtonsUntil(sibling, collapsed_obj)
				focusable_buttons = []
				for btn in all_buttons:
					states = getattr(btn, "states", set())
					if 16777216 in states:
						focusable_buttons.append(btn)
				if len(focusable_buttons) >= 2:
					read_more_btn = focusable_buttons[1]
				elif len(focusable_buttons) == 1:
					read_more_btn = focusable_buttons[0]
				else:
					continue
				read_more_btn.doAction()
				wx.CallLater(100, lambda: None)
				all_text_parts = []
				try:
					updated_siblings = getattr(parent, "children", []) or []
					for sib in updated_siblings:
						all_text_parts.extend(self._collectTexts(sib, 20))
				except Exception: pass
				full_text = "\r\n".join(all_text_parts)
				if full_text and len(full_text) > 300:
					return full_text, None
				else:
					return None, _("Teks tidak ditemukan")
		return None, _("Teks tidak ditemukan")

	def script_readCompleteMessage(self, gesture):
		if not self._isMessageListFocus():
			gesture.send()
			return
		focus = api.getFocusObject()
		focus_name = getattr(focus, "name", "") or ""
		if "…" not in focus_name:
			ui.message(_("Bukan pesan teks"))
			gesture.send()
			return
		parent = getattr(focus, "parent", None)
		if not parent:
			ui.message(_("Pesan tidak ditemukan"))
			return
		siblings = getattr(parent, "children", []) or []
		def findReadMore(obj):
			try:
				children = getattr(obj, "children", []) or []
				found_ellipsis = False
				for child in children:
					role = _role(child)
					name = (getattr(child, "name", "") or "").strip()
					if role == 7 and name == "…":
						found_ellipsis = True
						continue
					if found_ellipsis and role == 9:
						return child
					if name:
						found_ellipsis = False
				for child in children:
					result = findReadMore(child)
					if result: return result
			except Exception: pass
			return None

		read_more_found = None
		for sibling in siblings:
			read_more_found = findReadMore(sibling)
			if read_more_found: break

		if read_more_found:
			read_more_found.doAction()
			message_parent = parent
			def speak_after_click():
				speech.cancelSpeech()
				text_parts = []
				try:
					updated_siblings = getattr(message_parent, "children", []) or []
					for sib in updated_siblings:
						text_parts.extend(self._collectTexts(sib, 10))
				except Exception: pass
				expanded = [t for t in text_parts if "…" not in t]
				full_text = "\r\n".join(expanded)
				if full_text:
					ui.message(full_text)
				else:
					ui.message(_("Teks tidak ditemukan"))
			wx.CallLater(150, speak_after_click)
			return
		all_text_parts = []
		for sibling in siblings:
			all_text_parts.extend(self._collectTexts(sibling, 10))
		expanded_parts = [t for t in all_text_parts if "…" not in t]
		if expanded_parts:
			ui.message("\r\n".join(expanded_parts))
			return
		ui.message(_("Teks tidak ditemukan"))

	def script_readCompleteMessageBrowse(self, gesture):
		if not self._isMessageListFocus():
			gesture.send()
			return
		focus = api.getFocusObject()
		focus_name = getattr(focus, "name", "") or ""
		if not focus_name:
			gesture.send()
			return
		text, error = self._getMessageText(require_expanded=True)
		if not error and text:
			ui.browseableMessage(text)
		else:
			parent = getattr(focus, "parent", None)
			if parent:
				siblings = getattr(parent, "children", []) or []
				all_text_parts = []
				for sibling in siblings:
					all_text_parts.extend(self._collectTexts(sibling, 20))
				existing_text = " ".join(all_text_parts)
				if existing_text.strip():
					ui.browseableMessage(existing_text)
				else:
					text = focus_name.strip()
					text = re.sub(r'\s*secção$', '', text, flags=re.IGNORECASE)
					text = re.sub(r'\s*list\s*item$', '', text, flags=re.IGNORECASE)
					text = re.sub(r'\s*\d+\s*de\s*\d+$', '', text)
					text = re.sub(r'\s*$', '', text)
					if text.strip():
						ui.browseableMessage(text)
					else:
						gesture.send()
			else:
				gesture.send()

	def script_contextMenu(self, gesture):
		try:
			if not self._isMessageListFocus():
				gesture.send()
				return
			focus = api.getFocusObject()
			parent = getattr(focus, "parent", None)
			if not parent:
				ui.message(_("Menu tidak ditemukan"))
				return
			siblings = getattr(parent, "children", [])
			for sibling in siblings:
				buttons = self._findButtons(sibling)
				if not buttons: continue
				for btn in buttons:
					states = getattr(btn, "states", set())
					if 512 in states:
						btn.doAction()
						return
				buttons[-1].doAction()
				return
			ui.message(_("Menu tidak ditemukan"))
		except Exception:
			ui.message(_("Menu tidak ditemukan"))

	def script_reactMessage(self, gesture):
		try:
			if not self._isMessageListFocus():
				gesture.send()
				return
			focus = api.getFocusObject()
			parent = getattr(focus, "parent", None)
			if not parent:
				gesture.send()
				return
			siblings = getattr(parent, "children", [])
			for sibling in siblings:
				all_buttons = self._findButtons(sibling)
				for i, btn in enumerate(all_buttons):
					states = getattr(btn, "states", set())
					if 512 in states:
						if i + 1 < len(all_buttons):
							all_buttons[i + 1].doAction()
							return
			gesture.send()
		except Exception:
			gesture.send()

	def script_focusComposer(self, gesture):
		self._toggling = True
		try:
			wa_window = self._findWhatsAppWindow()
			if not wa_window:
				ui.message(_("Kotak ketik tidak ditemukan"))
				return
			path = [0, 0, 0, 0, 3, 4, 0, 3, 0, 0, 0, 2, 0]
			obj = wa_window
			valid = True
			for i in path:
				children = getattr(obj, "children", []) or []
				if i < len(children):
					obj = children[i]
				else:
					valid = False
					break
			if valid:
				obj.setFocus()
				ui.message(_("Kotak Ketik"))
			else:
				ui.message(_("Kotak ketik tidak ditemukan"))
		except Exception:
			ui.message(_("Kotak ketik tidak ditemukan"))
		finally:
			self._toggling = False

	def event_gainFocus(self, obj, nextHandler):
		if not self._config_cache['autoFocusMode']:
			nextHandler()
			return
		try:
			app = getattr(obj, "appModule", None)
			if app and hasattr(app, "appName") and app.appName in ("whatsapp", "whatsapp.root", "msedgewebview2"):
				if obj.treeInterceptor:
					obj.treeInterceptor.passThrough = True
		except Exception: pass
		nextHandler()

	def event_NVDAObject_init(self, obj):
		if self._toggling: return
		try:
			app = getattr(obj, "appModule", None)
			if not (app and hasattr(app, "appName") and app.appName in ("whatsapp", "whatsapp.root", "msedgewebview2")):
				return
		except Exception: return
		try:
			obj_process_id = getattr(obj, "processID", None)
			if obj_process_id is not None and obj_process_id != self.processID:
				return
		except Exception: pass
		if not obj.name: return

		name = obj.name
		name_len = len(name)
		original_role = _role(obj)

		if self._shouldFilterUsageHints():
			if original_role == 86 and not self._hasTableInAncestors(obj):
				if USAGE_HINT_RE.search(name):
					name = USAGE_HINT_RE.split(name)[0].strip()
					name = re.sub(r"\s{2,}", " ", name).strip()
					obj.name = name
					name_len = len(name)
					obj.role = controlTypes.Role.LISTITEM

		obj_role = _role(obj)
		if obj_role == 86 and self._hasTableInAncestors(obj):
			obj.name = " "
			obj.role = controlTypes.Role.LISTITEM

		if name_len < 12 and not name.startswith('Talvez '): return
		has_plus = '+' in name
		starts_with_maybe = name.startswith('Talvez ')
		if not has_plus and not starts_with_maybe: return
		filter_chat = self._config_cache['filterChatList']
		filter_msg = self._config_cache['filterMessageList']
		if not filter_chat and not filter_msg and not starts_with_maybe: return

		try:
			obj_role = original_role
			if obj_role != 86 and obj_role != 29: return
			filtered = False
			if obj_role == 86:
				has_table_ancestor = self._hasTableInAncestors(obj)
				if has_table_ancestor:
					if filter_chat:
						obj.name = PHONE_RE.sub("", name)
						filtered = True
				else:
					if filter_msg:
						obj.name = PHONE_RE.sub("", name)
						filtered = True
				if starts_with_maybe:
					if filtered:
						obj.name = obj.name[7:] if obj.name.startswith('Talvez ') else obj.name
					else:
						obj.name = name[7:]
					filtered = True
			elif obj_role == 29:
				if filter_chat:
					obj.name = PHONE_RE.sub("", name)
					filtered = True
			if filtered:
				obj.name = re.sub(r"\s{2,}", " ", obj.name).strip()
		except Exception: pass

	def _hasTableInAncestors(self, obj):
		if controlTypes.Role is None: return False
		table_role = getattr(controlTypes.Role, "TABLE", None)
		if table_role is None: return False
		current = obj
		for _ in range(3):
			try:
				current = current.parent
				if current is None: return False
				role = getattr(current, "role", None)
				if role == table_role: return True
			except Exception: break
		return False

	def _isConversationListFocus(self):
		try: focus = api.getFocusObject()
		except Exception: return False
		return self._hasTableInAncestors(focus)

	def _isMessageListFocus(self):
		try: focus = api.getFocusObject()
		except Exception: return False
		foreground = api.getForegroundObject()
		window_title = getattr(foreground, "name", "") or ""
		if "whatsapp" not in window_title.lower(): return False
		focus_role = _role(focus)
		if focus_role == controlTypes.Role.STATICTEXT:
			parent = getattr(focus, "parent", None)
			if parent and _role(parent) == 86:
				return not self._hasTableInAncestors(focus)
			return False
		if focus_role != controlTypes.Role.LISTITEM and focus_role != 86: return False
		return not self._hasTableInAncestors(focus)

	def _isVideoMessage(self, parent):
		try:
			children = getattr(parent, "children", []) or []
			all_buttons = []
			for child in children:
				all_buttons.extend(self._findButtons(child))
			if not all_buttons: return False
			first_button = all_buttons[0]
			name = getattr(first_button, "name", "") or ""
			return bool(DURATION_RE.search(name))
		except Exception: return False

	def _clickFirstButton(self, focus):
		try:
			parent = getattr(focus, "parent", None)
			if not parent: return
			for child in getattr(parent, "children", []):
				button = self._findFirstButton(child)
				if button:
					button.doAction()
					return
		except Exception: pass

	def script_goToConversationList(self, gesture):
		self._toggling = True
		try:
			cached_cell = self._getConversationListCell()
			if cached_cell:
				cached_cell.setFocus()
				ui.message(_("Daftar Obrolan"))
				return
			cached_list = self._getConversationListContainer()
			if cached_list:
				cached_list.setFocus()
				ui.message(_("Daftar Obrolan"))
				return
			wa_window = self._findWhatsAppWindow()
			if not wa_window:
				ui.message(_("Daftar obrolan tidak ditemukan"))
				return
			path = [0, 0, 0, 0, 3, 3, 1, 3, 0, 0, 0]
			obj = wa_window
			valid = True
			for i in path:
				children = getattr(obj, "children", []) or []
				if i < len(children):
					obj = children[i]
				else:
					valid = False
					break
			if valid and _role(obj) == 28:
				self._setConversationListContainer(obj)
				cell = self._findFirstCell(obj)
				if cell:
					self._setConversationListCell(cell)
					cell.setFocus()
				else:
					obj.setFocus()
				ui.message(_("Daftar Obrolan"))
			else:
				ui.message(_("Daftar obrolan tidak ditemukan"))
		except Exception:
			ui.message(_("Daftar obrolan tidak ditemukan"))
		finally:
			self._toggling = False

	def script_goToMessageList(self, gesture):
		self._toggling = True
		try:
			wa_window = self._findWhatsAppWindow()
			if not wa_window:
				ui.message(_("Daftar pesan tidak ditemukan"))
				return
			paths_to_try = [
				[0, 0, 0, 0, 3, 4, 0, 2, 2, 1],
				[0, 0, 0, 0, 3, 4, 0, 2, 1, 1],
				[0, 0, 0, 0, 3, 4, 0, 2, 2, 0],
				[0, 0, 0, 0, 3, 4, 0, 2, 1, 0],
				[0, 0, 0, 0, 3, 5, 0, 2, 2, 1],
				[0, 0, 0, 0, 3, 5, 0, 2, 1, 1],
			]
			best_obj = None
			max_children = -1
			for path_indices in paths_to_try:
				try:
					obj = wa_window
					valid_path = True
					for i in path_indices:
						children = getattr(obj, "children", []) or []
						if i < len(children):
							obj = children[i]
						else:
							valid_path = False
							break
					if not valid_path: continue
					obj_children = getattr(obj, "children", []) or []
					child_count = len(obj_children)
					if child_count > max_children:
						max_children = child_count
						best_obj = obj
				except Exception: continue
			if best_obj:
				best_obj.setFocus()
				ui.message(_("Daftar Pesan"))
			else:
				ui.message(_("Daftar pesan tidak ditemukan"))
		except Exception:
			ui.message(_("Daftar pesan tidak ditemukan"))
		finally:
			self._toggling = False

	def script_togglePhoneReadingInChatList(self, gesture):
		try:
			if not self._isConversationListFocus():
				ui.message(_("Gunakan perintah ini di daftar obrolan"))
				return
			current = self._shouldFilterChatList()
			new_val = not current
			config.conf[CONFIG_SECTION]["filterChatList"] = new_val
			config.conf.save()
			self._config_cache['filterChatList'] = new_val
			if new_val:
				ui.message(_("Daftar obrolan: nomor telepon disembunyikan"))
			else:
				ui.message(_("Daftar obrolan: nomor telepon ditampilkan"))
		except Exception: pass

	def script_togglePhoneReadingInMessageList(self, gesture):
		try:
			if not self._isMessageListFocus():
				ui.message(_("Gunakan perintah ini di daftar pesan"))
				return
			current = self._shouldFilterMessageList()
			new_val = not current
			config.conf[CONFIG_SECTION]["filterMessageList"] = new_val
			config.conf.save()
			self._config_cache['filterMessageList'] = new_val
			if new_val:
				ui.message(_("Daftar pesan: nomor telepon disembunyikan"))
			else:
				ui.message(_("Daftar pesan: nomor telepon ditampilkan"))
		except Exception: pass

	def script_toggleUsageHints(self, gesture):
		current = self._shouldFilterUsageHints()
		new_val = not current
		config.conf[CONFIG_SECTION]["filterUsageHints"] = new_val
		config.conf.save()
		self._config_cache['filterUsageHints'] = new_val
		if new_val:
			ui.message(_("Petunjuk penggunaan: disembunyikan"))
		else:
			ui.message(_("Petunjuk penggunaan: ditampilkan"))

	def script_toggleAutoFocusMode(self, gesture):
		current = self._shouldAutoFocusMode()
		new_val = not current
		config.conf[CONFIG_SECTION]["autoFocusMode"] = new_val
		config.conf.save()
		self._config_cache['autoFocusMode'] = new_val
		if new_val:
			ui.message(_("Mode Fokus Otomatis: nyala"))
		else:
			ui.message(_("Mode Fokus Otomatis: mati"))

def _role(obj):
	try:
		return obj.role
	except Exception:
		return None

class KeyManagerDialog(wx.Dialog):
	def __init__(self, parent, plugin):
		super(KeyManagerDialog, self).__init__(parent, title=_("Pengelola Pintasan Taklukkan WhatsApp"), size=(550, 450))
		self.plugin = plugin
		self.temp_keys = self.plugin.custom_keys.copy()
		
		self.available_actions = {
			"goToMessageList": _("Pergi ke Daftar Pesan"),
			"goToConversationList": _("Pergi ke Daftar Obrolan"),
			"focusComposer": _("Fokus ke Kotak Ketik"),
			"copyMessage": _("Salin Pesan ke Clipboard"),
			"playAudio": _("Putar Pesan Suara"),
			"readCompleteMessage": _("Baca Pesan Secara Lengkap (Klik 'Baca Selengkapnya')"),
			"readCompleteMessageBrowse": _("Baca Pesan Lengkap dalam Mode Telusur"),
			"contextMenu": _("Buka Menu Konteks Pesan"),
			"reactMessage": _("Beri Reaksi pada Pesan"),
			"togglePhoneReadingInChatList": _("Sembunyikan/Tampilkan Nomor Telepon di Daftar Obrolan"),
			"togglePhoneReadingInMessageList": _("Sembunyikan/Tampilkan Nomor Telepon di Daftar Pesan"),
			"toggleUsageHints": _("Tampilkan/Sembunyikan Petunjuk Penggunaan"),
			"toggleAutoFocusMode": _("Matikan/Nyalakan Mode Fokus Otomatis"),
			"openKeyManager": _("Buka Pengelola Pintasan"),
			"checkForUpdates": _("Cek Pembaruan Add-on via GitHub")
		}
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		
		self.listCtrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
		self.listCtrl.InsertColumn(0, _("Tombol"), width=100)
		self.listCtrl.InsertColumn(1, _("Aksi"), width=400)
		sizer.Add(self.listCtrl, 1, wx.ALL | wx.EXPAND, 10)
		
		self.populateList()
		
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.addBtn = wx.Button(self, label=_("&Add Key"))
		self.addBtn.Bind(wx.EVT_BUTTON, self.onAdd)
		btnSizer.Add(self.addBtn, 0, wx.ALL, 5)
		
		self.delBtn = wx.Button(self, label=_("&Delete Key"))
		self.delBtn.Bind(wx.EVT_BUTTON, self.onDelete)
		btnSizer.Add(self.delBtn, 0, wx.ALL, 5)

		self.resBtn = wx.Button(self, label=_("&Restore Defaults"))
		self.resBtn.Bind(wx.EVT_BUTTON, self.onRestore)
		btnSizer.Add(self.resBtn, 0, wx.ALL, 5)
		
		sizer.Add(btnSizer, 0, wx.ALIGN_CENTER)
		
		mainBtnSizer = wx.StdDialogButtonSizer()
		saveBtn = wx.Button(self, wx.ID_OK, label=_("&Simpan"))
		saveBtn.Bind(wx.EVT_BUTTON, self.onSave)
		cancelBtn = wx.Button(self, wx.ID_CANCEL, label=_("Batal"))
		mainBtnSizer.AddButton(saveBtn)
		mainBtnSizer.AddButton(cancelBtn)
		mainBtnSizer.Realize()
		
		sizer.Add(mainBtnSizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
		
		self.SetSizer(sizer)
		self.Center()
	
	def populateList(self):
		self.listCtrl.DeleteAllItems()
		
		# Show custom keys
		for key, action in self.temp_keys.items():
			action_name = self.available_actions.get(action, action)
			idx = self.listCtrl.InsertItem(self.listCtrl.GetItemCount(), key)
			self.listCtrl.SetItem(idx, 1, action_name)

		# Show immutable keys
		for key, action in self.plugin.immutable_keys.items():
			action_name = self.available_actions.get(action, action) + _(" (Mutlak)")
			idx = self.listCtrl.InsertItem(self.listCtrl.GetItemCount(), key)
			self.listCtrl.SetItem(idx, 1, action_name)
			self.listCtrl.SetItemTextColour(idx, wx.Colour(128, 128, 128))

	def onAdd(self, event):
		actions_list = list(self.available_actions.values())
		action_keys = list(self.available_actions.keys())
		
		dlg = wx.SingleChoiceDialog(self, _("Pilih aksi untuk ditambahkan:"), _("Pilih Aksi"), actions_list)
		if dlg.ShowModal() == wx.ID_OK:
			sel = dlg.GetSelection()
			action = action_keys[sel]
			
			key_dlg = wx.TextEntryDialog(self, _("Masukkan satu huruf atau angka (tanpa Control/Alt/Shift):"), _("Input Tombol"))
			if key_dlg.ShowModal() == wx.ID_OK:
				key = key_dlg.GetValue().strip().lower()
				if len(key) != 1 or not key.isalnum():
					wx.MessageBox(_("Hanya boleh satu huruf atau angka!"), _("Error"), wx.OK | wx.ICON_ERROR)
				elif key in self.plugin.immutable_keys:
					wx.MessageBox(_("Tombol ini adalah tombol mutlak bawaan sistem dan tidak bisa diubah."), _("Error"), wx.OK | wx.ICON_ERROR)
				elif key in self.temp_keys:
					wx.MessageBox(_("Maaf, pintasan sudah digunakan. Silahkan masukkan yang lain."), _("Error"), wx.OK | wx.ICON_ERROR)
				else:
					self.temp_keys[key] = action
					self.populateList()
			key_dlg.Destroy()
		dlg.Destroy()

	def onDelete(self, event):
		idx = self.listCtrl.GetFirstSelected()
		if idx != -1:
			key = self.listCtrl.GetItemText(idx, 0)
			if key in self.plugin.immutable_keys:
				wx.MessageBox(_("Tombol ini adalah tombol mutlak bawaan sistem dan tidak bisa dihapus."), _("Error"), wx.OK | wx.ICON_ERROR)
			elif key in self.temp_keys:
				del self.temp_keys[key]
				self.populateList()
		else:
			wx.MessageBox(_("Pilih salah satu pintasan di daftar terlebih dahulu."), _("Info"), wx.OK | wx.ICON_INFORMATION)

	def onRestore(self, event):
		res = wx.MessageBox(_("Apakah Anda yakin ingin mengembalikan semua pintasan ke pengaturan awal?"), _("Konfirmasi"), wx.YES_NO | wx.ICON_QUESTION)
		if res == wx.YES:
			self.temp_keys = {"m": "goToMessageList", "c": "goToConversationList", "d": "focusComposer"}
			self.populateList()

	def onSave(self, event):
		self.plugin.custom_keys = self.temp_keys
		self.plugin.save_keys()
		self.plugin.active_keys = self.plugin.custom_keys.copy()
		self.plugin.active_keys.update(self.plugin.immutable_keys)
		wx.MessageBox(_("Pintasan berhasil disimpan."), _("Sukses"), wx.OK | wx.ICON_INFORMATION)
		self.EndModal(wx.ID_OK)
