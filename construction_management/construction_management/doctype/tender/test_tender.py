# Copyright (c) 2026, Amar Karthick P and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, now_datetime, today

from construction_management.crm.opportunity import create_tender_from_opportunity
from erpnext.crm.doctype.lead.lead import make_opportunity


class TestTender(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		frappe.local.test_objects["Tender"] = []
		super().setUpClass()

	def setUp(self):
		super().setUp()
		self.company = "BUILDX Engineering and Contracting"
		if not frappe.db.exists("Company", self.company):
			self.company = frappe.get_all("Company", limit=1)[0].name

		# Ensure custom roles exist
		for r in ["Management Approver", "QS / Estimation"]:
			if not frappe.db.exists("Role", r):
				frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(
					ignore_permissions=True
				)

		# Ensure test items exist for Opportunity Items
		self.setup_test_items()

		# Ensure test users
		self.setup_test_users()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def setup_test_items(self):
		"""Ensure standard non-stock/service items exist for construction activities."""
		items = [
			("EXCAVATION", "Excavation Work", "Cubic Meter"),
			("CONCRETE", "Concrete Work", "Cubic Meter"),
			("STEEL", "Structural Steel", "Metric Ton"),
			("MASONRY", "Blockwork", "Square Meter"),
		]
		for code, name, uom in items:
			if not frappe.db.exists("UOM", uom):
				frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert(ignore_permissions=True)
			if not frappe.db.exists("Item", code):
				doc = frappe.get_doc(
					{
						"doctype": "Item",
						"item_code": code,
						"item_name": name,
						"item_group": "All Item Groups",
						"stock_uom": uom,
						"is_stock_item": 0,
					}
				)
				doc.insert(ignore_permissions=True)

	def setup_test_users(self):
		"""Create test users for role verification."""
		# 1. Management Approver user
		if not frappe.db.exists("User", "test_ceo@buildx.ae"):
			u = frappe.get_doc(
				{
					"doctype": "User",
					"email": "test_ceo@buildx.ae",
					"first_name": "Test",
					"last_name": "CEO",
					"roles": [{"role": "Management Approver"}, {"role": "Desk User"}],
				}
			)
			u.insert(ignore_permissions=True)

		# 2. Sales User
		if not frappe.db.exists("User", "test_sales@buildx.ae"):
			u = frappe.get_doc(
				{
					"doctype": "User",
					"email": "test_sales@buildx.ae",
					"first_name": "Test",
					"last_name": "Sales",
					"roles": [{"role": "Sales User"}, {"role": "Desk User"}],
				}
			)
			u.insert(ignore_permissions=True)

	def create_test_lead(self, qualified=False):
		"""Helper to create a Lead with construction fields."""
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": f"Test Client {frappe.generate_hash(length=6)}",
				"email_id": f"client_{frappe.generate_hash(length=6)}@example.com",
				"company": self.company,
				"utm_source": "Direct client enquiry",
				"qualification_status": "Qualified" if qualified else "In Process",
				"custom_project_type": "Building Construction",
				"custom_project_location": "Downtown Dubai, Plot 102",
				"custom_estimated_project_value": 5000000.0,
				"custom_expected_project_start": add_days(today(), 60),
				"custom_project_duration_months": 18,
				"custom_project_description": "Construction of G+12 Commercial Building",
			}
		)
		lead.insert(ignore_permissions=True)
		return lead

	def create_test_opportunity(self, with_items=True, from_lead=None):
		"""Helper to create an Opportunity with or without Items."""
		opp_data = {
			"doctype": "Opportunity",
			"company": self.company,
			"opportunity_amount": 5000000.0,
			"currency": "AED",
			"custom_project_type": "Building Construction",
			"custom_project_location": "Downtown Dubai, Plot 102",
			"custom_expected_project_start": add_days(today(), 60),
			"custom_project_duration_months": 18,
			"custom_expected_tender_date": add_days(today(), 20),
			"custom_client_decision_maker": "Eng. Tariq Al Mansoor",
			"custom_competitor_information": "ABC Contracting, Arabtec",
			"custom_project_description": "Commercial Tower G+12 Turnkey Contract",
		}

		if from_lead:
			opp_data["opportunity_from"] = "Lead"
			opp_data["party_name"] = from_lead.name
			opp_data["title"] = from_lead.lead_name
		else:
			opp_data["opportunity_from"] = "Customer"
			customer_name = frappe.db.get_value("Customer", {"disabled": 0}, "name")
			if not customer_name:
				cust = frappe.get_doc(
					{
						"doctype": "Customer",
						"customer_name": f"Cust {frappe.generate_hash(length=4)}",
						"customer_type": "Company",
					}
				).insert(ignore_permissions=True)
				customer_name = cust.name
			opp_data["party_name"] = customer_name
			opp_data["title"] = f"Opportunity {frappe.generate_hash(length=5)}"

		if with_items:
			opp_data["items"] = [
				{
					"item_code": "EXCAVATION",
					"item_name": "Excavation Work",
					"description": "Mass excavation and shoring",
					"qty": 500.0,
					"uom": "Cubic Meter",
					"rate": 25.0,
					"amount": 12500.0,
				},
				{
					"item_code": "CONCRETE",
					"item_name": "Concrete Work",
					"description": "Reinforced concrete works",
					"qty": 200.0,
					"uom": "Cubic Meter",
					"rate": 350.0,
					"amount": 70000.0,
				},
				{
					"item_code": "STEEL",
					"item_name": "Structural Steel",
					"description": "Fabrication and erection",
					"qty": 20.0,
					"uom": "Metric Ton",
					"rate": 3500.0,
					"amount": 70000.0,
				},
				{
					"item_code": "MASONRY",
					"item_name": "Blockwork",
					"description": "Hollow concrete blocks 200mm",
					"qty": 1000.0,
					"uom": "Square Meter",
					"rate": 85.0,
					"amount": 85000.0,
				},
			]
			opp_data["opportunity_amount"] = 237500.0

		opp = frappe.get_doc(opp_data)
		opp.insert(ignore_permissions=True)
		return opp

	def advance_to_state(self, tender, target_state):
		"""Helper to transition Tender through valid Workflow states."""
		if tender.workflow_state == target_state:
			return

		states_order = [
			"Draft",
			"Under Evaluation",
			"Pending Bid Decision",
			"Approved to Bid",
			"Ready for Submission",
			"Submitted",
			"Awaiting Result",
		]

		current_idx = states_order.index(tender.workflow_state)
		target_idx = states_order.index(target_state)

		for i in range(current_idx + 1, target_idx + 1):
			next_st = states_order[i]
			if next_st == "Under Evaluation":
				tender.workflow_state = "Under Evaluation"
				tender.save()
			elif next_st == "Pending Bid Decision":
				tender.technical_feasibility = "Feasible"
				tender.resource_availability = "Available"
				tender.commercial_feasibility = "Feasible"
				tender.risk_assessment = "Low"
				tender.recommended_decision = "Bid"
				if not tender.evaluations:
					tender.append(
						"evaluations",
						{
							"evaluation_area": "Technical",
							"evaluated_by": "Administrator",
							"rating": "Good",
							"remarks": "Compliant",
							"evaluation_date": today(),
						},
					)
				tender.workflow_state = "Pending Bid Decision"
				tender.save()
			elif next_st == "Approved to Bid":
				frappe.set_user("test_ceo@buildx.ae")
				tender.workflow_state = "Approved to Bid"
				tender.save()
				frappe.set_user("Administrator")
			elif next_st == "Ready for Submission":
				tender.workflow_state = "Ready for Submission"
				tender.save()
			elif next_st == "Submitted":
				tender.workflow_state = "Submitted"
				tender.save()
			elif next_st == "Awaiting Result":
				tender.workflow_state = "Awaiting Result"
				tender.save()

	# -------------------------------------------------------------
	# Test Scenarios
	# -------------------------------------------------------------

	def test_01_lead_creation_and_custom_fields(self):
		"""1. Verify Lead creation with construction-specific custom fields."""
		lead = self.create_test_lead(qualified=False)
		self.assertEqual(lead.custom_project_type, "Building Construction")
		self.assertEqual(lead.custom_project_location, "Downtown Dubai, Plot 102")
		self.assertEqual(flt(lead.custom_estimated_project_value), 5000000.0)
		self.assertEqual(lead.custom_project_duration_months, 18)
		self.assertIn("G+12 Commercial Building", lead.custom_project_description)

	def test_02_unqualified_lead_cannot_be_converted_to_opportunity(self):
		"""2. Verify server-side gate blocks conversion of Unqualified Leads."""
		unqualified_lead = self.create_test_lead(qualified=False)
		unqualified_lead.qualification_status = "In Process"
		unqualified_lead.save()

		# Attempting to save an Opportunity referencing this unqualified Lead must fail
		opp = frappe.get_doc(
			{
				"doctype": "Opportunity",
				"opportunity_from": "Lead",
				"party_name": unqualified_lead.name,
				"company": self.company,
				"title": "Premature Opportunity",
			}
		)
		self.assertRaises(frappe.ValidationError, opp.insert)

	def test_03_qualified_lead_can_be_converted_to_opportunity(self):
		"""3. Verify Lead conversion succeeds when qualification_status is Qualified."""
		qualified_lead = self.create_test_lead(qualified=True)
		opp_doc = make_opportunity(qualified_lead.name)
		opp_doc.company = self.company
		opp_doc.insert()

		self.assertEqual(opp_doc.opportunity_from, "Lead")
		self.assertEqual(opp_doc.party_name, qualified_lead.name)
		self.assertEqual(opp_doc.custom_project_type, qualified_lead.custom_project_type)
		self.assertEqual(opp_doc.custom_project_location, qualified_lead.custom_project_location)

	def test_04_create_opportunity_items_preliminary_scope(self):
		"""4. Verify preliminary scope using standard Opportunity Items table."""
		opp = self.create_test_opportunity(with_items=True)
		self.assertEqual(len(opp.items), 4)
		total_amount = sum(flt(d.amount) for d in opp.items)
		self.assertEqual(total_amount, 237500.0)

	def test_05_create_opportunity_without_items(self):
		"""5. Verify an Opportunity can exist without Items."""
		opp = self.create_test_opportunity(with_items=False)
		self.assertEqual(len(opp.get("items", [])), 0)
		self.assertTrue(opp.name)

	def test_06_create_tender_from_opportunity_and_snapshot(self):
		"""6 & 7. Create Tender from Opportunity and verify field mapping & scope snapshot."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)

		self.assertEqual(res.get("status"), "success")
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		self.assertEqual(tender.opportunity, opp.name)
		self.assertEqual(tender.company, opp.company)
		self.assertEqual(tender.project_type, opp.custom_project_type)
		self.assertEqual(tender.project_location, opp.custom_project_location)
		self.assertEqual(tender.currency, opp.currency)
		self.assertEqual(flt(tender.estimated_contract_value), flt(opp.opportunity_amount))
		self.assertEqual(tender.workflow_state, "Draft")

		# Check Preliminary Scope snapshot
		self.assertEqual(len(tender.preliminary_scope_items), len(opp.items))
		first_item = tender.preliminary_scope_items[0]
		self.assertEqual(first_item.item_code, "EXCAVATION")
		self.assertEqual(flt(first_item.qty), 500.0)
		self.assertEqual(flt(first_item.estimated_rate), 25.0)
		self.assertEqual(flt(first_item.amount), 12500.0)

	def test_07_scope_snapshot_independence(self):
		"""8. Verify snapshot independence: editing Tender does not affect Opportunity and vice versa."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		# Add a new item to Opportunity (reload first)
		opp.reload()
		opp.append(
			"items",
			{
				"item_code": "EXCAVATION",
				"qty": 100.0,
				"rate": 20.0,
				"amount": 2000.0,
			},
		)
		opp.save()

		# Reload Tender and verify snapshot unchanged
		tender.reload()
		self.assertEqual(len(tender.preliminary_scope_items), 4)

	def test_08_draft_reuse_guard(self):
		"""9. Verify Draft Reuse Guard opens existing Draft without creating duplicates."""
		opp = self.create_test_opportunity(with_items=True)
		res1 = create_tender_from_opportunity(opp.name)
		first_tender_name = res1.get("tender_name")

		# Second click without package title should reuse draft
		res2 = create_tender_from_opportunity(opp.name)
		self.assertEqual(res2.get("status"), "reuse")
		self.assertEqual(res2.get("tender_name"), first_tender_name)

		# Ensure total tenders count for this opportunity is still 1
		count = frappe.db.count("Tender", {"opportunity": opp.name})
		self.assertEqual(count, 1)

	def test_09_multiple_tenders_with_distinct_package_titles(self):
		"""10. Verify multiple Tenders can be created from one Opportunity with distinct package titles."""
		opp = self.create_test_opportunity(with_items=True)

		# Package 1: Civil & Structural
		res1 = create_tender_from_opportunity(opp.name, package_title="Package A - Civil & Structural")
		self.assertEqual(res1.get("status"), "success")

		# Package 2: MEP & HVAC
		res2 = create_tender_from_opportunity(opp.name, package_title="Package B - MEP & HVAC")
		self.assertEqual(res2.get("status"), "success")

		self.assertNotEqual(res1.get("tender_name"), res2.get("tender_name"))
		tenders_count = frappe.db.count("Tender", {"opportunity": opp.name})
		self.assertEqual(tenders_count, 2)

	def test_10_normalized_title_uniqueness_under_same_opportunity(self):
		"""11. Verify duplicate title check handles whitespace and case differences."""
		opp = self.create_test_opportunity(with_items=True)
		create_tender_from_opportunity(opp.name, package_title="Fitout Works Package")

		# Attempting same title with extra spaces and mixed casing should be blocked
		self.assertRaises(
			frappe.DuplicateEntryError,
			create_tender_from_opportunity,
			opp.name,
			package_title="  fitout   works   package  ",
		)

	def test_11_tender_reference_uniqueness_within_company(self):
		"""12. Verify Tender Reference uniqueness within Company."""
		opp = self.create_test_opportunity(with_items=True)
		res1 = create_tender_from_opportunity(opp.name, package_title="Ref Test Package 1")
		t1 = frappe.get_doc("Tender", res1.get("tender_name"))
		t1.tender_reference = "REF-2026-BUILDX-001"
		t1.save()

		res2 = create_tender_from_opportunity(opp.name, package_title="Ref Test Package 2")
		t2 = frappe.get_doc("Tender", res2.get("tender_name"))
		t2.tender_reference = "REF-2026-BUILDX-001"

		self.assertRaises(frappe.DuplicateEntryError, t2.save)

	def test_12_strict_evaluation_gate_blocks_incomplete_tender(self):
		"""13 & 14. Verify evaluation gate blocks submission for Bid Decision with Pending assessments."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		tender.workflow_state = "Under Evaluation"
		tender.save()

		# Attempt to move to Pending Bid Decision without completing feasibility
		tender.workflow_state = "Pending Bid Decision"
		self.assertRaises(frappe.ValidationError, tender.save)

		# Set feasibility but leave evaluations empty
		tender.technical_feasibility = "Feasible"
		tender.resource_availability = "Available"
		tender.commercial_feasibility = "Feasible"
		tender.risk_assessment = "Medium"
		tender.recommended_decision = "Bid"

		# Should still fail because len(evaluations) == 0
		self.assertRaises(frappe.ValidationError, tender.save)

	def test_13_strict_evaluation_gate_blocks_on_further_review(self):
		"""15. Verify evaluation gate blocks when Recommended Decision is 'Further Review'."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		tender.technical_feasibility = "Feasible"
		tender.resource_availability = "Available"
		tender.commercial_feasibility = "Feasible"
		tender.risk_assessment = "Medium"
		tender.recommended_decision = "Further Review"
		tender.append(
			"evaluations",
			{
				"evaluation_area": "Technical",
				"evaluated_by": "Administrator",
				"rating": "Good",
				"remarks": "Feasibility verified",
				"evaluation_date": today(),
			},
		)

		tender.workflow_state = "Pending Bid Decision"
		self.assertRaises(frappe.ValidationError, tender.save)

	def test_14_evaluation_gate_success_and_evaluator_stamp(self):
		"""16. Verify successful transition to Pending Bid Decision automatically stamps evaluator."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		tender.workflow_state = "Under Evaluation"
		tender.save()

		tender.technical_feasibility = "Feasible"
		tender.resource_availability = "Available"
		tender.commercial_feasibility = "Feasible"
		tender.risk_assessment = "Low"
		tender.recommended_decision = "Bid"
		tender.append(
			"evaluations",
			{
				"evaluation_area": "Technical",
				"evaluated_by": "Administrator",
				"rating": "Good",
				"remarks": "Fully compliant with specifications",
				"evaluation_date": today(),
			},
		)

		tender.workflow_state = "Pending Bid Decision"
		tender.save()

		tender.reload()
		self.assertEqual(tender.workflow_state, "Pending Bid Decision")
		self.assertEqual(tender.evaluated_by, frappe.session.user)
		self.assertTrue(tender.evaluation_date)

	def test_15_urgent_exception_override(self):
		"""17. Verify Management Approver can authorize urgent exception for fast-track tenders."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))
		tender.workflow_state = "Under Evaluation"
		tender.save()

		# Call authorize_urgent_exception as CEO
		frappe.set_user("test_ceo@buildx.ae")
		tender.authorize_urgent_exception("Urgent tender submission deadline within 24 hours")

		tender.reload()
		self.assertEqual(tender.urgent_exception_authorized, 1)
		self.assertEqual(tender.exception_authorized_by, "test_ceo@buildx.ae")

		# Now transition to Pending Bid Decision succeeds even with pending fields
		tender.workflow_state = "Pending Bid Decision"
		tender.save()
		self.assertEqual(tender.workflow_state, "Pending Bid Decision")

		frappe.set_user("Administrator")

	def test_16_bid_approval_by_management_approver(self):
		"""18 & 19. Verify only Management Approver can approve Bid and stamps are set."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		self.advance_to_state(tender, "Pending Bid Decision")

		# Unauthorized user (Sales User) attempts to approve
		frappe.set_user("test_sales@buildx.ae")
		tender.workflow_state = "Approved to Bid"
		self.assertRaises(frappe.PermissionError, tender.save)

		# Authorized user (Management Approver) approves
		frappe.set_user("test_ceo@buildx.ae")
		tender.reload()
		tender.workflow_state = "Approved to Bid"
		tender.save()

		tender.reload()
		self.assertEqual(tender.workflow_state, "Approved to Bid")
		self.assertEqual(tender.bid_decision, "Bid")
		self.assertEqual(tender.approved_by, "test_ceo@buildx.ae")
		self.assertTrue(tender.approval_date)

		frappe.set_user("Administrator")

	def test_17_no_bid_decline_requires_decision_remarks(self):
		"""20. Verify No-Bid decline requires mandatory decision remarks."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		self.advance_to_state(tender, "Pending Bid Decision")

		frappe.set_user("test_ceo@buildx.ae")
		tender.workflow_state = "No-Bid / Closed"
		tender.decision_remarks = ""  # Missing remarks

		self.assertRaises(frappe.ValidationError, tender.save)

		# With remarks, succeeds
		tender.reload()
		tender.workflow_state = "No-Bid / Closed"
		tender.decision_remarks = "Severe resource constraints and critical liquidity risk."
		tender.save()

		tender.reload()
		self.assertEqual(tender.workflow_state, "No-Bid / Closed")
		self.assertEqual(tender.bid_decision, "No Bid")
		self.assertEqual(tender.approved_by, "test_ceo@buildx.ae")

		frappe.set_user("Administrator")

	def test_18_field_locking_after_bid_approval(self):
		"""21. Verify core commercial fields cannot be modified after approval."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		self.advance_to_state(tender, "Approved to Bid")

		# Attempt to silently change estimated_contract_value in Approved state
		tender.reload()
		tender.estimated_contract_value = 9999999.0
		self.assertRaises(frappe.PermissionError, tender.save)

	def test_19_return_to_evaluation_workflow_action(self):
		"""22. Verify Return to Evaluation creates amendment log and resets approvals."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		self.advance_to_state(tender, "Approved to Bid")

		# Management returns tender to evaluation
		frappe.set_user("test_ceo@buildx.ae")
		tender.return_to_evaluation("Client issued Addendum 3 with 30% scope increase")

		tender.reload()
		self.assertEqual(tender.workflow_state, "Under Evaluation")
		self.assertIsNone(tender.approved_by)
		self.assertEqual(tender.bid_decision, "Pending")
		self.assertEqual(len(tender.amendment_logs), 1)
		self.assertEqual(tender.amendment_logs[0].action_type, "Return to Evaluation")
		self.assertIn("Addendum 3", tender.amendment_logs[0].reason)

		frappe.set_user("Administrator")

	def test_20_won_and_lost_outcome_validations(self):
		"""23. Verify Won and Lost outcome validations and prerequisites."""
		opp = self.create_test_opportunity(with_items=True)
		res = create_tender_from_opportunity(opp.name)
		tender = frappe.get_doc("Tender", res.get("tender_name"))

		# Attempting to record Won before Submission should fail
		self.assertRaises(
			frappe.ValidationError,
			tender.record_won_outcome,
			award_date=today(),
			awarded_contract_value=250000.0,
		)

		# Move to Submitted
		self.advance_to_state(tender, "Submitted")

		# Record Won without value should fail
		self.assertRaises(
			frappe.ValidationError,
			tender.record_won_outcome,
			award_date=today(),
			awarded_contract_value=0.0,
		)
		tender.reload()

		# Valid Won outcome
		tender.record_won_outcome(
			award_date=today(),
			awarded_contract_value=245000.0,
			award_reference="AWARD-LTR-BUILDX-01",
		)
		tender.reload()
		self.assertEqual(tender.workflow_state, "Won")
		self.assertEqual(flt(tender.awarded_contract_value), 245000.0)

	def test_21_opportunity_rollups_calculation(self):
		"""24. Verify Opportunity rollups update accurately on Tender state changes."""
		opp = self.create_test_opportunity(with_items=True)

		# 1. First tender
		res1 = create_tender_from_opportunity(opp.name, package_title="Package 1")
		t1 = frappe.get_doc("Tender", res1.get("tender_name"))
		t1.estimated_contract_value = 100000.0
		t1.save()
		self.advance_to_state(t1, "Submitted")

		# 2. Second tender
		res2 = create_tender_from_opportunity(opp.name, package_title="Package 2")
		t2 = frappe.get_doc("Tender", res2.get("tender_name"))
		t2.estimated_contract_value = 150000.0
		t2.save()

		opp.reload()
		self.assertEqual(opp.custom_total_tenders, 2)
		self.assertEqual(opp.custom_active_tenders, 2)
		self.assertEqual(opp.custom_submitted_tenders, 1)
		self.assertEqual(flt(opp.custom_total_submitted_value), 100000.0)

		# Win first tender
		t1.record_won_outcome(award_date=today(), awarded_contract_value=98000.0)

		opp.reload()
		self.assertEqual(opp.custom_won_tenders, 1)

	def test_22_cross_company_isolation_validation(self):
		"""25. Verify cross-company consistency enforcement."""
		# Other company
		other_company = "Planex Aluminum and Glass"
		if not frappe.db.exists("Company", other_company):
			return  # skip if not present

		opp = self.create_test_opportunity(with_items=True)

		# Attempt to create Tender with mismatched Company
		mismatched_tender = frappe.get_doc(
			{
				"doctype": "Tender",
				"opportunity": opp.name,
				"tender_title": "Cross Company Tender",
				"company": other_company,  # different from Opportunity's company
				"project_type": "Building Construction",
				"tender_type": "Direct Client Invitation",
				"invitation_date": today(),
				"submission_deadline": f"{add_days(today(), 30)} 17:00:00",
				"currency": "AED",
				"estimated_contract_value": 50000.0,
			}
		)
		self.assertRaises(frappe.ValidationError, mismatched_tender.insert)
