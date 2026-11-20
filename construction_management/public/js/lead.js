// Copyright (c) 2026, Amar Karthick P and contributors
// For license information, please see license.txt

frappe.ui.form.on("Lead", {
	refresh(frm) {
		// Advisory tooltip or indicator for qualification
		if (frm.doc.qualification_status !== "Qualified" && !frm.is_new()) {
			frm.dashboard.set_headline(
				__("This Lead is currently <b>{0}</b>. It must be <b>Qualified</b> before converting to an Opportunity.", [
					frm.doc.qualification_status || __("Unqualified")
				]),
				"orange"
			);
		}
	}
});
