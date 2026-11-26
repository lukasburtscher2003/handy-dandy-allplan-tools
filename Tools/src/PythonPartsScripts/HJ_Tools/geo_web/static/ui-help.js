// Short contextual help, shared by desktop and intranet; never touches export options.
(() => {
  const entries = [
    ['kgFilter', 'Katastralgemeinde', 'KG bedeutet Katastralgemeinde: ein Bereich des Grundstückskatasters. Die Auswahl grenzt die Grundstückssuche ein.'],
    ['frameMode', 'Exportbereich', 'Der Rahmen bestimmt den Bereich für Gelände und Luftbild. Für „Um das ausgewählte Grundstück“ zuerst eine Parzelle auf der Karte oder in der Suche wählen.'],
    ['terrainMode', 'Geländeauswahl', '„Bodenpunkte“ erzeugt ein gleichmäßiges Raster mit berechneten Höhen. „Oberfläche“ verwendet vorhandene Bodenmesspunkte; beide Varianten enthalten weder Gebäude noch Vegetation.'],
    ['grid', 'Punktabstand', 'Kleinere Abstände liefern mehr Punkte und größere Dateien. Bei „Oberfläche“ wird je belegter Rasterzelle ein vorhandener Bodenmesspunkt ausgewählt.'],
    ['useDkmMargin', 'Zusätzliche Grundstücke', 'Erweitert nur die Grundstücksauswahl um den gewählten Abstand auf jeder Seite. Gelände und Luftbild bleiben im sichtbaren Rahmen.'],
    ['dkmMargin', 'Abstand um den Exportbereich', 'Beispiel: 50 m erweitert die Grundstücksauswahl auf jeder Seite um 50 m. Alle davon berührten Grundstücke werden vollständig exportiert.'],
    ['raw', 'Alle Bodenmesspunkte', 'Exportiert vorhandene Bodenmesspunkte ohne Rasterauswahl. Dadurch können deutlich größere Dateien entstehen; die zusätzlichen Randpunkte bleiben erhalten.'],
    ['boundarySpacing', 'Punktabstand am Rahmenrand', 'Größter Abstand zwischen zusätzlichen Punkten auf den Rahmenkanten, unabhängig vom inneren Raster. Die Ecken sind immer enthalten; die Höhen werden berechnet.'],
    ['terrainFileTypes', 'Geländeformate', 'DXF eignet sich für CAD, XYZ für einfache Punktlisten und LAS/LAZ für Punktwolkenprogramme. LAZ ist komprimiert; standardmäßig wird nur DXF ausgegeben.'],
    ['parcelFileTypes', 'Grundstücksformate', 'DXF eignet sich für CAD und GeoJSON für GIS. GeoJSON verwendet ohne lokalen Ursprung geografische Koordinaten; mit lokalem Ursprung sind es ausdrücklich Meter.'],
    ['aerialFileTypes', 'Luftbildformate', 'GeoTIFF speichert Bild und Lageinformation gemeinsam. Bei PNG/JPEG die mitgelieferten World- und Projektionsdateien zusammen mit dem Bild aufbewahren.'],
    ['includeAdjacent', 'Angrenzende Grundstücke', 'Ergänzt genau eine direkte Nachbarreihe einschließlich Eckberührungen. Eingeschlossene Grundstücke starten keine weitere Nachbarreihe.'],
    ['parcelDecimals', 'Rundung der Grenzen', 'Standard sind drei Nachkommastellen in Metern. Zentimeterrundung verändert die Geometrie, verbessert aber nicht die Vermessungsgenauigkeit; Messpunkte und grafische Stützpunkte sind zu unterscheiden.'],
    ['originMode', 'Gemeinsamer Ursprung', 'Verschiebt alle Exportdaten gemeinsam in ein lokales Koordinatensystem. Höhen bleiben unverändert; Versatz und Rückrechnung stehen in den Exportmetadaten.'],
    ['offsetX', 'X-Offset', 'Dieser Wert wird von allen X-Landeskoordinaten abgezogen. Mit „Ausgabe + Offset“ erhältst du die ursprünglichen Landeskoordinaten.'],
    ['offsetY', 'Y-Offset', 'Dieser Wert wird von allen Y-Landeskoordinaten abgezogen. Gelände, Grundstücke und Luftbild verwenden denselben Versatz.'],
    ['dataSources', 'Datenquellen', 'Gelände: LiDAR 2023, Grundstücke: aktueller VOGIS-Dienstabruf, Luftbild: gewähltes Jahr. „Datenindex prüfen“ aktualisiert die Liste verfügbarer Geländekacheln und kann länger dauern.'],
    ['coverage', 'Datenabdeckung', 'Die Anzeige bestätigt passende Geländekacheln, keine lückenlosen Bodenmessungen. Messlücken und die Luftbildabdeckung werden beim Export geprüft.'],
    ['printAreaMode', 'Druckbereich wählen', '„Papierrahmen“: eigener, auf der Karte verschiebbarer Druckbereich mit frei eingestelltem Maßstab. „Exportrahmen“: der vorhandene Geodatenrahmen wird vollständig in die PDF-Seite eingepasst; der passende Maßstab wird automatisch berechnet.'],
    ['printScale', 'PDF-Maßstab', 'Maßstab 1:n, z. B. 1000 für 1:1000. Beim Papierrahmen legt er die Fläche auf dem Papier fest. Beim vorhandenen Exportrahmen wird der Maßstab automatisch berechnet und das Feld ist gesperrt. Die PDF bei 100 % drucken, nicht „An Seite anpassen“.']
  ];
  let active = null, pinned = false, closeTimer = null;
  const stopTimer = () => clearTimeout(closeTimer);
  function close() {
    stopTimer();
    if (active) { active.tip.hidden = true; active.button.setAttribute('aria-expanded', 'false'); }
    active = null; pinned = false;
  }
  function position() {
    if (!active) return;
    const { button, tip } = active, r = button.getBoundingClientRect();
    const w = document.documentElement.clientWidth, h = window.innerHeight, pad = 10;
    const sidebar = button.closest('aside')?.getBoundingClientRect();
    if (r.bottom < 0 || r.top > h || (sidebar && (r.bottom < sidebar.top || r.top > sidebar.bottom))) return close();
    tip.style.maxWidth = `${Math.max(1, Math.min(310, w - pad * 2))}px`;
    tip.style.maxHeight = `${Math.max(1, h - pad * 2)}px`;
    const size = tip.getBoundingClientRect();
    let top = r.bottom + 9;
    if (top + size.height > h - pad) top = r.top - size.height - 9;
    tip.style.left = `${Math.max(pad, Math.min(r.left, w - size.width - pad))}px`;
    tip.style.top = `${Math.max(pad, Math.min(top, h - size.height - pad))}px`;
  }
  function show(entry, pin = false) {
    stopTimer();
    if (active !== entry) { close(); active = entry; }
    pinned = pin || pinned;
    entry.tip.hidden = false; entry.button.setAttribute('aria-expanded', 'true'); position();
  }
  function later() {
    stopTimer();
    closeTimer = setTimeout(() => {
      if (active && !pinned && document.activeElement !== active.button) close();
    }, 140);
  }
  for (const [id, title, text] of entries) {
    const target = document.getElementById(id);
    if (!target) continue;
    const label = target.closest('label') || document.querySelector(`label[for="${id}"]`);
    const subject = label || target;
    const row = document.createElement('div'); row.className = 'help-field';
    if (label?.classList.contains('check')) row.classList.add('help-field-check');
    if (label && !label.contains(target)) row.classList.add('help-field-caption');
    if (!label) row.classList.add('help-field-content');
    subject.before(row); row.append(subject);
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'help-button'; button.textContent = '?';
    button.setAttribute('aria-label', `Hilfe: ${title}`);
    button.setAttribute('aria-expanded', 'false'); button.setAttribute('aria-describedby', `help-${id}`);
    const tip = document.createElement('div'); tip.id = `help-${id}`;
    tip.className = 'context-help'; tip.setAttribute('role', 'tooltip'); tip.hidden = true; tip.textContent = text;
    (button.closest('dialog') || subject.closest('dialog') || document.body).append(tip);
    row.append(button);
    const entry = { button, tip };
    button.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse') show(entry); });
    button.addEventListener('pointerleave', later);
    button.addEventListener('focus', () => show(entry));
    button.addEventListener('blur', later);
    button.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); if (active === entry && pinned) close(); else show(entry, true); });
    tip.addEventListener('pointerenter', stopTimer); tip.addEventListener('pointerleave', later);
  }
  document.addEventListener('pointerdown', e => { if (active && !active.button.contains(e.target) && !active.tip.contains(e.target)) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && active) { e.preventDefault(); e.stopPropagation(); close(); } }, true);
  document.addEventListener('scroll', e => { if (active && !active.tip.contains(e.target)) position(); }, true);
  window.addEventListener('resize', position);
})();
