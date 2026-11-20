// Copyright (c) 2026, thanhnc and contributors
// For license information, please see license.txt

// Model choices per provider. "Custom" reveals a free-text field for any other model id.
const ERP_BUDDY_MODELS = {
	Anthropic: ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5", "claude-fable-5-2"],
	"OpenAI Compatible": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o-mini"],
};

function erp_buddy_set_model_options(frm, reset) {
	const models = ERP_BUDDY_MODELS[frm.doc.provider] || [];
	frm.set_df_property("model", "options", [...models, "Custom"].join("\n"));
	if (reset && frm.doc.model !== "Custom" && !models.includes(frm.doc.model)) {
		frm.set_value("model", models[0] || "Custom");
	}
}

frappe.ui.form.on("ERP Buddy Settings", {
	refresh(frm) {
		erp_buddy_set_model_options(frm, false);
	},
	provider(frm) {
		erp_buddy_set_model_options(frm, true);
	},
});
