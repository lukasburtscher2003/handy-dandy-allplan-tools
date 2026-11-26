"""Preview snapshots, local coordinate exports and durable job history."""
import json, math, time, uuid, datetime, threading, hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union, transform
from ezdxf.math import Matrix44
from rasterio import Affine

LOCAL_WKT='LOCAL_CS["Lokales Planungssystem",LOCAL_DATUM["Rahmenecke in EPSG 31254",0],UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'

def register(s):
    def save_job(job):
        folder=s.CACHE/'history';folder.mkdir(exist_ok=True)
        payload=s.public(job);tmp=folder/(job['id']+'.tmp')
        tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8');tmp.replace(folder/(job['id']+'.json'))
    s.save_job=save_job

    @s.app.get('/api/jobs')
    def history():
        return s.jsonify(jobs=[s.public(j) for j in sorted(s.JOBS.values(),key=lambda j:j['created'],reverse=True) if j.get('kind','export')=='export'][:30])

    @s.app.get('/api/kgs')
    def kgs():
        path=s.CACHE/'kg.json'
        if not path.exists():path=s.HERE/'data/kg.json'
        rows=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
        return s.jsonify(rows=sorted(rows,key=lambda r:r['name'].casefold()))

    @s.app.post('/api/preview')
    def preview():
        opts=s.validate(s.request.json);b=opts['bbox']
        rows,count=s.select_parcels(opts) if 'parcels' in opts['types'] else ([],0)
        token=uuid.uuid4().hex
        for key,value in list(s.PREVIEWS.items()):
            if time.time()-value['created']>1800:s.PREVIEWS.pop(key,None)
        if len(s.PREVIEWS)>=50:s.PREVIEWS.pop(min(s.PREVIEWS,key=lambda k:s.PREVIEWS[k]['created']),None)
        s.PREVIEWS[token]={'created':time.time(),'rows':rows,'baseCount':count,'bbox':b,'includeAdjacent':opts['includeAdjacent'],'dkmMargin':opts['dkmMargin'],'hasParcels':'parcels' in opts['types']}
        features=[]
        for i,row in enumerate(rows):
            f=s.ll_feature(row);f['properties']['_selection']=row.get('_selection','selected' if i<count else 'adjacent');features.append(f)
        tiles=[t for t in s.INDEX['tiles'] if s.intersect(t['bbox'],b)]
        covered=unary_union([box(*t['bbox']) for t in tiles]).intersection(box(*b)).area if tiles else 0
        categories={c:sum(r.get('_selection')==c for r in rows) for c in ['selected','buffer','adjacent','enclosed']}
        return s.jsonify(token=token,features=features,selectionCount=count,adjacentCount=categories['adjacent'],enclosedCount=categories['enclosed'],categoryCounts=categories,dkmBounds=opts['dkmBounds'],
                         width=b[2]-b[0],height=b[3]-b[1],coveragePercent=round(100*covered/box(*b).area,1),tiles=len(tiles),
                         coverageNote='LiDAR-Kachelgrenzen; Bodenpunktlücken werden erst beim Geländeabruf geprüft. Luftbildabdeckung wird beim Export geprüft.')

    def terrain_preview(job,opts):
        folder=s.OUTPUT/job['id'];folder.mkdir()
        meta={'sources':[],'warnings':[]}
        try:
            job['state']='running';s.terrain(job,opts,folder,meta)
            job.update(state='done',progress=100,message='Geländevorschau fertig',files=['gelaende-vorschau.json'],metadata=meta)
        except InterruptedError as e:job.update(state='cancelled',message=str(e))
        except Exception as e:job.update(state='error',message=str(e))
        finally:
            if job['state']!='done':
                for p in folder.iterdir():
                    if p.is_file():p.unlink()

    @s.app.post('/api/terrain-preview')
    def create_preview():
        opts=s.validate(s.request.json);opts.update(types=['terrain'],formats=[],localOrigin=False,_terrainPreview=True)
        # Dense raw previews use the same measured-cell algorithm, explicitly marked in the result.
        if opts['raw']:opts.update(raw=False,grid=max(2.,opts['grid']),_rawPreview=True)
        cells=(opts['bbox'][2]-opts['bbox'][0])*(opts['bbox'][3]-opts['bbox'][1])/opts['grid']**2
        if cells>30000:raise ValueError('Für die 3D-Vorschau höchstens 30.000 Rasterpositionen wählen; Rasterweite erhöhen.')
        with s.LOCK:
            if any(j['state'] in ['queued','running'] for j in s.JOBS.values()):raise ValueError('Ein Auftrag läuft bereits. Bitte warten oder abbrechen.')
            job={'id':uuid.uuid4().hex,'kind':'preview','state':'queued','progress':0,'message':'Gelände laden','files':[],'created':time.time(),'cancel':threading.Event()}
            s.JOBS[job['id']]=job;s.POOL.submit(terrain_preview,job,opts)
        return s.jsonify(s.public(job)),202

    @s.app.get('/api/index')
    def index_status():
        return s.jsonify(tiles=len(s.INDEX['tiles']),updated=s.INDEX.get('checkedAt',s.INDEX.get('createdAt','übernommener Ausgangsindex')),report=s.INDEX.get('refreshReport'))

    def refresh_index(job):
        try:
            job['state']='running';s.update(job,2,'VOGIS-Katalog prüfen')
            url='https://vogis.cnv.at/geodaten/api/public/share/OTSj-JMs/gelaendemodelle/lidarpunkte/kacheln/2023'
            items=s.get(url).json()['items'];items=[i for i in items if not i.get('isDir') and i['name'].endswith('.copc.laz')]
            if not items:raise ValueError('Katalog enthält keine COPC-Kacheln; bisheriger Index bleibt erhalten.')
            old={t['name']:t for t in s.INDEX['tiles']};tiles=[];changed=0
            for i,item in enumerate(items):
                s.update(job,5+int(85*i/len(items)),f'Quellenindex · Kachel {i+1}/{len(items)}')
                previous=old.get(item['name']);modified=item.get('modified',item.get('lastModified'))
                if previous and previous['size']==item['size'] and previous.get('modified')==modified:
                    tiles.append(previous);continue
                signature=hashlib.sha256(json.dumps([item['path'],item['size'],modified]).encode()).hexdigest()[:20]
                t={'name':item['name'],'path':item['path'],'size':item['size'],'modified':modified,'source':s.DL+item['path'],'signature':signature,'status':'ok'}
                with s.laspy.CopcReader(s.CachedRange(t,job)) as reader:
                    h=reader.header
                    if not s.is_gk_west(h.parse_crs()):raise ValueError('Neue Kachel hat unbestätigten Koordinatenbezug.')
                    t.update(id=item['name'].split('_')[1].split('.')[0],bbox=[float(h.mins[0]),float(h.mins[1]),float(h.maxs[0]),float(h.maxs[1])],z=[float(h.mins[2]),float(h.maxs[2])],pointCount=h.point_count,pointFormat=h.point_format.id,recordLength=h.point_format.size,scale=h.scales.tolist(),offset=h.offsets.tolist(),crs=s.CRS_CODE)
                tiles.append(t);changed+=1
            result={**s.INDEX,'tiles':tiles,'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'refreshReport':{'catalog':url,'changedOrNew':changed,'removed':len(set(old)-{t['name'] for t in tiles}),'total':len(tiles)}}
            path=s.HERE/'data/copc-index-2023.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');tmp.replace(path);s.INDEX=result
            job.update(state='done',progress=100,message=f'Quellenindex geprüft: {len(tiles)} Kacheln, {changed} neu oder geändert.',metadata=result['refreshReport'])
        except InterruptedError as e:job.update(state='cancelled',message=str(e))
        except Exception as e:job.update(state='error',message='Indexprüfung fehlgeschlagen; bisheriger Index bleibt erhalten. '+str(e))

    s.refresh_index=refresh_index

    @s.app.post('/api/index/refresh')
    def refresh():
        with s.LOCK:
            if any(j['state'] in ['queued','running'] for j in s.JOBS.values()):raise ValueError('Ein Auftrag läuft bereits.')
            job={'id':uuid.uuid4().hex,'kind':'index','state':'queued','progress':0,'message':'Indexprüfung wartet','files':[],'created':time.time(),'cancel':threading.Event()}
            s.JOBS[job['id']]=job;s.POOL.submit(refresh_index,job)
        return s.jsonify(s.public(job)),202

    def restore_history():
        folder=s.CACHE/'history'
        for p in folder.glob('*.json'):
            try:
                j=json.loads(p.read_text(encoding='utf-8'))
                if time.time()-j['created']>86400:p.unlink();continue
                if j['state'] in ['running','queued']:j.update(state='error',message='Anwendung während des Auftrags beendet. Auftrag kann wiederholt werden.')
                if j['state']=='done' and not (s.OUTPUT/j['id']/'geodaten.zip').exists():continue
                j['cancel']=threading.Event();s.JOBS[j['id']]=j
            except (ValueError,KeyError):continue
    s.restore_history=restore_history
    s.apply_local_origin=lambda directory,opts,meta:apply_local_origin(s,directory,opts,meta)

def apply_local_origin(s,directory,opts,meta):
    """Translate every spatial output together. No false EPSG tag on local coordinates."""
    ox,oy=opts.get('offset',opts['bbox'][:2])
    shift=lambda x,y,z=None:(np.asarray(x)-ox,np.asarray(y)-oy) if z is None else (np.asarray(x)-ox,np.asarray(y)-oy,z)
    meta['coordinateOffset']={'x':ox,'y':oy,'z':0,'formula':'Lokal X = GK X − Offset X; Lokal Y = GK Y − Offset Y; Z unverändert.','sourceCRS':s.CRS_CODE,'outputCRS':LOCAL_WKT}
    meta['horizontalCRS']='Lokales Planungssystem (Meter)'
    for path in directory.glob('*.dxf'):
        if path.name=='grundstuecke.dxf' and meta.get('_parcelsFinalCoordinates'):continue
        doc=s.ezdxf.readfile(path)
        for entity in doc.modelspace():entity.transform(Matrix44.translate(-ox,-oy,0))
        doc.saveas(path)
    path=directory/'gelaende.xyz'
    if path.exists():
        xyz=np.loadtxt(path,ndmin=2);xyz[:,:2]-=[ox,oy];np.savetxt(path,xyz,fmt='%.3f',header=f'X Y Z; lokal Meter; GK Offset {ox} {oy}; Hoehe EPSG:5778')
    for fmt in ['las','laz']:
        path=directory/f'gelaende.{fmt}'
        if path.exists():
            las=s.laspy.read(path);x=np.asarray(las.x)-ox;y=np.asarray(las.y)-oy;z=np.asarray(las.z)
            las.header.offsets=np.array([0.,0.,0.]);las.points.change_scaling(offsets=las.header.offsets);las.x=x;las.y=y;las.z=z
            las.header.vlrs=[v for v in las.header.vlrs if v.user_id not in ['LASF_Projection','copc']]
            from laspy.vlrs.known import WktCoordinateSystemVlr
            las.header.vlrs.append(WktCoordinateSystemVlr(LOCAL_WKT));las.header.global_encoding.wkt=True;las.write(path)
    path=directory/'grundstuecke.geojson'
    if path.exists() and not meta.get('_parcelsFinalCoordinates'):
        data=json.loads(path.read_text(encoding='utf-8'))
        for f in data['features']:
            g=transform(s.TO_GK.transform,shape(f['geometry']));f['geometry']=mapping(transform(shift,g));f['properties'].pop('_label',None)
        data['crs']={'type':'name','properties':{'name':'LOCAL:FRAME_ORIGIN_METRES'}};data['coordinateOffset']=[ox,oy,0]
        path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        meta['warnings'].append('Lokales GeoJSON verwendet Meter und einen dokumentierten lokalen Bezug; es ist kein RFC-7946-Lon/Lat-GeoJSON.')
        meta['parcels']['geojsonCRS']='LOCAL:FRAME_ORIGIN_METRES'
    path=directory/'luftbild.tif'
    if path.exists():
        with s.rasterio.open(path,'r+') as raster:
            a=raster.transform;raster.transform=Affine(a.a,a.b,a.c-ox,a.d,a.e,a.f-oy);raster.crs=LOCAL_WKT
    for extension in ['pgw','jgw']:
        path=directory/f'luftbild.{extension}'
        if path.exists():
            v=[float(x) for x in path.read_text().splitlines()];v[4]-=ox;v[5]-=oy;path.write_text('\n'.join(map(str,v))+'\n',encoding='ascii')
    path=directory/'luftbild.prj'
    if path.exists():path.write_text(LOCAL_WKT,encoding='utf-8')
    # GDAL image sidecars can also contain the original transform/CRS.
    for path in directory.glob('*.aux.xml'):
        path.unlink()
    if 'terrain' in meta:meta['terrain']['horizontalCRS']='LOCAL:FRAME_ORIGIN_METRES'
