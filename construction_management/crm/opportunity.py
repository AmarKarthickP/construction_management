# Copyright (c) 2026, Amar Karthick P and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, now_datetime, today


def validate_lead_qualification(doc, method=None):
	"""Server-side gate: Prevent Opportunity creation from unverified/unqualified Leads."""
	if doc.opportunity_from == "Lead" and doc.party_name:
		qualification_status = frappe.db.get_value("Lead", doc.party_name, "qualification_status")
		if qualification_status != "Qualified":
			frappe.throw(
				_(
					"Lead {0} has qualification status '{1}'. Only leads with status 'Qualified' can be converted to an Opportunity."
				).format(
					frappe.bold(doc.party_name),
					frappe.bold(qualification_status or _("Unqualified")),
				),
				frappe.ValidationError,
			)


def update_opportunity_rollups(opportunity_name):
	"""Calculate and persist linked Tender metrics on the parent Opportunity."""
	if not opportunity_name or not frappe.db.exists("Opportunity", opportunity_name):
		return

	tenders = frappe.get_all(
		"Tender",
		filters={"opportunity": opportunity_name},
		fields=["name", "workflow_state", "estimated_contract_value"],
	)

	total_tenders = len(tenders)
	active_states = [
		"Draft",
		"Under Evaluation",
		"Pending Bid Decision",
		"Approved to Bid",
		"Ready for Submission",
		"Submitted",
		"Awaiting Result",
	]
	submitted_states = ["Submitted", "Awaiting Result", "Won", "Lost", "Withdrawn / Closed"]

	active_count = sum(1 for t in tenders if t.workflow_state in active_states)
	submitted_count = sum(1 for t in tenders if t.workflow_state in submitted_states)
	won_count = sum(1 for t in tenders if t.workflow_state == "Won")
	lost_count = sum(1 for t in tenders if t.workflow_state in ["Lost", "No-Bid / Closed"])
	submitted_value = sum(
		flt(t.estimated_contract_value) for t in tenders if t.workflow_state in submitted_states
	)

	# Update rollup fields directly in DB to avoid triggering loops
	frappe.db.set_value(
		"Opportunity",
		opportunity_name,
		{
			"custom_total_tenders": total_tenders,
			"custom_active_tenders": active_count,
			"custom_submitted_tenders": submitted_count,
			"custom_won_tenders": won_count,
			"custom_lost_tenders": lost_count,
			"custom_total_submitted_value": submitted_value,
		},
		update_modified=False,
	)


@frappe.whitelist()
def create_tender_from_opportunity(opportunity_name, package_title=None):
	"""
	Server-side creation of a Tender from an Opportunity with Draft reuse guard,
	multi-package uniqueness, concurrency locking, and preliminary scope snapshot.
	"""
	if not frappe.has_permission("Tender", "create"):
		frappe.throw(_("You do not have permission to create Tenders."), frappe.PermissionError)

	if not opportunity_name:
		frappe.throw(_("Opportunity name is required."))

	# Acquire a row lock to handle concurrent clicks safely
	frappe.db.sql("SELECT name FROM `tabOpportunity` WHERE name = %s FOR UPDATE", (opportunity_name,))

	opp = frappe.get_doc("Opportunity", opportunity_name)

	# 1. Draft Reuse Guard: If no package_title specified, check for existing Drafts
	if not package_title or not package_title.strip():
		drafts = frappe.get_all(
			"Tender",
			filters={"opportunity": opportunity_name, "workflow_state": "Draft"},
			fields=["name", "tender_title"],
		)

		if len(drafts) == 1:
			return {
				"status": "reuse",
				"tender_name": drafts[0].name,
				"message": _("Existing Draft Tender found: {0} ({1}). Opening Draft.").format(
					drafts[0].tender_title, drafts[0].name
				),
			}
		elif len(drafts) > 1:
			return {
				"status": "select_draft",
				"drafts": drafts,
				"message": _(
					"Multiple Draft Tenders already exist for this Opportunity. Please select one or provide a distinct package title."
				),
			}

	# 2. Determine Tender Title
	if package_title and package_title.strip():
		tender_title = package_title.strip()
	else:
		tender_title = opp.title or opp.customer_name or opp.name

	# 3. Server-side normalized uniqueness check
	normalized_title = " ".join(tender_title.strip().split()).lower()
	existing_title = frappe.db.sql(
		"""
		SELECT name FROM `tabTender`
		WHERE opportunity = %s AND LOWER(TRIM(tender_title)) = %s
		""",
		(opportunity_name, normalized_title),
	)
	if existing_title:
		frappe.throw(
			_("A Tender with the title '{0}' already exists for this Opportunity ({1}).").format(
				tender_title, existing_title[0][0]
			),
			frappe.DuplicateEntryError,
		)

	# 4. Map Fields
	default_currency = (
		opp.currency or frappe.db.get_value("Company", opp.company, "default_currency") or "AED"
	)
	estimated_val = flt(opp.opportunity_amount)

	# Preliminary Scope snapshot from Opportunity Items
	scope_items = []
	items_total = 0.0
	for item in opp.get("items", []):
		row_amount = flt(item.amount) or (flt(item.qty) * flt(item.rate))
		items_total += row_amount
		scope_items.append(
			{
				"doctype": "Tender Preliminary Scope",
				"item_code": item.item_code,
				"item_name": item.item_name or item.item_code,
				"description": item.description,
				"qty": flt(item.qty),
				"uom": item.uom,
				"estimated_rate": flt(item.rate),
				"amount": row_amount,
			}
		)

	if estimated_val <= 0 and items_total > 0:
		estimated_val = items_total

	# Construct Tender document
	tender = frappe.get_doc(
		{
			"doctype": "Tender",
			"opportunity": opp.name,
			"tender_title": tender_title,
			"company": opp.company,
			"customer": opp.party_name if opp.opportunity_from == "Customer" else None,
			"lead": opp.party_name if opp.opportunity_from == "Lead" else None,
			"tender_owner": frappe.session.user,
			"project_type": opp.get("custom_project_type") or opp.get("project_type") or "Building Construction",
			"tender_type": "Direct Client Invitation",
			"workflow_state": "Draft",
			"invitation_date": today(),
			"submission_deadline": f"{add_days(today(), 30)} 17:00:00",
			"currency": default_currency,
			"estimated_contract_value": estimated_val,
			"project_location": opp.get("custom_project_location") or opp.get("project_location"),
			"expected_duration_months": opp.get("custom_project_duration_months") or opp.get("project_duration_months") or 0,
			"scope_description": opp.get("custom_project_description") or opp.get("project_description"),
			"preliminary_scope_items": scope_items,
		}
	)

	tender.insert()

	# If this is the first Tender, automatically set Sales Stage to 'Tender' if stage exists
	existing_tenders_count = frappe.db.count("Tender", {"opportunity": opportunity_name})
	if existing_tenders_count == 1:
		if frappe.db.exists("Sales Stage", "Tender"):
			frappe.db.set_value("Opportunity", opportunity_name, "sales_stage", "Tender")

	# Update rollup metrics
	update_opportunity_rollups(opportunity_name)

	return {
		"status": "success",
		"tender_name": tender.name,
		"message": _("Tender {0} created successfully.").format(tender.name),
	}


def get_dashboard_data(data=None):
	"""Extend standard Opportunity dashboard to display linked Tenders."""
	data = data or {"fieldname": "opportunity", "transactions": []}
	data.setdefault("transactions", []).append(
		{
			"label": _("Bidding"),
			"items": ["Tender"],
		}
	)
	return data
