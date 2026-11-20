// Copyright (c) 2026, Amar Karthick P and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tender", {
	refresh(frm) {
		frm.trigger("setup_queries");
		frm.trigger("setup_custom_buttons");
		frm.trigger("apply_field_read_only");
	},

	setup_queries(frm) {
		frm.set_query("lost_reason", () => {
			return {
				filters: {
					is_active: 1
				}
			};
		});

		frm.set_query("opportunity", () => {
			if (frm.doc.company) {
				return {
					filters: {
						company: frm.doc.company
					}
				};
			}
		});

		frm.set_query("tender_owner", () => {
			return {
				filters: {
					enabled: 1,
					user_type: "System User"
				}
			};
		});
	},

	apply_field_read_only(frm) {
		const locked_states = [
			"Approved to Bid",
			"Ready for Submission",
			"Submitted",
			"Awaiting Result",
			"Won",
			"Lost",
			"Cancelled",
			"Withdrawn / Closed"
		];

		const is_locked = locked_states.includes(frm.doc.workflow_state);
		frm.set_df_property("estimated_contract_value", "read_only", is_locked ? 1 : 0);
		frm.set_df_property("currency", "read_only", is_locked ? 1 : 0);
		frm.set_df_property("company", "read_only", is_locked ? 1 : 0);
		frm.set_df_property("opportunity", "read_only", is_locked ? 1 : 0);
		frm.set_df_property("project_type", "read_only", is_locked ? 1 : 0);

		// Scope child table is permanently read-only once created
		frm.set_df_property("preliminary_scope_items", "read_only", frm.doc.name ? 1 : 0);
	},

	setup_custom_buttons(frm) {
		if (frm.is_new()) return;

		const state = frm.doc.workflow_state;

		// Management: Authorize Urgent Exception during Under Evaluation
		if (state === "Under Evaluation" && !frm.doc.urgent_exception_authorized) {
			if (frappe.user.has_role("Management Approver") || frappe.user.has_role("System Manager")) {
				frm.add_custom_button(__("Authorize Urgent Exception"), () => {
					frappe.prompt(
						[
							{
								label: __("Exception Reason / Justification"),
								fieldname: "reason",
								fieldtype: "Small Text",
								reqd: 1
							}
						],
						(values) => {
							frm.call("authorize_urgent_exception", { reason: values.reason }).then(() => {
								frm.reload_doc();
							});
						},
						__("Urgent Tender Exception Authorization"),
						__("Authorize")
					);
				}, __("Management Actions"));
			}
		}

		// Management: Return to Evaluation
		if (["Approved to Bid", "Ready for Submission"].includes(state)) {
			if (frappe.user.has_role("Management Approver") || frappe.user.has_role("System Manager")) {
				frm.add_custom_button(__("Return to Evaluation"), () => {
					frappe.prompt(
						[
							{
								label: __("Amendment / Return Reason"),
								fieldname: "reason",
								fieldtype: "Small Text",
								reqd: 1
							}
						],
						(values) => {
							frm.call("return_to_evaluation", { reason: values.reason }).then(() => {
								frm.reload_doc();
							});
						},
						__("Return Tender for Re-evaluation"),
						__("Return")
					);
				}, __("Management Actions"));
			}
		}

		// Outcome: Record Won
		if (["Submitted", "Awaiting Result"].includes(state)) {
			frm.add_custom_button(__("Record Won"), () => {
				frappe.prompt(
					[
						{
							label: __("Award Date"),
							fieldname: "award_date",
							fieldtype: "Date",
							default: frappe.datetime.get_today(),
							reqd: 1
						},
						{
							label: __("Awarded Contract Value"),
							fieldname: "awarded_contract_value",
							fieldtype: "Currency",
							options: frm.doc.currency,
							default: frm.doc.estimated_contract_value,
							reqd: 1
						},
						{
							label: __("Award Reference Number"),
							fieldname: "award_reference",
							fieldtype: "Data"
						}
					],
					(values) => {
						frm.call("record_won_outcome", values).then(() => {
							frm.reload_doc();
						});
					},
					__("Record Tender Award (Won)"),
					__("Record Won")
				);
			}, __("Tender Outcome"));

			// Outcome: Record Lost
			frm.add_custom_button(__("Record Lost"), () => {
				frappe.prompt(
					[
						{
							label: __("Lost Reason"),
							fieldname: "lost_reason",
							fieldtype: "Link",
							options: "Tender Lost Reason",
							reqd: 1,
							get_query: () => ({ filters: { is_active: 1 } })
						},
						{
							label: __("Lost Remarks / Debrief Notes"),
							fieldname: "lost_remarks",
							fieldtype: "Small Text"
						}
					],
					(values) => {
						frm.call("record_lost_outcome", values).then(() => {
							frm.reload_doc();
						});
					},
					__("Record Tender Loss"),
					__("Record Lost")
				);
			}, __("Tender Outcome"));

			// Client Withdrawal / Scrapped
			if (frappe.user.has_role("Management Approver") || frappe.user.has_role("System Manager")) {
				frm.add_custom_button(__("Client Withdrawal / Scrapped"), () => {
					frappe.prompt(
						[
							{
								label: __("Withdrawal / Cancellation Reason"),
								fieldname: "reason",
								fieldtype: "Small Text",
								reqd: 1
							}
						],
						(values) => {
							frm.call("record_cancellation", {
								reason: values.reason,
								is_post_submission_withdrawal: true
							}).then(() => {
								frm.reload_doc();
							});
						},
						__("Client Tender Withdrawal"),
						__("Record Withdrawal")
					);
				}, __("Tender Outcome"));
			}
		}

		// Pre-submission Cancellation
		if (["Draft", "Under Evaluation", "Pending Bid Decision"].includes(state)) {
			frm.add_custom_button(__("Cancel Tender"), () => {
				frappe.prompt(
					[
						{
							label: __("Cancellation Reason"),
							fieldname: "reason",
							fieldtype: "Small Text",
							reqd: 1
						}
					],
					(values) => {
						frm.call("record_cancellation", {
							reason: values.reason,
							is_post_submission_withdrawal: false
						}).then(() => {
							frm.reload_doc();
						});
					},
					__("Cancel Tender"),
					__("Cancel Tender")
				);
			});
		}
	}
});
