// ERP Buddy — floating chat widget on every Desk page.
// Plain classic script (no build step). All data access happens server-side as the
// logged-in user; this file only renders and calls erp_buddy.api.*.
(function () {
	"use strict";

	const API = "erp_buddy.api.";
	const AVATAR = "/assets/erp_buddy/images/erp_buddy_avatar.png";

	// Inline SVG icons (Lucide-style strokes) so the widget needs no icon font.
	const svg = (paths) =>
		`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
	const ICONS = {
		flow: svg('<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="19" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M12 7.5v4M12 11.5 6.5 16.8M12 11.5l5.5 5.3"/>'),
		book: svg('<path d="M2 5.5A2.5 2.5 0 0 1 4.5 3H11v17H4.5A2.5 2.5 0 0 0 2 22.5z"/><path d="M22 5.5A2.5 2.5 0 0 0 19.5 3H13v17h6.5a2.5 2.5 0 0 1 2.5 2.5z"/>'),
		database: svg('<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>'),
		shield: svg('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>'),
		cart: svg('<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.7 12.4a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.6L21 7H6"/>'),
		box: svg('<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>'),
		file: svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>'),
		user_plus: svg('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/>'),
		send: svg('<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>'),
		minus: svg('<path d="M5 12h14"/>'),
		close: svg('<path d="M18 6 6 18M6 6l12 12"/>'),
		plus: svg('<path d="M12 5v14M5 12h14"/>'),
		history: svg('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>'),
		trash: svg('<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>'),
	};

	const CAPABILITIES = [
		["flow", "Explain business processes"],
		["book", "Guide you step by step in the ERP system"],
		["database", "Look up and create data for you"],
		["shield", "Always within your own permissions"],
	];
	const SUGGESTIONS = [
		["cart", "How does the buying process work?"],
		["box", "How do I receive stock into a warehouse?"],
		["file", "Purchase Order vs Purchase Invoice: what's the difference?"],
		["user_plus", "Create a new customer for me"],
	];

	class ERPBuddyChat {
		constructor() {
			this.conversation = this.loadConversation();
			this.busy = false;
			this.status = null;
			this.render();
		}

		// ---- storage (per user, best effort) -----------------------------------------
		storageKey() {
			return "erpb_conversation_" + (frappe.session && frappe.session.user);
		}
		loadConversation() {
			try {
				return localStorage.getItem(this.storageKey()) || null;
			} catch (e) {
				return null;
			}
		}
		saveConversation(name) {
			this.conversation = name || null;
			try {
				if (name) localStorage.setItem(this.storageKey(), name);
				else localStorage.removeItem(this.storageKey());
			} catch (e) {
				/* storage unavailable: the chat still works for this page view */
			}
		}

		// ---- layout ------------------------------------------------------------------
		render() {
			this.$launcher = $(`
				<button class="erpb-launcher" title="${__("ERP Buddy - your ERP support assistant")}">
					<img src="${AVATAR}" alt="ERP Buddy">
				</button>`).appendTo(document.body);

			this.$panel = $(`
				<div class="erpb-panel" role="dialog" aria-label="ERP Buddy">
					<div class="erpb-header">
						<img class="erpb-header-avatar" src="${AVATAR}" alt="">
						<div class="erpb-title">
							<div class="erpb-title-name">ERP Buddy <span class="erpb-sparkle">✦</span></div>
						</div>
						<div class="erpb-header-actions">
							<button class="erpb-round-btn erpb-btn-history" title="${__("History")}">${ICONS.history}</button>
							<button class="erpb-round-btn erpb-btn-new" title="${__("New conversation")}">${ICONS.plus}</button>
							<button class="erpb-round-btn erpb-btn-min" title="${__("Minimize")}">${ICONS.minus}</button>
							<button class="erpb-round-btn erpb-btn-close" title="${__("Close")}">${ICONS.close}</button>
						</div>
					</div>
					<div class="erpb-history"></div>
					<div class="erpb-body"></div>
					<div class="erpb-footer">
						<div class="erpb-input-wrap">
							<textarea rows="1" placeholder="${__("Type your question…")}"></textarea>
							<button class="erpb-send" title="${__("Send")}">${ICONS.send}</button>
						</div>
					</div>
				</div>`).appendTo(document.body);

			this.$body = this.$panel.find(".erpb-body");
			this.$history = this.$panel.find(".erpb-history");
			this.$input = this.$panel.find("textarea");
			this.$send = this.$panel.find(".erpb-send");

			this.$launcher.on("click", () => this.toggle());
			this.$panel.find(".erpb-btn-min").on("click", () => this.toggle(false));
			this.$panel.find(".erpb-btn-close").on("click", () => {
				this.$history.removeClass("open");
				this.toggle(false);
			});
			this.$panel.find(".erpb-btn-new").on("click", () => this.newConversation());
			this.$panel.find(".erpb-btn-history").on("click", () => this.toggleHistory());
			this.$send.on("click", () => this.send());
			this.$input.on("keydown", (e) => {
				if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
					e.preventDefault();
					this.send();
				}
			});
			this.$input.on("input", () => this.autosize());
			this.$body.on("click", ".erpb-suggestion", (e) => this.send($(e.currentTarget).attr("data-text")));
		}

		autosize() {
			const el = this.$input[0];
			el.style.height = "auto";
			el.style.height = Math.min(el.scrollHeight, 120) + "px";
		}

		async toggle(force) {
			const open = force === undefined ? !this.$panel.hasClass("open") : force;
			this.$panel.toggleClass("open", open);
			// The panel takes the launcher's corner while open; minimize/close bring it back.
			this.$launcher.toggleClass("erpb-hidden", open);
			if (!open) return;
			if (!this.status) await this.loadStatus();
			if (!this.loaded) {
				this.loaded = true;
				await this.loadConversationMessages();
			}
			this.$input.trigger("focus");
		}

		async loadStatus() {
			try {
				this.status = (await frappe.xcall(API + "get_status", {}, "GET")) || {};
			} catch (e) {
				this.status = { enabled: false, configured: false };
			}
			if (!this.status.enabled || !this.status.configured) {
				const settingsLink = this.status.is_admin
					? `<br><br><a href="/app/erp-buddy-settings">${__("Open ERP Buddy Settings")}</a>`
					: "";
				const msg = !this.status.enabled
					? __("ERP Buddy is disabled.")
					: __("ERP Buddy has no LLM configured yet (provider, model, API key).");
				this.$body.html(`<div class="erpb-notice">${msg}${settingsLink}</div>`);
				this.$input.prop("disabled", true);
				this.$send.prop("disabled", true);
				this.loaded = true;
			}
		}

		// ---- conversations -------------------------------------------------------------
		newConversation() {
			this.saveConversation(null);
			this.$history.removeClass("open");
			this.showWelcome();
		}

		showWelcome() {
			const esc = frappe.utils.escape_html;
			const name = esc((this.status && this.status.full_name) || "");
			const caps = CAPABILITIES.map(
				([icon, text]) => `<li><span class="erpb-cap-icon">${ICONS[icon]}</span>${esc(__(text))}</li>`
			).join("");
			const chips = SUGGESTIONS.map(([icon, text]) => {
				const label = esc(__(text));
				return `<button class="erpb-suggestion" data-text="${label}">${ICONS[icon]}<span>${label}</span></button>`;
			}).join("");
			this.$body.html(`
				<div class="erpb-welcome">
					<div class="erpb-row">
						<img class="erpb-avatar" src="${AVATAR}" alt="">
						<div class="erpb-welcome-card">
							<div class="erpb-welcome-hello">${__("Hello")}${name ? " " + name : ""}! 👋</div>
							<div>${__("I'm {0}. I can help you:", ["<b>ERP Buddy</b>"])}</div>
							<ul class="erpb-caps">${caps}</ul>
						</div>
					</div>
					<div class="erpb-ask-title">${__("You can ask:")}</div>
					<div class="erpb-suggestions">${chips}</div>
				</div>`);
		}

		async loadConversationMessages() {
			if (!this.conversation) return this.showWelcome();
			try {
				const data = await frappe.xcall(API + "get_conversation", { name: this.conversation }, "GET");
				if (data.missing) {
					this.saveConversation(null);
					return this.showWelcome();
				}
				this.$body.empty();
				(data.messages || []).forEach((m) => this.appendMessage(m));
				if (!(data.messages || []).length) this.showWelcome();
				this.scrollDown();
			} catch (e) {
				this.saveConversation(null);
				this.showWelcome();
			}
		}

		async toggleHistory() {
			if (this.$history.hasClass("open")) return this.$history.removeClass("open");
			const items = await frappe.xcall(API + "list_conversations", {}, "GET");
			this.$history.empty();
			if (!items.length) {
				this.$history.html(`<div class="erpb-history-empty">${__("No conversations yet.")}</div>`);
			}
			items.forEach((c) => {
				const $item = $(`
					<div class="erpb-history-item">
						<span>${frappe.utils.escape_html(c.title || __("(untitled)"))}</span>
						<small class="text-muted">${frappe.datetime.prettyDate(c.modified)}</small>
						<button class="erpb-icon-btn" title="${__("Delete")}">${ICONS.trash}</button>
					</div>`);
				$item.on("click", async () => {
					this.saveConversation(c.name);
					this.$history.removeClass("open");
					await this.loadConversationMessages();
				});
				$item.find("button").on("click", async (e) => {
					e.stopPropagation();
					await frappe.xcall(API + "delete_conversation", { name: c.name });
					if (this.conversation === c.name) this.newConversation();
					$item.remove();
				});
				this.$history.append($item);
			});
			this.$history.addClass("open");
		}

		// ---- messages --------------------------------------------------------------------
		pageContext() {
			const ctx = { route: (frappe.get_route() || []).join("/") };
			if (window.cur_frm && cur_frm.doctype && frappe.get_route()[0] === "Form") {
				ctx.doctype = cur_frm.doctype;
				ctx.docname = cur_frm.is_new() ? null : cur_frm.docname;
			}
			return JSON.stringify(ctx);
		}

		async send(text) {
			text = (text || this.$input.val() || "").trim();
			if (!text || this.busy) return;
			this.busy = true;
			this.$send.prop("disabled", true);
			this.$input.val("");
			this.autosize();

			this.$body.find(".erpb-welcome").remove();
			this.appendMessage({ role: "user", text });
			const $typing = $(`
				<div class="erpb-row erpb-typing-row">
					<img class="erpb-avatar" src="${AVATAR}" alt="">
					<div class="erpb-typing" role="status">
						<span class="erpb-dots"><span></span><span></span><span></span></span>
						<span class="erpb-typing-label">${__("Thinking")}</span>
					</div>
				</div>`).appendTo(this.$body);
			this.scrollDown();

			try {
				const r = await frappe.xcall(API + "send_message", {
					message: text,
					conversation: this.conversation,
					context: this.pageContext(),
				});
				$typing.remove();
				if (r.conversation) this.saveConversation(r.conversation);
				if (r.error) {
					this.appendError(r.error);
				} else {
					this.appendMessage({ role: "assistant", text: r.reply, steps: r.steps, actions: r.actions });
				}
			} catch (e) {
				$typing.remove();
				this.appendError(__("Could not send the message. Please try again."));
			} finally {
				this.busy = false;
				this.$send.prop("disabled", false);
				this.$input.trigger("focus");
				this.scrollDown();
			}
		}

		appendMessage(m) {
			if (m.role === "user") {
				$(`<div class="erpb-msg user"></div>`).text(m.text).appendTo(this.$body);
				return;
			}
			const $msg = $(`<div class="erpb-msg assistant"></div>`);
			if (m.steps && m.steps.length) {
				const $steps = $(`<div class="erpb-steps"></div>`);
				m.steps.forEach((s) => {
					const denied = s.status === "Permission Denied";
					const icon = denied ? "🔒" : s.status === "Error" ? "⚠️" : "✓";
					$(`<div class="erpb-step"></div>`)
						.toggleClass("denied", denied)
						.text(`${icon} ${s.label}${denied ? " — " + __("not permitted") : ""}`)
						.appendTo($steps);
				});
				$msg.append($steps);
			}
			$msg.append($(`<div class="erpb-text"></div>`).html(this.renderMarkdown(m.text || "")));
			(m.actions || []).forEach((a) => $msg.append(this.renderActionCard(a)));
			$(`<div class="erpb-row"><img class="erpb-avatar" src="${AVATAR}" alt=""></div>`)
				.append($msg)
				.appendTo(this.$body);
		}

		appendError(text) {
			$(`<div class="erpb-msg error"></div>`).text(text).appendTo(this.$body);
		}

		// Model output is untrusted: escape HTML before markdown, then allow only safe links.
		renderMarkdown(text) {
			const escaped = String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
			const $html = $("<div>").html(frappe.markdown(escaped));
			$html.find("a").each(function () {
				const href = $(this).attr("href") || "";
				if (/^\/(?!\/)/.test(href)) return; // same-site path: Desk's router handles it
				if (/^https?:\/\//i.test(href)) {
					$(this).attr({ target: "_blank", rel: "noopener noreferrer" });
					return;
				}
				$(this).replaceWith($("<span>").text($(this).text()));
			});
			$html.find("img, script, iframe, style").remove();
			return $html.html();
		}

		renderActionCard(a) {
			const esc = (v) => frappe.utils.escape_html(v === null || v === undefined ? "" : String(v));
			const rows = (a.preview || [])
				.map((p) => {
					let value = esc(typeof p.value === "object" ? JSON.stringify(p.value) : p.value);
					if (p.old !== undefined) value = `<span class="erpb-old">${esc(p.old)}</span>${value}`;
					if (p.rows && p.rows.length) {
						value += "<br>" + p.rows
							.slice(0, 10)
							.map((r) => "• " + esc(Object.entries(r).map(([k, v]) => `${k}: ${v}`).join(", ")))
							.join("<br>");
					}
					return `<tr><td>${esc(p.label)}</td><td>${value}</td></tr>`;
				})
				.join("");

			const $card = $(`
				<div class="erpb-card">
					<div class="erpb-card-title">📝 ${esc(a.title)}</div>
					<table>${rows}</table>
					<div class="erpb-card-actions">
						<button class="btn btn-primary btn-xs erpb-confirm">${__("Confirm")}</button>
						<button class="btn btn-default btn-xs erpb-cancel">${__("Cancel")}</button>
					</div>
					<div class="erpb-card-status"></div>
				</div>`);

			const setState = (status, result) => {
				$card.removeClass("done failed cancelled");
				$card.find(".erpb-card-actions").toggle(status === "pending");
				const $status = $card.find(".erpb-card-status").empty();
				if (status === "done") {
					$card.addClass("done");
					$status.html(
						`✅ ${esc(result && result.message)} — <a href="${esc(result && result.url)}">${__("Open")}</a>`
					);
				} else if (status === "failed") {
					$card.addClass("failed");
					$status.text("❌ " + ((result && result.message) || __("Failed")));
				} else if (status === "cancelled") {
					$card.addClass("cancelled");
					$status.text(__("Cancelled."));
				}
			};
			setState(a.status || "pending", a.result);

			const resolve = async (confirm) => {
				$card.find("button").prop("disabled", true);
				try {
					const r = await frappe.xcall(API + "resolve_action", {
						conversation: this.conversation,
						action_id: a.id,
						confirm: confirm ? 1 : 0,
					});
					const action = r.action || {};
					setState(action.status || (r.ok ? "done" : "failed"), action.result || r);
				} catch (e) {
					$card.find("button").prop("disabled", false);
				}
			};
			$card.find(".erpb-confirm").on("click", () => resolve(true));
			$card.find(".erpb-cancel").on("click", () => resolve(false));
			return $card;
		}

		scrollDown() {
			this.$body.scrollTop(this.$body[0].scrollHeight);
		}
	}

	function boot() {
		if (window.erp_buddy_chat || !window.frappe || !frappe.session || frappe.session.user === "Guest") return;
		if (frappe.boot && frappe.boot.user && frappe.boot.user.user_type && frappe.boot.user.user_type !== "System User")
			return;
		window.erp_buddy_chat = new ERPBuddyChat();
	}

	$(document).on("app_ready", boot);
	if (window.frappe && frappe.boot && frappe.boot.user) $(boot);
})();
