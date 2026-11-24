"""Natural Earth 50m land (world-atlas topojson) -> one SVG path for the Caribbean, Gulf and Bahamas.
Projection (shared with app/trip.py and app.js): x=(lon-LON0)*K*S, y=(LAT1-lat)*S.

  make-caribbean-map.py land-50m.json web/img/caribbean.svg            (8 to 33 N)
  make-caribbean-map.py land-50m.json web/img/north.svg 33 49          (the US above it, for "How far is Mom?";
                                                                       same units, so its y runs negative)"""
import json,math,sys
LON0,LON1,LAT0,LAT1=-98.0,-58.0,8.0,33.0
K=math.cos(math.radians(22)); S=30.0
W=(LON1-LON0)*K*S
C0,C1=(float(sys.argv[3]),float(sys.argv[4])) if len(sys.argv)>4 else (LAT0,LAT1)   # the latitudes to draw
Y0=(LAT1-C1)*S; H=(C1-C0)*S
topo=json.load(open(sys.argv[1]))
sc=topo['transform']['scale']; tr=topo['transform']['translate']
arcs=[]
for a in topo['arcs']:
    x=y=0; pts=[]
    for dx,dy in a:
        x+=dx;y+=dy; pts.append((x*sc[0]+tr[0], y*sc[1]+tr[1]))
    arcs.append(pts)
def ring(idx):
    pts=[]
    for i in idx:
        a=arcs[i] if i>=0 else arcs[~i][::-1]
        pts.extend(a if not pts else a[1:])
    return pts
def rdp(pts,eps):
    keep=[False]*len(pts); keep[0]=keep[-1]=True; st=[(0,len(pts)-1)]
    while st:
        a,b=st.pop(); (x1,y1),(x2,y2)=pts[a],pts[b]; dx,dy=x2-x1,y2-y1; L=math.hypot(dx,dy)
        dm,ix=0,0
        for i in range(a+1,b):
            x,y=pts[i]; d=abs(dy*x-dx*y+x2*y1-y2*x1)/L if L else math.hypot(x-x1,y-y1)
            if d>dm: dm,ix=d,i
        if dm>eps: keep[ix]=True; st+=[(a,ix),(ix,b)]
    return [p for p,k in zip(pts,keep) if k]
polys=[]
for g in topo['objects']['land']['geometries']:
    polys.extend([g['arcs']] if g['type']=='Polygon' else g['arcs'] if g['type']=='MultiPolygon' else [])
d=[]
for poly in polys:
    for r in poly:
        pts=ring(r)
        lo=[p[0] for p in pts]; la=[p[1] for p in pts]
        if max(lo)<LON0-2 or min(lo)>LON1+2 or max(la)<C0-2 or min(la)>C1+2: continue
        xy=[((lon-LON0)*K*S,(LAT1-lat)*S) for lon,lat in pts]
        # clamp far-away parts (big continents) to a margin box so the path stays small
        m=60; xy=[(min(max(x,-m),W+m),min(max(y,Y0-m),Y0+H+m)) for x,y in xy]
        area=abs(sum(xy[i][0]*xy[i-1][1]-xy[i-1][0]*xy[i][1] for i in range(len(xy))))/2
        if area<0.08: continue
        s=rdp(xy,0.2)
        if len(s)<3: continue
        d.append('M'+' '.join('%.1f,%.1f'%p for p in s).replace('.0,',',').replace('.0 ',' ')+'Z')
path=''.join(d)
open(sys.argv[2],'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {Y0:.1f} {W:.1f} {H:.1f}" width="{W:.1f}" height="{H:.1f}"><path d="{path}" fill="#E8DFC9" stroke="#B9A57A" stroke-width="0.8" stroke-linejoin="round"/></svg>\n')
print(len(d), len(path), round(W,1), H)
