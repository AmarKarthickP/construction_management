# Copyright (c) 2026, Amar Karthick P and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Opportunity ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Opportunity",
			"width": 140,
		},
		{
			"label": _("Title"),
			"fieldname": "title",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Party Name"),
			"fieldname": "party_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 140,
		},
		{
			"label": _("Sales Stage"),
			"fieldname": "sales_stage",
			"fieldtype": "Link",
			"options": "Sales Stage",
			"width": 120,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Project Type"),
			"fieldname": "custom_project_type",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Opportunity Amount"),
			"fieldname": "opportunity_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"label": _("Total Tenders"),
			"fieldname": "custom_total_tenders",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Active Tenders"),
			"fieldname": "custom_active_tenders",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Won Tenders"),
			"fieldname": "custom_won_tenders",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Submitted Tender Value"),
			"fieldname": "custom_total_submitted_value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("Owner"),
			"fieldname": "opportunity_owner",
			"fieldtype": "Link",
			"options": "User",
			"width": 130,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("company"):
		conditions.append("company = %(company)s")
		values["company"] = filters.get("company")

	if filters.get("sales_stage"):
		conditions.append("sales_stage = %(sales_stage)s")
		values["sales_stage"] = filters.get("sales_stage")

	if filters.get("project_type"):
		conditions.append("custom_project_type = %(project_type)s")
		values["project_type"] = filters.get("project_type")

	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters.get("status")

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	query = f"""
		SELECT
			name, title, party_name, company, sales_stage, status,
			custom_project_type, opportunity_amount, currency,
			custom_total_tenders, custom_active_tenders, custom_won_tenders,
			custom_total_submitted_value, opportunity_owner
		FROM `tabOpportunity`
		{where_clause}
		ORDER BY creation DESC
	"""

	return frappe.db.sql(query, values, as_dict=True)


def get_chart_data(data):
	if not data:
		return None

	stage_totals = {}
	for row in data:
		stage = row.get("sales_stage") or _("Not Assigned")
		stage_totals[stage] = stage_totals.get(stage, 0) + flt(row.get("opportunity_amount"))

	labels = list(stage_totals.keys())
	values = [stage_totals[l] for l in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Pipeline Amount"), "values": values}],
		},
		"type": "bar",
	}


def get_report_summary(data):
	if not data:
		return None

	total_opps = len(data)
	total_amount = sum(flt(d.get("opportunity_amount")) for d in data)
	total_tenders = sum(int(d.get("custom_total_tenders") or 0) for d in data)
	total_active_tenders = sum(int(d.get("custom_active_tenders") or 0) for d in data)
	total_submitted_tender_value = sum(flt(d.get("custom_total_submitted_value")) for d in data)

	return [
		{
			"value": total_opps,
			"label": _("Total Opportunities"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_amount,
			"label": _("Total Opportunity Value"),
			"datatype": "Currency",
			"indicator": "green",
		},
		{
			"value": total_tenders,
			"label": _("Linked Tenders"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_active_tenders,
			"label": _("Active Bidding Packages"),
			"datatype": "Int",
			"indicator": "orange",
		},
		{
			"value": total_submitted_tender_value,
			"label": _("Total Submitted Tender Value"),
			"datatype": "Currency",
			"indicator": "purple",
		},
	]
