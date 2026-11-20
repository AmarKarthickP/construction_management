// Copyright (c) 2026, Amar Karthick P and contributors
// For license information, please see license.txt

frappe.listview_settings["Tender"] = {
	add_fields: [
		"workflow_state",
		"customer",
		"opportunity",
		"company",
		"submission_deadline",
		"estimated_contract_value",
		"currency"
	],
	get_indicator(doc) {
		const state_colors = {
			"Draft": "grey",
			"Under Evaluation": "blue",
			"Pending Bid Decision": "orange",
			"Approved to Bid": "cyan",
			"Ready for Submission": "cyan",
			"Submitted": "purple",
			"Awaiting Result": "purple",
			"Won": "green",
			"Lost": "red",
			"No-Bid / Closed": "red",
			"Cancelled": "darkgrey",
			"Withdrawn / Closed": "darkgrey"
		};

		const state = doc.workflow_state || "Draft";
		return [__(state), state_colors[state] || "grey", `workflow_state,=,${state}`];
	}
};
