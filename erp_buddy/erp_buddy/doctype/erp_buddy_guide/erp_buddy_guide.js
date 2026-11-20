// Copyright (c) 2026, thanhnc and contributors
// For license information, please see license.txt

const ERP_BUDDY_TRAINING_GUIDE = "How to teach ERP Buddy (training template)";

// Starting point for a new guide; the training template guide explains each part.
const ERP_BUDDY_GUIDE_TEMPLATE = `# <Task, e.g. Create a sales order>

**Used for:** <when and why someone does this>
**Before you start:** <records that must exist first, e.g. Customer, Item>

## Steps
1. Open [<Screen name>](/app/<screen-url>/new).
2. Fill in **<Field>**: <what to enter>.
3. Add the rows in **<Table>**: <columns to fill>.
4. **Save**, check the totals, then **Submit**.

## Notes
- <Common mistakes and how to avoid them>
- <Company rules, approvals, limits>

## Related
- Next step: <the document created after this one>
- Report: <report to check the result>
`;

frappe.ui.form.on("ERP Buddy Guide", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.content) {
			frm.set_value("content", ERP_BUDDY_GUIDE_TEMPLATE);
		}
	},

	refresh(frm) {
		frm.add_custom_button(__("Training template"), () => {
			frappe.set_route("Form", "ERP Buddy Guide", ERP_BUDDY_TRAINING_GUIDE);
		});
		if (frm.doc.name === ERP_BUDDY_TRAINING_GUIDE) {
			frm.set_intro(
				__("This guide explains how to teach ERP Buddy. Copy the templates below into new guides."),
				"blue"
			);
		}
	},
});
