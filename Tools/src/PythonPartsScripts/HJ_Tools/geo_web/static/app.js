const $=id=>document.getElementById(id);
Object.assign(L.drawLocal.draw.toolbar.buttons,{rectangle:'Rechteck zeichnen'});
Object.assign(L.drawLocal.draw.toolbar.actions,{title:'Zeichnen abbrechen',text:'Abbrechen'});
L.drawLocal.draw.handlers.rectangle.tooltip.start='Klicken und ziehen, um den Rahmen zu zeichnen.';
L.drawLocal.draw.handlers.simpleshape.tooltip.end='Loslassen, um den Rahmen festzulegen.';
Object.assign(L.drawLocal.edit.toolbar.buttons,{edit:'Rahmen bearbeiten',editDisabled:'Noch kein Rahmen gewählt',remove:'Rahmen löschen',removeDisabled:'Noch kein Rahmen gewählt'});
Object.assign(L.drawLocal.edit.toolbar.actions.save,{title:'Änderungen übernehmen',text:'Speichern'});
Object.assign(L.drawLocal.edit.toolbar.actions.cancel,{title:'Änderungen verwerfen',text:'Abbrechen'});
Object.assign(L.drawLocal.edit.toolbar.actions.clearAll,{title:'Rahmen löschen',text:'Alle löschen'});
Object.assign(L.drawLocal.edit.handlers.edit.tooltip,{text:'Ecken ziehen, um den Rahmen anzupassen.',subtext:'Speichern übernimmt die Änderung.'});
L.drawLocal.edit.handlers.remove.tooltip.text='Rahmen anklicken, um ihn zu löschen.';
proj4.defs('EPSG:31254','+proj=tmerc +lat_0=0 +lon_0=10.3333333333333 +k=1 +x_0=0 +y_0=-5000000 +ellps=bessel +towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs');
const gk=p=>proj4('EPSG:4326','EPSG:31254',p), ll=p=>proj4('EPSG:31254','EPSG:4326',p);
const map=L.map('map',{zoomControl:true}).setView([47.4125,9.7415],13);
const aerial=L.tileLayer.wms('https://vogis.cnv.at/mapserver/mapserv?MAP=i_luftbilder_r_wms.map',{layers:'ef2025_10cm',format:'image/jpeg',version:'1.1.1',maxZoom:22,attribution:'Land Vorarlberg · VOGIS · Orthofoto 2025'}).addTo(map);
const parcelLayer=L.geoJSON(null,{style:{color:'#e1ef99',weight:1.3,fillOpacity:0},onEachFeature:(f,l)=>{l.bindTooltip(`KG ${f.properties.kg} · ${f.properties.gnr}`,{sticky:true});l.on('click',()=>chooseParcel(f))}}).addTo(map);
const labelLayer=L.layerGroup().addTo(map), selection=L.featureGroup().addTo(map);
const drawControl=new L.Control.Draw({draw:{rectangle:{shapeOptions:{color:'#feeb6b',weight:3,fillOpacity:.12}},polygon:false,polyline:false,circle:false,circlemarker:false,marker:false},edit:{featureGroup:selection,remove:true}});map.addControl(drawControl);
let selectedParcel=null;
let bbox=null,jobId=null,poll=null,mapAbort=null,searchAbort=null,selectionRevision=0,estimateTimer=null,previewToken=null,pollingJob=false;
const categoryColors={selected:'#43ac7c',buffer:'#408bd4',adjacent:'#e59836',enclosed:'#a260c4'};
const marginLayer=L.layerGroup().addTo(map);
const chosenLayer=L.geoJSON(null,{style:{color:'#00c9dd',weight:5,fillOpacity:.10}}).addTo(map);
const previewLayer=L.geoJSON(null,{style:f=>({color:categoryColors[f.properties._selection]||'#43ac7c',weight:3,fillOpacity:.17}),onEachFeature:(f,l)=>{l.on('click',()=>chooseParcel(f));l.bindTooltip(`${({selected:'Berührt',buffer:'Zusatzrahmen',adjacent:'Nachbar',enclosed:'Eingeschlossen'})[f.properties._selection]} · KG ${f.properties.kg} · ${f.properties.gnr}`)}}).addTo(map);
const searchHighlight=L.geoJSON(null,{style:{color:'#58b8eb',weight:4,fillOpacity:.12},pointToLayer:(f,p)=>L.circleMarker(p,{radius:10,color:'#58b8eb',fillOpacity:.7})}).addTo(map);
const formatter=new Intl.NumberFormat('de-DE',{maximumFractionDigits:1});
function status(message,bad=false){$('status').textContent=message;$('status').classList.toggle('warning',bad)}
async function api(url,options={}){const r=await fetch(url,options);const d=await r.json();if(!r.ok)throw new Error(d.error||'Anfrage fehlgeschlagen');return d}
function options(){return {bbox,types:['terrain','parcels','aerial'].filter(id=>$(id).checked),grid:Number($('grid').value),boundarySpacing:Number($('boundarySpacing').value),terrainMode:$('terrainMode').value,originMode:$('originMode').value,offset:[Number($('offsetX').value),Number($('offsetY').value)],previewToken,year:Number($('year').value),raw:$('raw').checked,includeAdjacent:$('includeAdjacent').checked,dkmMargin:$('useDkmMargin').checked?Number($('dkmMargin').value):0,parcelDecimals:Number($('parcelDecimals').value),labelColor:$('labelColor').value,labelHeight:Number($('labelHeight').value),selectedParcel:selectedParcel?{kg:selectedParcel.properties.kg,gnr:selectedParcel.properties.gnr}:null,formatsByType:Object.fromEntries(['terrain','parcels','aerial'].map(t=>[t,[...document.querySelectorAll(`[data-type="${t}"]:checked`)].map(e=>e.dataset.format)]))}}
function chooseParcel(f){selectedParcel=f;chosenLayer.clearLayers();chosenLayer.addData(f);$('frameMode').querySelector('[value="parcel"]').disabled=false;$('chosenParcel').textContent=`Gewählt: KG ${f.properties.kg} · Grundstück ${f.properties.gnr}`;}
function drawMargin(){marginLayer.clearLayers();if(!bbox||!$('useDkmMargin').checked||!$('showDkmFrame').checked)return;const m=Number($('dkmMargin').value);if(!Number.isFinite(m))return;const b=[bbox[0]-m,bbox[1]-m,bbox[2]+m,bbox[3]+m];L.polygon([[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]].map(p=>{const q=ll(p);return [q[1],q[0]]}),{color:'#408bd4',dashArray:'7 7',weight:2,fill:false,interactive:false}).addTo(marginLayer)}
function summaries(){for(const t of ['terrain','parcels','aerial'])$(t+'Formats').textContent='Export: '+options().formatsByType[t].map(f=>f.toUpperCase()).join(', ');document.documentElement.style.setProperty('--parcel-number',({magenta:'#e0007a',black:'#000',green:'#008c46'})[$('labelColor').value]);$('offsetX').disabled=$('offsetY').disabled=$('originMode').value!=='custom';$('dkmMargin').disabled=!$('useDkmMargin').checked;drawMargin()}

function setBox(b){bbox=b.map(v=>Math.round(v*10)/10);if(typeof syncPrintAreaControls==='function')syncPrintAreaControls();const w=bbox[2]-bbox[0],h=bbox[3]-bbox[1];$('width').value=w.toFixed(1);$('height').value=h.toFixed(1);$('area').textContent=`${formatter.format(w)} × ${formatter.format(h)} m · ${formatter.format(w*h)} m²`;$('export').disabled=true;$('terrainPreview').disabled=true;previewToken=null;selectionRevision++;clearTimeout(estimateTimer);estimateTimer=setTimeout(estimate,250)}
function layerBox(layer){const corners=layer.getLatLngs().flat(Infinity).map(p=>gk([p.lng,p.lat]));setBox([Math.min(...corners.map(p=>p[0])),Math.min(...corners.map(p=>p[1])),Math.max(...corners.map(p=>p[0])),Math.max(...corners.map(p=>p[1]))])}
function redraw(){drawMargin();selection.clearLayers();if(!bbox)return;const corners=[[bbox[0],bbox[1]],[bbox[2],bbox[1]],[bbox[2],bbox[3]],[bbox[0],bbox[3]]].map(p=>{const q=ll(p);return [q[1],q[0]]});L.polygon(corners,{color:'#feeb6b',weight:3,fillOpacity:.12}).addTo(selection)}
map.on(L.Draw.Event.CREATED,e=>{selection.clearLayers();selection.addLayer(e.layer);layerBox(e.layer);redraw()});map.on(L.Draw.Event.EDITED,e=>{e.layers.eachLayer(layerBox);redraw()});map.on(L.Draw.Event.DELETED,()=>clearBox());
function clearBox(){bbox=null;if(typeof syncPrintAreaControls==='function')syncPrintAreaControls();marginLayer.clearLayers();selection.clearLayers();$('area').textContent='Noch kein Rahmen gewählt';$('estimate').textContent='Kein festes Flächenlimit. Große Exporte benötigen mehr Ressourcen.';$('export').disabled=true;$('terrainPreview').disabled=true;previewLayer.clearLayers();$('previewCard').hidden=true;previewToken=null;selectionRevision++}
$('draw').onclick=()=>new L.Draw.Rectangle(map,drawControl.options.draw.rectangle).enable();$('clear').onclick=clearBox;
$('resize').onclick=()=>{const mode=$('frameMode').value;if(mode==='parcel'&&!selectedParcel)return status('Zuerst ein Grundstück wählen.',true);const c=mode==='parcel'?selectedParcel.properties._centerGK:mode==='map'||!bbox?gk([map.getCenter().lng,map.getCenter().lat]):[(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2];const w=Number($('width').value),h=Number($('height').value);if(!Number.isFinite(w+h)||w<=0||h<=0)return status('Gültige Maße eingeben.',true);setBox([c[0]-w/2,c[1]-h/2,c[0]+w/2,c[1]+h/2]);redraw();map.fitBounds(selection.getBounds(),{padding:[100,100]})};
async function estimate(){if(!bbox)return;const rev=selectionRevision;try{const d=await api('/api/estimate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(options())});if(rev!==selectionRevision)return;$('estimate').textContent=`${d.options.raw ? "Alle Bodenmesspunkte + " + d.boundaryPoints + " Randpunkte" : "Bis zu etwa " + formatter.format(d.gridPoints) + " Gelände- und Randpunkte"} · Luftbild ca. ${formatter.format(d.aerialUncompressedMB)} MB vor Komprimierung.`;await loadPreview(rev);if(rev!==selectionRevision)return;$('export').disabled=!!jobId;$('terrainPreview').disabled=!!jobId;if(!jobId)status('')}catch(e){if(rev!==selectionRevision)return;status(e.message,true);$('export').disabled=true}}
document.querySelectorAll('section input[type=checkbox],section select,#boundarySpacing,#dkmMargin,#parcelDecimals,#labelHeight,#offsetX,#offsetY').forEach(el=>el.addEventListener('change',()=>{if(['frameMode','showDkmFrame','kgFilter','searchKind'].includes(el.id)){summaries();return}selectionRevision++;previewToken=null;$('export').disabled=true;summaries();estimate()}));
$('year').onchange=()=>{map.attributionControl.removeAttribution(aerial.options.attribution);aerial.options.attribution='Land Vorarlberg · VOGIS · Orthofoto '+$('year').value;map.attributionControl.addAttribution(aerial.options.attribution);aerial.setParams({layers:'ef'+$('year').value+'_10cm'});$('mapTitle').textContent='Luftbild '+$('year').value;selectionRevision++;previewToken=null;$('export').disabled=true;estimate()};
$('raw').addEventListener('change',()=>{$('grid').disabled=$('gridSlider').disabled=$('raw').checked;$('terrainMode').disabled=$('raw').checked});
async function search(event){event.preventDefault();status('');searchAbort?.abort();searchAbort=new AbortController();$('results').replaceChildren();$('searchButton').disabled=true;try{const d=await api('/api/search?'+new URLSearchParams({q:$('search').value,kind:$('searchKind').value,kg:$('kgFilter').value}),{signal:searchAbort.signal});for(const f of d.results){const button=document.createElement('button');button.type='button';button.className='result';const category=document.createElement('span');category.textContent=f.category;button.append(category,document.createTextNode(f.label));button.onclick=()=>{searchHighlight.clearLayers();if(f.feature){if(f.feature.properties?.kg&&f.feature.properties?.gnr)chooseParcel(f.feature);searchHighlight.addData(f.feature);map.fitBounds(searchHighlight.getBounds(),{maxZoom:18,padding:[90,90]})}else map.flyTo([f.lat,f.lon],18);document.querySelectorAll('.result').forEach(b=>b.classList.remove('active'));button.classList.add('active');status(f.label);};$('results').append(button)}if(!d.results.length)$('results').textContent='Keine Treffer. Suche mit Gemeinde oder KG präzisieren.';if(d.warnings?.length)status(d.warnings.join(' '),true)}catch(e){if(e.name!=='AbortError')status(e.message,true)}finally{$('searchButton').disabled=false}}
$('searchForm').onsubmit=search;
async function refreshParcels(){mapAbort?.abort();const zoom=map.getZoom();parcelLayer.clearLayers();labelLayer.clearLayers();if(zoom<16){$('mapNote').textContent='Zoome hinein, um Grundstücke zu sehen.';return}if(!$('showParcels').checked&&!$('showLabels').checked)return;mapAbort=new AbortController();try{const b=map.getBounds();const d=await api('/api/parcels?bbox='+[b.getWest(),b.getSouth(),b.getEast(),b.getNorth()].join(','),{signal:mapAbort.signal});parcelLayer.addData(d);if(d.zoomIn){$('mapNote').textContent='Für Grundstücke näher heranzoomen.';return}for(const f of d.features){const anchor=f.properties._label,center=anchor?L.latLng(anchor[1],anchor[0]):L.geoJSON(f).getBounds().getCenter();const el=document.createElement('span');el.textContent=f.properties.gnr;L.marker(center,{interactive:false,keyboard:false,icon:L.divIcon({className:'parcel-label',html:el,iconSize:[60,18]})}).addTo(labelLayer)}$('mapNote').textContent=`${d.features.length} Grundstücke · DKM / BEV`}catch(e){if(e.name!=='AbortError')$('mapNote').textContent='Grundstücke konnten nicht geladen werden: '+e.message}}
let moveTimer;map.on('moveend',()=>{clearTimeout(moveTimer);moveTimer=setTimeout(refreshParcels,300)});map.on('mousemove',e=>{const p=gk([e.latlng.lng,e.latlng.lat]);$('coordinates').textContent=`GK West · ${formatter.format(p[0])} / ${formatter.format(p[1])} m`});
for(const [id,layer] of [['showAerial',aerial],['showParcels',parcelLayer],['showLabels',labelLayer]])$(id).onchange=()=>{$(id).checked?layer.addTo(map):map.removeLayer(layer);if(id!=='showAerial')refreshParcels()};
aerial.on('tileerror',()=>{$('mapNote').textContent='Luftbild-Kartenabruf fehlgeschlagen. Bitte Verbindung prüfen.'});
$('export').onclick=async()=>{if(!bbox)return;$('export').disabled=true;$('downloads').replaceChildren();try{const d=await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(options())});jobId=d.id;$('terrainPreview').disabled=true;$('refreshIndex').disabled=true;$('progress').hidden=false;$('cancel').hidden=false;poll=setInterval(pollJob,1200);pollJob()}catch(e){status(e.message,true);$('export').disabled=false}};
async function pollJob(){const id=jobId;if(!id||pollingJob)return;pollingJob=true;try{const d=await api('/api/jobs/'+id);if(jobId!==id)return;status(d.message,d.state==='error');$('progress').value=d.progress;if(['done','error','cancelled'].includes(d.state)){clearInterval(poll);$('cancel').hidden=true;if(d.state==='done'){if(d.kind==='preview')showTerrain(await api(`/api/jobs/${id}/files/gelaende-vorschau.json`));else if(d.kind==='index')refreshIndexStatus();else{appendDownloads($('downloads'),d);if(d.metadata?.warnings?.length)status('Fertig. '+d.metadata.warnings.join(' '),true)}}jobId=null;$('export').disabled=!bbox||!previewToken;$('terrainPreview').disabled=!bbox;$('refreshIndex').disabled=false;refreshHistory()}}catch(e){clearInterval(poll);status(e.message,true);$('cancel').hidden=true;$('export').disabled=!bbox||!previewToken;$('terrainPreview').disabled=!bbox;jobId=null}finally{pollingJob=false}}
$('cancel').onclick=async()=>{if(jobId){const d=await api('/api/jobs/'+jobId+'/cancel',{method:'POST'});status(d.message)}};

async function loadPreview(rev){$('previewCard').hidden=false;$('previewSummary').textContent='Grundstücksauswahl wird geprüft …';previewLayer.clearLayers();const d=await api('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...options(),previewToken:null})});if(rev!==selectionRevision)return;previewToken=d.token;previewLayer.addData(d.features);$('previewSummary').textContent=`${d.features.length} Grundstücke: ${d.categoryCounts.selected} am Rahmen, ${d.categoryCounts.buffer} im Zusatzrahmen, ${d.adjacentCount} Nachbarn, ${d.enclosedCount} eingeschlossen · ${formatter.format(d.width)} × ${formatter.format(d.height)} m`;$('coverage').textContent=`Passende Geländekacheln: ${d.coveragePercent} %. Messlücken werden beim Export geprüft.`}
function appendDownloads(target,d){
  if(window.chrome?.webview && d.metadata?.allplanImportVersion===1){
    const button=document.createElement('button');
    button.className='primary';
    button.textContent='Geodaten in Allplan übernehmen';
    button.onclick=()=>window.chrome.webview.postMessage({action:'importGeodata',job:d.id});
    target.append(button);
  }
  for(const f of ['geodaten.zip',...d.files.filter(f=>f!=='geodaten.zip')]){
    const a=document.createElement('a');
    a.href=`/api/jobs/${d.id}/files/${encodeURIComponent(f)}`;
    a.textContent=f==='geodaten.zip'?'↓ Alle Daten als ZIP':'↓ '+f;
    target.append(a);
  }
}
async function refreshHistory(){try{const d=await api('/api/jobs');$('history').replaceChildren();for(const j of d.jobs){const item=document.createElement('details'),summary=document.createElement('summary');summary.textContent=`${new Date(j.created*1000).toLocaleString('de-DE')} · ${j.state==='done'?'Fertig':j.state==='error'?'Fehlgeschlagen':j.state==='cancelled'?'Abgebrochen':'Läuft'}`;item.append(summary);const info=document.createElement('p');info.textContent=j.message;item.append(info);if(j.state==='done')appendDownloads(item,j);const retry=document.createElement('button');retry.className='text';retry.textContent='Auswahl wiederherstellen / erneut exportieren';retry.onclick=()=>{if(jobId)return status('Bitte laufenden Auftrag abwarten.',true);const o=j.options||j.metadata.options;for(const t of ['terrain','parcels','aerial'])$(t).checked=o.types.includes(t);for(const f of document.querySelectorAll('[data-format]'))f.checked=(o.formatsByType?.[f.dataset.type]||o.formats||[]).includes(f.dataset.format);for(const k of ['grid','year','boundarySpacing','terrainMode'])$(k).value=o[k]??({grid:5,year:2025,boundarySpacing:o.grid||5,terrainMode:'measured'}[k]);for(const k of ['raw','includeAdjacent'])$(k).checked=!!o[k];$('gridSlider').value=$('grid').value;$('originMode').value=o.originMode||(o.localOrigin?'frame':'world');$('offsetX').value=o.offset?.[0]||0;$('offsetY').value=o.offset?.[1]||0;$('useDkmMargin').checked=!!o.dkmMargin;$('dkmMargin').value=o.dkmMargin||50;for(const k of ['parcelDecimals','labelColor','labelHeight'])$(k).value=o[k]??({parcelDecimals:3,labelColor:'magenta',labelHeight:1.5}[k]);selectedParcel=null;chosenLayer.clearLayers();$('frameMode').value='free';$('frameMode').querySelector('[value=parcel]').disabled=true;$('chosenParcel').textContent='Grundstück auswählen.';if(o.selectedParcel)api('/api/parcel?'+new URLSearchParams(o.selectedParcel)).then(chooseParcel).catch(e=>status(e.message,true));summaries();$('grid').disabled=$('gridSlider').disabled=$('raw').checked;$('terrainMode').disabled=$('raw').checked;aerial.setParams({layers:'ef'+o.year+'_10cm'});setBox(o.bbox);redraw();map.fitBounds(selection.getBounds(),{padding:[90,90]});status('Auswahl wiederhergestellt. Vorschau prüfen und Export starten.');};item.append(retry);$('history').append(item)}}catch(e){$('history').textContent=e.message}}
async function startAuxiliary(url){if(jobId)return;try{const d=await api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(options())});jobId=d.id;$('export').disabled=true;$('terrainPreview').disabled=true;$('refreshIndex').disabled=true;$('progress').hidden=false;$('cancel').hidden=false;poll=setInterval(pollJob,1200);pollJob()}catch(e){status(e.message,true)}}
$('terrainPreview').onclick=()=>startAuxiliary('/api/terrain-preview');$('refreshIndex').onclick=()=>startAuxiliary('/api/index/refresh');
async function refreshIndexStatus(){try{const d=await api('/api/index');$('indexStatus').textContent=`LiDAR 2023 · ${d.tiles} Kacheln · geprüft: ${d.updated}` }catch(e){$('indexStatus').textContent=e.message}}
$('recenter').onclick=()=>{if(!bbox)return;const c=gk([map.getCenter().lng,map.getCenter().lat]),w=bbox[2]-bbox[0],h=bbox[3]-bbox[1];setBox([c[0]-w/2,c[1]-h/2,c[0]+w/2,c[1]+h/2]);redraw()};
let moving=false,moveStart=null;
$('moveFrame').onclick=()=>{moving=!moving;$('moveFrame').textContent=moving?'Verschieben beenden':'Rahmen verschieben';status(moving?'Rahmen anklicken und ziehen.':'')};
map.on('mousedown',e=>{if(!moving||!bbox)return;const p=gk([e.latlng.lng,e.latlng.lat]);if(p[0]<bbox[0]||p[0]>bbox[2]||p[1]<bbox[1]||p[1]>bbox[3])return;moveStart={p,b:[...bbox]};map.dragging.disable()});
map.on('mousemove',e=>{if(!moveStart)return;const p=gk([e.latlng.lng,e.latlng.lat]),dx=p[0]-moveStart.p[0],dy=p[1]-moveStart.p[1];bbox=moveStart.b.map((v,i)=>v+(i%2?dy:dx));redraw()});
function finishMove(){if(!moveStart)return;moveStart=null;map.dragging.enable();setBox(bbox);redraw()}map.on('mouseup',finishMove);window.addEventListener('mouseup',finishMove);
api('/api/kgs').then(d=>{for(const kg of d.rows){const o=document.createElement('option');o.value=kg.code;o.textContent=`${kg.name} · ${kg.code}`;$('kgFilter').append(o)}}).catch(e=>status(e.message,true));refreshHistory();refreshIndexStatus();

for(const id of ['gridSlider','grid'])$(id).addEventListener('input',()=>{$(id==='grid'?'gridSlider':'grid').value=$(id).value;selectionRevision++;previewToken=null;$('export').disabled=true;clearTimeout(estimateTimer);estimateTimer=setTimeout(estimate,350)});
$('frameMode').addEventListener('change',()=>{$('draw').disabled=$('frameMode').value!=='free'});summaries();
if(window.chrome?.webview){
  $('originMode').value='frame';
  $('terrain').checked=true;
  $('aerial').checked=true;
  document.querySelectorAll('[data-type="terrain"]').forEach(el=>el.checked=el.dataset.format==='xyz');
  document.querySelectorAll('[data-type="aerial"]').forEach(el=>el.checked=el.dataset.format==='png');
  document.querySelectorAll('[data-type="parcels"]').forEach(el=>el.checked=el.dataset.format==='geojson');
  $('export').textContent='Geodaten für Allplan vorbereiten';
  summaries();
}


// Maßstäblicher PDF-Druckrahmen, unabhängig von der CAD-/Datenauswahl.
const printFrameLayer=L.layerGroup().addTo(map);
let printFrameVisible=false,printFrame=null,printCenter=null,printFrameDrag=null;
const usesExportFrame=()=>$('printAreaMode').value==='export';
function scaleForExportFrame(){
  if(!bbox)return null;const [pw,ph]=printPaperDimensions();
  const raw=Math.ceil(Math.max((bbox[2]-bbox[0])*1000/(pw-24),(bbox[3]-bbox[1])*1000/(ph-43)));
  return Math.max(50,Math.ceil(raw/50)*50);
}
function syncPrintAreaControls(){
  const cad=usesExportFrame();
  $('printScale').readOnly=cad;
  $('printFrameToggle').hidden=cad;
  $('printFrameCenter').hidden=cad;
  if(cad){const scale=scaleForExportFrame();if(scale!==null)$('printScale').value=scale;}
  $('printFrameInfo').textContent=cad?(bbox?`Exportrahmen: ${formatter.format(bbox[2]-bbox[0])} × ${formatter.format(bbox[3]-bbox[1])} m · Maßstab automatisch angepasst.`:'Zuerst in Schritt 02 einen Exportrahmen festlegen.'):'Papierformat und Maßstab bestimmen die Größe des Druckrahmens. Rahmen auf der Karte verschieben.';
}
function printPaperDimensions(){
  const p=$('printPaper').value==='A3'?[297,420]:[210,297];
  return $('printOrientation').value==='landscape'?[p[1],p[0]]:p;
}
function printSize(){
  const [w,h]=printPaperDimensions(),scale=Number($('printScale').value);
  if(!Number.isFinite(scale)||scale<50||scale>1000000)throw new Error('Maßstab zwischen 1:50 und 1:1.000.000 wählen.');
  // Muss mit den Papiermaßen in print_plan.py übereinstimmen.
  return [(w-24)*scale/1000,(h-43)*scale/1000];
}
function printBounds(){
  const [w,h]=printSize();const c=printCenter||gk([map.getCenter().lng,map.getCenter().lat]);
  return [c[0]-w/2,c[1]-h/2,c[0]+w/2,c[1]+h/2];
}
function updatePrintFrame(){
  printFrameLayer.clearLayers();printFrame=null;
  if(!printFrameVisible||usesExportFrame())return;
  let b;try{b=printBounds()}catch(e){$('printStatus').textContent=e.message;return}
  const coords=[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]].map(p=>{const q=ll(p);return [q[1],q[0]]});
  printFrame=L.polygon(coords,{color:'#ff6d24',weight:3,fillColor:'#fff5aa',fillOpacity:.12,dashArray:'10 5',className:'print-outline'}).addTo(printFrameLayer);
  printFrame.bindTooltip(`Druckbereich ${$('printPaper').value} · 1:${$('printScale').value} — zum Verschieben ziehen`,{sticky:true,className:'print-frame-label'});
  printFrame.on('mousedown',e=>{if(e.originalEvent?.button>0)return;L.DomEvent.stopPropagation(e.originalEvent);printFrameDrag={start:gk([e.latlng.lng,e.latlng.lat]),center:[...printCenter]};map.dragging.disable();});
  $('printFrameInfo').textContent=`Druckbereich: ${formatter.format(b[2]-b[0])} × ${formatter.format(b[3]-b[1])} m · Rahmen auf der Karte verschieben.`;
}
map.on('mousemove',e=>{
  if(!printFrameDrag)return;
  const p=gk([e.latlng.lng,e.latlng.lat]);
  printCenter=[printFrameDrag.center[0]+p[0]-printFrameDrag.start[0],printFrameDrag.center[1]+p[1]-printFrameDrag.start[1]];
  updatePrintFrame();
});
function finishPrintFrameMove(){if(printFrameDrag){printFrameDrag=null;map.dragging.enable()}}
map.on('mouseup',finishPrintFrameMove);window.addEventListener('mouseup',finishPrintFrameMove);
// Printing mode hides the CAD selection temporarily without deleting its geometry.
// Click into PDF settings to activate, click another sidebar section to return to CAD mode.
const printSection=$('printSection');
let cadLayersBeforePrint=null;
function setPrintMode(active){
  if(active===printFrameVisible)return;
  printFrameVisible=active;
  if(active){
    if(!printCenter)printCenter=gk([map.getCenter().lng,map.getCenter().lat]);
    cadLayersBeforePrint=[selection,marginLayer,previewLayer].filter(layer=>map.hasLayer(layer));
    cadLayersBeforePrint.filter(layer=>!usesExportFrame()||layer!==selection).forEach(layer=>map.removeLayer(layer));
  }else{
    (cadLayersBeforePrint||[]).forEach(layer=>{if(!map.hasLayer(layer))map.addLayer(layer)});
    cadLayersBeforePrint=null;
    finishPrintFrameMove();
  }
  document.body.classList.toggle('pdf-print-mode',active);
  $('printFrameToggle').textContent=active?'▣ Druckrahmen ausblenden':'▣ Druckrahmen auf Karte anzeigen';
  $('printFrameToggle').classList.toggle('print-frame-active',active);
  $('printFrameToggle').setAttribute('aria-pressed',String(active));
  syncPrintAreaControls();
  updatePrintFrame();
}
$('printAreaMode').addEventListener('change',()=>{
  if(printFrameVisible){
    if(usesExportFrame()){
      if(cadLayersBeforePrint?.includes(selection)&&!map.hasLayer(selection))map.addLayer(selection);
    }else if(map.hasLayer(selection))map.removeLayer(selection);
  }
  syncPrintAreaControls();updatePrintFrame();
});
$('printFrameToggle').onclick=()=>setPrintMode(!printFrameVisible);
$('printFrameCenter').onclick=()=>{
  printCenter=gk([map.getCenter().lng,map.getCenter().lat]);
  setPrintMode(true);
  updatePrintFrame();
};
// Activating the PDF section automatically switches from CAD selection to print preview.
printSection.addEventListener('pointerdown',event=>{
  if(event.target.closest('#printFrameToggle'))return;
  if(!printFrameVisible)setPrintMode(true);
});
printSection.addEventListener('focusin',event=>{
  if(event.target.id!=='printFrameToggle'&&!printFrameVisible)setPrintMode(true);
});
for(const section of document.querySelectorAll('aside > section')){
  if(section===printSection)continue;
  section.addEventListener('pointerdown',()=>{if(printFrameVisible)setPrintMode(false)});
  section.addEventListener('focusin',()=>{if(printFrameVisible)setPrintMode(false)});
}
for(const id of ['printPaper','printOrientation','printScale'])$(id).addEventListener('change',()=>{syncPrintAreaControls();updatePrintFrame()});
$('printScale').addEventListener('input',updatePrintFrame);
syncPrintAreaControls();

// Separater, maßstäblicher Druckexport (unabhängig vom Gelände-/CAD-Export).
$('printPdf').onclick=async()=>{
  if(!printFrameVisible){setPrintMode(true)}
  if(usesExportFrame()&&!bbox){$('printStatus').textContent='Zuerst in Schritt 02 einen Exportrahmen festlegen.';return}
  const button=$('printPdf');button.disabled=true;$('printStatus').textContent='PDF wird erstellt …';
  try{
    syncPrintAreaControls();
    const settings={bbox:usesExportFrame()?[...bbox]:printBounds(),autoScale:usesExportFrame(),printFrameOnly:true,paper:$('printPaper').value,orientation:$('printOrientation').value,scale:Number($('printScale').value),labels:$('printLabels').checked,year:Number($('year').value),title:$('printTitle').value,header:$('printHeader').value,footer:$('printFooter').value};
    const r=await fetch('/api/print-plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)});
    if(!r.ok){let e;try{e=await r.json()}catch{}throw new Error(e?.error||'PDF-Erstellung fehlgeschlagen.')}
    const blob=await r.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;
    a.download=`lageplan_${settings.paper}_1-${settings.scale}.pdf`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),15000);
    $('printStatus').textContent='Lageplan erstellt. Zum maßstäblichen Drucken 100 % verwenden.';
  }catch(e){$('printStatus').textContent=e.message}finally{button.disabled=false}
};
