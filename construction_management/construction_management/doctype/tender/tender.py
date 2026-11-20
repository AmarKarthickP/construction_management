# Copyright (c) 2026, Amar Karthick P and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, today


class Tender(Document):
	def validate(self):
		self.validate_company_consistency()
		self.validate_title_uniqueness()
		self.validate_reference_uniqueness()
		self.validate_preliminary_scope_immutability()
		self.validate_workflow_state_transitions()
		self.validate_outcome_details()

	def before_save(self):
		self.handle_workflow_state_side_effects()

	def validate_company_consistency(self):
		"""Ensure linked Opportunity, Customer, and Company match."""
		if not self.company:
			frappe.throw(_("Company is mandatory for Tender."))

		if self.opportunity:
			opp_company = frappe.db.get_value("Opportunity", self.opportunity, "company")
			if opp_company and opp_company != self.company:
				frappe.throw(
					_("Company {0} does not match Opportunity Company {1}.").format(
						frappe.bold(self.company), frappe.bold(opp_company)
					)
				)

			# Auto-fetch Lead and Customer from Opportunity if missing
			opp_details = frappe.db.get_value(
				"Opportunity",
				self.opportunity,
				["party_name", "opportunity_from", "customer_name"],
				as_dict=True,
			)
			if opp_details:
				if opp_details.opportunity_from == "Lead" and not self.lead:
					self.lead = opp_details.party_name
				elif opp_details.opportunity_from == "Customer" and not self.customer:
					self.customer = opp_details.party_name

	def validate_title_uniqueness(self):
		"""Enforce normalized uniqueness of (opportunity, tender_title)."""
		if not self.opportunity or not self.tender_title:
			return

		normalized_title = " ".join(self.tender_title.strip().split()).lower()

		query = """
			SELECT name FROM `tabTender`
			WHERE opportunity = %s
			  AND LOWER(TRIM(tender_title)) = %s
			  AND name != %s
		"""
		existing = frappe.db.sql(query, (self.opportunity, normalized_title, self.name or ""))
		if existing:
			frappe.throw(
				_("A Tender with the title '{0}' already exists for Opportunity {1} ({2}).").format(
					self.tender_title, self.opportunity, existing[0][0]
				),
				frappe.DuplicateEntryError,
			)

	def validate_reference_uniqueness(self):
		"""Validate that Tender Reference is unique within the Company."""
		if not self.tender_reference or not self.company:
			return

		query = """
			SELECT name FROM `tabTender`
			WHERE company = %s
			  AND tender_reference = %s
			  AND name != %s
		"""
		existing = frappe.db.sql(query, (self.company, self.tender_reference.strip(), self.name or ""))
		if existing:
			frappe.throw(
				_("Tender Reference '{0}' is already used in Tender {1} for Company {2}.").format(
					self.tender_reference, existing[0][0], self.company
				),
				frappe.DuplicateEntryError,
			)

	def validate_preliminary_scope_immutability(self):
		"""Lock core commercial and scope fields after approval."""
		if not self.is_new() and self.has_value_changed("workflow_state") is False:
			locked_states = [
				"Approved to Bid",
				"Ready for Submission",
				"Submitted",
				"Awaiting Result",
				"Won",
				"Lost",
				"Cancelled",
				"Withdrawn / Closed",
			]
			if self.workflow_state in locked_states:
				# Check if core commercial fields were modified
				for fld in ["estimated_contract_value", "currency", "company", "opportunity", "project_type"]:
					if self.has_value_changed(fld):
						frappe.throw(
							_("Field '{0}' is locked in state '{1}'. Use 'Return to Evaluation' for commercial amendments.").format(
								self.meta.get_label(fld), self.workflow_state
							),
							frappe.PermissionError,
						)

	def validate_workflow_state_transitions(self):
		"""Validate business rules required for specific workflow transitions."""
		prev_doc = self.get_doc_before_save()
		prev_state = prev_doc.workflow_state if prev_doc else (self.workflow_state or "Draft")
		current_state = self.workflow_state or "Draft"

		# If moving to Pending Bid Decision, validate strict evaluation gate
		if current_state == "Pending Bid Decision" and prev_state != "Pending Bid Decision":
			self.validate_evaluation_gate()

		# If moving to Approved to Bid, ensure authorized role
		if current_state == "Approved to Bid" and prev_state != "Approved to Bid":
			self.validate_management_approver_role(_("approve Bid"))

		# If moving to No-Bid / Closed, ensure authorized role and mandatory remarks
		if current_state == "No-Bid / Closed" and prev_state != "No-Bid / Closed":
			self.validate_management_approver_role(_("decline Bid (No-Bid)"))
			if not self.decision_remarks or not self.decision_remarks.strip():
				frappe.throw(_("Decision Remarks are mandatory when deciding No-Bid."))

		# If moving to Submitted, validate submission details
		if current_state == "Submitted" and prev_state != "Submitted":
			if not self.submission_deadline:
				frappe.throw(_("Submission Deadline is mandatory before marking Tender as Submitted."))
			if flt(self.estimated_contract_value) <= 0:
				frappe.throw(_("Estimated Contract Value must be greater than zero for submission."))

		# If moving to Won or Lost, must be coming from Submitted or Awaiting Result
		if current_state in ["Won", "Lost"] and prev_state not in ["Submitted", "Awaiting Result", current_state]:
			frappe.throw(
				_("Tender cannot be marked as {0} unless it has been Submitted or is Awaiting Result (Current: {1}).").format(
					current_state, prev_state
				)
			)

	def validate_evaluation_gate(self):
		"""Strict evaluation gate before escalating to management."""
		# If urgent exception authorized by Management Approver, allow bypass
		if self.urgent_exception_authorized and self.exception_authorized_by:
			return

		missing = []
		if self.technical_feasibility in ["Pending", None]:
			missing.append("Technical Feasibility")
		if self.resource_availability in ["Pending", None]:
			missing.append("Resource Availability")
		if self.commercial_feasibility in ["Pending", None]:
			missing.append("Commercial Feasibility")
		if not self.risk_assessment:
			missing.append("Risk Assessment")
		if not self.recommended_decision:
			missing.append("Recommended Decision")

		if missing:
			frappe.throw(
				_("Cannot submit for Bid Decision. The following assessments are incomplete: {0}.").format(
					", ".join(missing)
				)
			)

		if self.recommended_decision == "Further Review":
			frappe.throw(
				_("Recommended Decision is 'Further Review'. Evaluation must be finalized before submitting for Bid Decision.")
			)

		# Require at least one row in evaluations
		if not self.evaluations or len(self.evaluations) == 0:
			frappe.throw(
				_("At least one evaluation entry must be recorded in the Evaluation Matrix before submitting for Bid Decision.")
			)

		# Validate mandatory tender documents have attachments
		missing_docs = []
		for doc_row in (self.documents or []):
			if doc_row.mandatory and not doc_row.attachment:
				missing_docs.append(doc_row.document_name or doc_row.document_type)

		if missing_docs:
			frappe.throw(
				_("The following mandatory Tender Documents are missing attachments: {0}.").format(
					", ".join(missing_docs)
				)
			)

	def validate_management_approver_role(self, action_name):
		"""Validate that current user has Management Approver or System Manager role."""
		user_roles = frappe.get_roles(frappe.session.user)
		if "Management Approver" not in user_roles and "System Manager" not in user_roles:
			frappe.throw(
				_("Only users with the 'Management Approver' role can {0}.").format(action_name),
				frappe.PermissionError,
			)

	def validate_outcome_details(self):
		"""Validate mandatory details when reaching terminal states."""
		if self.workflow_state == "Won":
			if not self.award_date:
				frappe.throw(_("Award Date is mandatory for Won Tenders."))
			if flt(self.awarded_contract_value) <= 0:
				frappe.throw(_("Awarded Contract Value must be greater than zero for Won Tenders."))

		elif self.workflow_state == "Lost":
			if not self.lost_reason:
				frappe.throw(_("Lost Reason is mandatory for Lost Tenders."))

		elif self.workflow_state in ["Cancelled", "Withdrawn / Closed"]:
			if not self.cancellation_reason or not self.cancellation_reason.strip():
				frappe.throw(_("Cancellation / Withdrawal Reason is mandatory."))

	def handle_workflow_state_side_effects(self):
		"""Handle automated stamps and logging on state transitions."""
		prev_doc = self.get_doc_before_save()
		prev_state = prev_doc.workflow_state if prev_doc else (self.workflow_state or "Draft")
		current_state = self.workflow_state or "Draft"

		if prev_state != current_state:
			# Auto-stamp on Submit for Bid Decision
			if current_state == "Pending Bid Decision":
				self.evaluated_by = frappe.session.user
				self.evaluation_date = now_datetime()

			# Auto-stamp on Approve Bid
			elif current_state == "Approved to Bid":
				self.bid_decision = "Bid"
				self.approved_by = frappe.session.user
				self.approval_date = now_datetime()

			# Auto-stamp on Decline Bid
			elif current_state == "No-Bid / Closed":
				self.bid_decision = "No Bid"
				self.approved_by = frappe.session.user
				self.approval_date = now_datetime()

			# Handle Return to Evaluation
			elif current_state == "Under Evaluation" and prev_state in [
				"Approved to Bid",
				"Ready for Submission",
				"Pending Bid Decision",
			]:
				self.log_return_to_evaluation(prev_state)

	def log_return_to_evaluation(self, prev_state):
		"""Log amendment and clear previous approvals."""
		self.validate_management_approver_role(_("return Tender to Evaluation"))
		amendment_reason = getattr(self, "_amendment_reason", None) or self.decision_remarks or _("Returned for Re-evaluation")

		snapshot = {
			"previous_state": prev_state,
			"estimated_contract_value": flt(self.estimated_contract_value),
			"currency": self.currency,
			"approved_by": self.approved_by,
			"approval_date": str(self.approval_date) if self.approval_date else None,
			"bid_decision": self.bid_decision,
		}

		self.append(
			"amendment_logs",
			{
				"action_type": "Return to Evaluation",
				"previous_state": prev_state,
				"action_by": frappe.session.user,
				"action_date": now_datetime(),
				"reason": amendment_reason,
				"snapshot_data": json.dumps(snapshot, indent=2),
			},
		)

		# Reset approval fields
		self.approved_by = None
		self.approval_date = None
		self.bid_decision = "Pending"

	@frappe.whitelist()
	def authorize_urgent_exception(self, reason):
		"""Authorize urgent tender exception by Management Approver."""
		self.validate_management_approver_role(_("authorize urgent exception"))
		if not reason or not reason.strip():
			frappe.throw(_("Exception reason is mandatory."))

		self.urgent_exception_authorized = 1
		self.exception_reason = reason.strip()
		self.exception_authorized_by = frappe.session.user
		self.exception_date = now_datetime()
		self.save()
		frappe.msgprint(_("Urgent tender exception authorized by {0}.").format(frappe.session.user))

	@frappe.whitelist()
	def return_to_evaluation(self, reason):
		"""Trigger Return to Evaluation workflow action."""
		self.validate_management_approver_role(_("return Tender to Evaluation"))
		if not reason or not reason.strip():
			frappe.throw(_("Amendment reason is mandatory to return Tender for re-evaluation."))

		self._amendment_reason = reason.strip()
		self.workflow_state = "Under Evaluation"
		self.save()
		frappe.msgprint(_("Tender returned to 'Under Evaluation' state."))

	@frappe.whitelist()
	def record_won_outcome(self, award_date, awarded_contract_value, award_reference=None):
		"""Record Won outcome with award details."""
		if self.workflow_state not in ["Submitted", "Awaiting Result"]:
			frappe.throw(_("Tender must be in 'Submitted' or 'Awaiting Result' state to record Won outcome."))

		if not award_date:
			frappe.throw(_("Award Date is mandatory for Won Tenders."))
		if flt(awarded_contract_value) <= 0:
			frappe.throw(_("Awarded Contract Value must be greater than zero for Won Tenders."))

		self.award_date = award_date
		self.awarded_contract_value = flt(awarded_contract_value)
		self.award_reference = award_reference
		self.workflow_state = "Won"
		self.save()
		frappe.msgprint(_("Tender successfully recorded as Won."))

	@frappe.whitelist()
	def record_lost_outcome(self, lost_reason, lost_remarks=None):
		"""Record Lost outcome with reason."""
		if self.workflow_state not in ["Submitted", "Awaiting Result"]:
			frappe.throw(_("Tender must be in 'Submitted' or 'Awaiting Result' state to record Lost outcome."))

		if not lost_reason:
			frappe.throw(_("Lost Reason is mandatory."))

		self.lost_reason = lost_reason
		self.lost_remarks = lost_remarks
		self.workflow_state = "Lost"
		self.save()
		frappe.msgprint(_("Tender recorded as Lost."))

	@frappe.whitelist()
	def record_cancellation(self, reason, is_post_submission_withdrawal=False):
		"""Cancel tender or record client withdrawal."""
		if not reason or not reason.strip():
			frappe.throw(_("Reason is mandatory for cancellation/withdrawal."))

		if is_post_submission_withdrawal or self.workflow_state in ["Submitted", "Awaiting Result"]:
			self.validate_management_approver_role(_("withdraw submitted tender"))
			self.workflow_state = "Withdrawn / Closed"
		else:
			self.workflow_state = "Cancelled"

		self.cancellation_reason = reason.strip()
		self.save()
		frappe.msgprint(_("Tender updated to {0}.").format(self.workflow_state))

	def on_trash(self):
		pass
