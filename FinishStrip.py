import wx
import os
import sys
import glob
import math

contrastColour = wx.Colour( 255, 130, 0 )

def formatTime( secs, highPrecision = True ):
	if secs is None:
		secs = 0
	if secs < 0:
		sign = '-'
		secs = -secs
	else:
		sign = ''
	f, ss = math.modf(secs)
	secs = int(ss)
	hours = int(secs // (60*60))
	minutes = int( (secs // 60) % 60 )
	secs = secs % 60
	if highPrecision:
		secStr = '{:05.2f}'.format( secs + f )
	else:
		secStr = '{:02d}'.format( secs )
	if hours > 0:
		return "{}{}:{:02d}:{}".format(sign, hours, minutes, secStr)
	if minutes > 0:
		return "{}{}:{}".format(sign, minutes, secStr)
	return "{}{}".format(sign, secStr.lstrip('0') if not secStr.startswith('00') else secStr[1:] )
		
class PhotoExists( wx.Panel ):
	def __init__( self, parent, id=wx.ID_ANY, size=(640,480), style=0,
			tMin= 0, tMax=600.0, pixelsPerSec = 1.0, tPhotos = [] ):
		super(PhotoExists, self).__init__( parent, id, size=size, style=style )
		self.SetBackgroundStyle( wx.BG_STYLE_CUSTOM )
		self.tMin = tMin
		self.tMax = tMax
		self.tPhotos = tPhotos
		self.pixelsPerSec = pixelsPerSec
		
		self.Bind( wx.EVT_PAINT, self.OnPaint )
		self.Bind( wx.EVT_SIZE, self.OnSize )
		self.Bind( wx.EVT_ERASE_BACKGROUND, self.OnErase )

	def SetTimeMinMax( self, tMin, tMax ):
		self.tMin = tMin
		self.tMax = tMax
		wx.CallAfter( self.Refresh )
	
	def SetTimePhotos( self, tPhotos ):
		self.tPhotos = tPhotos
		wx.CallAfter( self.Refresh )
		
	def SetPixelsPerSec( self, pixelsPerSec ):
		self.pixelsPerSec = pixelsPerSec
		wx.CallAfter( self.Refresh )
	
	def OnErase( self, event ):
		pass
	
	def OnSize( self, event ):
		wx.CallAfter( self.Refresh )
		event.Skip()
		
	def OnPaint( self, event=None ):
		dc = wx.AutoBufferedPaintDC( self )
		dc.SetBackground( wx.Brush(self.GetBackgroundColour()) )
		dc.Clear()
		
		if not self.tPhotos:
			return
		
		w, h = self.GetSize()
		x = 12
		w -= x * 2
		mult = float(w) / float(self.tMax - self.tMin)
		
		photoWidth = w * (float(640)/self.pixelsPerSec) / float(self.tMax - self.tMin)
		
		dc.SetPen( wx.Pen(wx.Colour(64,64,64), max(1, photoWidth)) )
		for t in self.tPhotos:
			tx = x + int((t - self.tMin) * mult)
			dc.DrawLine( tx, 0, tx, h )

class FinishStrip( wx.Panel ):
	def __init__( self, parent, id=wx.ID_ANY, size=(640,480), style=0,
			fps=25,
			photoFolder='Test_Photos',
			leftToRight=False ):
		super(FinishStrip, self).__init__( parent, id, size=size, style=style )
		self.SetBackgroundStyle( wx.BG_STYLE_CUSTOM )
		
		self.fps = float(fps)
		self.scale = 1.0
		self.xTimeLine = None
		
		self.Bind( wx.EVT_PAINT, self.OnPaint )
		self.Bind( wx.EVT_SIZE, self.OnSize )
		self.Bind( wx.EVT_ERASE_BACKGROUND, self.OnErase )
		self.Bind( wx.EVT_LEFT_UP, self.OnLeftUp )
		
		self.Bind( wx.EVT_ENTER_WINDOW, self.OnEnterWindow )
		self.Bind( wx.EVT_MOTION, self.OnMotion )
		self.Bind( wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow )
		self.xMotionLast = None
		self.yMotionLast = None
		
		self.photoFolder = photoFolder
		self.timeBitmaps = []
		
		self.leftToRight = leftToRight
		self.tDrawStart = 0.0
		self.pixelsPerSec = 25
		
		self.tDrawStartCallback = None
		
		self.RefreshBitmaps()
		
		tMin, tMax = self.GetTimeMinMax()
		if tMin is not None:
			self.tDrawStart = tMin
		
	def SetLeftToRight( self, leftToRight=True ):
		self.leftToRight = leftToRight
		wx.CallAfter( self.Refresh )
		
	def SetPixelsPerSec( self, pixelsPerSec ):
		self.pixelsPerSec = pixelsPerSec
		wx.CallAfter( self.Refresh )

	def SetDrawStartTime( self, tDrawStart ):
		self.tDrawStart = tDrawStart
		wx.CallAfter( self.Refresh )
		
	def GetTimeMinMax( self ):
		return (self.timeBitmaps[0][0], self.timeBitmaps[-1][0]) if self.timeBitmaps else (None, None)
		
	def GetTimePhotos( self ):
		return [t for t, bm in self.timeBitmaps]
		
	def getPhotoTime( self, fname ):
		fname = os.path.splitext(os.path.basename(fname))[0]
		
		# Parse time and index from filename.
		tstr = fname.split( '-time-' )[1]
		hh, mm, ss, dd, ii = tstr.split( '-' )
		t = float(hh)*60.0*60.0 + float(mm)*60.0 + float('{}.{}'.format(ss,dd))
		
		# Round to nearest frame based on index.
		t = math.floor(t * self.fps) / self.fps if ii == 1 else math.ceil(t * self.fps) / self.fps
		return t
		
	def RefreshBitmaps( self, tStart=0.0, tEnd=sys.float_info.max, reusePrevious=True ):
		bitmaps = {t:bm for t, bm in self.timeBitmaps} if reusePrevious else {}
		
		for f in glob.glob(os.path.join(self.photoFolder, '*.jpg')):
			t = self.getPhotoTime( f )
			if t in bitmaps or not (tStart <= t <= tEnd):
				continue
			
			image = wx.Image( f, wx.BITMAP_TYPE_JPEG )
			image.Rescale( int(image.GetWidth()*self.scale), int(image.GetHeight()*self.scale), wx.IMAGE_QUALITY_HIGH )
			bitmaps[t] = wx.BitmapFromImage( image )
		
		self.timeBitmaps = [(t, bm) for t, bm in bitmaps.iteritems()]
		self.timeBitmaps.sort( key=lambda tb: tb[0] )
		
	def OnErase( self, event ):
		pass
	
	def OnSize( self, event ):
		wx.CallAfter( self.Refresh )
		event.Skip()
		
	def getXTimeLine( self ):
		widthWin, heightWin = self.GetClientSize()
		widthWinHalf = widthWin // 2
		return min( widthWin, self.xTimeLine if self.xTimeLine is not None else widthWinHalf )
		
	def OnLeftUp( self, event ):
		x = event.GetX()
		self.tDrawStart += (x - self.getXTimeLine()) / float(self.pixelsPerSec) * (-1.0 if self.leftToRight else 1.0)
		self.xTimeLine = x
		wx.CallAfter( self.OnLeaveWindow )
		wx.CallAfter( self.Refresh )
		if self.tDrawStartCallback:
			wx.CallAfter( self.tDrawStartCallback, self.tDrawStart )
		
	def drawXorLine( self, x, y ):
		if x is None or not self.timeBitmaps:
			return
		
		dc = wx.ClientDC( self )
		dc.SetLogicalFunction( wx.XOR )
		
		dc.SetPen( wx.WHITE_PEN )
		widthWin, heightWin = self.GetClientSize()
		widthWinHalf = widthWin // 2
		
		xTimeLine = self.getXTimeLine()
		text = formatTime( self.tDrawStart + (x - xTimeLine) / float(self.pixelsPerSec) * (-1.0 if self.leftToRight else 1.0))
		fontHeight = max(5, heightWin//20)
		font = wx.FontFromPixelSize(
			wx.Size(0,fontHeight),
			wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
		)
		dc.SetFont( font )
		tWidth, tHeight = dc.GetTextExtent( text )
		border = int(tHeight / 3)
		
		bm = wx.BitmapFromImage( wx.EmptyImage(tWidth, tHeight) )
		memDC = wx.MemoryDC( bm )
		memDC.SetBackground( wx.BLACK_BRUSH )
		memDC.Clear()
		memDC.SetFont( font )
		memDC.SetTextForeground( wx.WHITE )
		memDC.DrawText( text, 0, 0 )
		bmMask = wx.BitmapFromImage( bm.ConvertToImage() )
		bm.SetMask( wx.Mask(bmMask, wx.BLACK) )
		
		dc.Blit( x+border, y - tHeight, tWidth, tHeight, memDC, 0, 0, useMask=True, rop=wx.XOR )
		
		dc.DrawLine( x, 0, x, heightWin )
		
		memDC.SelectObject( wx.NullBitmap )

	def OnEnterWindow( self, event ):
		pass
		
	def OnMotion( self, event ):
		widthWin, heightWin = self.GetClientSize()
		self.drawXorLine( self.xMotionLast, self.yMotionLast )
		self.xMotionLast = event.GetX()
		self.yMotionLast = event.GetY()
		self.drawXorLine( self.xMotionLast, self.yMotionLast )
		
	def OnLeaveWindow( self, event=None ):
		self.drawXorLine( self.xMotionLast, self.yMotionLast )
		self.xMotionLast = None
	
	def OnPaint( self, event=None ):
		dc = wx.PaintDC( self )
		dc.SetBackground( wx.Brush(wx.Colour(128,128,150)) )
		dc.Clear()
		
		self.xMotionLast = None
		if not self.timeBitmaps:
			return
		
		widthPhoto, heightPhoto = self.timeBitmaps[0][1].GetSize()
		widthPhotoHalf = widthPhoto // 2
		widthWin, heightWin = self.GetClientSize()
		widthWinHalf = widthWin // 2
		
		xTimeLine = self.getXTimeLine()
		
		# Draw the composite photo.
		bitmapDC = wx.MemoryDC()
		if self.leftToRight:
			def getX( t ):
				return int(xTimeLine - widthPhotoHalf - (t - self.tDrawStart) * self.pixelsPerSec)
			
			bmRightEdge = []
			for t, bm in self.timeBitmaps:
				xLeft = getX(t)
				xRight = xLeft + widthPhoto
				if xLeft >= widthWin:
					continue
				if xRight < 0:
					break
				bmRightEdge.append( (bm, xRight) )
			bmRightEdge.append( (None, 0) )
			
			for i in xrange(0, len(bmRightEdge)-1):
				bm, xRight = bmRightEdge[i]
				bmNext, xRightNext = bmRightEdge[i+1]
				bmWidth = max( xRight - xRightNext, widthPhoto )
				bitmapDC.SelectObject( bm )
				dc.Blit(
					xRight - bmWidth, 0, bmWidth, heightPhoto,
					bitmapDC,
					widthPhoto - bmWidth, 0,
				)
				bitmapDC.SelectObject( wx.NullBitmap )
		else:
			def getX( t ):
				return int(xTimeLine - widthPhotoHalf + (t - self.tDrawStart) * self.pixelsPerSec)
			
			bmLeftEdge = []
			for t, bm in self.timeBitmaps:
				xLeft = getX(t)
				xRight = xLeft + widthPhoto
				if xRight < 0:
					continue
				if xLeft >= widthWin:
					break
				bmLeftEdge.append( (bm, xLeft) )
			bmLeftEdge.append( (None, widthWin) )
			
			for i in xrange(0, len(bmLeftEdge)-1):
				bm, xLeft = bmLeftEdge[i]
				bmNext, xLeftNext = bmLeftEdge[i+1]
				bmWidth = max( xLeftNext - xLeft, widthPhoto )
				bitmapDC.SelectObject( bm )
				dc.Blit(
					xLeft, 0, bmWidth, heightPhoto,
					bitmapDC,
					0, 0,
				)
				bitmapDC.SelectObject( wx.NullBitmap )
		
		# Draw the current time at the timeline.
		gc = wx.GraphicsContext.Create( dc )
		
		gc.SetPen( wx.Pen(contrastColour, 1) )
		gc.StrokeLine( xTimeLine, 0, xTimeLine, heightWin )
		
		text = formatTime( self.tDrawStart )
		fontHeight = max(5, heightWin//20)
		font = wx.FontFromPixelSize(
			wx.Size(0,fontHeight),
			wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
		)
		gc.SetFont( font, wx.BLACK )
		tWidth, tHeight = gc.GetTextExtent( text )
		border = int(tHeight / 3)
		
		gc.SetPen( wx.Pen(wx.Colour(64,64,64), 1) )
		gc.SetBrush( wx.Brush(wx.Colour(200,200,200)) )
		rect = wx.Rect( xTimeLine - tWidth//2 - border, 0, tWidth + border*2, tHeight + border*2 )
		gc.DrawRoundedRectangle( rect.GetLeft(), rect.GetTop(), rect.GetWidth(), rect.GetHeight(), border*1.5 )
		rect.SetTop( heightWin - tHeight - border )
		gc.DrawRoundedRectangle( rect.GetLeft(), rect.GetTop(), rect.GetWidth(), rect.GetHeight(), border*1.5 )
		
		gc.DrawText( text, xTimeLine - tWidth//2, border )
		gc.DrawText( text, xTimeLine - tWidth//2, heightWin - tHeight - border/2 )

class FinishStripPanel( wx.Panel ):
	def __init__( self, parent, id=wx.ID_ANY, size=wx.DefaultSize, style=0, fps=25.0 ):
		super(FinishStripPanel, self).__init__( parent, id, size=size, style=style )
		
		self.fps = fps
		
		vs = wx.BoxSizer( wx.VERTICAL )
		
		displayWidth, displayHeight = wx.GetDisplaySize()
	
		self.leftToRight = True
		self.finish = FinishStrip( self, size=(0, 480), leftToRight=self.leftToRight )
		self.finish.tDrawStartCallback = self.tDrawStartCallback
		
		self.timeSlider = wx.Slider( self, style=wx.SL_HORIZONTAL, minValue=0, maxValue=displayWidth )
		self.timeSlider.SetPageSize( 1 )
		self.timeSlider.Bind( wx.EVT_SCROLL, self.onChangeTime )
		
		self.photoExists = PhotoExists( self, size=(0, 12) )
		
		minPixelsPerSecond, maxPixelsPerSecond = self.getSpeedPixelsPerSecondMinMax()
		self.speedSlider = wx.Slider( self, style=wx.SL_HORIZONTAL|wx.SL_LABELS, minValue=minPixelsPerSecond, maxValue=maxPixelsPerSecond )
		self.speedSlider.SetPageSize( 1 )
		self.speedSlider.Bind( wx.EVT_SCROLL, self.onChangeSpeed )
		
		self.direction = wx.RadioBox( self,
			label=u'Direction',
			choices=[u'Right to Left', u'Left to Right'],
			majorDimension=1,
			style=wx.RA_SPECIFY_ROWS
		)
		self.direction.SetSelection( 1 if self.leftToRight else 0 )
		self.direction.Bind( wx.EVT_RADIOBOX, self.onDirection )
		
		fgs = wx.FlexGridSizer( cols=2, vgap=4, hgap=0 )
		
		fgs.Add( wx.StaticText(self, label=u'Time:'), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL )
		fgs.Add( self.timeSlider, flag=wx.EXPAND )
		
		fgs.Add( wx.StaticText(self) )
		fgs.Add( self.photoExists, flag=wx.EXPAND|wx.ALIGN_CENTRE_VERTICAL )
		
		fgs.Add( wx.StaticText(self, label=u'Pixels/Sec:'), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTRE_VERTICAL )
		fgs.Add( self.speedSlider, flag=wx.EXPAND )
		
		fgs.AddGrowableCol( 1, 1 )
		
		vs.Add( self.finish, flag=wx.EXPAND )
		
		vs.Add( fgs, flag=wx.EXPAND|wx.ALL, border=4 )
		vs.Add( self.direction, flag=wx.EXPAND|wx.ALL, border=4 )
		self.SetSizer( vs )
		wx.CallAfter( self.initUI )
		
	def initUI( self ):
		self.finish.SetPixelsPerSec( self.speedSlider.GetMin() )
		self.photoExists.SetTimeMinMax( *self.getPhotoTimeMinMax() )
		self.photoExists.SetTimePhotos( self.finish.GetTimePhotos() )
		self.photoExists.SetPixelsPerSec( self.speedSlider.GetMin() )
		
	def getSpeedPixelsPerSecondMinMax( self ):
		frameTime = 1.0 / self.fps
		
		viewWidth = 4.0			# meters seen in the finish line with the finish camera
		widthPix = 640			# width of the photo
		
		minMax = []
		for speedKMH in (2.0, 80.0):			# Speed of the target (km/h)
			speedMPS = speedKMH / 3.6			# Convert to m/s
			d = speedMPS * frameTime			# Distance the target moves between each frame at speed.
			pixels = widthPix * d / viewWidth	# Pixels the target moves between each frame at that speed.
			pixelsPerSecond = max(10, pixels * self.fps)
			minMax.append( int(pixelsPerSecond) )
		
		return minMax

	def onDirection( self, event ):
		self.leftToRight = (event.GetInt() == 1)
		self.finish.SetLeftToRight( self.leftToRight )
		event.Skip()
		
	def onChangeSpeed( self, event ):
		self.finish.SetPixelsPerSec( event.GetPosition() )
		self.photoExists.SetPixelsPerSec( event.GetPosition() )
		event.Skip()
		
	def getPhotoTimeMinMax( self ):
		tMin, tMax = self.finish.GetTimeMinMax()
		# Widen the range so we can see a few seconds before and after.
		tMin -= 5.0
		tMax += 5.0
		return tMin, tMax
		
	def onChangeTime( self, event ):
		r = float(event.GetPosition()) / float(event.GetEventObject().GetMax())
		tMin, tMax = self.getPhotoTimeMinMax()
		self.finish.SetDrawStartTime( tMin + (tMax - tMin) * r )
		event.Skip()
				
	def tDrawStartCallback( self, tDrawStart ):
		tMin, tMax = self.getPhotoTimeMinMax()
		vMin, vMax = self.timeSlider.GetMin(), self.timeSlider.GetMax()
		self.timeSlider.SetValue( int((tDrawStart - tMin) * float(vMax - vMin) / float(tMax - tMin)) )
		
if __name__ == '__main__':
	app = wx.App(False)
	
	displayWidth, displayHeight = wx.GetDisplaySize()
	
	photoHeight = 480
	width = int(displayWidth * 0.9)
	height = 650
	
	mainWin = wx.Frame(None,title="FinishStrip", size=(width, height))
	FinishStrip = FinishStripPanel( mainWin )
	mainWin.Show()
	app.MainLoop()