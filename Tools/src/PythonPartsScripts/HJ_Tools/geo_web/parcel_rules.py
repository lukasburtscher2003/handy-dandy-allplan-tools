"""DKM selection uses source geometry; quantisation happens only at export."""
import copy,math
from decimal import Decimal,ROUND_HALF_UP
from shapely.geometry import shape,mapping,Polygon,MultiPolygon,Point,box
from shapely.ops import unary_union,transform
from shapely.validation import explain_validity

COLORS={'magenta':(224,0,122),'black':(0,0,0),'green':(0,140,70)}

def number(value,low,high,name):
    value=float(value)
    if not math.isfinite(value) or not low<=value<=high:raise ValueError(name+f' muss zwischen {low} und {high} liegen.')
    return value

def extra_options(data,b,formats,types):
    allowed={'terrain':{'dxf','xyz','las','laz'},'parcels':{'dxf','geojson'},'aerial':{'tif','png','jpg'}}
    default={'terrain':['dxf'],'parcels':['dxf','geojson'],'aerial':['tif']}
    by=data.get('formatsByType')
    if by is None:by={k:sorted(allowed[k].intersection(formats)) for k in allowed} if 'formats' in data else default
    if not isinstance(by,dict):raise ValueError('Ungültige Formatwahl.')
    by={k:by.get(k,[]) for k in allowed}
    for k,v in by.items():
        if not isinstance(v,list) or any(f not in allowed[k] for f in v) or (k in types and not v):raise ValueError('Für jede gewählte Datenart ein passendes Format wählen.')
    margin=number(data.get('dkmMargin',0),0,500,'DKM-Zusatzabstand')
    dkm=[b[0]-margin,b[1]-margin,b[2]+margin,b[3]+margin]
    if (dkm[2]-dkm[0])*(dkm[3]-dkm[1])>2000000:raise ValueError('DKM-Zusatzrahmen maximal 2 Millionen m²; Abstand oder Rahmen verkleinern.')
    places=data.get('parcelDecimals',3)
    if places not in [2,3]:raise ValueError('Grundstückskoordinaten: zwei oder drei Nachkommastellen wählen.')
    color=data.get('labelColor','magenta')
    if color not in COLORS:raise ValueError('Unbekannte Nummernfarbe.')
    height=number(data.get('labelHeight',1.5),.1,20,'Texthöhe')
    origin=data.get('originMode','frame' if data.get('localOrigin') else 'world')
    if origin not in ['world','frame','custom']:raise ValueError('Unbekannter Ursprung.')
    offset=b[:2] if origin=='frame' else [0.,0.]
    if origin=='custom':
        raw=data.get('offset')
        if not isinstance(raw,list) or len(raw)!=2:raise ValueError('X- und Y-Offset eingeben.')
        offset=[number(x,-1e7,1e7,'Offset') for x in raw]
    chosen=data.get('selectedParcel')
    if chosen is not None:
        if not isinstance(chosen,dict) or not isinstance(chosen.get('kg'),str) or not isinstance(chosen.get('gnr'),str):raise ValueError('Ungültige Grundstücksauswahl.')
        chosen={'kg':chosen['kg'][:5],'gnr':chosen['gnr'][:30]}
    return {'formatsByType':by,'formats':sorted({v for values in by.values() for v in values}),'dkmMargin':margin,'dkmBounds':dkm,'parcelDecimals':places,'labelColor':color,'labelHeight':height,'originMode':origin,'offset':offset,'localOrigin':origin!='world','selectedParcel':chosen}

def outer_shell(g):
    if g.geom_type=='Polygon':return Polygon(g.exterior)
    if g.geom_type=='MultiPolygon':return unary_union([Polygon(p.exterior) for p in g.geoms])
    raise ValueError('Grundstück hat keine Polygongeometrie.')

def parcel_key(row):return str(row['properties']['kg_gst'])

def selection(s,opts):
    b=opts['bbox'];margin=opts.get('dkmMargin',0);db=[b[0]-margin,b[1]-margin,b[2]+margin,b[3]+margin]
    frame=box(*b);area=box(*db);rows=[];known=set()
    def add(f,category):
        key=parcel_key(f)
        if key in known:return
        f=copy.deepcopy(f);f['_selection']=category;rows.append(f);known.add(key)
    for f in s.wfs('gst',bbox=db):
        g=shape(f['geometry'])
        if g.intersects(area):add(f,'selected' if g.intersects(frame) else 'buffer')
    base_count=len(rows)
    if rows and opts.get('includeAdjacent'):
        original=unary_union([shape(f['geometry']) for f in rows])
        for f in s.wfs('gst',bbox=list(original.buffer(.02).bounds)):
            if parcel_key(f) not in known and shape(f['geometry']).distance(original)<=.02:add(f,'adjacent')
    # Fill shell holes after the single neighbor ring; additions cannot start new rings.
    # Each candidate must be covered by one original outer shell, not merely its bbox
    # or a union of disconnected/adjacent parcels that could create an artificial hole.
    examined=set();candidates={}
    while True:
        parents=[(parcel_key(f),outer_shell(shape(f['geometry']))) for f in rows if parcel_key(f) not in examined]
        if not parents:break
        # VOGIS native CQL geometry has northing/easting axis order (verified
        # against DescribeFeatureType/GetCapabilities and parcel 92102-.520).
        # Ask for candidates within shells, avoiding the enormous envelope of
        # long roads or disconnected parcels. A 1 mm query buffer only guards
        # serialisation noise; exact source coverage is checked below.
        clauses=[]
        for _,g in parents:
            native=transform(lambda x,y:(y,x),g.buffer(.001))
            clauses.append('WITHIN(the_geom,'+native.wkt+')')
            if len(clauses)>=10:
                for f in s.wfs('gst',cql=' OR '.join(clauses)):candidates[parcel_key(f)]=f
                clauses=[]
        if clauses:
            for f in s.wfs('gst',cql=' OR '.join(clauses)):candidates[parcel_key(f)]=f
        for key,g in parents:
            examined.add(key)
            for f in list(candidates.values()):
                if parcel_key(f) not in known and g.covers(shape(f['geometry'])):add(f,'enclosed')
        if len(rows)>10000:raise ValueError('Mehr als 10.000 DKM-Grundstücke; Auswahl verkleinern.')
    return rows,base_count

def rounded_geometry(g,offset=(0,0),places=3,name='Grundstück'):
    quantum=Decimal(1).scaleb(-places)
    def xy(p):
        return tuple(float((Decimal(str(v)).quantize(Decimal('.001'),rounding=ROUND_HALF_UP)-Decimal(str(o))).quantize(quantum,rounding=ROUND_HALF_UP)) for v,o in zip(p[:2],offset))
    def ring(coords):
        original=list(coords);points=[xy(p) for p in original]
        for i in range(1,len(points)):
            if points[i]==points[i-1] and original[i][:2]!=original[i-1][:2]:raise ValueError(f'{name}: Rundung auf {places} Stellen lässt eine Kante zusammenfallen. Präzision erhöhen oder Quellgeometrie prüfen.')
        clean=[points[0]]
        for p in points[1:]:
            if p!=clean[-1]:clean.append(p)
        if clean[-1]!=clean[0]:clean.append(clean[0])
        if len(set(clean[:-1]))<3:raise ValueError(f'{name}: Ring kollabiert durch Rundung.')
        return clean
    if g.geom_type=='Polygon':result=Polygon(ring(g.exterior.coords),[ring(r.coords) for r in g.interiors])
    elif g.geom_type=='MultiPolygon':result=MultiPolygon([rounded_geometry(child,offset,places,name) for child in g.geoms])
    elif g.geom_type=='Point':return Point(xy(g.coords[0]))
    else:raise ValueError('Nicht unterstützte DKM-Geometrie.')
    if result.is_empty or not result.is_valid or result.area<=0:raise ValueError(f'{name}: ungültige gerundete Geometrie ({explain_validity(result)}). Keine automatische Reparatur angewendet.')
    return result

def export(s,job,opts,directory,meta):
    s.update(job,53,'Grundstücke, Einschlüsse und Nummern laden')
    snapshot=job.get('_parcelSnapshot') or s.PREVIEWS.get(opts.get('previewToken'))
    rows,base_count=(snapshot['rows'],snapshot['baseCount']) if snapshot else selection(s,opts)
    places=opts.get('parcelDecimals',3);offset=opts.get('offset',opts['bbox'][:2]) if opts.get('localOrigin') else [0,0]
    # Validate every rounded polygon before writing any spatial file.
    polygons={parcel_key(f):rounded_geometry(shape(f['geometry']),offset,places,parcel_key(f)) for f in rows}
    anchors=[]
    for start in range(0,len(rows),50):
        s.update(job,54,'Grundstücksnummern zuordnen')
        cql=' OR '.join('(kg='+s.literal(f['properties']['kg'])+' AND gnr='+s.literal(f['properties']['gnr'])+')' for f in rows[start:start+50])
        anchors.extend(s.wfs('gnr',cql=cql,limit=1000))
    anchors={(f['properties']['kg'],f['properties']['gnr']):shape(f['geometry']).representative_point() for f in anchors}
    features=[];labels=[];color=opts.get('labelColor','magenta');height=opts.get('labelHeight',1.5)
    for f in rows:
        p=f['properties'];g=polygons[parcel_key(f)];source=shape(f['geometry']);a=anchors.get((p['kg'],p['gnr']))
        if a is None or not source.covers(a):a=source.representative_point()
        a=rounded_geometry(a,offset,places)
        if not g.covers(a):
            r=g.representative_point();q=Decimal(1).scaleb(-places)
            a=Point(*(float(Decimal(str(v)).quantize(q,rounding=ROUND_HALF_UP)) for v in (r.x,r.y)))
            if not g.covers(a):
                part=g if g.geom_type=='Polygon' else max(g.geoms,key=lambda v:v.area);a=Point(part.exterior.coords[0])
                meta['warnings'].append(f'Nummer {parcel_key(f)}: gerundeter Ersatzanker am Grundstücksrand.')
        props={('source_fid' if k=='fid' else k):v for k,v in p.items()};props.update(source_id=f.get('id',''),selection=f.get('_selection','selected'))
        features.append({'type':'Feature','geometry':mapping(g),'properties':props})
        labels.append({'type':'Feature','geometry':mapping(a),'properties':{**props,'label_color':color,'label_height':height,'label_bold':1}})
    formats=opts['formats']
    # Native Allplan handoff: always retain the projected metre coordinates
    # (including world coordinates with zero offset), never geographic degrees.
    native=s.collection(features)
    native.update(crs={'type':'name','properties':{'name':'LOCAL:FRAME_ORIGIN_METRES'}},coordinateOffset=[*offset,0])
    (directory/'allplan_parcels.json').write_text(s.json.dumps(native,ensure_ascii=False),encoding='utf-8')
    (directory/'allplan_labels.json').write_text(s.json.dumps(s.collection(labels),ensure_ascii=False),encoding='utf-8')
    if 'geojson' in formats:
        if opts.get('localOrigin'):
            data=s.collection(features);data.update(crs={'type':'name','properties':{'name':'LOCAL:FRAME_ORIGIN_METRES'}},coordinateOffset=[*offset,0])
            meta['warnings'].append('Lokales GeoJSON: Meter, kein RFC-7946-Lon/Lat.')
        else:data=s.collection([{**f,'geometry':mapping(transform(s.TO_LL.transform,shape(f['geometry'])))} for f in features])
        (directory/'grundstuecke.geojson').write_text(s.json.dumps(data,ensure_ascii=False),encoding='utf-8')
    if 'dxf' in formats:
        from ezdxf.colors import rgb2int
        doc=s.new_dxf();doc.layers.new('GRUNDSTUECKSGRENZEN',dxfattribs={'color':7});doc.layers.new('GRUNDSTUECKSNUMMERN',dxfattribs={'color':6,'true_color':rgb2int(COLORS[color])})
        style=doc.styles.new('HJ_NUMMERN_FETT',dxfattribs={'font':'arialbd.ttf'});style.set_extended_font_data('Arial',bold=True,italic=False)
        def rings(g):
            if g.geom_type=='Polygon':yield g.exterior;yield from g.interiors
            else:
                for child in g.geoms:yield from rings(child)
        for f in features:
            for ring in rings(shape(f['geometry'])):doc.modelspace().add_lwpolyline(list(ring.coords),close=True,dxfattribs={'layer':'GRUNDSTUECKSGRENZEN'})
        for f in labels:
            a=shape(f['geometry']);doc.modelspace().add_text(f['properties']['gnr'],dxfattribs={'layer':'GRUNDSTUECKSNUMMERN','style':'HJ_NUMMERN_FETT','height':height,'insert':(a.x,a.y),'true_color':rgb2int(COLORS[color])})
        doc.saveas(directory/'grundstuecke.dxf')
    counts={c:sum(f.get('_selection','selected')==c for f in rows) for c in ['selected','buffer','adjacent','enclosed']}
    meta['parcels']={'count':len(rows),'selectionCount':base_count,'visibleCount':counts['selected'],'bufferCount':counts['buffer'],'adjacentCount':counts['adjacent'],'enclosedCount':counts['enclosed'],'fullTouchedParcels':True,'includeAdjacent':opts.get('includeAdjacent',False),'dkmMargin':opts.get('dkmMargin',0),'selectionBounds':opts.get('dkmBounds',opts['bbox']),'numberLabels':len(labels),'previewSelectionReused':bool(snapshot),'selectedIds':[parcel_key(f) for f in rows[:base_count]],'adjacentIds':[parcel_key(f) for f in rows if f.get('_selection')=='adjacent'],'enclosedIds':[parcel_key(f) for f in rows if f.get('_selection')=='enclosed'],'rounding':{'places':places,'sourceCanonicalMetres':.001,'outputResolutionMetres':10**-places,'order':'Quell-X/Y auf 0,001 m normalisieren; Offset abziehen; auf Ausgabepräzision runden. Halbwerte vom Nullpunkt weg. Auswahl auf unveränderten Quellen.'},'labels':{'font':'arialbd.ttf','family':'Arial','bold':True,'color':color,'heightMetres':height,'limitation':'CAD muss Arial Bold verfügbar haben; Schriftersetzung kann Darstellung ändern.'},'geojsonCRS':('LOCAL:FRAME_ORIGIN_METRES' if opts.get('localOrigin') else 'EPSG:4326') if 'geojson' in formats else None}
    if not rows:meta['warnings'].append('Keine Grundstücke im DKM-Auswahlbereich.')
    meta['_parcelsFinalCoordinates']=True
    meta['sources'].append({'type':'DKM','url':s.WFS,'layers':['vogis:gst','vogis:gnr'],'retrievedAt':s.datetime.datetime.now(s.datetime.timezone.utc).isoformat(),'attribution':'VOGIS / BEV'})
