import wx
import datetime
import os

import Model
import Utils
import JChip
import OutputStreamer

import wx.lib.masked as masked
from roundbutton import RoundButton

def StartRaceNow():
	with Model.LockRace() as race:
		if race is None:
			return
			
		Model.resetCache()
		race.startRaceNow()
		
	OutputStreamer.writeRaceStart()
	
	# Refresh the main window and switch to the Record pane.
	mainWin = Utils.getMainWin()
	if mainWin is not None:
		mainWin.showPageName( 'Record' )
		mainWin.refresh()

def GetNowSeconds():
	t = datetime.datetime.now()
	return t.hour * 60 * 60 + t.minute * 60 + t.second
		
class StartRaceAtTime( wx.Dialog ):
	def __init__( self, parent, id = wx.ID_ANY ):
		wx.Dialog.__init__( self, parent, id, "Start Race at Time:",
						style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME|wx.TAB_TRAVERSAL )
						
		bs = wx.GridBagSizer(vgap=5, hgap=5)

		font = wx.Font(24, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
		
		self.startSeconds = None
		self.timer = None

		race = Model.getRace()
		autoStartLabel = wx.StaticText( self, wx.ID_ANY, 'Automatically Start Race at:' )
		
		# Make sure we don't suggest a start time in the past.
		value = race.scheduledStart
		startSeconds = Utils.StrToSeconds( value ) * 60
		nowSeconds = GetNowSeconds()
		if startSeconds < nowSeconds:
			startOffset = 3 * 60
			startSeconds = nowSeconds - nowSeconds % startOffset
			startSeconds = nowSeconds + startOffset
			value = '%02d:%02d' % (startSeconds / (60*60), (startSeconds / 60) % 60)
		
		self.autoStartTime = masked.TimeCtrl( self, wx.ID_ANY, fmt24hr=True, display_seconds=False, value=value )
													
		self.countdown = wx.StaticText( self, wx.ID_ANY, '      ' )
		self.countdown.SetFont( font )
													
		self.okBtn = wx.Button( self, wx.ID_ANY, '&OK' )
		self.Bind( wx.EVT_BUTTON, self.onOK, self.okBtn )

		self.cancelBtn = wx.Button( self, wx.ID_ANY, '&Cancel' )
		self.Bind( wx.EVT_BUTTON, self.onCancel, self.cancelBtn )
		
		border = 8
		bs.Add( autoStartLabel, pos=(0,0), span=(1,1),
				border = border, flag=wx.LEFT|wx.TOP|wx.BOTTOM )
		bs.Add( self.autoStartTime, pos=(0,1), span=(1,1),
				border = border, flag=wx.RIGHT|wx.TOP|wx.BOTTOM|wx.ALIGN_BOTTOM )
		bs.Add( self.countdown, pos=(1,0), span=(1,2), border = border, flag=wx.ALL )
		bs.Add( self.okBtn, pos=(2, 0), span=(1,1), border = border, flag=wx.ALL )
		self.okBtn.SetDefault()
		bs.Add( self.cancelBtn, pos=(2, 1), span=(1,1), border = border, flag=wx.ALL )
		
		bs.AddGrowableRow( 1 )
		self.SetSizerAndFit(bs)
		bs.Fit( self )
		
		self.CentreOnParent(wx.BOTH)
		self.SetFocus()

	def updateCountdownClock( self, event = None ):
		if self.startSeconds is None:
			return
	
		nowSeconds = GetNowSeconds()
		
		if nowSeconds < self.startSeconds:
			self.countdown.SetLabel( Utils.SecondsToStr(self.startSeconds - nowSeconds) )
			return
		
		# Stop the timer.
		self.startSeconds = None
		self.timer.Stop()
		
		# Start the race.
		StartRaceNow()
		self.EndModal( wx.ID_OK )
	
	def onOK( self, event ):
		startTime = self.autoStartTime.GetValue()

		self.startSeconds = Utils.StrToSeconds( startTime ) * 60
		if self.startSeconds < GetNowSeconds() and \
			not Utils.MessageOKCancel( None, 'Race start time is in the past.\nStart race now?', 'Start Race Now' ):
			return

		# Setup the countdown clock.
		self.timer = wx.Timer( self, id=wx.NewId() )
		self.Bind( wx.EVT_TIMER, self.updateCountdownClock, self.timer )
		self.timer.Start( 1000 )
		
		# Disable buttons and switch to countdown state.
		self.okBtn.Enable( False )
		self.autoStartTime.Enable( False )
		self.updateCountdownClock()
		
	def onCancel( self, event ):
		self.startSeconds = None
		if self.timer is not None:
			self.timer.Stop()
		self.EndModal( wx.ID_CANCEL )

#-------------------------------------------------------------------------------------------
StartText = 'Start\nRace'
FinishText = 'Finish\nRace'

class Actions( wx.Panel ):
	def __init__( self, parent, id = wx.ID_ANY ):
		wx.Panel.__init__(self, parent, id)
		bs = wx.BoxSizer( wx.VERTICAL )
		
		self.SetBackgroundColour( wx.Colour(255,255,255) )
		
		fontPixels = 60
		font = wx.FontFromPixelSize((0,fontPixels), wx.DEFAULT, wx.NORMAL, weight=wx.FONTWEIGHT_BOLD)

		dc = wx.WindowDC( self )
		dc.SetFont( font )
		tw = max( dc.GetTextExtent('START')[0], dc.GetTextExtent('FINISH')[0] )
		
		buttonSize = int(tw * 1.5)
		self.button = RoundButton( self, wx.ID_ANY, size=(buttonSize, buttonSize) )
		self.button.SetFont( font )
		self.button.SetLabel( 'FINISH' )
		self.button.SetForegroundColour( wx.Colour(128,128,128) )
		self.Bind(wx.EVT_BUTTON, self.onPress, self.button )
		
		self.startRaceTimeCheckBox = wx.CheckBox(self, wx.ID_ANY, 'Start Race at Time')
		
		border = 8
		bs.Add(self.button, border=border, flag=wx.ALL)
		bs.Add(self.startRaceTimeCheckBox, border=border, flag=wx.ALL)
		self.SetSizer(bs)
		
		self.refresh()
	
	def onPress( self, event ):
		if not Model.race:
			return
		with Model.LockRace() as race:
			running = race.isRunning()
		if running:
			self.onFinishRace( event )
		elif self.startRaceTimeCheckBox.IsChecked():
			self.onStartRaceTime( event )
		else:
			self.onStartRace( event )
	
	def onStartRace( self, event ):
		if Model.race is not None and Utils.MessageOKCancel(self, 'Start Race Now?', 'Start Race'):
			StartRaceNow()
	
	def onStartRaceTime( self, event ):
		if Model.race is None:
			return
		dlg = StartRaceAtTime( self )
		dlg.ShowModal()
		dlg.Destroy()  
	
	def onFinishRace( self, event ):
		if Model.race is None or not Utils.MessageOKCancel(self, 'Finish Race Now?', 'Finish Race'):
			return
			
		with Model.LockRace() as race:
			race.finishRaceNow()
			if race.numLaps is None:
				race.numLaps = race.getMaxLap()
			Model.resetCache()
		
		Utils.writeRace()
		self.refresh()
		mainWin = Utils.getMainWin()
		if mainWin:
			mainWin.refresh()
		JChip.StopListener()
		
		OutputStreamer.writeRaceFinish()
		OutputStreamer.StopStreamer()
	
	def refresh( self ):
		self.button.Enable( False )
		self.startRaceTimeCheckBox.Enable( False )
		self.button.SetLabel( StartText )
		self.button.SetForegroundColour( wx.Colour(100,100,100) )
		with Model.LockRace() as race:
			if race is not None:
				if race.startTime is None:
					self.button.Enable( True )
					self.button.SetLabel( StartText )
					self.button.SetForegroundColour( wx.Colour(0,128,0) )
					
					self.startRaceTimeCheckBox.Enable( True )
					self.startRaceTimeCheckBox.Show( True )
				elif race.isRunning():
					self.button.Enable( True )
					self.button.SetLabel( FinishText )
					self.button.SetForegroundColour( wx.Colour(128,0,0) )
					
					self.startRaceTimeCheckBox.Enable( False )
					self.startRaceTimeCheckBox.Show( False )
					
		mainWin = Utils.getMainWin()
		if mainWin is not None:
			mainWin.updateRaceClock()
		
if __name__ == '__main__':
	app = wx.PySimpleApp()
	mainWin = wx.Frame(None,title="CrossMan", size=(1024,600))
	actions = Actions(mainWin)
	Model.newRace()
	actions.refresh()
	mainWin.Show()
	app.MainLoop()