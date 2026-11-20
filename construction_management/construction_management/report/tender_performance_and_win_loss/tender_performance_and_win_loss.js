// Copyright (c) 2026, Amar Karthick P and contributors
// For license information, please see license.txt

frappe.query_reports["Tender Performance and Win Loss"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "workflow_state",
			label: __("Status"),
			fieldtype: "Link",
			options: "Workflow State"
		},
		{
			fieldname: "bid_decision",
			label: __("Bid Decision"),
			fieldtype: "Select",
			options: "\nPending\nBid\nNo Bid"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date"
		}
	]
};
