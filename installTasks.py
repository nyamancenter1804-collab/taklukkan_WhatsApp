# -*- coding: UTF-8 -*-
# installTasks - shown on add-on installation

import gui, os, wx, addonHandler

addonHandler.initTranslation()

DONATE_METHODS = (
	{
		'label': _('Donate via PayPal'),
		'url': 'https://www.paypal.me/renovamusic12'
	},
)


class DonationDialog(gui.nvdaControls.MessageDialog):
	def __init__(self, parent, title, message, donateOptions):
		self.donateOptions = donateOptions
		super().__init__(parent, title, message, dialogType=gui.nvdaControls.MessageDialog.DIALOG_TYPE_WARNING)

	def _addButtons(self, buttonHelper):
		for k in self.donateOptions:
			btn = buttonHelper.addButton(self, label=k['label'], name=k['url'])
			btn.Bind(wx.EVT_BUTTON, self.onDonate)
		cancelBtn = buttonHelper.addButton(self, id=wx.ID_CANCEL, label=_("&Not now"))
		cancelBtn.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.CANCEL))

	def onDonate(self, evt):
		donateBtn = evt.GetEventObject()
		donateUrl = donateBtn.Name
		os.startfile(donateUrl)
		self.EndModal(wx.OK)


def showDonationsDialog(parentWindow, addonName, donateOptions):
	title = _("Request for contributions to %s") % addonName
	message = _("""Developing add-ons requires a lot of time and effort.
Your contribution helps maintain this and other free projects.
Would you like to contribute? Select a payment method below.
Thank you for your support!""")
	return DonationDialog(parentWindow, title, message, donateOptions).ShowModal()


def onInstall():
	gui.mainFrame.prePopup()
	wx.CallAfter(showDonationsDialog, gui.mainFrame, "WhatsApp NG", DONATE_METHODS)
	gui.mainFrame.postPopup()
