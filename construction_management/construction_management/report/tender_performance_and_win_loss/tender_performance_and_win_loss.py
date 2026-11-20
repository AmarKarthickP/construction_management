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
			"label": _("Tender ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Tender",
			"width": 140,
		},
		{
			"label": _("Tender Title"),
			"fieldname": "tender_title",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Opportunity"),
			"fieldname": "opportunity",
			"fieldtype": "Link",
			"options": "Opportunity",
			"width": 140,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 140,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 140,
		},
		{
			"label": _("Status"),
			"fieldname": "workflow_state",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Bid Decision"),
			"fieldname": "bid_decision",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Submission Deadline"),
			"fieldname": "submission_deadline",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"label": _("Estimated Value"),
			"fieldname": "estimated_contract_value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Awarded Value"),
			"fieldname": "awarded_contract_value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Award Date"),
			"fieldname": "award_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Lost Reason"),
			"fieldname": "lost_reason",
			"fieldtype": "Link",
			"options": "Tender Lost Reason",
			"width": 150,
		},
		{
			"label": _("Tender Owner"),
			"fieldname": "tender_owner",
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

	if filters.get("workflow_state"):
		conditions.append("workflow_state = %(workflow_state)s")
		values["workflow_state"] = filters.get("workflow_state")

	if filters.get("bid_decision"):
		conditions.append("bid_decision = %(bid_decision)s")
		values["bid_decision"] = filters.get("bid_decision")

	if filters.get("from_date"):
		conditions.append("invitation_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("invitation_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	query = f"""
		SELECT
			name, tender_title, opportunity, customer, company,
			workflow_state, bid_decision, submission_deadline,
			estimated_contract_value, awarded_contract_value,
			award_date, lost_reason, tender_owner, currency
		FROM `tabTender`
		{where_clause}
		ORDER BY creation DESC
	"""

	return frappe.db.sql(query, values, as_dict=True)


def get_chart_data(data):
	if not data:
		return None

	state_counts = {}
	for row in data:
		st = row.get("workflow_state") or "Draft"
		state_counts[st] = state_counts.get(st, 0) + 1

	labels = list(state_counts.keys())
	values = [state_counts[l] for l in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Tender Count"), "values": values}],
		},
		"type": "bar",
	}


def get_report_summary(data):
	if not data:
		return None

	total_tenders = len(data)
	won_count = sum(1 for d in data if d.get("workflow_state") == "Won")
	lost_count = sum(1 for d in data if d.get("workflow_state") in ["Lost", "No-Bid / Closed"])
	total_estimated_value = sum(flt(d.get("estimated_contract_value")) for d in data)
	total_awarded_value = sum(flt(d.get("awarded_contract_value")) for d in data)

	decided = won_count + lost_count
	win_rate = (won_count / decided * 100) if decided > 0 else 0

	return [
		{
			"value": total_tenders,
			"label": _("Total Tenders"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_estimated_value,
			"label": _("Total Estimated Value"),
			"datatype": "Currency",
			"indicator": "grey",
		},
		{
			"value": won_count,
			"label": _("Won Tenders"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": lost_count,
			"label": _("Lost / No-Bid"),
			"datatype": "Int",
			"indicator": "red",
		},
		{
			"value": f"{win_rate:.1f}%",
			"label": _("Win Rate"),
			"datatype": "Data",
			"indicator": "green" if win_rate >= 30 else "orange",
		},
		{
			"value": total_awarded_value,
			"label": _("Total Awarded Value"),
			"datatype": "Currency",
			"indicator": "green",
		},
	]
