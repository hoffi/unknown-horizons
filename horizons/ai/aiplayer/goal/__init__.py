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

import logging

from horizons.ai.aiplayer.constants import BUILD_RESULT, GOAL_RESULT
from horizons.util.python import decorators

class Goal(object):
	"""
	An object of this class describes a goal that an AI player attempts to fulfil.
	"""

	log = logging.getLogger("ai.aiplayer.goal")

	def __init__(self, owner):
		super(Goal, self).__init__()
		self.owner = owner
		self.personality = self.owner.personality_manager.get(self.get_personality_name())

		if not hasattr(Goal, '_next_id'):
			Goal._next_id = 1 # used to assign sequence numbers to goals to ensure consistent ordering
		self.sequence_number = Goal._next_id
		Goal._next_id += 1

	def get_personality_name(self):
		raise NotImplementedError, 'This function has to be overridden.'

	@property
	def priority(self):
		return self.personality.default_priority

	@property
	def active(self):
		return self.can_be_activated

	@property
	def can_be_activated(self):
		return self.personality.enabled and self.owner.settler_level >= self.personality.min_settler_level

	def execute(self):
		raise NotImplementedError, "This function has to be overridden."

	def update(self):
		"""All goals are updated before checking whether they are active"""
		pass

	@classmethod
	def _translate_build_result(cls, result):
		if result == BUILD_RESULT.OK:
			return GOAL_RESULT.BLOCK_ALL_BUILDING_ACTIONS
		elif result == BUILD_RESULT.NEED_RESOURCES:
			return GOAL_RESULT.BLOCK_SETTLEMENT_RESOURCE_USAGE
		elif result in [BUILD_RESULT.IMPOSSIBLE, BUILD_RESULT.UNKNOWN_ERROR, BUILD_RESULT.ALL_BUILT, BUILD_RESULT.SKIP]:
			return GOAL_RESULT.SKIP
		assert False, 'Unable to translate BUILD_RESULT %d to a GOAL_RESULT' % result

	def __lt__(self, other):
		if self.priority != other.priority:
			return self.priority < other.priority
		return self.sequence_number < other.sequence_number

	def __str__(self):
		return 'Goal(%d): %s(%d)' % (self.priority, self.__class__.__name__, self.sequence_number)

decorators.bind_all(Goal)