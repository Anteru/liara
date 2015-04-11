import os
import markdown2, yaml

class ItemAlreadyExistsException(Exception):
	def __init__(self, path):
		Exception.__init__ (self)
		self._path = path

	def __str__(self):
		return 'The path {} is already used by an item'.format (self._path)

class Item:
	"""A single site item

	An item is identified by its path. Only one item can exist for any given
	path."""
	def __init__ (self, path, content = None, metadata = set ()):
		self._path = path
		self._content = {'default' : content}
		self._metadata = metadata

	def __str__ (self):
		return 'Item: {}'.format (self._path)

	def GetMetadata (self):
		return self._metadata

	def GetAttribute (self, name, default=None):
		"""Get a metadata attribute."""
		return self._metadata.get (name, default)

	def SetAttribute (self, name, value):
		"""Set a metadata attribute."""
		self._metadata [name] = value

	def GetContent (self, kind='default', default=None):
		"""Get the content.

		If this file is binary, this will be the absolute path to the source
		file."""
		return self._content.get (kind, default)

	def SetContent (self, content, contentType = None, kind='default'):
		"""Set the content."""
		self._content[kind] = content
		if contentType is not None:
			assert contentType in {'text', 'binary'}, 'Content must be either text or binary'
			self._metadata ['content-type'] = contentType

	def IsText (self):
		"""Check if this item contains text content."""
		return self._metadata['content-type'] == 'text'

	def IsBinary (self):
		"""Check if this item contains binary content."""
		return self._metadata['content-type'] == 'binary'

	def GetPath (self):
		return self._path

class Reader:
	def GetItems (self):
		return []

class FilesystemReader(Reader):
	def __init__ (self, directory):
		self._directory = directory
		self.textExtensions = {'.md', '.html', '.blog', '.json', '.less', '.coffee', '.js'}

	def RegisterTextExtension (self, ext):
		self.textExtensions.insert (ext)

	def GetItems (self):
		for root, _, files in os.walk(self._directory):
			for filename in files:
				if filename.startswith ('.') and filename not in {'.htaccess'}:
					continue

				absolutePath = os.path.join (root, filename)

				name, ext = os.path.splitext (filename)
				relativePath = os.path.relpath (root, self._directory)

				if relativePath == '.':
					relativePath = '/' + name
				else:
					if name != 'index':
						relativePath = '/' + os.path.join (relativePath, name)
					else:
						relativePath = '/' + relativePath

				relativePath = relativePath.replace ('\\', '/')

				if ext in self.textExtensions:
					yield self._GetTextItem (relativePath, absolutePath)
				else:
					yield self._GetBinaryItem (relativePath, absolutePath)

	def _GetTextItem (self, relativePath, absolutePath):
		name, extension = os.path.splitext(os.path.basename (absolutePath))

		content = open(absolutePath, 'r', encoding='utf-8').read ()
		if (content.startswith ('---')):
			content = content[3:]

			metadata = yaml.load (content [:content.find ('---')])

			# +4, we want to get the \n as well
			content = content [content.find ('---')+4:]

			metadata ['content-type'] = 'text'
			metadata ['extension'] = extension
			metadata ['filename'] = name

			return Item (relativePath, content, metadata)
		else:
			return Item (relativePath, content,
				{'content-type': 'text',
				 'extension' : extension,
				 'filename' : name})

	def _GetBinaryItem (self, relativePath, absolutePath):
		name, extension = os.path.splitext(os.path.basename (absolutePath))
		return Item (relativePath + extension, absolutePath,
			{'content-type' : 'binary',
			 'filename' : name,
			 'extension' : extension,
			 'file_stats' : os.stat (absolutePath),
			 'use_extension' : False})

class Filter:
	def Visit (self, item):
		pass

class MarkdownFilter(Filter):
	def Visit (self, item):
		if item.IsText () and item.GetAttribute ('extension') in {'.blog', '.md'}:
			item.SetContent (markdown2.markdown (item.GetContent ()))
			item.SetAttribute ('extension', '.html')

class LessFilter(Filter):
	'''Process .less files using the less compiler.

	This filter only works on text files with the .less extension. It replaces
	the content with CSS and changes the extension to .css. It assumes that
	`lessc` is available.'''
	def __init__(self, includePath = '.'):
		self._includePath = includePath

	def Visit (self, item):
		import subprocess
		if item.IsText () and item.GetAttribute ('extension') in {'.less'}:
			process = subprocess.Popen ('lessc --include-path={} -'.format (self._includePath),
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE, shell=True)
			out, _ = process.communicate (item.GetContent ().encode ('utf-8'))
			item.SetContent (out.decode ('utf-8'))
			item.SetAttribute ('extension', '.css')

class CoffeeFilter(Filter):
	'''Process .coffee files using the coffee compiler.

	This filter only works on text files with the .coffee extension. It replaces
	the content with JavaScript and changes the extension to .js. It assumes that
	`coffee` is available.'''
	def Visit (self, item):
		import subprocess
		if item.IsText () and item.GetAttribute ('extension') in {'.coffee'}:
			process = subprocess.Popen ('coffee -s -p -c', stdin=subprocess.PIPE,
				stdout=subprocess.PIPE, shell=True)
			out, _ = process.communicate (item.GetContent ().encode ('utf-8'))
			item.SetContent (out.decode ('utf-8'))
			item.SetAttribute ('extension', '.js')

class UglifyjsFilter (Filter):
	'''Process .js files using UglifyJS.

	This filter only works on text files with the .js extension. It compresses
	the content. The filter assumes that `uglifyjs` is available.'''
	def Visit (self, item):
		import subprocess
		if item.IsText () and item.GetAttribute ('extension') in {'.js'}:
			process = subprocess.Popen ('uglifyjs - --comments all', stdin=subprocess.PIPE,
				stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
			out, _ = process.communicate (item.GetContent ().encode ('utf-8'))
			item.SetContent (out.decode ('utf-8'))

class Site:
	"""A web site.

	A web site consists of items. Each item is stored at a specific path. Items
	can be processed using Filters. Eventually, a site is deployed using a
	router."""
	def __init__(self, reader):
		self._items = {item.GetPath () : item for item in reader.GetItems () }

	def GetItem (self, path):
		return self._items.get (path, None)

	def GetItems (self, pathFilter = '*'):
		"""Get all items that match a specified path."""
		import fnmatch
		return (v for k,v in self._items.items () if fnmatch.fnmatch (k, pathFilter))

	def AddItem (self, item):
		"""Add a new item."""
		if item.GetPath () in self._items:
			raise ItemAlreadyExistsException (item.GetPath ())
		self._items [item.GetPath ()] = item

	def RemoveItem (self, item):
		"""Remove an item."""
		del self._items [item.GetPath ()]

	def Filter (self, theFilter, pathFilter = '*'):
		"""Filter the site using a specified filter.

		If the filter returns `False`, the item will be removed."""
		itemsToRemove = []

		for item in self.GetItems (pathFilter):
			keep = theFilter.Visit (item)

			if keep is False:
				itemsToRemove.append (item)

		for item in itemsToRemove:
			self.RemoveItem (item)

	def Route (self, router, callback, pathFilter = '*'):
		"""Route a page using a router.

		For each path that is successfully routed, the callback will be invoked."""
		for item in self.GetItems (pathFilter):
			targetPath = router.Route (item)
			if targetPath is not None:
				callback (targetPath, item)

	def Deploy (self, router, writer, pathFilter = '*'):
		"""Deploy the site using a specified router and writer."""
		self.Route (router, lambda path, item: writer.Write (path, item), pathFilter)

class Router:
	def __init__ (self):
		self._routes = {}

	def Add (self, routes):
		self._routes.update (routes)

	def Route (self, item):
		if (item.GetPath () in self._routes):
			return self._routes [item.GetPath ()]

		if item.GetAttribute ('use_extension', True):
			return item.GetPath () + item.GetAttribute ('extension')
		else:
			return item.GetPath ()

class IndexRouter:
	def __init__ (self):
		self._routes = {}

	def Add (self, routes):
		self._routes.update (routes)

	def Route (self, item):
		if (item.GetPath () in self._routes):
			return self._routes [item.GetPath ()]

		if item.GetPath () == '/':
			return 'index.html'
		elif item.GetAttribute ('use_extension', True):
			if item.GetAttribute ('extension') == '.html':
				return item.GetPath () + '/index.html'
			else:
				return item.GetPath () + item.GetAttribute ('extension')
		else:
			return item.GetPath ()

class SHA512Router(Router):
	def __init__ (self, pathFilter = None):
		Router.__init__(self)
		self._ignores = set ()
		self._pathFilter = pathFilter

	def AddIgnore (self, ignores):
		self._ignores.update (ignores)

	def Route (self, item):
		path = item.GetPath ()

		if path in self._ignores:
			return None

		if self._pathFilter is not None:
			path = self._pathFilter (path)

		return self._GetPath (path)

	def _GetPath (self, path):
		import hashlib
		return hashlib.sha512(path.encode('utf-8')).hexdigest() + '.html'

class Writer:
	def Write (self, path, item):
		pass

def CreateBreadcrumbs (site, item):
	"""Create a breadcrumb trail."""
	parts = item.GetPath ().split ('/')[1:]

	result = []
	currentPath = ''

	for part in parts:
		currentPath += '/' + part
		siteItem = site.GetItem (currentPath)
		if siteItem is not None:
			result.append ({'link' : currentPath, 'title' : siteItem.GetAttribute ('title')})
		else:
			# Intermediate item does not exist
			result.append ({'link' : None, 'title' : part})
	return result

class FilesystemWriter (Writer):
	def __init__ (self, outputDirectory):
		self._outputdir = outputDirectory
		self._cache = {}

	def _MakeDirectory (self, path):
		'''Create all directories for a specific path.'''
		directory = os.path.dirname (path)

		# docs says os.makedirs doesn't like ..
		outputDir = os.path.abspath (os.path.join(self._outputdir, directory))
		os.makedirs (outputDir, exist_ok = True)

	def GetCache (self):
		return self._cache

	def _CacheItemInfo (self, path, content):
		import hashlib
		if isinstance (content, str):
			self._cache [path] = hashlib.sha512(content.encode ('utf-8'))
		else:
			self._cache [path] = hashlib.sha512(content)

	def Write (self, path, item):
		self._MakeDirectory (path [1:])

		outputPath = self._outputdir + path

		if item.IsText ():
			with open(outputPath, 'w', encoding='utf-8') as outputFile:
				self._CacheItemInfo (path, item.GetContent ())
				outputFile.write (item.GetContent ())
		elif item.IsBinary ():
			with open(outputPath, 'wb') as outputFile, open(item.GetContent(), 'rb') as inputFile:
				content = inputFile.read ()
				self._CacheItemInfo (path, content)
				outputFile.write (content)
