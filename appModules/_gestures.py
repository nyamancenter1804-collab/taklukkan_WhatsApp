# -*- coding: UTF-8 -*-
import api
import ui
import speech
import wx
import re
import gui
import controlTypes
import scriptHandler
from ._update import ReadOnlyTextDialog

def _(msg):
    return msg

def _role(obj):
    try:
        return obj.role
    except:
        return None

@scriptHandler.script(description=_("Bantuan Taklukkan WhatsApp"))
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
		dlg.Raise()
		dlg.ShowModal()
		dlg.Destroy()
	wx.CallAfter(show_help_dialog)

@scriptHandler.script(description=_("Buka Pengelola Pintasan"))
def script_openKeyManager(self, gesture):
	def run():
		from .whatsapp_root import KeyManagerDialog
		dlg = KeyManagerDialog(gui.mainFrame, self)
		dlg.ShowModal()
		dlg.Destroy()
	wx.CallAfter(run)

@scriptHandler.script(description=_("Salin Pesan ke Clipboard"))
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

@scriptHandler.script(description=_("Putar Pesan Suara"))
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

@scriptHandler.script(description=_("Baca Pesan Secara Lengkap (Klik 'Baca Selengkapnya')"))
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

@scriptHandler.script(description=_("Baca Pesan Lengkap dalam Mode Telusur"))
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

@scriptHandler.script(description=_("Buka Menu Konteks Pesan"))
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

@scriptHandler.script(description=_("Beri Reaksi pada Pesan"))
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

@scriptHandler.script(description=_("Fokus ke Kotak Ketik"))
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

@scriptHandler.script(description=_("Pergi ke Daftar Obrolan"))
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

@scriptHandler.script(description=_("Pergi ke Daftar Pesan"))
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

@scriptHandler.script(description=_("Sembunyikan/Tampilkan Nomor Telepon di Daftar Obrolan"))
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

@scriptHandler.script(description=_("Sembunyikan/Tampilkan Nomor Telepon di Daftar Pesan"))
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

@scriptHandler.script(description=_("Tampilkan/Sembunyikan Petunjuk Penggunaan"))
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

@scriptHandler.script(description=_("Matikan/Nyalakan Mode Fokus Otomatis"))
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

@scriptHandler.script(description=_("Cek Pembaruan Add-on via GitHub"))
def script_checkForUpdates(self, gesture):
	from . import _update
	_update.check_for_updates()
