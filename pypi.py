import shutil
import os
import stat
import glob
import datetime
import subprocess
from Version import AppVerName

pypiDir = 'pypi'

def writeToFile( s, fname ):
	print 'creating', fname, '...'
	with open(os.path.join(pypiDir,fname), 'wb') as f:
		f.write( s )

#-----------------------------------------------------------------------
# Compile the help files
#
from helptxt.compile import CompileHelp
CompileHelp( 'helptxt' )

#------------------------------------------------------
# Create a release area for pypi
print 'Clearing previous contents...'
subprocess.call( ['rm', '-rf', pypiDir] )
os.mkdir( pypiDir )

#--------------------------------------------------------
readme = '''
========
CrossMgr
========

Free timing and results software for Cyclo-Cross races (donations recommended for
paid events).

CrossMgr quickly produces professional looking results including rider lap times.
It reads rider data from Excel, and formats result in Excel format or Html for
publishing to the web.
CrossMgr was created by a Cyclo-cross official, and has extensive features to
settle disputes.

See `CrossMgr <http://www.sites.google.com/site/crossmgrsoftware/>`__ for full details.
'''

writeToFile( readme, 'README.txt' )

#--------------------------------------------------------
changes = '''
See http://www.sites.google.com/site/crossmgrsoftware/ for details.
'''
writeToFile( changes, 'CHANGES.txt' )
	
#--------------------------------------------------------
license = '''
Copyright (C) 2008-%d Edward Sitarski

Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
and associated documentation files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
''' % datetime.datetime.now().year

writeToFile( license, 'License.txt' )

#--------------------------------------------------------

manifest = '''include *.txt
recursive-include CrossMgr/htmldoc *.html
recursive-include CrossMgr/html *.html
recursive-include CrossMgr/images *
'''

writeToFile( manifest, 'MANIFEST.in' )

#--------------------------------------------------------

srcDir = os.path.join( pypiDir, 'CrossMgr' )
os.mkdir( srcDir )
for dir in ['images', 'html', 'htmldoc']:
	print 'copying', dir, '...'
	shutil.copytree( dir, os.path.join(srcDir,dir) )

print 'Copy the src files and add the copyright notice.'
license = license.replace( '\n', '\n# ' )
for fname in glob.glob( '*.*' ):
	if not (fname.endswith( '.py' ) or fname.endswith('.pyw')):
		continue
	print '   ', fname, '...'
	with open(fname, 'rb') as f:
		contents = f.read()
	if contents.startswith('import'):
		p = 0
	else:
		for search in ['\nimport', '\nfrom']:
			p = contents.find(search)
			if p >= 0:
				p += 1
				break
	if p >= 0:
		contents = ''.join( [contents[:p],
							'\n',
							'#------------------------------------------------------',
							license,
							'\n',
							contents[p:]] )
		
	with open(os.path.join(srcDir, fname), 'wb' ) as f:
		f.write( contents )

print 'Adding script to bin dir..'
binDir = os.path.join( pypiDir, 'bin' )
os.mkdir( binDir )
shutil.copy( os.path.join(srcDir,'CrossMgr.pyw'), binDir )
exeName = os.path.join(binDir,'CrossMgr.pyw')
# Make it executable.
os.chmod( exeName, os.stat(exeName)[0] | stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH )
	
print 'Creating setup.py...'
setup = {
	'name':			'CrossMgr',
	'version':		AppVerName.split(' ')[1],
	'author':		'Edward Sitarski',
	'author_email':	'edward.sitarski@gmail.com',
	'packages':		['CrossMgr'],
	'scripts':		['bin/CrossMgr.pyw'],
	'url':			'http://www.sites.google.com/site/crossmgrsoftware/',
	'license':		'License.txt',
	'description':	'CrossMgr: free results software for Cyclo-Cross and other bike races',
	'install_requires':	[
							'xlrd >= 0.8.0',
							'xlwt >= 0.7.4',
							'wxPython >= 2.8.12',
						],
}

with open(os.path.join(pypiDir,'setup.py'), 'wb') as f:
	f.write( 'from distutils.core import setup\n' )
	f.write( 'setup(\n' )
	for key, value in setup.iteritems():
		f.write( '    %s=%s,\n' % (key, repr(value)) )
	f.write( "    long_description=open('README.txt').read()\n" )
	f.write( ')\n' )

print 'Creating install package...'
os.chdir( pypiDir )
subprocess.call( ['python', 'setup.py', 'sdist'] )
	
print 'Done.'
