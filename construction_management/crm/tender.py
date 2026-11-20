# Copyright (c) 2026, Amar Karthick P and contributors
# For license information, please see license.txt

import frappe
from construction_management.crm.opportunity import update_opportunity_rollups


def on_tender_update(doc, method=None):
	"""Sync rollup metrics to parent Opportunity when Tender is saved."""
	if doc.opportunity:
		update_opportunity_rollups(doc.opportunity)


def on_tender_trash(doc, method=None):
	"""Sync rollup metrics to parent Opportunity when Tender is deleted."""
	if doc.opportunity:
		update_opportunity_rollups(doc.opportunity)
