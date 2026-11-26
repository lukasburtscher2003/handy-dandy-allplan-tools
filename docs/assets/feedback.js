// HJ Support – Feedbackversand über Formspree
// © 2026 Lukas Burtscher

document.addEventListener("DOMContentLoaded", () => {
	"use strict";
	const form = document.getElementById("feedback");
	const button = document.getElementById("send");
	const status = document.getElementById("feedback-status");
	const endpoint = form.dataset.endpoint.trim();
	const configured = /^https:\/\/formspree\.io\/f\/[a-zA-Z0-9]+$/.test(endpoint);

	function showStatus(message, state = "") {
		status.textContent = message;
		status.dataset.state = state;
	}

	// Ohne gültigen Endpunkt bleibt der Versand deaktiviert.
	button.disabled = !configured;
	if (configured) showStatus("");

	const selectedTool = new URLSearchParams(location.search).get("tool");
	const toolSelect = document.getElementById("tool");
	for (const option of toolSelect.options) {
		if (option.value === selectedTool) toolSelect.value = selectedTool;
	}

	form.addEventListener("submit", async (event) => {
		event.preventDefault();
		if (!configured || button.disabled || !form.reportValidity()) return;
		button.disabled = true;
		showStatus("Feedback wird gesendet …");

		try {
			const response = await fetch(endpoint, {
				method: "POST",
				body: new FormData(form),
				headers: { Accept: "application/json" }
			});
			if (!response.ok) throw new Error("Versand fehlgeschlagen");

			form.reset();
			showStatus("Vielen Dank! Dein Feedback wurde übermittelt.", "success");
		} catch (error) {
			showStatus("Das Feedback konnte nicht gesendet werden. Bitte später erneut versuchen. Deine Eingaben bleiben erhalten.", "error");
		} finally {
			button.disabled = false;
		}
	});
});
