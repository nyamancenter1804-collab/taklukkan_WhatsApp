# -*- coding: UTF-8 -*-
# installTasks - shown on add-on installation

import gui, os, wx, addonHandler

addonHandler.initTranslation()

DONATE_METHODS = (
	{
		'label': 'Donasi dengan GoPay',
		'action': 'gopay'
	},
)

class DonationDialog(gui.nvdaControls.MessageDialog):
	def __init__(self, parent, title, message, donateOptions):
		self.donateOptions = donateOptions
		super().__init__(parent, title, message, dialogType=gui.nvdaControls.MessageDialog.DIALOG_TYPE_WARNING)

	def _addButtons(self, buttonHelper):
		for k in self.donateOptions:
			btn = buttonHelper.addButton(self, label=k['label'], name=k['action'])
			btn.Bind(wx.EVT_BUTTON, self.onDonate)
		cancelBtn = buttonHelper.addButton(self, id=wx.ID_CANCEL, label="&Nanti saja")
		cancelBtn.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.CANCEL))

	def onDonate(self, evt):
		actionBtn = evt.GetEventObject()
		actionName = actionBtn.Name
		if actionName == 'gopay':
			gui.messageBox(
				"Silakan transfer donasi GoPay Anda ke nomor HP berikut:\n\n089513491447\n\nTerima kasih banyak atas dukungan Anda!",
				"Informasi Donasi GoPay",
				wx.OK | wx.ICON_INFORMATION
			)
		self.EndModal(wx.OK)

def showDonationsDialog(parentWindow, addonName, donateOptions):
	title = "Permintaan kontribusi untuk %s" % addonName
	message = """Mengembangkan add-on membutuhkan banyak waktu dan usaha.
Kontribusi Anda membantu memelihara proyek ini dan proyek gratis lainnya.
Apakah Anda ingin berkontribusi? Silakan gunakan metode pembayaran di bawah ini.
Terima kasih atas dukungan Anda!"""
	return DonationDialog(parentWindow, title, message, donateOptions).ShowModal()

def onInstall():
	gui.mainFrame.prePopup()
	wx.CallAfter(showDonationsDialog, gui.mainFrame, "Taklukkan WhatsApp", DONATE_METHODS)
	gui.mainFrame.postPopup()

