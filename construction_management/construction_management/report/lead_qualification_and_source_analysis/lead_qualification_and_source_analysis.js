// Copyright (c) 2026, Amar Karthick P and contributors
// For license information, please see license.txt

frappe.query_reports["Lead Qualification and Source Analysis"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "source",
			label: __("Source"),
			fieldtype: "Link",
			options: "UTM Source"
		},
		{
			fieldname: "qualification_status",
			label: __("Qualification Status"),
			fieldtype: "Select",
			options: "\nUnqualified\nIn Process\nQualified"
		},
		{
			fieldname: "status",
			label: __("CRM Status"),
			fieldtype: "Select",
			options: "\nLead\nOpen\nReplied\nOpportunity\nQuotation\nLost Quotation\nInterested\nConverted\nDo Not Contact"
		}
	]
};
