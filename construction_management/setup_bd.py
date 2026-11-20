# Copyright (c) 2026, Amar Karthick P and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup_all():
	"""Complete setup of roles, masters, custom fields, and workflow for Business Development."""
	print("Setting up Roles...")
	setup_roles()
	print("Setting up Masters...")
	setup_masters()
	print("Setting up Company Defaults...")
	setup_company_defaults()
	print("Setting up Custom Fields...")
	setup_custom_fields()
	print("Setting up Workflow...")
	setup_workflow()
	frappe.db.commit()
	print("Setup completed successfully.")


def setup_company_defaults():
	"""Ensure BUILDX company has temporary opening account for test record creation."""
	company = "BUILDX Engineering and Contracting"
	if not frappe.db.exists("Company", company):
		return

	# Group account: Temporary Accounts
	group_acc = f"Temporary Accounts - BEAC"
	if not frappe.db.exists("Account", group_acc):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Temporary Accounts",
				"company": company,
				"parent_account": "Current Assets - BEAC",
				"root_type": "Asset",
				"is_group": 1,
			}
		).insert(ignore_permissions=True)

	# Child account: Temporary Opening
	opening_acc = f"Temporary Opening - BEAC"
	if not frappe.db.exists("Account", opening_acc):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Temporary Opening",
				"company": company,
				"parent_account": group_acc,
				"root_type": "Asset",
				"account_type": "Temporary",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)


def setup_roles():
	"""Create custom roles for BUILDX if not present and grant to Administrator."""
	roles = [
		{"role_name": "Management Approver", "desk_access": 1},
		{"role_name": "QS / Estimation", "desk_access": 1},
	]
	for r in roles:
		if not frappe.db.exists("Role", r["role_name"]):
			role = frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": r["role_name"],
					"desk_access": r.get("desk_access", 1),
				}
			)
			role.insert(ignore_permissions=True)

	# Ensure Administrator has these roles
	if frappe.db.exists("User", "Administrator"):
		admin_roles = frappe.get_roles("Administrator")
		admin_user = frappe.get_doc("User", "Administrator")
		for r in ["Management Approver", "QS / Estimation"]:
			if r not in admin_roles:
				admin_user.add_roles(r)


def setup_masters():
	"""Seed UTM Sources and Tender Lost Reasons."""
	# 1. UTM Sources
	sources = [
		"Direct client enquiry",
		"Public or government tender announcements",
		"Private construction companies",
		"Consultants and architects",
		"Existing customer referrals",
		"Website enquiries",
		"Business development networking",
	]
	for s in sources:
		if not frappe.db.exists("UTM Source", s):
			doc = frappe.get_doc({"doctype": "UTM Source", "name": s, "source": s})
			doc.insert(ignore_permissions=True)

	# 2. Tender Lost Reasons
	lost_reasons = [
		("Price Higher than Budget", "Commercial price was above client budget"),
		("Competitor Commercial Advantage", "Competitor offered more aggressive commercial terms"),
		("Client Budget Cancelled", "Client cancelled or deferred project funding"),
		("Technical / Specification Deviation", "Technical non-compliance or specification variance"),
		("Delivery Schedule Not Acceptable", "Proposed construction schedule was unacceptable"),
		("Insufficient Resources", "Resource constraints precluded competitive bidding"),
		("Contract Terms Unacceptable", "Onerous contract conditions / liquidated damages"),
		("Client Selected Another Contractor", "Client awarded to another contractor"),
		("Other", "Other commercial or strategic considerations"),
	]
	for reason, desc in lost_reasons:
		if not frappe.db.exists("Tender Lost Reason", reason):
			doc = frappe.get_doc(
				{
					"doctype": "Tender Lost Reason",
					"reason_name": reason,
					"description": desc,
					"is_active": 1,
				}
			)
			doc.insert(ignore_permissions=True)

	# 3. Sales Stage "Tender"
	if not frappe.db.exists("Sales Stage", "Tender"):
		doc = frappe.get_doc({"doctype": "Sales Stage", "stage_name": "Tender"})
		doc.insert(ignore_permissions=True)


def setup_custom_fields():
	"""Define custom fields on Lead and Opportunity with standard 'custom_' prefix."""
	project_type_options = (
		"Building Construction\n"
		"Civil Works\n"
		"Infrastructure\n"
		"Industrial Construction\n"
		"Renovation\n"
		"Other"
	)

	# Clean up obsolete custom fields if they exist
	old_fields = [
		("Lead", "cm_construction_section"),
		("Lead", "project_type"),
		("Lead", "project_location"),
		("Lead", "estimated_project_value"),
		("Lead", "cm_col_break_1"),
		("Lead", "expected_project_start"),
		("Lead", "project_duration_months"),
		("Lead", "project_description"),
		("Opportunity", "cm_construction_section"),
		("Opportunity", "project_type"),
		("Opportunity", "project_location"),
		("Opportunity", "client_decision_maker"),
		("Opportunity", "cm_col_break_1"),
		("Opportunity", "expected_project_start"),
		("Opportunity", "project_duration_months"),
		("Opportunity", "expected_tender_date"),
		("Opportunity", "competitor_information"),
		("Opportunity", "project_description"),
		("Opportunity", "cm_tender_summary_section"),
		("Opportunity", "cm_total_tenders"),
		("Opportunity", "cm_active_tenders"),
		("Opportunity", "cm_submitted_tenders"),
		("Opportunity", "cm_col_break_2"),
		("Opportunity", "cm_won_tenders"),
		("Opportunity", "cm_lost_tenders"),
		("Opportunity", "cm_total_submitted_value"),
	]
	for dt, fn in old_fields:
		cf_name = f"{dt}-{fn}"
		if frappe.db.exists("Custom Field", cf_name):
			frappe.delete_doc("Custom Field", cf_name, ignore_permissions=True)

	custom_fields = {
		"Lead": [
			{
				"fieldname": "custom_construction_details_section",
				"label": "Construction Project Details",
				"fieldtype": "Section Break",
				"insert_after": "qualification_tab",
			},
			{
				"fieldname": "custom_project_type",
				"label": "Project Type",
				"fieldtype": "Select",
				"options": project_type_options,
				"insert_after": "custom_construction_details_section",
			},
			{
				"fieldname": "custom_project_location",
				"label": "Project Location",
				"fieldtype": "Data",
				"insert_after": "custom_project_type",
			},
			{
				"fieldname": "custom_estimated_project_value",
				"label": "Estimated Project Value",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"insert_after": "custom_project_location",
			},
			{
				"fieldname": "custom_col_break_1",
				"fieldtype": "Column Break",
				"insert_after": "custom_estimated_project_value",
			},
			{
				"fieldname": "custom_expected_project_start",
				"label": "Expected Project Start",
				"fieldtype": "Date",
				"insert_after": "custom_col_break_1",
			},
			{
				"fieldname": "custom_project_duration_months",
				"label": "Project Duration (Months)",
				"fieldtype": "Int",
				"insert_after": "custom_expected_project_start",
			},
			{
				"fieldname": "custom_project_description",
				"label": "Project Description",
				"fieldtype": "Text Editor",
				"insert_after": "custom_project_duration_months",
			},
		],
		"Opportunity": [
			{
				"fieldname": "custom_construction_details_section",
				"label": "Construction Project Details",
				"fieldtype": "Section Break",
				"insert_after": "items_section",
			},
			{
				"fieldname": "custom_project_type",
				"label": "Project Type",
				"fieldtype": "Select",
				"options": project_type_options,
				"insert_after": "custom_construction_details_section",
			},
			{
				"fieldname": "custom_project_location",
				"label": "Project Location",
				"fieldtype": "Data",
				"insert_after": "custom_project_type",
			},
			{
				"fieldname": "custom_client_decision_maker",
				"label": "Client Decision Maker",
				"fieldtype": "Data",
				"insert_after": "custom_project_location",
			},
			{
				"fieldname": "custom_col_break_1",
				"fieldtype": "Column Break",
				"insert_after": "custom_client_decision_maker",
			},
			{
				"fieldname": "custom_expected_project_start",
				"label": "Expected Project Start",
				"fieldtype": "Date",
				"insert_after": "custom_col_break_1",
			},
			{
				"fieldname": "custom_project_duration_months",
				"label": "Project Duration (Months)",
				"fieldtype": "Int",
				"insert_after": "custom_expected_project_start",
			},
			{
				"fieldname": "custom_expected_tender_date",
				"label": "Expected Tender Date",
				"fieldtype": "Date",
				"insert_after": "custom_project_duration_months",
			},
			{
				"fieldname": "custom_competitor_information",
				"label": "Competitor Information",
				"fieldtype": "Small Text",
				"insert_after": "custom_expected_tender_date",
			},
			{
				"fieldname": "custom_project_description",
				"label": "Project Description",
				"fieldtype": "Text Editor",
				"insert_after": "custom_competitor_information",
			},
			{
				"fieldname": "custom_tender_summary_section",
				"label": "Tender Pipeline Summary",
				"fieldtype": "Section Break",
				"insert_after": "custom_project_description",
			},
			{
				"fieldname": "custom_total_tenders",
				"label": "Total Tenders",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "custom_tender_summary_section",
			},
			{
				"fieldname": "custom_active_tenders",
				"label": "Active Tenders",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "custom_total_tenders",
			},
			{
				"fieldname": "custom_submitted_tenders",
				"label": "Submitted Tenders",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "custom_active_tenders",
			},
			{
				"fieldname": "custom_col_break_2",
				"fieldtype": "Column Break",
				"insert_after": "custom_submitted_tenders",
			},
			{
				"fieldname": "custom_won_tenders",
				"label": "Won Tenders",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "custom_col_break_2",
			},
			{
				"fieldname": "custom_lost_tenders",
				"label": "Lost Tenders",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "custom_won_tenders",
			},
			{
				"fieldname": "custom_total_submitted_value",
				"label": "Total Submitted Value",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"read_only": 1,
				"insert_after": "custom_lost_tenders",
			},
		],
	}

	create_custom_fields(custom_fields, ignore_validate=True)


def setup_workflow():
	"""Configure Tender Lifecycle Workflow in Frappe."""
	states = [
		"Draft",
		"Under Evaluation",
		"Pending Bid Decision",
		"Approved to Bid",
		"No-Bid / Closed",
		"Ready for Submission",
		"Submitted",
		"Awaiting Result",
		"Won",
		"Lost",
		"Cancelled",
		"Withdrawn / Closed",
	]
	for s in states:
		if not frappe.db.exists("Workflow State", s):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s}).insert(
				ignore_permissions=True
			)

	actions = [
		"Submit for Evaluation",
		"Submit for Bid Decision",
		"Approve Bid",
		"Decline Bid (No-Bid)",
		"Prepare Bid Package",
		"Return to Evaluation",
		"Record Submission",
		"Bid Opened",
		"Record Won",
		"Record Lost",
		"Cancel Tender",
		"Client Scrapped / Withdrawn",
	]
	for a in actions:
		if not frappe.db.exists("Workflow Action Master", a):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": a}).insert(
				ignore_permissions=True
			)

	workflow_name = "Tender Lifecycle Workflow"
	if frappe.db.exists("Workflow", workflow_name):
		frappe.delete_doc("Workflow", workflow_name, ignore_permissions=True)

	doc_states = [
		{"state": "Draft", "doc_status": "0", "allow_edit": "Sales User"},
		{"state": "Under Evaluation", "doc_status": "0", "allow_edit": "QS / Estimation"},
		{"state": "Pending Bid Decision", "doc_status": "0", "allow_edit": "Management Approver"},
		{"state": "Approved to Bid", "doc_status": "0", "allow_edit": "Management Approver"},
		{"state": "No-Bid / Closed", "doc_status": "0", "allow_edit": "Management Approver"},
		{"state": "Ready for Submission", "doc_status": "0", "allow_edit": "QS / Estimation"},
		{"state": "Submitted", "doc_status": "0", "allow_edit": "Management Approver"},
		{"state": "Awaiting Result", "doc_status": "0", "allow_edit": "Management Approver"},
		{"state": "Won", "doc_status": "0", "allow_edit": "Management Approver"},
		{"state": "Lost", "doc_status": "0", "allow_edit": "Management Approver"},
		{"state": "Cancelled", "doc_status": "0", "allow_edit": "Management Approver"},
		{"state": "Withdrawn / Closed", "doc_status": "0", "allow_edit": "Management Approver"},
	]

	transitions = [
		# Draft transitions
		{
			"state": "Draft",
			"action": "Submit for Evaluation",
			"next_state": "Under Evaluation",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Draft",
			"action": "Submit for Evaluation",
			"next_state": "Under Evaluation",
			"allowed": "QS / Estimation",
			"allow_self_approval": 1,
		},
		{
			"state": "Draft",
			"action": "Submit for Evaluation",
			"next_state": "Under Evaluation",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Draft",
			"action": "Cancel Tender",
			"next_state": "Cancelled",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Draft",
			"action": "Cancel Tender",
			"next_state": "Cancelled",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		# Under Evaluation transitions
		{
			"state": "Under Evaluation",
			"action": "Submit for Bid Decision",
			"next_state": "Pending Bid Decision",
			"allowed": "QS / Estimation",
			"allow_self_approval": 1,
		},
		{
			"state": "Under Evaluation",
			"action": "Submit for Bid Decision",
			"next_state": "Pending Bid Decision",
			"allowed": "Projects Manager",
			"allow_self_approval": 1,
		},
		{
			"state": "Under Evaluation",
			"action": "Submit for Bid Decision",
			"next_state": "Pending Bid Decision",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Under Evaluation",
			"action": "Cancel Tender",
			"next_state": "Cancelled",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		# Pending Bid Decision transitions (Management Approver ONLY)
		{
			"state": "Pending Bid Decision",
			"action": "Approve Bid",
			"next_state": "Approved to Bid",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Pending Bid Decision",
			"action": "Decline Bid (No-Bid)",
			"next_state": "No-Bid / Closed",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Pending Bid Decision",
			"action": "Cancel Tender",
			"next_state": "Cancelled",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		# Approved to Bid transitions
		{
			"state": "Approved to Bid",
			"action": "Prepare Bid Package",
			"next_state": "Ready for Submission",
			"allowed": "QS / Estimation",
			"allow_self_approval": 1,
		},
		{
			"state": "Approved to Bid",
			"action": "Prepare Bid Package",
			"next_state": "Ready for Submission",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Approved to Bid",
			"action": "Prepare Bid Package",
			"next_state": "Ready for Submission",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Approved to Bid",
			"action": "Return to Evaluation",
			"next_state": "Under Evaluation",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Approved to Bid",
			"action": "Cancel Tender",
			"next_state": "Cancelled",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		# Ready for Submission transitions
		{
			"state": "Ready for Submission",
			"action": "Record Submission",
			"next_state": "Submitted",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Ready for Submission",
			"action": "Record Submission",
			"next_state": "Submitted",
			"allowed": "QS / Estimation",
			"allow_self_approval": 1,
		},
		{
			"state": "Ready for Submission",
			"action": "Record Submission",
			"next_state": "Submitted",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Ready for Submission",
			"action": "Return to Evaluation",
			"next_state": "Under Evaluation",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Ready for Submission",
			"action": "Cancel Tender",
			"next_state": "Cancelled",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		# Submitted transitions
		{
			"state": "Submitted",
			"action": "Record Won",
			"next_state": "Won",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Submitted",
			"action": "Record Won",
			"next_state": "Won",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Submitted",
			"action": "Record Lost",
			"next_state": "Lost",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Submitted",
			"action": "Record Lost",
			"next_state": "Lost",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Submitted",
			"action": "Bid Opened",
			"next_state": "Awaiting Result",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Submitted",
			"action": "Bid Opened",
			"next_state": "Awaiting Result",
			"allowed": "QS / Estimation",
			"allow_self_approval": 1,
		},
		{
			"state": "Submitted",
			"action": "Bid Opened",
			"next_state": "Awaiting Result",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Submitted",
			"action": "Client Scrapped / Withdrawn",
			"next_state": "Withdrawn / Closed",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		# Awaiting Result transitions
		{
			"state": "Awaiting Result",
			"action": "Record Won",
			"next_state": "Won",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Awaiting Result",
			"action": "Record Won",
			"next_state": "Won",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Awaiting Result",
			"action": "Record Lost",
			"next_state": "Lost",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
		{
			"state": "Awaiting Result",
			"action": "Record Lost",
			"next_state": "Lost",
			"allowed": "Sales User",
			"allow_self_approval": 1,
		},
		{
			"state": "Awaiting Result",
			"action": "Client Scrapped / Withdrawn",
			"next_state": "Withdrawn / Closed",
			"allowed": "Management Approver",
			"allow_self_approval": 1,
		},
	]

	wf = frappe.get_doc(
		{
			"doctype": "Workflow",
			"workflow_name": workflow_name,
			"document_type": "Tender",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"override_status": 0,
			"states": doc_states,
			"transitions": transitions,
		}
	)
	wf.insert(ignore_permissions=True)
