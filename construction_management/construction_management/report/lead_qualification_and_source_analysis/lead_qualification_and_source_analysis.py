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
			"label": _("Lead ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Lead",
			"width": 140,
		},
		{
			"label": _("Lead Name"),
			"fieldname": "lead_name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Organization"),
			"fieldname": "company_name",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Source"),
			"fieldname": "utm_source",
			"fieldtype": "Link",
			"options": "UTM Source",
			"width": 140,
		},
		{
			"label": _("Qualification Status"),
			"fieldname": "qualification_status",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("CRM Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Project Type"),
			"fieldname": "custom_project_type",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Project Location"),
			"fieldname": "custom_project_location",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Estimated Value"),
			"fieldname": "custom_estimated_project_value",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Lead Owner"),
			"fieldname": "lead_owner",
			"fieldtype": "Link",
			"options": "User",
			"width": 140,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("company"):
		conditions.append("company = %(company)s")
		values["company"] = filters.get("company")

	if filters.get("source"):
		conditions.append("utm_source = %(source)s")
		values["source"] = filters.get("source")

	if filters.get("qualification_status"):
		conditions.append("qualification_status = %(qualification_status)s")
		values["qualification_status"] = filters.get("qualification_status")

	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters.get("status")

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	query = f"""
		SELECT
			name, lead_name, company_name, utm_source,
			qualification_status, status, custom_project_type,
			custom_project_location, custom_estimated_project_value, lead_owner
		FROM `tabLead`
		{where_clause}
		ORDER BY creation DESC
	"""

	return frappe.db.sql(query, values, as_dict=True)


def get_chart_data(data):
	if not data:
		return None

	source_counts = {}
	for row in data:
		src = row.get("utm_source") or _("Not Specified")
		source_counts[src] = source_counts.get(src, 0) + 1

	labels = list(source_counts.keys())
	values = [source_counts[l] for l in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Lead Count"), "values": values}],
		},
		"type": "donut",
	}


def get_report_summary(data):
	if not data:
		return None

	total = len(data)
	qualified = sum(1 for d in data if d.get("qualification_status") == "Qualified")
	in_process = sum(1 for d in data if d.get("qualification_status") == "In Process")
	unqualified = total - qualified - in_process
	total_value = sum(flt(d.get("custom_estimated_project_value")) for d in data)

	return [
		{"value": total, "label": _("Total Leads"), "datatype": "Int", "indicator": "blue"},
		{
			"value": qualified,
			"label": _("Qualified Leads"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": in_process,
			"label": _("In Process"),
			"datatype": "Int",
			"indicator": "orange",
		},
		{
			"value": unqualified,
			"label": _("Unqualified / Disqualified"),
			"datatype": "Int",
			"indicator": "red",
		},
		{
			"value": total_value,
			"label": _("Total Estimated Pipeline"),
			"datatype": "Currency",
			"indicator": "grey",
		},
	]
