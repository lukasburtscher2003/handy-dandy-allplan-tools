// A dependency-free orthographic point view; no interpolated mesh hides missing data.
let terrainData=null,angle=-.65,tilt=.7,zoom=1,drag=null;
const canvas=document.getElementById('terrainCanvas'),dialog=document.getElementById('terrainDialog');
function showTerrain(data){terrainData=data;angle=-.65;tilt=.7;zoom=1;dialog.showModal();const t=data.terrain;document.getElementById('terrainInfo').textContent=`Oberfläche: ${t.originalOutputPoints} Messpunkte · Bodenpunkte: ${t.interpolatedGridPoints} berechnete Punkte · ${t.boundaryPoints} Randpunkte. ${data.gaps.length} Positionen ohne sichere Höhen.${data.displaySampled?' Die Ansicht ist ausgedünnt; der Export bleibt vollständig.':''}`;renderTerrain()}
function renderTerrain(){if(!terrainData||!dialog.open)return;const d=terrainData,rect=canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1;canvas.width=rect.width*ratio;canvas.height=rect.height*ratio;const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);ctx.fillStyle='#eef0f2';ctx.fillRect(0,0,rect.width,rect.height);
 const all=[...d.measured,...d.grid,...d.boundary],b=d.bbox;if(!all.length)return;const zmin=all.reduce((m,p)=>Math.min(m,p[2]),Infinity),zmax=all.reduce((m,p)=>Math.max(m,p[2]),-Infinity),cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2,cz=(zmin+zmax)/2;
 const scale=zoom*Math.min(rect.width,rect.height)*.65/Math.max(b[2]-b[0],b[3]-b[1],zmax-zmin,1),ca=Math.cos(angle),sa=Math.sin(angle),ct=Math.cos(tilt),st=Math.sin(tilt);
 function project(p){const x=p[0]-cx,y=p[1]-cy,z=p[2]-cz,u=x*ca-y*sa,v=x*sa+y*ca;return [rect.width/2+u*scale,rect.height/2-(v*ct+z*st)*scale,v*st-z*ct]}
 const points=[...d.measured.map(p=>[p,'#268b64']),...d.grid.map(p=>[p,'#a451b2']),...d.boundary.map(p=>[p,'#dc8b23'])].map(([p,c])=>[project(p),c]).sort((a,b)=>a[0][2]-b[0][2]);
 for(const [p,color]of points){ctx.fillStyle=color;ctx.beginPath();ctx.arc(p[0],p[1],color==='#dc8b23'?3:2,0,Math.PI*2);ctx.fill()}
 ctx.strokeStyle='#bc3434';for(const p of d.gaps){const q=project([p[0],p[1],zmin]);ctx.beginPath();ctx.moveTo(q[0]-4,q[1]-4);ctx.lineTo(q[0]+4,q[1]+4);ctx.moveTo(q[0]+4,q[1]-4);ctx.lineTo(q[0]-4,q[1]+4);ctx.stroke()}
 ctx.fillStyle='#183831';ctx.font='12px Segoe UI';ctx.fillText(`Höhen ${zmin.toFixed(2)}–${zmax.toFixed(2)} m · EPSG:5778`,16,24);ctx.fillText('X Ost / Y Nord · Meter',16,rect.height-16);
}
canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)};
canvas.onpointermove=e=>{if(!drag)return;angle+=(e.clientX-drag[0])*.008;tilt=Math.max(.05,Math.min(1.5,tilt+(e.clientY-drag[1])*.008));drag=[e.clientX,e.clientY];renderTerrain()};canvas.onpointerup=()=>drag=null;canvas.onpointercancel=()=>drag=null;
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.25,Math.min(5,zoom*Math.exp(-e.deltaY*.001)));renderTerrain()},{passive:false});window.addEventListener('resize',renderTerrain);document.getElementById('closeTerrain').onclick=()=>dialog.close();
