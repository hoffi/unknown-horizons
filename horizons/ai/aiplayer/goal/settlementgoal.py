# ###################################################
# Copyright (C) 2011 The Unknown Horizons Team
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

from horizons.ai.aiplayer.goal import Goal
from horizons.util.python import decorators

class SettlementGoal(Goal):
	"""
	An object of this class describes a goal that a settlement of an AI player attempts to fulfil.
	"""

	def __init__(self, settlement_manager):
		super(SettlementGoal, self).__init__(settlement_manager.owner)
		self.__init(settlement_manager)

	def __init(self, settlement_manager):
		self.settlement_manager = settlement_manager

	@property
	def can_be_activated(self):
		return super(SettlementGoal, self).can_be_activated and self.personality.residences_required <= self.settlement_manager.tents

	def __str__(self):
		return super(SettlementGoal, self).__str__() + ', ' + self.settlement_manager.settlement.name

decorators.bind_all(SettlementGoal)