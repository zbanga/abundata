import socket
import Utils
from pyllrp.pyllrp import *

def findImpinjHost( impinjPort, callback = None ):
	''' Search ip addresses adjacent to the computer in an attempt to find the reader. '''
	ip = [int(i) for i in Utils.GetDefaultHost().split('.')]
	j = 0
	for i in xrange(14):
		j = -j if j > 0 else -j + 1
		
		ipTest = list( ip )
		ipTest[-1] += j
		if not (0 <= ipTest[-1] < 256):
			continue
			
		impinjHost = '.'.join( '{}'.format(v) for v in ipTest )
		
		if callback:
			callback( '{}:{}'.format(impinjHost, impinjPort) )
		
		readerSocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
		readerSocket.settimeout( 3.0 )
		try:
			readerSocket.connect( (impinjHost, impinjPort) )
		except Exception as e:
			continue
		
		try:
			response = UnpackMessageFromSocket( readerSocket )
		except Exception as e:
			readerSocket.close()
			continue
			
		readerSocket.close()
		
		# Check that the return from the reader is valid.
		try:
			readerTime = response.getFirstParameterByClass(UTCTimestamp_Parameter).Microseconds
		except Exception as e:
			continue
		else:
			return impinjHost
	
	return None

def AutoDetect( impinjPort, callback = None ):
	return findImpinjHost( impinjPort, callback )
		
if __name__ == '__main__':
	print AutoDetect(5084)
