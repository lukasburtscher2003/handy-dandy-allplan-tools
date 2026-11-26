"""Local Vorarlberg exporter. Run with python server.py."""
import sys,os
from pathlib import Path
RESOURCE = Path(__file__).resolve().parent
HERE = RESOURCE
from . import parcel_rules
import concurrent.futures, datetime, json, math, re, threading, time, uuid, zipfile, warnings, hashlib
import numpy as np
import requests, laspy, rasterio, ezdxf
from flask import Flask, request, jsonify, send_from_directory
from pyproj import Transformer, CRS
from shapely.geometry import shape, box, mapping
from shapely.ops import transform
from shapely.ops import unary_union
from scipy.spatial import cKDTree
from rasterio.transform import from_origin
from rasterio.windows import Window
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
HTTP=requests.Session()
HTTP.mount('https://',HTTPAdapter(max_retries=Retry(total=2,connect=2,read=1,status=2,backoff_factor=.5,status_forcelist=[429,502,503,504],allowed_methods=['GET'],respect_retry_after_header=False)))

CRS_CODE = 'EPSG:31254'
WFS = 'https://vogis.cnv.at/geoserver/vogis/wfs'
MAP = 'https://vogis.cnv.at/mapserver/mapserv'
DL = 'https://vogis.cnv.at/geodaten/api/public/dl/OTSj-JMs'
CACHE = HERE / 'cache'
OUTPUT = HERE / 'exports'
INDEX = json.loads((RESOURCE / 'data/copc-index-2023.json').read_text(encoding='utf-8'))
TO_GK = Transformer.from_crs(4326, 31254, always_xy=True)
TO_LL = Transformer.from_crs(31254, 4326, always_xy=True)
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1)
JOBS = {}; LOCK = threading.Lock(); PREVIEWS = {}
app = Flask(__name__, static_folder=str(RESOURCE/'static'), static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024
YEARS = {2025:'ef2025_10cm', 2022:'ef2022_10cm', 2020:'ef2020_10cm', 2018:'ef2018_10cm'}
POIS = {'schulen_vorarlberg':('Schule','name'), 'museen':('Museum','name'), 'oepnv_haltestellen':('Haltestelle','hst_name')}

class CachedRange:
    """Seekable, verified HTTP ranges; never downloads a full COPC file."""
    def __init__(self, tile, job):
        self.url=tile['source']; self.position=0; self.job=job
        self.folder=CACHE/('copc-'+tile['signature']); self.folder.mkdir(exist_ok=True)
    def seek(self,pos,whence=0):
        if whence!=0 or pos<0: raise ValueError('Ungültiger Bytebereich.')
        self.position=pos
    def tell(self): return self.position
    def read(self,n):
        update(self.job,self.job['progress'],self.job['message'])
        if not n: return b''
        if n<0 or n>64*1024*1024: raise ValueError('LiDAR-Teilabruf zu groß; Rahmen verkleinern.')
        p=self.folder/f'{self.position}-{n}.bin'
        if p.exists(): data=p.read_bytes()
        else:
            start=self.position; end=start+n-1
            r=HTTP.get(self.url,headers={'Range':f'bytes={start}-{end}','User-Agent':'Vorarlberg-Geodatenexport/1.0'},timeout=(15,90))
            r.raise_for_status()
            if r.status_code!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'): raise ValueError('Server unterstützt den benötigten LiDAR-Teilabruf nicht.')
            data=r.content
            if len(data)!=n: raise ValueError('Unvollständiger LiDAR-Teilabruf.')
            p.write_bytes(data)
        self.position+=n; return data
    def close(self): pass

def get(url, **kw):
    r = HTTP.get(url, timeout=(15, 90), headers={'User-Agent':'Vorarlberg-Geodatenexport/1.0'}, **kw)
    r.raise_for_status(); return r

def wfs(layer, bbox=None, cql=None, limit=10000, truncate=False):
    """Paginate; fail rather than silently truncate an export."""
    params = {'service':'WFS','version':'2.0.0','request':'GetFeature', 'typeNames':'vogis:'+layer,
              'srsName':CRS_CODE,'outputFormat':'application/json','count':min(limit,1000)}
    if bbox: params['bbox'] = ','.join(map(str,bbox))+','+CRS_CODE
    if cql: params['CQL_FILTER'] = cql
    key=hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()
    cached=CACHE/('wfs-'+key+'.json')
    if cached.exists() and time.time()-cached.stat().st_mtime<900:
        rows=json.loads(cached.read_text(encoding='utf-8'))
        if truncate: return rows[:limit]
        if len(rows)>limit: raise ValueError('Zu viele Objekte. Bitte Auswahl verkleinern.')
        return rows
    rows = []
    while True:
        params['startIndex'] = len(rows)
        # GeoServer accepts WFS KVP POST too; large shell filters exceed URL limits.
        if len(requests.Request('GET',WFS,params=params).prepare().url)>6000:
            r=HTTP.post(WFS,data=params,timeout=(15,90));r.raise_for_status()
        else:r = get(WFS, params=params)
        try: data = r.json()
        except ValueError: raise ValueError('VOGIS konnte den Layer '+layer+' nicht liefern: '+r.text[:180])
        part = data.get('features',[]); rows.extend(part)
        if truncate:
            cached.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8'); return rows[:limit]
        total = data.get('numberMatched')
        if not part or (isinstance(total,int) and len(rows)>=total) or len(part)<params['count']: break
        if len(rows)>=limit: raise ValueError('Zu viele Objekte. Bitte Auswahl verkleinern.')
    if len(rows)>limit: raise ValueError('Zu viele Objekte. Bitte Auswahl verkleinern.')
    cached.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8'); return rows

def literal(s): return "'"+s.replace("'","''")+"'"
def like(s): return literal('%'+s.replace('%','').replace('_','')+'%')
def collection(rows): return {'type':'FeatureCollection','features':rows}
def ll_feature(f):
    g=shape(f['geometry']); properties=dict(f['properties'])
    if g.geom_type in ['Polygon','MultiPolygon']:
        p=g.representative_point(); properties['_label']=list(TO_LL.transform(p.x,p.y));center=g.centroid
        if not g.covers(center):center=p
        properties['_centerGK']=[center.x,center.y]
    return {'type':'Feature','id':f.get('id'),'geometry':mapping(transform(TO_LL.transform,g)),'properties':properties}
def intersect(a,b): return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]

def is_gk_west(crs):
    if crs is None: return False
    if crs.to_epsg()==31254: return True
    # VOGIS WKT uses a duplicate name and an unusual axis definition. Verify every
    # projection parameter and ellipsoid rather than trusting its authority tag.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return crs.to_dict()==CRS.from_epsg(31254).to_dict()

def validate(data):
    b = data.get('bbox')
    if not isinstance(b,list) or len(b)!=4: raise ValueError('Ein Rechteck auf der Karte auswählen.')
    b = [round(float(v),1) for v in b]
    if not all(math.isfinite(v) for v in b) or b[0]>=b[2] or b[1]>=b[3]: raise ValueError('Ungültiger Rahmen.')
    if not (-70000<=b[0]<b[2]<=5000 and 180000<=b[1]<b[3]<=285000): raise ValueError('Rahmen liegt außerhalb von Vorarlberg.')
    types = data.get('types',[])
    if not isinstance(types,list) or not types or any(t not in ['terrain','parcels','aerial'] for t in types): raise ValueError('Mindestens eine gültige Datenart wählen.')
    grid = float(data.get('grid',5))
    if not math.isfinite(grid) or not 0.5<=grid<=50: raise ValueError('Rasterweite muss zwischen 0,5 und 50 m liegen.')
    year = int(data.get('year',2025))
    if year not in YEARS: raise ValueError('Orthofoto-Jahr nicht unterstützt.')
    formats = data.get('formats', ['dxf','xyz','geojson','tif'])
    if not isinstance(formats,list) or any(t not in ['dxf','xyz','las','laz','geojson','tif','png','jpg'] for t in formats): raise ValueError('Ungültiges Exportformat.')
    requirements = {'terrain':{'dxf','xyz','las','laz'},'parcels':{'dxf','geojson'},'aerial':{'tif','png','jpg'}}
    if any(not requirements[t].intersection(formats) for t in types): raise ValueError('Für jede Datenart mindestens ein Format wählen.')
    boundary=float(data.get('boundarySpacing',grid))
    if not math.isfinite(boundary) or not .5<=boundary<=50: raise ValueError('Randabstand muss zwischen 0,5 und 50 m liegen.')
    mode=data.get('terrainMode','measured')
    if mode not in ['measured','interpolated']: raise ValueError('Unbekannte Geländeauswahl.')
    if data.get('raw',False):mode='measured'
    token=data.get('previewToken')
    if token:
        snapshot=PREVIEWS.get(token)
        if not snapshot or time.time()-snapshot['created']>1800: raise ValueError('Grundstücksvorschau abgelaufen. Vorschau erneut laden.')
        if snapshot['bbox']!=b or snapshot['includeAdjacent']!=bool(data.get('includeAdjacent',False)): raise ValueError('Rahmen oder Nachbaroption geändert. Vorschau erneut laden.')
    extra=parcel_rules.extra_options(data,b,formats,types)
    if token:
        if snapshot.get('dkmMargin',0)!=extra['dkmMargin'] or snapshot.get('hasParcels',True)!=('parcels' in types):raise ValueError('DKM-Auswahl geändert. Vorschau erneut laden.')
    return {**extra,'bbox':b,'types':types,'grid':grid,'year':year,'includeAdjacent':bool(data.get('includeAdjacent',False)),'raw':bool(data.get('raw',False)), 'boundarySpacing':boundary,'terrainMode':mode,'previewToken':token}

@app.before_request
def local_only():
    if request.host not in app.config.get('LOCAL_HOSTS',['127.0.0.1:8790','localhost:8790']): return jsonify(error='Nur lokaler Zugriff zulässig.'),403
    if request.method=='POST' and request.headers.get('Origin') not in [None,*app.config.get('LOCAL_ORIGINS',['http://127.0.0.1:8790','http://localhost:8790'])]: return jsonify(error='Fremder Ursprung.'),403

@app.errorhandler(Exception)
def error(e):
    from werkzeug.exceptions import HTTPException
    return jsonify(error=str(e)), e.code if isinstance(e,HTTPException) else 400

@app.get('/')
def home(): return app.send_static_file('index.html')

@app.post('/api/print-plan')
def print_plan():
    from flask import send_file
    from .print_plan import make_plan
    result=make_plan(sys.modules[__name__],request.get_json(silent=True))
    return send_file(result,mimetype='application/pdf',as_attachment=True,download_name='lageplan.pdf')

@app.get('/api/search')
def search():
    q = request.args.get('q','').strip()[:120]; kind=request.args.get('kind','all')
    if len(q)<2: return jsonify(results=[])
    out=[]; warnings=[]
    def add(rows, category, label):
        for f in rows[:15]:
            g=shape(f['geometry']); p=g.representative_point(); lon,lat=TO_LL.transform(p.x,p.y)
            out.append({'category':category,'label':label(f['properties']),'lon':lon,'lat':lat,'bbox':list(g.bounds),'id':f.get('id'),'feature':ll_feature(f)})
    if kind in ['all','address']:
        try:
            terms=q.split(); filters=[]
            for term in terms:
                filters.append('('+' OR '.join(f'{field} ILIKE {like(term)}' for field in ['strasse','hausnr','gemeinde','postleitza'])+')')
            add(wfs('adressen',cql=' AND '.join(filters),limit=15,truncate=True),'Adresse',lambda p:f"{p['strasse']} {p['hausnr']}, {p['postleitza']} {p['gemeinde']}")
        except Exception as e: warnings.append('Adresssuche: '+str(e))
    if kind in ['all','parcel','place']:
        try:
            add(wfs('kat_gem',cql='kgem_name ILIKE '+like(q)+' OR pgem_name ILIKE '+like(q)+' OR kg='+literal(q),limit=10,truncate=True),'Katastralgemeinde',lambda p:f"{p['kgem_name']} · KG {p['kg']} · {p['pgem_name']}")
        except Exception as e: warnings.append('Ortsuche: '+str(e))
    if kind in ['all','parcel'] and re.search(r'\d',q):
        try:
            tokens=q.replace(',',' ').split(); kg=next((t for t in tokens if re.fullmatch(r'9\d{4}',t)),None)
            numbers=[t for t in tokens if re.fullmatch(r'\.?\d+(?:/\d*)?',t) and t!=kg]
            if numbers:
                f='gnr ILIKE '+like(numbers[-1])
                words=' '.join(t for t in tokens if t not in numbers and t!=kg)
                if kg: f+=' AND kg='+literal(kg)
                elif words:
                    # KG lookup uses the verified cadastral layer, with schema populated at setup.
                    kgs=kg_lookup(words)
                    if kgs: f+=' AND kg IN ('+','.join(literal(k) for k in kgs)+')'
                    else: f+=' AND pgem_name ILIKE '+like(words)
                requested_kg=request.args.get('kg','')
                if requested_kg:
                    if not re.fullmatch(r'9\d{4}',requested_kg): raise ValueError('Ungültige KG-Nummer.')
                    f+=' AND kg='+literal(requested_kg)
                kg_path=CACHE/'kg.json'
                if not kg_path.exists():kg_path=HERE/'data/kg.json'
                kg_names={r['code']:r['name'] for r in json.loads(kg_path.read_text(encoding='utf-8'))} if kg_path.exists() else {}
                add(wfs('gst',cql=f,limit=15,truncate=True),'Grundstück',lambda p:f"{p['pgem_name']} · KG {kg_names.get(p['kg'],'')} {p['kg']} · Grundstück {p['gnr']}")
        except Exception as e: warnings.append('Grundstückssuche: '+str(e))
    if kind in ['all','poi']:
        for layer,(category,field) in POIS.items():
            try: add(wfs(layer,cql=f'{field} ILIKE {like(q)}',limit=10,truncate=True),category,lambda p,field=field:str(p[field]))
            except Exception as e: warnings.append(category+': '+str(e))
    return jsonify(results=out[:50],warnings=warnings)

def kg_lookup(word):
    path=CACHE/'kg.json'
    if not path.exists():path=HERE/'data/kg.json'
    if not path.exists(): return []
    rows=json.loads(path.read_text(encoding='utf-8'))
    return [r['code'] for r in rows if word.casefold() in r['name'].casefold()]

@app.get('/api/parcel')
def parcel_by_number():
    kg=request.args.get('kg','');gnr=request.args.get('gnr','')
    if not re.fullmatch(r'9\d{4}',kg) or not re.fullmatch(r'\.?\d+(?:/\d+)?',gnr):raise ValueError('KG oder Grundstücksnummer ungültig.')
    rows=wfs('gst',cql='kg='+literal(kg)+' AND gnr='+literal(gnr),limit=100)
    if len(rows)!=1:raise ValueError('Grundstück konnte nicht eindeutig geladen werden.')
    return jsonify(ll_feature(rows[0]))

@app.get('/api/parcels')
def parcels_map():
    ll=list(map(float,request.args['bbox'].split(',')))
    b=list(TO_GK.transform_bounds(*ll))
    if (b[2]-b[0])*(b[3]-b[1])>1000000: return jsonify(collection([]),zoomIn=True)
    rows=wfs('gst',bbox=b,limit=5000)
    return jsonify(collection([ll_feature(f) for f in rows]))

@app.post('/api/estimate')
def estimate():
    opts=validate(request.json); b=opts['bbox'];radius=max(10.,opts['grid']*2,opts.get('boundarySpacing',opts['grid'])*2)
    support=[b[0]-radius,b[1]-radius,b[2]+radius,b[3]+radius]
    tiles=[t for t in INDEX['tiles'] if intersect(t['bbox'],support)]
    area=(b[2]-b[0])*(b[3]-b[1]); cells=(math.floor(b[2]/opts['grid'])-math.floor(b[0]/opts['grid'])+1)*(math.floor(b[3]/opts['grid'])-math.floor(b[1]/opts['grid'])+1)
    edges=2*math.ceil((b[2]-b[0])/opts['boundarySpacing'])+2*math.ceil((b[3]-b[1])/opts['boundarySpacing'])
    return jsonify(options=opts,area=area,tiles=len(tiles),gridPoints=cells+edges,boundaryPoints=edges,aerialPixels=round(area/0.01),aerialUncompressedMB=round(area/0.01*3/1e6,1),warnings=['Quellenjahre: LiDAR 2023, Orthofoto '+str(opts['year'])+'. DKM ist ein aktueller Dienstabruf.','Die tatsächliche Abdeckung und Punktzahl werden während des Exports geprüft.'])

def update(job, progress, message):
    if job['cancel'].is_set(): raise InterruptedError('Export abgebrochen.')
    job.update(progress=progress,message=message)

def new_dxf():
    doc=ezdxf.new('R2010'); doc.units=6
    doc.header['$PDMODE']=3; doc.header['$PDSIZE']=0.3
    return doc

def terrain(job, opts, directory, meta):
    b=opts['bbox']; radius=max(10.,opts['grid']*2,opts.get('boundarySpacing',opts['grid'])*2)
    support=[b[0]-radius,b[1]-radius,b[2]+radius,b[3]+radius]
    tiles=[t for t in INDEX['tiles'] if intersect(t['bbox'],support)]
    if not tiles: raise ValueError('Keine LiDAR-Kacheln für diesen Rahmen.')
    if len(tiles)>8: raise ValueError('Mehr als 8 LiDAR-Kacheln; Rahmen verkleinern.')
    arrays=[]; header=None; count=0
    for i,t in enumerate(tiles):
        update(job,10+int(30*i/len(tiles)),f'Bodenpunkte lesen · Kachel {i+1}/{len(tiles)}')
        with laspy.CopcReader(CachedRange(t,job)) as reader:
            source_crs=reader.header.parse_crs()
            if not is_gk_west(source_crs): raise ValueError('LiDAR-Koordinatenbezug nicht bestätigt.')
            bounds=laspy.copc.Bounds(np.array([support[0],support[1],-10000.]),np.array([support[2],support[3],10000.]))
            nodes=laspy.copc.load_octree_for_query(reader.source,reader.copc_info,reader.root_page,query_bounds=bounds)
            if sum(n.point_count for n in nodes)>6000000: raise ValueError('LiDAR-Ausschnitt erfordert mehr als 6 Millionen Kandidatenpunkte pro Kachel. Rahmen verkleinern.')
            p=reader.query(bounds) # no resolution: every hierarchy level, preserves dimensions
            mask=(p.classification==2)&(~np.asarray(p.withheld,dtype=bool))
            p=p[mask]; count+=len(p)
            if count>5000000: raise ValueError('Mehr als 5 Millionen Bodenpunkte. Rahmen verkleinern.')
            if header is None: header=reader.header.copy()
            elif p.point_format!=arrays[0].point_format: raise ValueError('Kacheln mit unterschiedlichen Punktformaten.')
            arrays.append(p)
        meta['sources'].append({'type':'LiDAR','url':t['source'],'year':2023,'class':2})
    if not count: raise ValueError('Keine gültigen Bodenpunkte im Rahmen.')
    # Source scales and offsets can differ between tiles; convert all records into one common header.
    combined=laspy.ScaleAwarePointRecord.zeros(count,header=header); cursor=0
    for p in arrays:
        combined.array[cursor:cursor+len(p)]=p.array
        combined.x[cursor:cursor+len(p)]=p.x; combined.y[cursor:cursor+len(p)]=p.y; combined.z[cursor:cursor+len(p)]=p.z
        cursor+=len(p)
    xyz=np.column_stack((combined.x,combined.y,combined.z))
    inside=np.flatnonzero((xyz[:,0]>=b[0])&(xyz[:,0]<=b[2])&(xyz[:,1]>=b[1])&(xyz[:,1]<=b[3]))
    if not len(inside): raise ValueError('Keine Bodenpunkte innerhalb des Rahmens.')
    if opts['raw']: chosen=inside
    else: chosen=inside[grid_indices(xyz[inside],b,opts['grid'])]
    gaps=[]; interpolated=np.empty((0,3))
    if opts.get('terrainMode')=='interpolated' and not opts['raw']:
        xy=regular_xy(b,opts['grid']); heights=interpolate_heights(xyz,xy,radius)
        gaps=xy[~np.isfinite(heights)].tolist();interpolated=np.column_stack((xy,heights))[np.isfinite(heights)]
        chosen=np.array([],dtype=int)
        if gaps: meta['warnings'].append(f'{len(gaps)} Rasterpositionen ohne lokale Höhenquelle; im interpolierten Raster ausgelassen.')
    elif not opts['raw']:
        gaps=missing_cells(xyz[inside],b,opts['grid'])
        if gaps:meta['warnings'].append(f'{len(gaps)} innere Rasterzellen ohne Bodenmesspunkt bleiben leer.')
    edge=boundary_points(xyz,b,opts.get('boundarySpacing',opts['grid']),radius)
    original=combined[chosen]
    # Avoid duplicate XY if a selected original already coincides with an edge node.
    existing={tuple(p) for p in xyz[chosen,:2]}
    edge=np.array([p for p in edge if tuple(p[:2]) not in existing]).reshape(-1,3)
    derived=np.vstack((interpolated,edge))
    header.scales=np.array([.001,.001,.001])
    points=laspy.ScaleAwarePointRecord.zeros(len(original)+len(derived),header=header)
    points.array[:len(original)]=original.array
    points.x[:len(original)]=original.x;points.y[:len(original)]=original.y;points.z[:len(original)]=original.z
    if len(derived):
        points.x[len(original):]=derived[:,0];points.y[len(original):]=derived[:,1];points.z[len(original):]=derived[:,2]
        points.classification[len(original):]=2;points.synthetic[len(original):]=True
    coords=np.column_stack((points.x,points.y,points.z))
    update(job,48,f'{len(coords):,} Geländepunkte schreiben')
    if 'dxf' in opts['formats']:
        doc=new_dxf(); doc.layers.new('GELAENDEPUNKTE',dxfattribs={'color':3});doc.layers.new('GELAENDERAND',dxfattribs={'color':4});doc.layers.new('GELAENDERASTER',dxfattribs={'color':6})
        for i,p in enumerate(coords): doc.modelspace().add_point(tuple(p),dxfattribs={'layer':'GELAENDEPUNKTE' if i<len(original) else 'GELAENDERASTER' if i<len(original)+len(interpolated) else 'GELAENDERAND'})
        doc.saveas(directory/'gelaende.dxf')
    if 'xyz' in opts['formats']: np.savetxt(directory/'gelaende.xyz',coords,fmt='%.3f',header='X Y Z; EPSG:31254; Hoehe EPSG:5778; Meter')
    # COPC hierarchy VLRs are not valid for a newly written ordinary LAS/LAZ.
    header.vlrs=[v for v in header.vlrs if v.user_id!='copc']; header.evlrs=None
    las=laspy.LasData(header,points); las.header.add_crs(CRS.from_user_input('EPSG:31254+5778'))
    for fmt in ['las','laz']:
        if fmt in opts['formats']: las.write(directory/f'gelaende.{fmt}')
    meta['terrain']={'inputGroundPoints':len(inside),'supportGroundPoints':count,'originalOutputPoints':len(original),'interpolatedGridPoints':len(interpolated),'missingGridPoints':len(gaps),'mode':opts.get('terrainMode','measured'),'boundaryPoints':len(edge),'outputPoints':len(coords),'grid':None if opts['raw'] else opts['grid'],'method':'Innen: reale Messpunkte bzw. regelmäßiges interpoliertes Raster. Rand: exakte XY auf vier Kanten und Ecken. Interpolation: IDW (1/d², bis acht Bodenpunkte), nur innerhalb des lokalen Stützradius.','boundarySpacing':opts.get('boundarySpacing',opts['grid']),'boundarySupportRadius':radius,'horizontalCRS':CRS_CODE,'verticalCRS':'EPSG:5778','attributes':'Originalpunkte behalten ihre Attribute. Abgeleitete Punkte: synthetic=1, Klasse 2, andere Messattribute ungesetzt/0; DXF-Layer GELAENDERAND bzw. GELAENDERASTER.'}

    if opts.get('_terrainPreview'):
        step=max(1,math.ceil(len(original)/12000));displayed=coords[:len(original):step]
        missing=gaps
        (directory/'gelaende-vorschau.json').write_text(json.dumps({'bbox':b,'measured':displayed.tolist(),'grid':interpolated.tolist(),'boundary':edge.tolist(),'gaps':missing,'displaySampled':step>1 or opts.get('_rawPreview',False),'terrain':meta['terrain']}),encoding='utf-8')

def missing_cells(xyz,b,spacing):
    xs=(np.arange(math.floor(b[0]/spacing),math.ceil(b[2]/spacing))+.5)*spacing;ys=(np.arange(math.floor(b[1]/spacing),math.ceil(b[3]/spacing))+.5)*spacing
    xs=xs[(xs>=b[0])&(xs<=b[2])];ys=ys[(ys>=b[1])&(ys<=b[3])];xx,yy=np.meshgrid(xs,ys);nodes=np.column_stack((xx.ravel(),yy.ravel()))
    occupied={tuple(p) for p in np.floor(xyz[:,:2]/spacing).astype(int)}
    return [p.tolist() for p in nodes if tuple(np.floor(p/spacing).astype(int)) not in occupied]

def regular_xy(b,spacing):
    xs=np.arange(math.floor(b[0]/spacing)+1,math.ceil(b[2]/spacing))*spacing
    ys=np.arange(math.floor(b[1]/spacing)+1,math.ceil(b[3]/spacing))*spacing
    if len(xs)*len(ys)>1000000: raise ValueError('Interpoliertes Raster zu dicht; Rasterweite erhöhen.')
    x,y=np.meshgrid(xs,ys);return np.column_stack((x.ravel(),y.ravel()))

def interpolate_heights(xyz,xy,radius):
    if not len(xy): return np.empty(0)
    distances,indices=cKDTree(xyz[:,:2]).query(xy,k=min(8,len(xyz)),distance_upper_bound=radius)
    if distances.ndim==1: distances=distances[:,None];indices=indices[:,None]
    valid=np.isfinite(distances);weights=np.where(valid,1/np.maximum(distances,1e-9)**2,0)
    heights=xyz[np.minimum(indices,len(xyz)-1),2];total=weights.sum(axis=1)
    return np.divide((weights*heights).sum(axis=1),total,out=np.full(len(xy),np.nan),where=total>0)

def boundary_points(xyz,b,spacing,radius):
    """Closed rectangular perimeter with exact corners and bounded local height support."""
    xs=np.linspace(b[0],b[2],math.ceil((b[2]-b[0])/spacing)+1)
    ys=np.linspace(b[1],b[3],math.ceil((b[3]-b[1])/spacing)+1)
    xy=np.unique(np.vstack([np.column_stack((xs,np.full(len(xs),y))) for y in [b[1],b[3]]]+[np.column_stack((np.full(len(ys),x),ys)) for x in [b[0],b[2]]]),axis=0)
    z=interpolate_heights(xyz,xy,radius)
    if np.any(~np.isfinite(z)): raise ValueError('Randhöhen können wegen fehlender Bodenpunkte nicht vollständig bestimmt werden. Rahmen verschieben oder Randabstand erhöhen.')
    return np.column_stack((xy,z))

def grid_indices(xyz,b,spacing):
    """One real measurement per occupied cell; globally anchored grid."""
    ix=np.floor(xyz[:,0]/spacing).astype(np.int64); iy=np.floor(xyz[:,1]/spacing).astype(np.int64)
    distance=(xyz[:,0]-(ix+0.5)*spacing)**2+(xyz[:,1]-(iy+0.5)*spacing)**2
    order=np.lexsort((distance,iy,ix)); keys=np.column_stack((ix[order],iy[order]))
    keep=np.r_[True,np.any(keys[1:]!=keys[:-1],axis=1)]
    return order[keep]

def select_parcels(opts):
    return parcel_rules.selection(sys.modules[__name__],opts)

def parcel_export(job,opts,directory,meta):
    return parcel_rules.export(sys.modules[__name__],job,opts,directory,meta)

def aerial(job,opts,directory,meta):
    b=opts['bbox']; width=round((b[2]-b[0])*10); height=round((b[3]-b[1])*10)
    tif=directory/'luftbild.tif'; affine=from_origin(b[0],b[3],0.1,0.1)
    steps=math.ceil(width/2000)*math.ceil(height/2000); done=0
    with rasterio.open(tif,'w',driver='GTiff',width=width,height=height,count=3,dtype='uint8',crs=CRS_CODE,transform=affine,compress='deflate',tiled=True,BIGTIFF='IF_SAFER') as dst:
        for y in range(0,height,2000):
            for x in range(0,width,2000):
                update(job,60+int(25*done/steps),f'Orthofoto {opts["year"]} · Teil {done+1}/{steps}')
                w=min(2000,width-x); h=min(2000,height-y)
                bounds=[b[0]+x*.1,b[3]-(y+h)*.1,b[0]+(x+w)*.1,b[3]-y*.1]
                params={'MAP':'i_luftbilder_r_wms.map','SERVICE':'WCS','VERSION':'1.0.0','REQUEST':'GetCoverage','COVERAGE':YEARS[opts['year']],'CRS':CRS_CODE,'RESPONSE_CRS':CRS_CODE,'BBOX':','.join(map(str,bounds)),'WIDTH':w,'HEIGHT':h,'FORMAT':'GTiff','INTERPOLATION':'NEAREST'}
                payload=get(MAP,params=params).content
                with rasterio.MemoryFile(payload) as mem:
                    with mem.open() as src:
                        if src.width!=w or src.height!=h or src.count<3 or src.crs.to_epsg()!=31254: raise ValueError('Unerwartetes Raster vom WCS.')
                        expected=from_origin(bounds[0],bounds[3],.1,.1)
                        if not np.allclose(tuple(src.transform),tuple(expected),atol=1e-5,rtol=0): raise ValueError('WCS-Raster liegt nicht deckungsgleich auf dem Rahmen.')
                        pixels=src.read([1,2,3]); dst.write(pixels,window=Window(x,y,w,h))
                        if np.all(pixels==0): meta['warnings'].append(f'Leerer/schwarzer Luftbildteil bei {bounds}; Abdeckung prüfen.')
                done+=1
    for fmt,driver,extension in [('png','PNG','pgw'),('jpg','JPEG','jgw')]:
        if fmt in opts['formats']:
            from rasterio.shutil import copy
            copy(tif,directory/f'luftbild.{fmt}',driver=driver)
            (directory/f'luftbild.{extension}').write_text(f'0.1\n0\n0\n-0.1\n{b[0]+.05}\n{b[3]-.05}\n',encoding='ascii')
            (directory/'luftbild.prj').write_text(CRS.from_epsg(31254).to_wkt(version='WKT1_ESRI'),encoding='utf-8')
    if 'tif' not in opts['formats']: tif.unlink()
    meta['sources'].append({'type':'Orthofoto','url':MAP,'service':'WCS 1.0.0 GetCoverage','coverage':YEARS[opts['year']],'year':opts['year'],'resolutionMetres':0.1,'attribution':'Land Vorarlberg / VOGIS','method':'Rasterdienst, native Auflösung und gemeinsames 10-cm-Raster; kein WMS-Screenshot'})

def run_job(job,opts):
    directory=OUTPUT/job['id']; directory.mkdir()
    meta={'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'options':opts,'horizontalCRS':CRS_CODE,'units':'Metre','sources':[],'warnings':[],'license':'Quellenspezifische Nutzungsbedingungen beachten; keine pauschale Lizenz aus der öffentlichen Verfügbarkeit abgeleitet.'}
    try:
        job['state']='running'; update(job,2,'Export vorbereiten')
        if 'terrain' in opts['types']: terrain(job,{**opts,'formats':sorted(set(opts.get('formatsByType',{}).get('terrain',opts['formats']))|{'xyz'})},directory,meta)
        if 'parcels' in opts['types']: parcel_export(job,{**opts,'formats':opts.get('formatsByType',{}).get('parcels',opts['formats'])},directory,meta)
        if 'aerial' in opts['types']: aerial(job,{**opts,'formats':sorted(set(opts.get('formatsByType',{}).get('aerial',opts['formats']))|{'png'})},directory,meta)
        if opts.get('localOrigin'): apply_local_origin(directory,opts,meta)
        meta['outputBounds']=[v-opts.get('offset',opts['bbox'][:2])[i%2] for i,v in enumerate(opts['bbox'])] if opts.get('localOrigin') else opts['bbox']
        meta.pop('_parcelsFinalCoordinates',None)
        meta['allplanImportVersion']=1
        update(job,90,'Metadaten und ZIP schreiben')
        (directory/'metadaten.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        (directory/'IMPORT-HINWEISE.txt').write_text('Alle DXF-/XYZ-/Rasterkoordinaten: Gauß-Krüger West EPSG:31254, Meter.\nGeländehöhen: EPSG:5778.\nAllplan: DXF über CAD-Import, Einheit Meter. Bei großen Landeskoordinaten Projekt-Offset verwenden und denselben Offset für alle Dateien anwenden. DXF enthält 3D-POINT-Elemente auf GELAENDEPUNKTE, keine triangulierte Oberfläche.\nXYZ: X Y Z, Leerzeichen, Dezimalpunkt, Kommentarzeile beginnt mit #.\nGeoJSON (falls gewählt): EPSG:4326 nach RFC 7946.\nEine Importprüfung in Ihrer Allplan-Version ist zusätzlich erforderlich.\n',encoding='utf-8')
        if opts.get('localOrigin'):
            hint=directory/'IMPORT-HINWEISE.txt'
            hint.write_text(f"Lokales Planungssystem, Meter. Alle X/Y-Ausgaben gemeinsam verschoben.\nOffset GK West EPSG:31254: X={opts.get('offset',opts['bbox'][:2])[0]}, Y={opts.get('offset',opts['bbox'][:2])[1]}; GK = Lokal + Offset.\nZ unverändert: EPSG:5778. Bezug gemäß gewähltem Ursprung; GK = Lokal + Offset.\nAllplan CAD-Import: Meter, keine zusätzliche Verschiebung dieser lokalen Dateien.\nDXF: 3D-POINT, Polylinien und TEXT. Keine triangulierte Geländefläche.\nGELAENDEPUNKTE: Messpunkte; GELAENDERASTER/GELAENDERAND: interpoliert.\nGeoTIFF und LAS erhalten einen lokalen Bezug, keine falsche EPSG-Kennung.\nLokales GeoJSON: Meter, kein RFC-7946-Lon/Lat. Siehe metadaten.json.\nPNG/JPEG zusammen mit Worldfile und PRJ verwenden.\n",encoding='utf-8')
        with (directory/'IMPORT-HINWEISE.txt').open('a',encoding='utf-8') as hint:
            hint.write('\nGrundstücksnummern: Arial Bold (arialbd.ttf), echte Fett-Zuordnung; CAD-Schriftersetzung kann Darstellung ändern.\nDKM-Auswahl inklusive Zusatzbereich und eingeschlossener Grundstücke; Gelände und Luftbild bleiben im sichtbaren Rahmen.\nDKM: Quelle auf 0,001 m normalisieren, Offset abziehen, dann gewählte 2/3 Dezimalstellen. Einzelheiten in metadaten.json.\n')
        files=[p for p in directory.iterdir() if p.is_file()]
        with zipfile.ZipFile(directory/'geodaten.zip','w',zipfile.ZIP_DEFLATED) as z:
            for p in files: update(job,95,'ZIP fertigstellen'); z.write(p,p.name)
        job.update(state='done',progress=100,message='Export fertig',files=[p.name for p in files]+['geodaten.zip'],metadata=meta)
    except InterruptedError as e: job.update(state='cancelled',message=str(e))
    except Exception as e: job.update(state='error',message=str(e))
    finally:
        save_job(job)
        if job['state']!='done':
            for p in directory.iterdir():
                if p.is_file(): p.unlink()

def public(job): return {k:v for k,v in job.items() if k!='cancel' and not k.startswith('_')}

def restore_jobs():
    for path in OUTPUT.iterdir():
        if not path.is_dir() or not re.fullmatch(r'[a-f0-9]{32}',path.name): continue
        if not (path/'geodaten.zip').exists() or not (path/'metadaten.json').exists(): continue
        try: meta=json.loads((path/'metadaten.json').read_text(encoding='utf-8'))
        except ValueError: continue
        JOBS[path.name]={'id':path.name,'state':'done','progress':100,'message':'Export fertig','created':path.stat().st_mtime,'files':[f.name for f in path.iterdir() if f.is_file()],'metadata':meta,'options':meta['options'],'cancel':threading.Event()}

@app.post('/api/jobs')
def create_job():
    opts=validate(request.json)
    with LOCK:
        if any(j['state'] in ['queued','running'] for j in JOBS.values()): raise ValueError('Ein Export läuft bereits. Bitte warten oder abbrechen.')
        cleanup()
        job={'id':uuid.uuid4().hex,'state':'queued','progress':0,'message':'Wartet','files':[],'created':time.time(),'options':opts,'cancel':threading.Event()}
        if opts.get('previewToken'):job['_parcelSnapshot']=PREVIEWS[opts['previewToken']]
        JOBS[job['id']]=job; save_job(job); POOL.submit(run_job,job,opts)
    return jsonify(public(job)),202

def cleanup():
    # Only our explicit export directories; no recursive deletion of computed outside paths.
    for path in OUTPUT.iterdir():
        if path.is_dir() and re.fullmatch(r'[a-f0-9]{32}',path.name) and time.time()-path.stat().st_mtime>86400:
            for f in path.iterdir():
                if f.is_file(): f.unlink()
            path.rmdir(); JOBS.pop(path.name,None)
    # Expire our range/WFS cache after seven days, and bound disk use to 1 GB.
    files=[p for p in CACHE.rglob('*') if p.is_file() and p.name!='kg.json' and p.parent.name!='history']
    total=sum(p.stat().st_size for p in files)
    for p in sorted(files,key=lambda p:p.stat().st_mtime):
        size=p.stat().st_size
        if total>1024**3 or time.time()-p.stat().st_mtime>7*86400:
            p.unlink(); total-=size

@app.get('/api/jobs/<job_id>')
def job_status(job_id):
    if job_id not in JOBS: return jsonify(error='Export nicht gefunden.'),404
    return jsonify(public(JOBS[job_id]))

@app.post('/api/jobs/<job_id>/cancel')
def cancel(job_id):
    job=JOBS[job_id]; job['cancel'].set(); return jsonify(message='Abbruch angefordert; laufender Datenabruf wird beendet.')

@app.get('/api/jobs/<job_id>/files/<name>')
def download(job_id,name):
    job=JOBS.get(job_id)
    if not job or job['state']!='done' or name not in job['files']: return jsonify(error='Datei nicht verfügbar.'),404
    return send_from_directory(OUTPUT/job_id,name,as_attachment=True)

from . import enhancements
enhancements.register(sys.modules[__name__])

if __name__=='__main__':
    cleanup(); restore_jobs(); restore_history()
    print('Vorarlberg Geodatenexport: http://127.0.0.1:8790',flush=True)
    app.run(host='127.0.0.1',port=8790,threaded=True,debug=False)
