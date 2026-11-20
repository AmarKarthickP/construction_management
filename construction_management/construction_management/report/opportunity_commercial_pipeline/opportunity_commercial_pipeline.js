// Copyright (c) 2026, Amar Karthick P and contributors
// For license information, please see license.txt

frappe.query_reports["Opportunity Commercial Pipeline"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "sales_stage",
			label: __("Sales Stage"),
			fieldtype: "Link",
			options: "Sales Stage"
		},
		{
			fieldname: "project_type",
			label: __("Project Type"),
			fieldtype: "Select",
			options: "\nBuilding Construction\nCivil Works\nInfrastructure\nIndustrial Construction\nRenovation\nOther"
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nOpen\nQuotation\nConverted\nLost\nReplied\nClosed"
		}
	]
};
