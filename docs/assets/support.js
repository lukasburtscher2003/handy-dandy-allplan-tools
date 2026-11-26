// HJ Support – Gemeinsame Seitenstruktur und Werkzeuge
// © 2026 Lukas Burtscher

// Neue Werkzeuge nur hier ergänzen.
const tools = [
	{
		title: "UrbGEN",
		href: "urbgen.html",
		version: "2.0",
		description: "Parametrische Bebauungsplanung, Gebäudegenerierung und Variantenoptimierung."
	},
	{
		title: "GeoIMPORT",
		href: "geoimport.html",
		version: "0.4",
		description: "Grundstücksgrenzen, Luftbilder und Geländepunkte direkt in Allplan übernehmen."
	},
	{
		title: "ModelCHECK",
		href: "modelcheck.html",
		version: "1.0",
		description: "Volumen und wichtige Modellattribute prüfen; fehlerhafte Elemente gezielt finden."
	}
];

const navigation = [
	{ title: "Übersicht", href: "index.html" },
	...tools,
	{ title: "FAQ & Hilfe", href: "faq.html" },
	{ title: "Versionshistorie", href: "versionen.html" },
	{ title: "Feedback", href: "feedback.html" }
];

// Gemeinsame Kopf- und Fußzeile.
function renderLayout() {
	const header = document.querySelector("[data-header]");
	const footer = document.querySelector("[data-footer]");

	if (header) {
		header.innerHTML = `
			<div class="header-inner">
				<a href="index.html" aria-label="Startseite">
					<img class="logo" src="assets/logo-hj.jpg" alt="Hilti &amp; Jehle">
				</a>
				<div class="brand">
					HJ Support
					<small>Digitale Werkzeuge &amp; Dokumentation</small>
				</div>
				<span class="status"></span>
			</div>
		`;
		header.querySelector(".status").textContent =
			header.dataset.status || "ALLPLAN 2027";
	}

	if (footer) {
		footer.innerHTML = `
			<span>© 2026 Lukas Burtscher · Dokumentation</span>
			<span>Hilti &amp; Jehle · HJ Support</span>
		`;
	}
}

// Hauptnavigation ergänzen; individuelle Kapitel bleiben erhalten.
function renderNavigation(currentPage) {
	const sidebar = document.querySelector("[data-navigation]");
	if (!sidebar) return;

	const menu = document.createDocumentFragment();
	const label = document.createElement("div");
	label.className = "label";
	label.textContent = "Supportportal";
	menu.append(label);

	for (const item of navigation) {
		const link = document.createElement("a");
		link.href = item.href;
		link.textContent = item.title;

		if (currentPage === item.href) {
			link.setAttribute("aria-current", "page");
		}

		menu.append(link);
	}

	sidebar.prepend(menu);
}

// Werkzeugkacheln und Suche auf der Startseite.
function renderTools() {
	const grid = document.querySelector("[data-tools]");
	if (!grid) return;

	for (const tool of tools) {
		const card = document.createElement("a");
		card.className = "card";
		card.href = tool.href;
		card.dataset.tool = "";
		card.innerHTML = `
			<span class="pill"></span>
			<h2></h2>
			<p></p>
			<span class="arrow">Anleitung öffnen →</span>
		`;
		card.querySelector(".pill").textContent = "Allplan 2027 · v" + tool.version;
		card.querySelector("h2").textContent = tool.title;
		card.querySelector("p").textContent = tool.description;
		grid.append(card);
	}

	const input = document.querySelector("[data-search]");
	const empty = document.querySelector("[data-empty]");
	const cards = grid.querySelectorAll("[data-tool]");
	if (!input) return;

	function filterTools() {
		const query = input.value.toLocaleLowerCase("de").trim();
		let visibleCount = 0;

		for (const card of cards) {
			const visible = card.textContent.toLocaleLowerCase("de").includes(query);
			card.style.display = visible ? "" : "none";
			if (visible) visibleCount++;
		}

		if (empty) empty.hidden = visibleCount !== 0;
	}

	input.addEventListener("input", filterTools);
	filterTools();
}

// Werkzeugliste im Feedback und direkter Link aus den Anleitungen.
function renderFeedback(currentPage) {
	const select = document.querySelector("[data-feedback-tools]");
	if (select) {
		const options = tools.map(tool => new Option(tool.title, tool.title));
		select.options[0].after(...options);
	}

	const tool = tools.find(item => item.href === currentPage);
	const main = document.querySelector("main");
	if (!tool || !main) return;

	const links = main.querySelector(".navlinks");
	const link = document.createElement("a");
	link.href = "feedback.html?tool=" + encodeURIComponent(tool.title);
	link.textContent = "Feedback zu " + tool.title + " geben →";
	link.className = "button";

	if (links) {
		links.append(link);
	} else {
		main.append(link);
	}
}

document.addEventListener("DOMContentLoaded", () => {
	const currentPage = location.pathname.split("/").pop() || "index.html";
	renderLayout();
	renderNavigation(currentPage);
	renderTools();
	renderFeedback(currentPage);
});
