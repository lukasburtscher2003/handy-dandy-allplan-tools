"""True-scale single-page cadastral orthophoto printouts (GK West, metres)."""
import io, math
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor, white
from shapely.geometry import shape, box, Polygon, MultiPolygon, GeometryCollection

PAPER = {'A4': (210.,297.), 'A3': (297.,420.)}
MM = 72. / 25.4


def iter_parcels(core, extent, limit=4500, max_depth=12, max_requests=4096):
    """Yield unique cadastral features without the WFS 5,000-feature cutoff.

    Dense regions are recursively split on the longer edge. Do not truncate
    results: a PDF must never silently omit boundaries.
    """
    seen=set()
    requests=0

    def visit(bounds, depth):
        nonlocal requests
        requests += 1
        if requests > max_requests:
            raise ValueError('Der Lageplan enthält außergewöhnlich viele Grundstücke. Bitte einen kleineren Druckausschnitt wählen.')
        try:
            features=core.wfs('gst',bbox=bounds,limit=limit)
        except ValueError as exc:
            if 'Zu viele Objekte' not in str(exc):
                raise
            if depth>=max_depth or max(bounds[2]-bounds[0],bounds[3]-bounds[1]) < 1.0:
                raise ValueError('Zu viele Grundstücke in einem einzelnen Teilbereich. Bitte einen kleineren Druckausschnitt wählen.') from exc
            x0,y0,x1,y1=bounds
            if x1-x0 >= y1-y0:
                mid=(x0+x1)/2
                pieces=([x0,y0,mid,y1],[mid,y0,x1,y1])
            else:
                mid=(y0+y1)/2
                pieces=([x0,y0,x1,mid],[x0,mid,x1,y1])
            for piece in pieces:
                yield from visit(piece,depth+1)
            return
        for f in features:
            # A parcel straddling a tile boundary can be returned twice.
            uid=f.get('id')
            if uid is None:
                prop=f.get('properties') or {}
                uid=(prop.get('kg'),prop.get('gnr'),str(f.get('geometry')))
            if uid in seen:continue
            seen.add(uid)
            yield f

    yield from visit(extent,0)


def make_plan(core, settings):
    if not isinstance(settings,dict): raise ValueError('Ungültige Druckparameter.')
    b=settings.get('bbox')
    if not isinstance(b,list) or len(b)!=4: raise ValueError('Zuerst einen Exportbereich festlegen.')
    try: b=list(map(float,b));scale=int(settings.get('scale',1000))
    except (ValueError,TypeError): raise ValueError('Ungültiger Maßstab oder Rahmen.')
    if not all(math.isfinite(v) for v in b) or b[0]>=b[2] or b[1]>=b[3]:raise ValueError('Ungültiger Rahmen.')
    if not (-70000<=b[0]<b[2]<=5000 and 180000<=b[1]<b[3]<=285000):raise ValueError('Rahmen liegt außerhalb von Vorarlberg.')
    if not 50<=scale<=1000000:raise ValueError('Maßstabszahl zwischen 50 und 1.000.000 eingeben.')
    paper=settings.get('paper','A4');orient=settings.get('orientation','landscape')
    if paper not in PAPER or orient not in ('portrait','landscape'):raise ValueError('Ungültiges Papierformat.')
    year=int(settings.get('year',2025))
    if year not in core.YEARS:raise ValueError('Ungültiges Luftbildjahr.')
    labels=settings.get('labels',True)
    if not isinstance(labels,bool):raise ValueError('Ungültige Nummernoption.')
    def print_text(name, default, limit):
        val=settings.get(name,default)
        if not isinstance(val,str):raise ValueError('Ungültiger Text für den PDF-Plan.')
        return ''.join(ch for ch in val if ch.isprintable() and ch not in '\r\n')[:limit]
    title=print_text('title','Lageplan | Luftbild und Grundstücksgrenzen',130)
    header=print_text('header','',150)
    footer=print_text('footer','Land Vorarlberg / VOGIS · BEV | EPSG:31254',180)
    print_frame_only=settings.get('printFrameOnly',False) is True
    pw,ph=PAPER[paper]
    if orient=='landscape':pw,ph=ph,pw
    margin=12.; top=24.; bottom=19.
    mw=pw-2*margin; mh=ph-top-bottom
    # At 1:n, each millimetre of paper equals n/1000 metres on the ground.
    if settings.get('autoScale',False) is True:
        # Treat the existing export frame as the content to fit on the paper.
        # Round upwards so it is never cut off by the print margins.
        required=math.ceil(max((b[2]-b[0])*1000/mw,(b[3]-b[1])*1000/mh))
        scale=max(50,math.ceil(required/50)*50)
        if scale>1000000:raise ValueError('Exportrahmen zu groß für den maximal unterstützten PDF-Maßstab.')
    spanx=mw*scale/1000.; spany=mh*scale/1000.
    centerx=(b[0]+b[2])/2.;centery=(b[1]+b[3])/2.
    extent=[centerx-spanx/2,centery-spany/2,centerx+spanx/2,centery+spany/2]
    if b[2]-b[0]>spanx+0.2 or b[3]-b[1]>spany+0.2:
        required=math.ceil(max((b[2]-b[0])*1000/mw,(b[3]-b[1])*1000/mh))
        raise ValueError(f'Auswahl passt bei 1:{scale} nicht auf {paper}. Mindestens ca. 1:{required} wählen oder Rahmen verkleinern.')
    if not (-70000<=extent[0] and extent[2]<=5000 and 180000<=extent[1] and extent[3]<=285000):
        raise ValueError('Druckausschnitt liegt teilweise außerhalb der unterstützten Vorarlberg-Koordinaten.')
    # Limit raster to paper resolution; never download native 10 cm aerials for prints.
    dpi=160
    width=round(mw/25.4*dpi);height=round(mh/25.4*dpi)
    params={'MAP':'i_luftbilder_r_wms.map','SERVICE':'WMS','VERSION':'1.1.1','REQUEST':'GetMap',
            'LAYERS':core.YEARS[year],'STYLES':'','SRS':core.CRS_CODE,
            'BBOX':','.join(str(v) for v in extent),'WIDTH':width,'HEIGHT':height,'FORMAT':'image/jpeg'}
    response=core.get(core.MAP,params=params)
    raw=response.content
    from PIL import Image
    try:
        aerial=Image.open(io.BytesIO(raw));aerial.load()
        if aerial.size!=(width,height):raise ValueError('Luftbildauflösung stimmt nicht.')
    except Exception as exc:raise ValueError('Orthofoto konnte nicht als Bild geladen werden: '+str(exc))
    # Fetch parcels in bounded spatial chunks. WFS itself has a per-request
    # feature limit; subdivide dense areas rather than rejecting the plan.
    parcels=iter_parcels(core,extent)
    buffer=io.BytesIO();cv=canvas.Canvas(buffer,pagesize=(pw*MM,ph*MM),pageCompression=1)
    cv.setTitle(f'Lageplan {paper} 1:{scale}');cv.setAuthor('Geodatenexport')
    left=margin*MM;lower=bottom*MM;wp=mw*MM;hp=mh*MM
    cv.drawImage(ImageReader(aerial),left,lower,width=wp,height=hp)
    cv.saveState();p=cv.beginPath();p.rect(left,lower,wp,hp);cv.clipPath(p,stroke=0,fill=0)
    cv.setStrokeColor(HexColor('#ffff3a'));cv.setLineWidth(.65)
    clip=box(*extent)
    def px(x):return left+(x-extent[0])/spanx*wp
    def py(y):return lower+(y-extent[1])/spany*hp
    def outlines(geom):
        if geom.is_empty:return
        if isinstance(geom,Polygon):
            rings=[geom.exterior,*geom.interiors]
            for ring in rings:
                xy=list(ring.coords)
                if len(xy)<2:continue
                path=cv.beginPath();path.moveTo(px(xy[0][0]),py(xy[0][1]))
                for x,y in xy[1:]:path.lineTo(px(x),py(y))
                cv.drawPath(path,stroke=1,fill=0)
        elif isinstance(geom,(MultiPolygon,GeometryCollection)):
            for part in geom.geoms:outlines(part)
    for f in parcels:
        geom=shape(f['geometry'])
        if not geom.intersects(clip):continue
        outlines(geom.intersection(clip))
        if labels:
            point=geom.representative_point()
            if clip.covers(point):
                label=str(f.get('properties',{}).get('gnr',''))[:24]
                if label:
                    x,y=px(point.x),py(point.y)
                    cv.setFont('Helvetica-Bold',7)
                    # White halo helps readability on dark aerials.
                    from reportlab.pdfbase.pdfmetrics import stringWidth
                    t=stringWidth(label,'Helvetica-Bold',7)
                    cv.setFillColor(white);cv.rect(x-t/2-2,y-2,t+4,10,fill=1,stroke=0)
                    cv.setFillColor(HexColor('#15191f'));cv.drawCentredString(x,y,label)
    # Selected area, slightly highlighted for orientation.
    if not print_frame_only:
        cv.setDash(3,2);cv.setStrokeColor(HexColor('#ef2d80'));cv.setLineWidth(1.1)
        cv.rect(px(b[0]),py(b[1]),(b[2]-b[0])/spanx*wp,(b[3]-b[1])/spany*hp,fill=0,stroke=1)
    cv.restoreState()
    cv.setStrokeColor(HexColor('#333333'));cv.setLineWidth(.6);cv.rect(left,lower,wp,hp,stroke=1,fill=0)
    def fitted(line, font, size, maxwidth):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        while line and stringWidth(line,font,size)>maxwidth:
            line=line[:-1]
        return line
    cv.setFillColor(HexColor('#171f29'))
    cv.setFont('Helvetica',8)
    if header:cv.drawString(left,(ph-7)*MM,fitted(header,'Helvetica',8,wp))
    cv.setFont('Helvetica-Bold',13)
    cv.drawString(left,(ph-14)*MM,fitted(title,'Helvetica-Bold',13,wp))
    cv.setFont('Helvetica',8)
    cv.drawString(left,(ph-20)*MM,f'Blatt: {paper} {"Querformat" if orient=="landscape" else "Hochformat"}    Maßstab 1:{scale}    Luftbild {year}')
    cv.drawString(left,10*MM,fitted(footer,'Helvetica',8,wp))
    cv.setFont('Helvetica',7)
    cv.drawRightString((pw-margin)*MM,5*MM,'Maßstab gilt bei Druck mit 100 % / tatsächlicher Größe')
    # Physical control bar, consistent with ground distance.
    bar_m=round(spanx/5/10)*10
    if bar_m>0 and bar_m < spanx/2:
        bar=bar_m/spanx*wp; x=left+8; y=lower+10
        cv.setStrokeColor(white);cv.setLineWidth(3);cv.line(x,y,x+bar,y)
        cv.setStrokeColor(HexColor('#222222'));cv.setLineWidth(1.3);cv.line(x,y,x+bar,y)
        cv.setFillColor(white);cv.rect(x-2,y+3,55,11,fill=1,stroke=0)
        cv.setFillColor(HexColor('#222222'));cv.setFont('Helvetica-Bold',8);cv.drawString(x,y+6,f'{bar_m} m')
    cv.showPage();cv.save();buffer.seek(0)
    return buffer
