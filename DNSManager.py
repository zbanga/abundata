import Model
import Utils
import wx
import wx.grid		as gridlib
import re
import os
import sys
import itertools
from string import Template
import ColGrid
from FixCategories import FixCategories, SetCategory
import  wx.lib.mixins.listctrl  as  listmix
from Undo import undo

class AutoWidthListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
	def __init__(self, parent, ID, pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=0):
		wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
		listmix.ListCtrlAutoWidthMixin.__init__(self)

class DNSManager( wx.Panel, listmix.ColumnSorterMixin ):
	def __init__( self, parent, id = wx.ID_ANY ):
		wx.Panel.__init__(self, parent, id)
		
		self.category = None

		self.hbs = wx.BoxSizer(wx.HORIZONTAL)
		self.categoryLabel = wx.StaticText( self, wx.ID_ANY, 'Category:' )
		self.categoryChoice = wx.Choice( self )
		self.Bind(wx.EVT_CHOICE, self.doChooseCategory, self.categoryChoice)
		
		self.selectAll = wx.Button( self, wx.ID_ANY, 'Select All', style=wx.BU_EXACTFIT )
		self.Bind( wx.EVT_BUTTON, self.onSelectAll, self.selectAll )
		
		self.deSelectAll = wx.Button( self, wx.ID_ANY, 'Deselect All', style=wx.BU_EXACTFIT )
		self.Bind( wx.EVT_BUTTON, self.onDeselectAll, self.deSelectAll )
		
		self.setDNS = wx.Button( self, wx.ID_ANY, 'DNS Selected', style=wx.BU_EXACTFIT )
		self.Bind( wx.EVT_BUTTON, self.onSetDNS, self.setDNS )
		
		self.il = wx.ImageList(16, 16)
		self.sm_rt = self.il.Add(wx.Bitmap( os.path.join(Utils.getImageFolder(), 'SmallRightArrow.png'), wx.BITMAP_TYPE_PNG))
		self.sm_up = self.il.Add(wx.Bitmap( os.path.join(Utils.getImageFolder(), 'SmallUpArrow.png'), wx.BITMAP_TYPE_PNG))
		self.sm_dn = self.il.Add(wx.Bitmap( os.path.join(Utils.getImageFolder(), 'SmallDownArrow.png'), wx.BITMAP_TYPE_PNG ))
		
		self.list = AutoWidthListCtrl( self, wx.ID_ANY, style = wx.LC_REPORT 
														 | wx.BORDER_NONE
														 | wx.LC_SORT_ASCENDING
														 | wx.LC_HRULES
														 )
		self.list.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
				
		self.hbs.Add( self.categoryLabel, flag=wx.TOP | wx.BOTTOM | wx.LEFT | wx.ALIGN_CENTRE_VERTICAL, border=4 )
		self.hbs.Add( self.categoryChoice, flag=wx.ALL, border=4 )
		self.hbs.AddSpacer( 32 )
		self.hbs.Add( self.selectAll, flag=wx.ALL | wx.ALIGN_CENTRE_VERTICAL, border=4 )
		self.hbs.Add( self.deSelectAll, flag=wx.ALL | wx.ALIGN_CENTRE_VERTICAL, border=4 )
		self.hbs.AddSpacer( 32 )
		self.hbs.Add( self.setDNS, flag=wx.ALL | wx.ALIGN_CENTRE_VERTICAL, border=4 )

		bs = wx.BoxSizer(wx.VERTICAL)
		
		bs.Add(self.hbs, 0, wx.EXPAND )
		bs.Add(wx.StaticText(self, wx.ID_ANY, '  Potential DNS Entrants (use Shift-Click and Ctrl-Click to multi-select)'), 0, wx.ALL, 4 )
		bs.Add(self.list, 1, wx.EXPAND|wx.GROW|wx.ALL, 5 )
		
		self.SetSizer(bs)
		bs.SetSizeHints(self)
	
	def onSelectAll(self, evt):
		for row in xrange(self.list.GetItemCount()):
			self.list.SetItemState(row, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
		wx.CallAfter( self.list.SetFocus )
		
	def onDeselectAll( self, evt ):
		for row in xrange(self.list.GetItemCount()):
			self.list.SetItemState(row, 0, wx.LIST_STATE_SELECTED)
		wx.CallAfter( self.list.SetFocus )
		
	def onSetDNS( self, evt ):
		if not self.list.GetItemCount():
			return
			
		with Model.LockRace() as race:
			if not race:
				return
		
		# Get all selected items.
		nums = [self.list.GetItemData(row) for row in xrange(self.list.GetItemCount())
						if self.list.GetItem(row).m_state & wx.LIST_STATE_SELECTED]
		
		if not nums:
			Utils.MessageOK( self, 'No entrants selected to DNS', 'No entrants selected to DNS' )
			return
		
		lines = []
		for i in xrange( 0, len(nums), 10 ):
			lines.append( ', '.join( str(n) for n in itertools.islice( nums, i, min(i+10, len(nums)) ) ) )
		message = 'DNS the following entrants?\n\n%s' % ',\n'.join( lines )
			
		if not Utils.MessageOKCancel( self, message, 'DNS Entrants' ):
			return
		
		undo.pushState()
		with Model.LockRace() as race:
			for n in nums:
				rider = race.getRider( n )
				rider.status = rider.DNS
			race.setChanged()
		self.refresh()
		wx.CallAfter( self.list.SetFocus )
		
	def doChooseCategory( self, event ):
		Utils.setCategoryChoice( self.categoryChoice.GetSelection(), 'DNSManager' )
		self.refresh()

	def clearGrid( self ):
		self.list.ClearAll()
		
	def GetListCtrl( self ):
		return self.list
		
	def GetSortImages(self):
		return (self.sm_dn, self.sm_up)
		
	def refresh( self ):
		self.category = None
		self.clearGrid()
		
		potentialDNS = {}
		with Model.LockRace() as race:
			if not race:
				return
			catName = FixCategories( self.categoryChoice, getattr(race, 'DNSManagerCategory', 0) )
			self.hbs.RecalcSizes()
			self.hbs.Layout()
			for si in self.hbs.GetChildren():
				if si.IsWindow():
					si.GetWindow().Refresh()
			self.category = race.categories.get( catName, None )
			
			try:
				externalFields = race.excelLink.getFields()
				externalInfo = race.excelLink.read()
			except:
				self.clearGrid()
				return
		
			for num, info in externalInfo.iteritems():
				if self.category and race.getCategory(num) != self.category:
					continue
				rider = race.riders.get( num, None )
				if not rider:
					potentialDNS[num] = info
				else:
					# Also add riders marked as Finishers that have no times.
					if rider.status == rider.Finisher and not rider.times:
						potentialDNS[num] = info
			
		if not potentialDNS:
			return
		
		# Add the headers.
		for c, f in enumerate(externalFields):
			self.list.InsertColumn( c+1, f, wx.LIST_FORMAT_RIGHT if f.startswith('Bib') else wx.LIST_FORMAT_LEFT )
		
		# Create the data.  Sort by Bib#
		data = [tuple( num if i == 0 else info.get(f, '') for i, f in enumerate(externalFields)) for num, info in potentialDNS.iteritems()]
		data.sort()
		
		# Populate the list.
		for row, d in enumerate(data):
			index = self.list.InsertImageStringItem(sys.maxint, str(d[0]), self.sm_rt)
			for i, v in enumerate(itertools.islice(d, 1, len(d))):
				self.list.SetStringItem( index, i+1, v )
			self.list.SetItemData( row, d[0] )		# This key links to the sort fields used by ColumnSorterMixin
		
		# Set the sort fields and configure the sorter mixin.
		self.itemDataMap = dict( (d[0], d) for d in data )
		listmix.ColumnSorterMixin.__init__(self, len(externalFields))

		# Make all column widths autosize.
		for i, f in enumerate(externalFields):
			self.list.SetColumnWidth( i, wx.LIST_AUTOSIZE )
			
		# Fixup the Bib number, as autosize gets confused with the graphic.
		self.list.SetColumnWidth( 0, 64 )
		self.list.SetFocus()

	def commit( self ):
		pass

class DNSManagerDialog( wx.Dialog ):
	def __init__( self, parent, id = wx.ID_ANY ):
		wx.Dialog.__init__( self, parent, id, "DNS Manager",
						style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME|wx.TAB_TRAVERSAL )
						
		vs = wx.BoxSizer( wx.VERTICAL )
		
		self.dnsManager = DNSManager( self )
		self.dnsManager.SetMinSize( (700, 500) )
		
		vs.Add( self.dnsManager, 1, flag=wx.ALL|wx.EXPAND, border = 4 )
		
		self.helpBtn = wx.Button( self, wx.ID_ANY, '&Help' )
		self.Bind( wx.EVT_BUTTON, self.onHelp, self.helpBtn )
		
		self.closeBtn = wx.Button( self, wx.ID_ANY, '&Close (Ctrl-Q)' )
		self.Bind( wx.EVT_BUTTON, self.onClose, self.closeBtn )
		self.Bind( wx.EVT_CLOSE, self.onClose )

		hs = wx.BoxSizer( wx.HORIZONTAL )
		hs.AddStretchSpacer()
		hs.Add( self.helpBtn, flag=wx.ALL|wx.ALIGN_RIGHT, border = 4 )
		hs.Add( self.closeBtn, flag=wx.ALL|wx.ALIGN_RIGHT, border = 4 )
		vs.Add( hs, flag=wx.EXPAND )
		
		self.SetSizerAndFit(vs)
		vs.Fit( self )
		
		# Add Ctrl-Q to close the dialog.
		self.Bind(wx.EVT_MENU, self.onClose, id=wx.ID_CLOSE)
		self.Bind(wx.EVT_MENU, self.onUndo, id=wx.ID_UNDO)
		self.Bind(wx.EVT_MENU, self.onRedo, id=wx.ID_REDO)
		accel_tbl = wx.AcceleratorTable([
			(wx.ACCEL_CTRL,  ord('Q'), wx.ID_CLOSE),
			(wx.ACCEL_CTRL,  ord('Z'), wx.ID_UNDO),
			(wx.ACCEL_CTRL,  ord('Y'), wx.ID_REDO),
			])
		self.SetAcceleratorTable(accel_tbl)
		
		self.CentreOnParent(wx.BOTH)
		self.SetFocus()
		
		wx.CallAfter( self.dnsManager.refresh )

	def refresh( self ):
		self.dnsManager.refresh()
	
	def onUndo( self, event ):
		undo.doUndo()
		self.refresh()
		
	def onRedo( self, event ):
		undo.doRedo()
		self.refresh()
	
	def onHelp( self, event ):
		Utils.showHelp( 'Menu-DataMgmt.html#add-dns-from-external-excel-data' )
		
	def onClose( self, event ):
		wx.CallAfter( Utils.refresh )
		self.dnsManager.commit()
		self.EndModal( wx.ID_OK )

		
if __name__ == '__main__':
	Utils.disable_stdout_buffering()
	app = wx.PySimpleApp()
	mainWin = wx.Frame(None,title="CrossMan", size=(600,600))
	Model.setRace( Model.Race() )
	Model.getRace()._populate()
	
	from ReadSignOnSheet import ExcelLink
	e = ExcelLink()
	e.fileName = r'Wyoming\chips and bibs for Wyoming August 26 2012.xls'
	e.sheetName = r'chips and bibs'
	e.fieldCol = {'Bib#':2, 'LastName':3, 'FirstName':4, 'Team':-1, 'License':-1, 'Category':-1, 'Tag':-1, 'Tag2':-1}
	e.read()
	Model.race.excelLink = e
	
	dnsManager = DNSManager(mainWin)
	dnsManager.refresh()
	mainWin.Show()
	app.MainLoop()