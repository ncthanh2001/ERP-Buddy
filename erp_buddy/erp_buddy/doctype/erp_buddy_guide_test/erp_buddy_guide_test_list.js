// Copyright (c) 2026, thanhnc and contributors
// For license information, please see license.txt

frappe.listview_settings["ERP Buddy Guide Test"] = {
	get_indicator(doc) {
		const colors = { Passed: "green", Failed: "red", "Not Run": "gray" };
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
	onload(listview) {
		listview.page.add_inner_button(__("Run All Tests"), async () => {
			const r = await frappe.xcall(
				"erp_buddy.erp_buddy.doctype.erp_buddy_guide_test.erp_buddy_guide_test.run_all_tests"
			);
			listview.refresh();
			const indicator = r.failed.length ? "orange" : "green";
			frappe.show_alert(
				{ message: __("{0} of {1} tests passed", [r.passed, r.total]), indicator },
				8
			);
		});
	},
};
