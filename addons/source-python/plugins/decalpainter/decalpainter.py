import json
from collections import OrderedDict, MutableMapping

from effects import TempEntity
from mathlib import Vector
from listeners import OnClientActive
from path import Path
from core import echo_console
from engines.server import global_vars
from stringtables.downloads import Downloadables
from engines.precache import Decal
from commands.server import ServerCommand
from plugins.info import PluginInfo

base_path = Path(__file__).parent

MODNAME = base_path.namebase
DECALPATH = base_path.joinpath('decallist.json')
COORDSDIR = base_path.joinpath('coords')

dl = Downloadables()

class FifoDict(MutableMapping):
	def __init__(self, *args, **kwargs):
		self._maxlen = None
		self._data = OrderedDict(*args, **kwargs)
	def __setitem__(self, key, value):
		if self._maxlen and len(self) >= self._maxlen:
			self.popitem()
		self._data[key] = value
	def __delitem__(self, key):
		del self._data[key]
	def __iter__(self):
		return iter(self._data)
	def __len__(self):
		return len(self._data)
	def __getitem__(self,key):
		return self._data[key]
	def __contains__(self, key):
		return OrderedDict.__contains__(self, key)
	def setmaxlen(self, maxlen):
		if maxlen != None:
			self._maxlen = maxlen
		else:
			raise NotImplementedError

class DecalManager(object):
	def __init__(self, decalpath, coordsdir, refresh=True):
		self.decalpath = decalpath
		self.coordsdir = coordsdir
		if refresh:
			self.refresh()

	def refresh(self):
		with self.decalpath.open() as f:
			self._decals = json.load(f)
		self._decalcoords = FifoDict()
		self._decalcoords.setmaxlen(1)
		self._compile_decals()
		self._compile_coords()

	def paint_decals(self, rcpt):
		try:
			decals = self._decalcoords[self.map_name]
		except KeyError:
			self._compile_decals()
			self._compile_coords()
			decals = self._decalcoords[self.map_name]
		for decal in decals:
			index = self._decals[decal]["index"]
			for coord in self._decalcoords[self.map_name][decal]:
				self._paint_decal(rcpt, index, coord)

	def _compile_decals(self):
		for decal in self._decals:
			dl.add('materials/'+self._decals[decal]["vmt"])
			dl.add('materials/'+self._decals[decal]["vtf"])
			self._decals[decal]["index"] = Decal(self._decals[decal]["vmt"], download=False, preload=True)

	def _compile_coords(self):
		self._decalcoords[self.map_name] = dict()
		try:
			with self._get_coords_file() as f:
				coords = json.load(f)
		except AttributeError:
			pass
		else:
			for decal in coords:
				self._decalcoords[self.map_name][decal] = coords[decal]

	def _get_coords_file(self):
		map_coords = self.coordsdir.joinpath('{0}{1}.json'.format(self.map_name, self.map_version))
		if map_coords.isfile():
			return map_coords.open()
		map_coords = self.coordsdir.joinpath('{0}.json'.format(self.map_name))
		if map_coords.isfile():
			return map_coords.open()
		return None

	def _paint_decal(self, rcpt, material, coord):
		TempEntity('BSP Decal', decal=material, origin=Vector(*coord)).create(rcpt)

	@property
	def map_name(self):
		return global_vars.map_name

	@property
	def map_version(self):
		return global_vars.map_version

decalmanager = DecalManager(DECALPATH, COORDSDIR)


@OnClientActive
def on_client_active(index):
	decalmanager.paint_decals([index])

@ServerCommand("{0}_refresh".format(MODNAME))
def server_command_test(command):
	decalmanager.refresh()
	echo_console("Refreshed the decals to paint!")