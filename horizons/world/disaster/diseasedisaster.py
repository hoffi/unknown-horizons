# -*- coding: utf-8 -*-
# ###################################################
# Copyright (C) 2012 The Unknown Horizons Team
# team@unknown-horizons.org
# This file is part of Unknown Horizons.
#
# Unknown Horizons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# ###################################################

from horizons.world.disaster import Disaster
from horizons.messaging import AddStatusIcon, RemoveStatusIcon, NewDisaster
from horizons.world.status import DiseaseStatusIcon
from horizons.constants import GAME_SPEED, BUILDINGS, RES, TIER
from horizons.command.building import Build
from horizons.scheduler import Scheduler
from horizons.util.python.callback import Callback
from horizons.util import WorldObject

class DiseaseDisaster(Disaster):
	"""Simulates a disease.

	Currently only affects settlers.
	Starts at a certain building and will spread out over time.

	"""

	TYPE = "Disease"
	NOTIFICATION_TYPE = 'BUILDING_DISEASED'

	SEED_CHANCE = 0.5


	EXPANSION_RADIUS = 3

	# Defines the mininum number of settler buildings that need to be in a
	# settlement before this disaster can break loose
	MIN_SETTLERS_FOR_BREAKOUT = 10

	DEFAULT_HAVOC_TIME = GAME_SPEED.TICKS_PER_SECOND * 30

	DISASTER_RES = RES.DISEASE

	def __init__(self, settlement, manager):
		super(DiseaseDisaster, self).__init__(settlement, manager)
		self._affected_buildings = []
		self.havoc_time = self.DEFAULT_HAVOC_TIME

	def save(self, db):
		super(DiseaseDisaster, self).save(db)
		for building in self._affected_buildings:
			ticks = Scheduler().get_remaining_ticks(self, Callback(self.wreak_havoc, building), True)
			db("INSERT INTO disease_disaster(disaster, building, remaining_ticks_havoc) VALUES(?, ?, ?)",
			   self.worldid, building.worldid, ticks)

	def load(self, db, worldid):
		super(DiseaseDisaster, self).load(db, worldid)
		for building_id, ticks in db("SELECT building, remaining_ticks_havoc FROM disease_disaster WHERE disaster = ?", worldid):
			# do half of infect()
			building = WorldObject.get_object_by_id(building_id)
			self.log.debug("%s loading disaster %s", self, building)
			self.infect(building, load=(db, worldid))

	@classmethod
	def can_breakout(cls, settlement):
		return settlement.owner.settler_level >= TIER.SETTLERS and \
		       settlement.count_buildings(BUILDINGS.RESIDENTIAL) > cls.MIN_SETTLERS_FOR_BREAKOUT

	def expand(self):
		if not self.evaluate():
			self._manager.end_disaster(self._settlement)
			self.log.debug("%s ending", self)
			# We are done here, time to leave
			return
		self.log.debug("%s still active, expanding..", self)
		for building in self._affected_buildings:
			for tile in self._settlement.get_tiles_in_radius(building.position, self.EXPANSION_RADIUS, False):
				if tile.object is not None and tile.object.id == BUILDINGS.RESIDENTIAL and tile.object not in self._affected_buildings:
					if self._settlement.session.random.random() <= self.SEED_CHANCE:
						self.calculate_times(tile.object)
						self.infect(tile.object)
						return

	def end(self):
		Scheduler().rem_all_classinst_calls(self)

	def infect(self, building, load=None):
		"""Infect a building with fire.
		@load: (db, disaster_worldid), set on restoring infected state of savegame"""
		super(DiseaseDisaster, self).infect(building, load=load)
		# keep in sync with load()
		AddStatusIcon.broadcast(building, DiseaseStatusIcon(building))
		NewDisaster.broadcast(building.owner, building, DiseaseDisaster)
		self._affected_buildings.append(building)

		if load:
			db, worldid = load
			self.havoc_time = db("SELECT remaining_ticks_havoc FROM disease_disaster WHERE disaster = ? AND building = ?", worldid, building.worldid)[0][0]

		Scheduler().add_new_object(Callback(self.wreak_havoc, building), self, run_in=self.havoc_time)

	def recover(self, building):
		super(DiseaseDisaster, self).recover(building)
		RemoveStatusIcon.broadcast(self, building, DiseaseStatusIcon)
		Scheduler().rem_call(self, Callback(self.wreak_havoc, building))
		self._affected_buildings.remove(building)

	def wreak_havoc(self, building):
		super(DiseaseDisaster, self).wreak_havoc(building)
		self._affected_buildings.remove(building)

		# Create a ruin at buildings position
		command = Build(BUILDINGS.SETTLER_RUIN, building.position.origin.x,
		                building.position.origin.y, island=building.island, settlement=building.settlement)

		Scheduler().add_new_object(
			Callback.ChainedCallbacks(building.remove, Callback(command, building.owner)), # remove, then build new
			building, run_in=0)
