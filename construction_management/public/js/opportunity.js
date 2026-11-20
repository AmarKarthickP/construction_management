// Copyright (c) 2026, Amar Karthick P and contributors
// For license information, please see license.txt

frappe.ui.form.on("Opportunity", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.trigger("add_tender_buttons");
	},

	add_tender_buttons(frm) {
		// Main "Create Tender" button
		frm.add_custom_button(__("Create Tender"), () => {
			frappe.call({
				method: "construction_management.crm.opportunity.create_tender_from_opportunity",
				args: {
					opportunity_name: frm.doc.name
				},
				freeze: true,
				freeze_message: __("Processing Tender Creation..."),
				callback(r) {
					if (!r.message) return;

					if (r.message.status === "reuse") {
						frappe.show_alert({
							message: r.message.message,
							indicator: "blue"
						});
						frappe.set_route("Form", "Tender", r.message.tender_name);
					} else if (r.message.status === "select_draft") {
						const options = r.message.drafts.map((d) => ({
							label: `${d.tender_title} (${d.name})`,
							value: d.name
						}));

						const d = new frappe.ui.Dialog({
							title: __("Existing Draft Tenders"),
							fields: [
								{
									label: __("Select Existing Draft to Open"),
									fieldname: "selected_draft",
									fieldtype: "Select",
									options: options
								},
								{
									label: __("Or Create New Package Title"),
									fieldname: "new_package_title",
									fieldtype: "Data",
									description: __("e.g., Civil & Structural, MEP, HVAC, Fitout")
								}
							],
							primary_action_label: __("Proceed"),
							primary_action(values) {
								d.hide();
								if (values.new_package_title && values.new_package_title.trim()) {
									frm.trigger("create_new_tender_package", values.new_package_title.trim());
								} else if (values.selected_draft) {
									frappe.set_route("Form", "Tender", values.selected_draft);
								}
							}
						});
						d.show();
					} else if (r.message.status === "success") {
						frappe.show_alert({
							message: r.message.message,
							indicator: "green"
						});
						frappe.set_route("Form", "Tender", r.message.tender_name);
					}
				}
			});
		}, __("Tender"));

		// "Create New Package" button for explicit multi-package tenders
		frm.add_custom_button(__("Create New Package"), () => {
			frappe.prompt(
				[
					{
						label: __("Tender Package Title / Scope Name"),
						fieldname: "package_title",
						fieldtype: "Data",
						reqd: 1,
						description: __("e.g., Civil & Structural, MEP, HVAC, Fitout")
					}
				],
				(values) => {
					frm.trigger("create_new_tender_package", values.package_title);
				},
				__("Create Specific Tender Package"),
				__("Create Package")
			);
		}, __("Tender"));

		// "View Linked Tenders" shortcut button
		frm.add_custom_button(__("View Linked Tenders"), () => {
			frappe.set_route("List", "Tender", { opportunity: frm.doc.name });
		}, __("Tender"));
	},

	create_new_tender_package(frm, package_title) {
		frappe.call({
			method: "construction_management.crm.opportunity.create_tender_from_opportunity",
			args: {
				opportunity_name: frm.doc.name,
				package_title: package_title
			},
			freeze: true,
			freeze_message: __("Creating Tender Package..."),
			callback(r) {
				if (r.message && r.message.tender_name) {
					frappe.show_alert({
						message: r.message.message,
						indicator: "green"
					});
					frappe.set_route("Form", "Tender", r.message.tender_name);
				}
			}
		});
	}
});
