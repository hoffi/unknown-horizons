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

from building import AbstractBuilding
from constants import BUILD_RESULT

from horizons.entities import Entities
from horizons.constants import BUILDINGS, RES
from horizons.command.building import Build
from horizons.util.python import decorators
from horizons.util import Point, Rect, WorldObject

class ProductionChain(object):
	log = logging.getLogger("ai.aiplayer.productionchain")

	def __init__(self, settlement_manager, resource_id, resource_producer):
		super(ProductionChain, self).__init__()
		self.settlement_manager = settlement_manager
		self.resource_id = resource_id
		self.chain = self._get_chain(resource_id, resource_producer, 1.0)
		self.chain.assign_identifier('/%d,%d' % (self.settlement_manager.worldid, self.resource_id))

	def _get_chain(self, resource_id, resource_producer, production_ratio):
		""" Returns None or ProductionChainSubtreeChoice depending on the number of options """
		options = []
		if resource_id in resource_producer:
			for production_line, abstract_building in resource_producer[resource_id]:
				possible = True
				sources = []
				for consumed_resource, amount in production_line.consumed_res.iteritems():
					next_production_ratio = abs(production_ratio * amount / production_line.produced_res[resource_id])
					subtree = self._get_chain(consumed_resource, resource_producer, next_production_ratio)
					if not subtree:
						possible = False
						break
					sources.append(subtree)
				if possible:
					options.append(ProductionChainSubtree(self.settlement_manager, resource_id, production_line, abstract_building, sources, production_ratio))
		if not options:
			return None
		return ProductionChainSubtreeChoice(options)

	@classmethod
	def create(cls, settlement_manager, resource_id):
		"""Creates a production chain that can produce the given resource"""
		resource_producer = {}
		for abstract_building in AbstractBuilding.buildings.itervalues():
			for resource, production_line in abstract_building.lines.iteritems():
				if resource not in resource_producer:
					resource_producer[resource] = []
				resource_producer[resource].append((production_line, abstract_building))
		return ProductionChain(settlement_manager, resource_id, resource_producer)

	def __str__(self):
		return 'ProductionChain(%d): %.5f\n%s' % (self.resource_id, self.get_final_production_level(), self.chain)

	def build(self, amount):
		"""Builds a building that gets it closer to producing at least amount of resource per tick."""
		return self.chain.build(amount)

	def reserve(self, amount, may_import):
		"""Reserves currently available production and imports from other islands if allowed"""
		return self.chain.reserve(amount, may_import)

	def get_final_production_level(self):
		""" returns the production level at the bottleneck """
		return self.chain.get_final_production_level()

	def get_ratio(self, resource_id):
		return self.chain.get_ratio(resource_id)

class ProductionChainSubtreeChoice(object):
	log = logging.getLogger("ai.aiplayer.productionchain")
	coverage_resources = set([RES.COMMUNITY_ID, RES.FAITH_ID, RES.EDUCATION_ID, RES.GET_TOGETHER_ID])

	def __init__(self, options):
		self.options = options
		self.resource_id = options[0].resource_id
		self.production_ratio = options[0].production_ratio
		self.ignore_production = options[0].ignore_production
		self.trade_manager = options[0].trade_manager
		self.settlement_manager = options[0].settlement_manager

	def assign_identifier(self, prefix):
		self.identifier = prefix + ('/choice' if len(self.options) > 1 else '')
		for option in self.options:
			option.assign_identifier(self.identifier)

	def __str__(self, level = 0):
		result = '%sChoice between %d options: %.5f\n' % ('  ' * level, len(self.options), self.get_final_production_level())
		for option in self.options:
			result += option.__str__(level + 1)
		if self.get_root_import_level() > 1e-9:
			result += '\n%sImport %.5f' % ('  ' * (level + 1), self.get_root_import_level())
		return result

	def get_root_production_level(self):
		return sum(option.get_root_production_level() for option in self.options)

	def get_root_import_level(self):
		return self.trade_manager.get_quota(self.identifier, self.resource_id) / self.production_ratio

	def get_final_production_level(self):
		""" returns the production level at the bottleneck """
		return sum(option.get_final_production_level() for option in self.options) + self.get_root_import_level()

	def get_expected_cost(self, amount):
		return min(option.get_expected_cost(amount) for option in self.options)

	def _get_available_options(self):
		available_options = []
		for option in self.options:
			if option.available:
				available_options.append(option)
		return available_options

	def build(self, amount):
		""" Builds the subtree that is currently the cheapest """
		current_production = self.get_final_production_level()
		if amount < current_production + 1e-7 and self.resource_id not in self.coverage_resources:
			# we are already producing enough
			return BUILD_RESULT.ALL_BUILT

		available_options = self._get_available_options()
		if not available_options:
			self.log.debug('%s: no available options', self)
			return BUILD_RESULT.IMPOSSIBLE
		elif len(available_options) == 1:
			return available_options[0].build(amount)

		# need to increase production: build the cheapest subtree
		expected_costs = []
		for i in xrange(len(available_options)):
			option = available_options[i]
			cost = option.get_expected_cost(amount - current_production + option.get_final_production_level())
			if cost is not None:
				expected_costs.append((cost, i, option))

		if not expected_costs:
			self.log.debug('%s: no possible options', self)
			return BUILD_RESULT.IMPOSSIBLE
		else:
			for option in zip(*sorted(expected_costs))[2]:
				result = option.build(amount)
				if result != BUILD_RESULT.IMPOSSIBLE:
					return result
			return BUILD_RESULT.IMPOSSIBLE

	def reserve(self, amount, may_import):
		"""
		Reserves currently available production and imports from other islands if allowed
		Returns the total amount it can reserve or import
		"""
		total_reserved = 0.0
		for option in self._get_available_options():
			total_reserved += option.reserve(max(0.0, amount - total_reserved), may_import)

		# check how much we can import
		if may_import:
			required_amount = max(0.0, amount - total_reserved)
			self.trade_manager.request_quota_change(self.identifier, self.resource_id, required_amount * self.production_ratio)
			total_reserved += self.get_root_import_level()

		return total_reserved

	def get_ratio(self, resource_id):
		return sum(option.get_ratio(resource_id) for option in self.options)

class ProductionChainSubtree:
	def __init__(self, settlement_manager, resource_id, production_line, abstract_building, children, production_ratio):
		self.settlement_manager = settlement_manager
		self.resource_manager = settlement_manager.resource_manager
		self.trade_manager = settlement_manager.trade_manager
		self.resource_id = resource_id
		self.production_line = production_line
		self.abstract_building = abstract_building
		self.children = children
		self.production_ratio = production_ratio
		self.ignore_production = abstract_building.ignore_production

	def assign_identifier(self, prefix):
		self.identifier = '%s/%d,%d' % (prefix, self.resource_id, self.abstract_building.id)
		for child in self.children:
			child.assign_identifier(self.identifier)

	@property
	def available(self):
		return self.settlement_manager.owner.settler_level >= self.abstract_building.settler_level

	def __str__(self, level = 0):
		result = '%sProduce %d (ratio %.2f) in %s (%.5f, %.5f)\n' % ('  ' * level, self.resource_id, \
			self.production_ratio, self.abstract_building.name, self.get_root_production_level(), self.get_final_production_level())
		for child in self.children:
			result += child.__str__(level + 1)
		return result

	def get_expected_children_cost(self, amount):
		total = 0
		for child in self.children:
			cost = child.get_expected_cost(amount)
			if cost is None:
				return None
			total += cost
		return total

	def get_expected_cost(self, amount):
		children_cost = self.get_expected_children_cost(amount)
		if children_cost is None:
			return None

		production_needed = (amount - self.get_root_production_level()) * self.production_ratio
		root_cost = self.abstract_building.get_expected_cost(self.resource_id, production_needed, self.settlement_manager)
		if root_cost is None:
			return None
		return children_cost + root_cost

	def get_root_production_level(self):
		""" returns the production level currently available to this subtree """
		return self.resource_manager.get_quota(self.identifier, self.resource_id, self.abstract_building.id) / self.production_ratio

	def get_final_production_level(self):
		""" returns the production level at the bottleneck """
		min_child_production = None
		for child in self.children:
			if child.ignore_production:
				continue
			production_level = child.get_final_production_level()
			if min_child_production is None:
				min_child_production = production_level
			else:
				min_child_production = min(min_child_production, production_level)
		if min_child_production is None:
			return self.get_root_production_level()
		else:
			return min(min_child_production, self.get_root_production_level())

	def need_more_buildings(self, amount):
		if not self.abstract_building.directly_buildable:
			return False # building must be triggered by children instead
		if self.abstract_building.coverage_building:
			return True
		return amount > self.get_root_production_level() + 1e-7

	def build(self, amount):
		# try to build one of the lower level buildings
		result = None
		for child in self.children:
			result = child.build(amount)
			if result == BUILD_RESULT.ALL_BUILT:
				continue # build another child or build this building
			elif result == BUILD_RESULT.NEED_PARENT_FIRST:
				break # parent building has to be built before child (example: farm before field)
			else:
				return result # an error or successful building

		if result == BUILD_RESULT.NEED_PARENT_FIRST or self.need_more_buildings(amount):
			if not self.settlement_manager.feeder_island and len(self.settlement_manager.owner.settlement_managers) > 1:
				if self.resource_id == RES.FOOD_ID:
					return BUILD_RESULT.ALL_BUILT # hack to force some resources to be produced on a feeder island

			# build a building
			(result, building) = self.abstract_building.build(self.settlement_manager, self.resource_id)
			if result == BUILD_RESULT.OUT_OF_SETTLEMENT:
				return self.settlement_manager.production_builder.extend_settlement(building)
			return result
		return BUILD_RESULT.ALL_BUILT

	def reserve(self, amount, may_import):
		"""
		Reserves currently available production and imports from other islands if allowed
		Returns the total amount it can reserve or import
		"""
		total_reserved = amount
		for child in self.children:
			total_reserved = min(total_reserved, child.reserve(amount, may_import))

		self.resource_manager.request_quota_change(self.identifier, True, self.resource_id, self.abstract_building.id, amount * self.production_ratio)
		total_reserved = min(total_reserved, self.resource_manager.get_quota(self.identifier, self.resource_id, self.abstract_building.id) / self.production_ratio)
		return total_reserved

	def get_ratio(self, resource_id):
		result = self.production_ratio if self.resource_id == resource_id else 0
		return result + sum(child.get_ratio(resource_id) for child in self.children)

decorators.bind_all(ProductionChain)
decorators.bind_all(ProductionChainSubtreeChoice)
decorators.bind_all(ProductionChainSubtree)