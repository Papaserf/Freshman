"""FRESHMAN cast generator, pass 3. Blender 4.2–5.3 target, no third-party add-ons.
python3 make_cast.py --out ./out
blender -b -P make_cast.py -- --out ./out
All geometry in meters; Blender front -Y, glTF front +Z.
"""
import argparse
import json
import math
import sys
import struct
from pathlib import Path
import bpy
from mathutils import Vector, Quaternion

# --------------------------- editable proportions ---------------------------
HEIGHT = 1.80
HEAD_H, HEAD_W, HEAD_D = .23, .16, .185
HEAD_CENTER = (0, -.006, 1.685)
NECK_Z = 1.51
SHOULDER_Z, SHOULDER_HALF = 1.455, .182
UPPER_ARM, FOREARM, HAND_LENGTH = .31, .27, .20
ARM_ANGLE = math.radians(8)
HIP_Z, HIP_HALF = .94, .10
THIGH, SHIN = .45, .40
ANKLE_Z = HIP_Z - THIGH - SHIN
FOOT_LENGTH, FOOT_WIDTH = .29, .12
RING_N = 20
MORPHS = ('heavy', 'broad', 'slim', 'curvy', 'adult')
SLOTS = ('Head', 'Skin', 'Shirt', 'Sleeves', 'Shorts', 'Shins', 'Shoes')
HAIRS = ('short', 'buzz', 'fade', 'curly', 'locs', 'messy', 'long', 'bald_ring')
TAU = 2 * math.pi
# Palette only for previews; runtime replaces these materials.
COLORS = ((.56,.33,.22),(.56,.33,.22),(.085,.17,.29),(.085,.17,.29),(.055,.09,.16),(.56,.33,.22),(.16,.19,.23))

HEAD_SECTIONS=[(-1.,.40,.38,.005),(-.89,.67,.58,-.005),(-.72,.91,.76,-.009),
                   (-.49,1.,.88,-.006),(-.24,.96,.96,0),(-.06,.97,1.,0),
                   (.10,1.,1.,0),(.24,.98,.98,0),(.43,.99,.99,.003),
                   (.62,.96,.94,.005),(.79,.83,.82,.006),(.91,.62,.64,.006),
                   (.98,.30,.33,.006),(1.,.035,.04,.006)]


def mix(a,b,t): return a+(b-a)*t

def smooth(t):
    t=max(0.,min(1.,t)); return t*t*(3-2*t)

def signpow(x,p): return math.copysign(abs(x)**p,x)

def gltf(p): return (p[0],p[2],-p[1])

def joint_weights(a,b,t):
    t=smooth(t); return {a:1-t,b:t}

# Joint positions are derived from the editable limb dimensions.
BONES = {}
def bone(name,parent,h,t): BONES[name]=(parent,Vector(h),Vector(t))
bone('root',None,(0,0,0),(0,0,.16))
bone('hips','root',(0,0,HIP_Z),(0,0,1.075))
bone('spine','hips',(0,0,1.075),(0,0,1.29))
bone('chest','spine',(0,0,1.29),(0,0,NECK_Z))
bone('neck','chest',(0,0,NECK_Z),(0,0,1.57))
bone('head','neck',(0,0,1.57),(0,0,HEIGHT))
for side,s in [('L',1),('R',-1)]:
    a=Vector((s*SHOULDER_HALF,0,SHOULDER_Z))
    d=Vector((s*math.sin(ARM_ANGLE),0,-math.cos(ARM_ANGLE)))
    e=a+d*UPPER_ARM; h=e+d*FOREARM
    bone('shoulder_'+side,'chest',a,e)
    bone('elbow_'+side,'shoulder_'+side,e,h)
    bone('hand_'+side,'elbow_'+side,h,h+d*HAND_LENGTH)
    p=Vector((s*HIP_HALF,0,HIP_Z)); k=p+Vector((0,-.012,-THIGH)); f=Vector((s*HIP_HALF,0,ANKLE_Z))
    bone('thigh_'+side,'hips',p,k)
    bone('knee_'+side,'thigh_'+side,k,f)
    bone('foot_'+side,'knee_'+side,f,(s*HIP_HALF,-.17,.045))


class Builder:
    """Indexed mesh + per-face material + normalized explicit weights.
    Ring strips share vertices along each strip, including material borders.
    Intersections between anatomical sections are intentional, not booleans.
    """
    def __init__(self):
        self.v=[]; self.f=[]; self.mat=[]; self.w=[]; self.tags=[]; self.sharp=set()
    def vertex(self,p,w,tag):
        self.v.append(tuple(p)); self.w.append(dict(w)); self.tags.append(tag); return len(self.v)-1
    def face(self,ids,mat): self.f.append(tuple(ids)); self.mat.append(mat)
    def ring(self,center,rx,ry,weights,tag,n=RING_N,power=1.,basis=None,phase=0.,warp=None):
        c=Vector(center); U,V=basis or (Vector((1,0,0)),Vector((0,1,0)))
        ids=[]
        for i in range(n):
            a=phase+TAU*i/n
            p=c+U*(rx*signpow(math.cos(a),power))+V*(ry*signpow(math.sin(a),power))
            if warp: p=Vector(warp(p,a))
            ids.append(self.vertex(p,weights,tag))
        return ids
    def join(self,a,b,mat,reverse=False):
        assert len(a)==len(b)
        for i in range(len(a)):
            j=(i+1)%len(a); f=(a[i],a[j],b[j],b[i]); self.face(f[::-1] if reverse else f,mat)
    def cap(self,a,mat,reverse=False):
        # ngon triangulates deterministically in Blender's mesh evaluation.
        self.face(a[::-1] if reverse else a,mat)
    def crease(self,r):
        for i in range(len(r)): self.sharp.add(tuple(sorted((r[i],r[(i+1)%len(r)]))))
    def ellipsoid(self,c,r,w,tag,mat,n=12,levels=6,power=.85):
        rings=[]
        for i in range(1,levels):
            a=-math.pi/2+math.pi*i/levels
            rings.append(self.ring((c[0],c[1],c[2]+r[2]*math.sin(a)),r[0]*math.cos(a),r[1]*math.cos(a),w,tag,n,power))
        self.cap(rings[0],mat,True)
        for a,b in zip(rings,rings[1:]): self.join(a,b,mat)
        self.cap(rings[-1],mat)
    def object(self,name,materials):
        m=bpy.data.meshes.new(name); m.from_pydata(self.v,[],self.f); m.update()
        obj=bpy.data.objects.new(name,m); bpy.context.collection.objects.link(obj)
        for mat in materials: m.materials.append(mat)
        for p,idx in zip(m.polygons,self.mat): p.material_index=idx; p.use_smooth=True
        for e in m.edges:
            if tuple(sorted(e.vertices)) in self.sharp: e.use_edge_sharp=True
        # Recalculate outward normals on each closed shell. Does not weld parts.
        import bmesh
        bm=bmesh.new(); bm.from_mesh(m); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(m); bm.free(); m.update()
        assert len(m.vertices)==len(self.v)
        assert all((v.co-Vector(p)).length<1e-6 for v,p in zip(m.vertices,self.v)), 'Vertex order changed'
        return obj


def torso_weights(z):
    if z<1.16: return joint_weights('hips','spine',(z-.98)/.16)
    if z<1.32: return joint_weights('spine','chest',(z-1.16)/.16)
    return {'chest':1.}


def make_geometry():
    b=Builder(); rings=[]
    # Bottom to top. Continuous shorts/torso shell with material border at waist.
    # Pass 4: athletic V-taper. Shallower chest/back (less barrel), no hip
    # ledge at the waistband, narrower shoulder cap so the deltoids carry width.
    sections=[(.915,.118,.072),(.925,.148,.090),(.94,.158,.098),(.99,.156,.096),
              (1.035,.146,.090),(1.075,.139,.086),(1.12,.141,.087),
              (1.17,.149,.091),(1.22,.161,.097),(1.27,.174,.103),
              (1.32,.184,.105),(1.37,.191,.101),(1.415,.196,.092),
              (1.455,.200,.077),(1.485,.142,.064),(1.51,.058,.055)]
    for z,x,y in sections:
        ring=b.ring((0,0,z),x,y,torso_weights(z),'torso',20,.68,phase=math.pi/2)
        # Pass 3: straighten only the anterior hem; retain the back and
        # lateral silhouette. The heavy morph adds its own belly below.
        if 1.035 <= z <= 1.12:
            for i in ring:
                px,py,pz=b.v[i]
                if py<0:
                    b.v[i]=(px,py*((.080 if z<1.075 else .082)/y),pz)
        # Eight-centimeter lateral blend band across the upper chest. Keep
        # central chest/trapezius stable; move the outer shoulder with the arm.
        for i in ring:
            px,py,pz=b.v[i]
            lateral=smooth((abs(px)-(SHOULDER_HALF-.08))/.08)
            vertical=smooth((pz-(SHOULDER_Z-.14))/.10)
            amount=.78*lateral*vertical
            if amount>0:
                side='L' if px>=0 else 'R'
                w={k:v*(1-amount) for k,v in b.w[i].items()}
                w['shoulder_'+side]=amount; b.w[i]=w
        rings.append(ring)
    b.cap(rings[0],4,True)
    for i,(a,c) in enumerate(zip(rings,rings[1:])): b.join(a,c,4 if sections[i][0]<1.075 else 2)
    b.cap(rings[-1],2)
    # Neck extends into both torso and head.
    rings=[]
    for z,x,y,t in [(1.485,.061,.056,0),(1.515,.057,.052,.3),(1.55,.052,.049,.85),(1.605,.054,.049,1)]:
        rings.append(b.ring((0,-.006,z),x,y,joint_weights('chest','neck',t),'neck',16))
    b.cap(rings[0],1,True)
    for a,c in zip(rings,rings[1:]): b.join(a,c,1)
    b.cap(rings[-1],1)
    # Flat-ish anterior plane, pronounced jaw and brow. No modeled eyes or mouth.
    head_sections=HEAD_SECTIONS
    rings=[]
    for q,wx,wy,dy in head_sections:
        z=HEAD_CENTER[2]+HEAD_H*q/2
        def face_warp(p,a,q=q):
            # Gentle central nose and wide brow ridge; face texture supplies detail.
            front=max(0.,-math.sin(a)); central=math.exp(-(p.x/.019)**2)
            p.y-=.010*front**6*central*math.exp(-((q+.10)/.25)**2)
            p.y-=.004*front**4*math.exp(-((q-.12)/.13)**2)
            return p
        rings.append(b.ring((0,HEAD_CENTER[1]+dy,z),HEAD_W/2*wx,HEAD_D/2*wy,{'head':1},'head',24,.68,phase=math.pi,warp=face_warp))
    b.cap(rings[0],0,True)
    for a,c in zip(rings,rings[1:]): b.join(a,c,0)
    b.cap(rings[-1],0); b.crease(rings[2]); b.crease(rings[6])
    for s in (-1,1): b.ellipsoid((s*.080,.003,1.676),(.016,.028,.040),{'head':1},'head',0,12,6)
    # Arms: continuous strip from shoulder to wrist; ring planes perpendicular to bone.
    for side,s in [('L',1),('R',-1)]:
        upper='shoulder_'+side; lower='elbow_'+side; hand='hand_'+side
        a=BONES[upper][1]; e=BONES[lower][1]; h=BONES[hand][1]; d=(e-a).normalized()
        U=Vector((math.cos(ARM_ANGLE),0,s*math.sin(ARM_ANGLE))); V=Vector((0,1,0))
        # Rounded deltoid: start with a small, buried medial cap, then
        # expand outward and downward. No full-width ring above the pivot.
        # (distance along arm, transverse radii, medial inset)
        lengths=[(-.055,.025,.035,.065),(-.040,.039,.050,.052),
                 (-.025,.055,.063,.037),(-.008,.067,.071,.022),
                 (.018,.076,.075,.009),(.045,.077,.071,0),
                 (.075,.074,.068,0),(.10,.071,.065,0),(.17,.064,.059,0),
                 (.235,.052,.049,0),(.27,.049,.047,0),(.29,.049,.047,0),
                 (.31,.048,.046,0),(.33,.048,.045,0),(.35,.050,.047,0),
                 (.385,.056,.050,0),(.435,.052,.046,0),(.49,.044,.039,0),
                 (.535,.037,.033,0),(.555,.033,.030,0),(.58,.032,.029,0),(.60,.030,.029,0)]
        lengths=[(t,rx*(.70 if t<.10 else .79 if t<=.31 else .86),ry*(.74 if t<.10 else .82 if t<=.31 else .88),inset*.8) for t,rx,ry,inset in lengths]
        rings=[]
        for t,rx,ry,inset in lengths:
            l=t*UPPER_ARM/.31 if t<=.31 else UPPER_ARM+(t-.31)*FOREARM/.27
            center=a+d*l-Vector((s*inset,0,0))
            if l<.10: w=joint_weights('chest',upper,(l+.065)/.165)
            elif l<UPPER_ARM+.06: w=joint_weights(upper,lower,(l-UPPER_ARM+.06)/.12)
            else: w=joint_weights(lower,hand,(l-UPPER_ARM-FOREARM+.045)/.075)
            ring=b.ring(center,rx,ry,w,'arm.'+side,16,.78,(U,V))
            if l<.10:
                for i in ring:
                    # Outer deltoid follows the humerus early; medial root
                    # follows the chest. Smoothly converge to rigid upper arm.
                    px,_,_=b.v[i]
                    outer=smooth((s*px-(SHOULDER_HALF-.08))/.115)
                    along=smooth((l+.055)/.155)
                    amount=along+(1-along)*outer*.85
                    b.w[i]={'chest':1-amount,upper:amount}
            rings.append(ring)
        b.cap(rings[0],3)
        for i,(r,q) in enumerate(zip(rings,rings[1:])): b.join(r,q,3 if lengths[i][0]<.31 else 1,True)
        b.cap(rings[-1],1,True); b.crease(rings[-2])
        # Pass 3: palms face thighs; four individually modeled fingers
        # and a separate thumb. All remain rigidly weighted to the hand
        # bone, preserving the procedural wrist-snap contract.
        palm=[]
        scale=HAND_LENGTH/.20
        for t,rx,ry in [(-.015,.031,.030),(.02,.033,.041),(.055,.027,.046),(.095,.022,.044)]:
            palm.append(b.ring(h+d*(t*scale),rx,ry,{hand:1},'hand_'+side,12,.68,(U,V)))
        b.cap(palm[0],1)
        for r,q in zip(palm,palm[1:]): b.join(r,q,1,True)
        b.cap(palm[-1],1,True)
        # Index is toward the front (-Y); little finger toward the back.
        # Bases overlap the palm slightly; narrow gaps read at silhouette.
        for offset,end,width in [(-.033,.184,.0105),(-.011,.20,.0105),
                                 (.011,.191,.0100),(.032,.166,.0090)]:
            finger=[]
            for t,depth,w,bend in [(.080,.015,width,0),
                                    (mix(.095,end,.55),.012,width*.91,.004),
                                    (end-.008,.009,width*.75,.010),
                                    (end,.005,width*.48,.013)]:
                c=h+d*(t*scale)+V*offset-U*(s*bend)
                finger.append(b.ring(c,depth,w,{hand:1},'hand_'+side,6,.85,(U,V)))
            b.cap(finger[0],1)
            for r,q in zip(finger,finger[1:]): b.join(r,q,1,True)
            b.cap(finger[-1],1,True)
        # Thumb diverges forward and inward from the palm, then curls
        # slightly toward the fingers. Same material and bone as before.
        thumb=[]
        for t,front,inward,rx,ry in [(.028,.030,.012,.019,.017),
                                     (.060,.052,.017,.016,.014),
                                     (.100,.058,.026,.012,.010),
                                     (.115,.052,.032,.007,.006)]:
            c=h+d*(t*scale)-V*front-U*(s*inward)
            thumb.append(b.ring(c,rx,ry,{hand:1},'hand_'+side,8,.85,(U,V)))
        b.cap(thumb[0],1)
        for r,q in zip(thumb,thumb[1:]): b.join(r,q,1,True)
        b.cap(thumb[-1],1,True)
    # Legs: continuous knee loops, shorts and shins share border topology.
    for side,s in [('L',1),('R',-1)]:
        thigh='thigh_'+side; knee='knee_'+side; foot='foot_'+side
        p=BONES[thigh][1]; k=BONES[knee][1]; f=BONES[foot][1]; rings=[]
        # Pass 4: leaner thighs, a real knee, a calf that sits behind the shin, thin ankles.
        specs=[(-.09,.088,.094),(-.055,.092,.098),(0,.090,.096),(.06,.086,.092),(.13,.081,.087),(.21,.074,.080),(.29,.066,.071),(.36,.058,.063),(.40,.054,.059),(.43,.052,.056),(.45,.051,.055),(.47,.050,.055),(.49,.050,.057),(.52,.052,.061),(.57,.054,.063),(.63,.050,.057),(.69,.043,.047),(.75,.036,.039),(.81,.032,.034),(.85,.035,.038)]
        for t,rx,ry in specs:
            l=t*THIGH/.45 if t<=.45 else THIGH+(t-.45)*SHIN/.40
            center=p.lerp(k,l/THIGH) if l<=THIGH else k.lerp(f,(l-THIGH)/SHIN)
            if l<.12: w=joint_weights('hips',thigh,(l+.055)/.175)
            elif l<THIGH+.07: w=joint_weights(thigh,knee,(l-THIGH+.07)/.14)
            else: w=joint_weights(knee,foot,(l-THIGH-SHIN+.06)/.09)
            rings.append(b.ring(center,rx,ry,w,'leg.'+side,16,.74))
        b.cap(rings[0],4)
        for i,(r,q) in enumerate(zip(rings,rings[1:])): b.join(r,q,4 if specs[i][0]<.40 else 5,True)
        b.cap(rings[-1],5,True); b.crease(rings[-1])
        # One shoe shell, with sharp sole edges and a squared toe box.
        shoe=[]
        for z,cy,rx,ry in [(0,-.055,.055,.137),(.012,-.055,.060,.145),(.030,-.055,.060,.145),(.041,-.056,.058,.142),(.065,-.052,.056,.137),(.087,-.023,.052,.105),(.112,.002,.049,.061),(.151,.003,.046,.051)]:
            shoe.append(b.ring((s*HIP_HALF,cy*FOOT_LENGTH/.29,z),rx*FOOT_WIDTH/.12,ry*FOOT_LENGTH/.29,{foot:1},'shoe.'+side,16,.58))
        b.cap(shoe[0],6,True)
        for r,q in zip(shoe[:2],shoe[1:3]): b.join(r,q,6)
        b.cap(shoe[2],6); b.crease(shoe[1]); b.crease(shoe[2])
        # Independent outsole shell, with a duplicated upper seam.
        upper_base=[b.vertex(b.v[i],{foot:1},'shoe.'+side) for i in shoe[2]]
        upper=[upper_base,*shoe[3:]]
        b.cap(upper_base,6,True); b.crease(upper_base)
        for r,q in zip(upper,upper[1:]): b.join(r,q,6)
        b.cap(shoe[-1],6); b.crease(shoe[-1])
    return b


def apply_uv(obj):
    m=obj.data; uv=m.uv_layers.new(name='UVMap'); center=Vector(HEAD_CENTER)
    for p in m.polygons:
        coords=[]
        for li in p.loop_indices:
            x,y,z=m.vertices[m.loops[li].vertex_index].co
            if p.material_index==0:
                d=Vector((x,y,z))-center; r=max(d.length,1e-10)
                u=(math.atan2(-d.y,-d.x)/TAU)%1
                v=1-math.acos(max(-1,min(1,d.z/r)))/math.pi
            elif p.material_index==2:
                u=(math.atan2(-x,y)/TAU)%1; v=(z-1.075)/(1.51-1.075)
            else:
                # Generic cylindrical limb/part UVs; only Head and Shirt are contractual.
                cx=0 if p.material_index==1 and z>1.48 else math.copysign(HIP_HALF if p.material_index in (4,5,6) else SHOULDER_HALF,x)
                u=(math.atan2(-(x-cx),y)/TAU)%1; v=z/HEIGHT
            coords.append([u,max(0,min(1,v))])
        # Duplicate the exact seam longitude on the other side when needed.
        # Never shift arbitrary vertices outside [0,1] or change the specified mapping.
        us=[a[0] for a in coords]
        interior=[u for u in us if 1e-12<u<1-1e-12]
        if interior:
            seam_value=1. if sum(interior)/len(interior)>.5 else 0.
            for a in coords:
                if a[0]<1e-12 or a[0]>1-1e-12: a[0]=seam_value
        for li,a in zip(p.loop_indices,coords): uv.data[li].uv=a


def make_rig():
    data=bpy.data.armatures.new('FRESHMAN_Rig'); rig=bpy.data.objects.new('FRESHMAN_Rig',data)
    bpy.context.collection.objects.link(rig); bpy.context.view_layer.objects.active=rig; rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name,(parent,h,t) in BONES.items():
        b=data.edit_bones.new(name); b.head=h; b.tail=t; b.roll=0
        if parent: b.parent=data.edit_bones[parent]
        b.use_connect=False
    bpy.ops.object.mode_set(mode='OBJECT'); rig.select_set(False); return rig


def skin(obj,b,rig):
    groups={name:obj.vertex_groups.new(name=name) for name in BONES}
    for i,w in enumerate(b.w):
        w={k:v for k,v in w.items() if v>1e-8}; total=sum(w.values())
        assert 0<len(w)<=4 and total>0
        for k,v in w.items(): groups[k].add([i],v/total,'REPLACE')
    mod=obj.modifiers.new('Skin','ARMATURE'); mod.object=rig
    # Linear blend skinning, matching Three.js rather than Blender-only dual quaternions.
    mod.use_deform_preserve_volume=False; obj.parent=rig


def morph_position(p,tag,name):
    x,y,z=p; s=1 if x>=0 else -1
    if tag in ('head','neck','shoe.L','shoe.R'): return p
    # Blend regions around fixed joint centers: changes girth more than joint placement.
    waist=math.exp(-((z-1.10)/.17)**2); chest=math.exp(-((z-1.36)/.15)**2)
    hip=math.exp(-((z-.96)/.15)**2)
    if tag=='torso':
        if name=='heavy': x*=1+.48*waist+.24*hip+.16*chest; y*=1+.96*waist+.32*hip; y-=.070*waist
        elif name=='broad':
            # V taper: preserve chest depth, narrow waist, and carry the
            # widened deltoid into the outer upper torso (fixed rig pivots).
            lateral=smooth((abs(x)-.075)/.13)
            shoulder_band=math.exp(-((z-1.445)/.115)**2)
            x*=1+.37*chest-.13*math.exp(-((z-1.10)/.085)**2)
            x+=s*.012*lateral*shoulder_band
            y*=1+.30*chest
        elif name=='slim': x*=.73; y*=.70
        elif name=='curvy': x*=1+.20*hip-.22*waist-.08*chest; y*=1+.13*hip-.13*waist+.10*chest; y-=.020*chest
        elif name=='adult': x*=1+.13*waist-.04*chest; y*=1+.25*waist; y-=.012*waist
    elif tag.startswith(('arm.','hand_','leg.')):
        side=tag[-1]; is_arm=tag.startswith(('arm.','hand_'))
        if is_arm:
            a=BONES['shoulder_'+side][1]; h=BONES['hand_'+side][1]; d=(h-a).normalized()
            center=a+d*((Vector(p)-a).dot(d)); base=Vector(p)-center
        else:
            center=Vector((s*HIP_HALF,0,z)); base=Vector(p)-center
        f={'heavy':1.40,'broad':1.12 if is_arm else 1.06,'slim':.65,'curvy':.88 if is_arm else 1.12,'adult':1.08}[name]
        if tag.startswith('hand_'): f=mix(1,f,.35)
        if not is_arm: f=mix(1,f,smooth((z-ANKLE_Z)/.18))
        x,y,z=center+base*f
        # Slight shoulder silhouette adjustment; keep motion pivots near fixed centers.
        if is_arm and not tag.startswith('hand_'):
            blend=math.exp(-((z-SHOULDER_Z)/.24)**2)
            x+=s*blend*{'heavy':.018,'broad':.035,'slim':-.030,'curvy':-.012,'adult':-.004}[name]
    return (x,y,z)


def add_morphs(obj,b):
    obj.shape_key_add(name='Basis',from_mix=False)
    for name in MORPHS:
        key=obj.shape_key_add(name=name,from_mix=False); key.slider_min=0; key.slider_max=1; key.value=0  # exported glTF default weights must be 0
        for i,(p,tag) in enumerate(zip(b.v,b.tags)): key.data[i].co=morph_position(p,tag,name)


def material(name,color):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.diffuse_color=(*color,1)
    node=m.node_tree.nodes.get('Principled BSDF'); node.inputs['Base Color'].default_value=(*color,1); node.inputs['Roughness'].default_value=.85
    return m


def export(path,objs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs: ob.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,
        export_apply=True,export_animations=False,export_morph=True,export_morph_normal=False,
        export_skins=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',
        export_all_influences=False)


def hair_cap(b,style):
    # Rings from crown to variable hairline; no face geometry below hairline.
    n=24; rings=[]; c=Vector(HEAD_CENTER)
    if style=='bald_ring':
        # Open horseshoe strip around side/back, omitting the front sector.
        rows=[]
        for phi in (.88,1.04,1.20,1.38,1.53):
            row=[]
            for i in range(19):
                a=-.10+(math.pi+.20)*i/18
                row.append(b.vertex(c+Vector((.084*math.sin(phi)*math.cos(a),.102*math.sin(phi)*math.sin(a),.121*math.cos(phi))),{},'hair'))
            rows.append(row)
        for a,d in zip(rows,rows[1:]):
            for i in range(len(a)-1): b.face((a[i],d[i],d[i+1],a[i+1]),0)
        return
    bulk={'buzz':.004,'fade':.008,'short':.012,'curly':.020,'locs':.019,'messy':.022,'long':.014}[style]
    if style in ('short','buzz','fade'):
        # Match the actual head's cross-sections, not an approximate sphere.
        # Front hairline z=1.725 m: roughly 2 cm above the drawn brow.
        # The side/back line wraps down, with a slightly higher fade temple.
        front_z=1.725
        def profile(z):
            q=(z-HEAD_CENTER[2])/(HEAD_H/2)
            for lo,hi in zip(HEAD_SECTIONS,HEAD_SECTIONS[1:]):
                if q<=hi[0]:
                    t=max(0,min(1,(q-lo[0])/(hi[0]-lo[0])))
                    return tuple(mix(lo[k],hi[k],t) for k in (1,2,3))
            return HEAD_SECTIONS[-1][1:]
        # Seven rings instead of six to follow the angular skull profile.
        # Keep the hairline itself thin and the upper shell slightly fuller.
        for j in range(7):
            row=[]
            t=j/6
            for i in range(n):
                a=TAU*i/n; front=max(0,-math.sin(a)); back=max(0,math.sin(a))
                side_z=1.685 if style!='fade' else 1.700
                line=side_z+(front_z-side_z)*front**2-.025*back**2
                z=mix(HEIGHT-.001,line,t)
                wx,wy,dy=profile(z)
                # Add radial clearance at skull corners; avoid a floating cap.
                clearance=mix(bulk,.0025,t**3)
                rx=HEAD_W/2*wx+clearance; ry=HEAD_D/2*wy+clearance
                crown=bulk*(1-t)**2
                px=rx*signpow(math.cos(a),.68)
                py=HEAD_CENTER[1]+dy+ry*signpow(math.sin(a),.68)
                row.append(b.vertex((px,py,z+crown),{},'hair'))
            rings.append(row)
    else:
        for j in range(1,7):
            row=[]
            for i in range(n):
                a=TAU*i/n; front=max(0,-math.sin(a)); back=max(0,math.sin(a))
                bottom=1.48-.47*front+.22*back
                if style=='fade': bottom-=.13*(1-front)
                phi=bottom*j/6
                jitter=0 if style in ('buzz','fade') else .003*math.sin(7*a+2*j)
                p=c+Vector(((.085+bulk*.48+jitter)*math.sin(phi)*signpow(math.cos(a),.68),(.100+bulk*.5+jitter)*math.sin(phi)*signpow(math.sin(a),.68),(.115+bulk+jitter)*math.cos(phi)))
                row.append(b.vertex(p,{},'hair'))
            rings.append(row)
    b.cap(rings[0],0)
    for a,d in zip(rings,rings[1:]): b.join(a,d,0,True)
    # Cap underside at the hairline: inside the head and unseen.
    b.cap(rings[-1],0,True)
    if style=='curly':
        for j in range(2):
            for i in range(9):
                a=TAU*(i+.5*j)/9; r=.038+.029*j
                b.ellipsoid((r*math.cos(a),r*math.sin(a),1.795-.025*j),(.025,.027,.029),{},'hair',0,7,3)
    elif style=='messy':
        for i in range(9):
            a=TAU*i/9; p=Vector((.050*math.cos(a),.055*math.sin(a),1.785))
            r=b.ring(p,.023,.020,{},'hair',7); tip=b.vertex(p+Vector((.025*math.cos(a+.6),.024*math.sin(a+.6),.045+.012*math.sin(i))),{},'hair')
            b.cap(r,0,True)
            for j in range(len(r)): b.face((r[j],r[(j+1)%len(r)],tip),0)
    elif style=='locs':
        for i in range(9):
            a=TAU*i/9; rows=[]
            for j in range(4):
                p=Vector((math.cos(a)*(.045+.035*j/3),math.sin(a)*(.056+.035*j/3),1.795-.045*j+.009*math.sin(i)))
                rows.append(b.ring(p,.015-.002*j,.015-.002*j,{},'hair',7,.85))
            b.cap(rows[0],0)
            for r,q in zip(rows,rows[1:]): b.join(r,q,0,True)
            b.cap(rows[-1],0,True)
    elif style=='long':
        rows=[]
        for z,y,xr,yr in [(1.72,.095,.034,.033),(1.68,.128,.038,.039),(1.60,.145,.042,.037),(1.51,.13,.035,.031),(1.44,.10,.018,.018)]:
            rows.append(b.ring((0,y,z),xr,yr,{},'hair',14,.75))
        b.cap(rows[0],0)
        for r,q in zip(rows,rows[1:]): b.join(r,q,0,True)
        b.cap(rows[-1],0,True)


def make_hair(style,rig,mat):
    b=Builder(); hair_cap(b,style); ob=b.object('hair_'+style,[mat])
    # glTF node local geometry must match HEAD BONE local axes, not world axes.
    # Blender exporter represents joint local axes with a basis conversion; use
    # the actual exported joint world matrix to avoid guessing that convention.
    uv=ob.data.uv_layers.new(name='UVMap')
    for loop in ob.data.loops:
        p=ob.data.vertices[loop.vertex_index].co-Vector(HEAD_CENTER)
        uv.data[loop.index].uv=((math.atan2(-p.y,-p.x)/TAU)%1,max(0,min(1,(p.z+.25)/.45)))
    return ob


def read_glb(path):
    raw=path.read_bytes(); magic,version,total=struct.unpack_from('<4sII',raw)
    assert magic==b'glTF' and version==2 and total==len(raw)
    n,typ=struct.unpack_from('<I4s',raw,12); assert typ==b'JSON'
    return json.loads(raw[20:20+n])


def node_world(doc,name):
    from mathutils import Matrix
    nodes=doc['nodes']; parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
    def local(n):
        if 'matrix' in n: return Matrix([n['matrix'][i::4] for i in range(4)])
        q=n.get('rotation',[0,0,0,1]); r=Quaternion((q[3],q[0],q[1],q[2])).to_matrix().to_4x4()
        return Matrix.Translation(n.get('translation',[0,0,0]))@r@Matrix.Diagonal((*n.get('scale',[1,1,1]),1))
    idx=next(i for i,n in enumerate(nodes) if n.get('name')==name); m=local(nodes[idx])
    while idx in parents: idx=parents[idx]; m=local(nodes[idx])@m
    return m


def hair_to_bone_local(ob,head_world):
    inv=head_world.inverted()
    for v in ob.data.vertices:
        local=inv@Vector(gltf(v.co)); v.co=(local.x,-local.z,local.y)
    ob.data.update()


def tri_count(ob):
    ob.data.calc_loop_triangles(); return len(ob.data.loop_triangles)


def check_body(ob,rig):
    assert list(ob.data.materials.keys())==list(SLOTS)
    assert list(ob.data.shape_keys.key_blocks.keys())==['Basis',*MORPHS]
    assert set(rig.data.bones.keys())==set(BONES)
    for name,(parent,h,t) in BONES.items():
        b=rig.data.bones[name]; assert (b.parent.name if b.parent else None)==parent
        assert (b.head_local-h).length<1e-5
    for v in ob.data.vertices:
        assert 1<=len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-5
    check_uv(ob)
    assert set(p.material_index for p in ob.data.polygons)==set(range(len(SLOTS)))
    n=tri_count(ob)
    assert 3000<=n<=6000,n


def check_uv(ob):
    assert ob.data.uv_layers.active is not None
    for l in ob.data.uv_layers.active.data: assert all(-1e-6<=v<=1+1e-6 for v in l.uv)


def check_export(path,body=False):
    d=read_glb(path)
    assert len(d['meshes'])==1
    if body:
        assert len(d.get('skins',[]))==1
        assert len(d['skins'][0]['joints'])==len(BONES)
        mesh=d['meshes'][0]; assert mesh.get('extras',{}).get('targetNames')==list(MORPHS)
        assert set(m['name'] for m in d['materials'])==set(SLOTS)
        for p in mesh['primitives']:
            assert len(p['targets'])==len(MORPHS)
            assert {'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}<=set(p['attributes'])
        nodes=d['nodes']; by_name={n.get('name'):i for i,n in enumerate(nodes)}
        parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
        for name,(parent,h,_) in BONES.items():
            assert (node_world(d,name).translation-Vector(gltf(h))).length<1e-4,name
            if parent: assert parents[by_name[name]]==by_name[parent],name
    else: assert not d.get('skins')
    limit=400 if body else 60
    return d


def setup_preview(eevee=False):
    scene=bpy.context.scene
    # Workbench is the fast CPU-friendly default; EEVEE is opt-in.
    engines=('BLENDER_EEVEE_NEXT','BLENDER_EEVEE','BLENDER_WORKBENCH') if eevee else ('BLENDER_WORKBENCH',)
    for engine in engines:
        try:
            scene.render.engine=engine
            break
        except (TypeError, ValueError):
            continue
    else:
        raise RuntimeError('No supported preview engine')
    scene.render.resolution_x=512; scene.render.resolution_y=512; scene.render.resolution_percentage=100
    scene.display.shading.color_type='MATERIAL'
    scene.display.shading.light='STUDIO'
    scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
    scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value=(.17,.19,.23,1); bg.inputs['Strength'].default_value=.4
    for name,pos,power,size in [('Key',(-3,-4,5),450,3),('Fill',(3,-2,2),180,3),('Rim',(1,3,4),400,2)]:
        ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.shape='DISK'; ld.size=size
        light=bpy.data.objects.new(name,ld); scene.collection.objects.link(light); light.location=pos
        light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
    camdata=bpy.data.cameras.new('PreviewCamera'); cam=bpy.data.objects.new('PreviewCamera',camdata); scene.collection.objects.link(cam)
    camdata.type='ORTHO'; camdata.ortho_scale=2.16; scene.camera=cam
    return cam


def render(cam,out,angle=0,pose=False):
    target=Vector((0,0,1.12 if pose else .93)); cam.data.ortho_scale=2.65 if pose else 2.16; cam.location=target+Vector((math.sin(angle)*4,-math.cos(angle)*4,.15 if not pose else .65))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene=bpy.context.scene; scene.render.filepath=str(out)
    try:
        bpy.ops.render.render(write_still=True)
    except RuntimeError:
        if scene.render.engine=='BLENDER_WORKBENCH': raise
        scene.render.engine='BLENDER_WORKBENCH'
        bpy.ops.render.render(write_still=True)


def pose_world_axis(rig,name,axis,degrees):
    pb=rig.pose.bones[name]; pb.rotation_mode='QUATERNION'
    local=pb.bone.matrix_local.to_3x3().inverted()@Vector(axis)
    pb.rotation_quaternion=Quaternion(local.normalized(),math.radians(degrees))


def preview_all(ob,rig,out,eevee=False,shoulder_previews=False):
    cam=setup_preview(eevee); keys=ob.data.shape_keys.key_blocks
    for name in ('base',*MORPHS):
        for k in MORPHS: keys[k].value=float(name==k)
        for view,angle in [('front',0),('side',math.pi/2),('threequarter',math.pi/4)]:
            render(cam,out/f'preview_{name}_{view}.png',angle)
    for k in MORPHS: keys[k].value=0
    # Positive X rotates downward arm toward +Y (back); negative X toward -Y (front).
    # Use opposite limbs to make all three test angles visible in one image.
    pose_world_axis(rig,'elbow_L',(1,0,0),-120)
    pose_world_axis(rig,'knee_L',(1,0,0),100)
    pose_world_axis(rig,'shoulder_R',(1,0,0),-160)
    bpy.context.view_layer.update()
    render(cam,out/'preview_pose.png',math.radians(35),True)
    for p in rig.pose.bones: p.rotation_quaternion=Quaternion((1,0,0,0))
    if shoulder_previews:
        # Isolate abduction from elbow/knee flexion for the shoulder QA pass.
        for degrees in (55,90):
            # L arm extends toward +X: rotation about -Y moves -Z toward +X.
            pose_world_axis(rig,'shoulder_L',(0,-1,0),degrees)
            bpy.context.view_layer.update()
            render(cam,out/f'preview_abduction_{degrees}.png',0,True)
        for p in rig.pose.bones: p.rotation_quaternion=Quaternion((1,0,0,0))


def main():
    args=argparse.ArgumentParser(); args.add_argument('--out',default='./out'); args.add_argument('--skip-previews',action='store_true'); args.add_argument('--eevee',action='store_true',help='Use EEVEE previews instead of fast Workbench'); args.add_argument('--shoulder-previews',action='store_true',help='Also render isolated 55 and 90 degree shoulder abduction tests')
    opt=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    out=Path(opt.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if bpy.context.scene.world is None: bpy.context.scene.world=bpy.data.worlds.new('World')
    mats=[material(n,c) for n,c in zip(SLOTS,COLORS)]
    checks={}; counts={}; produced=[]
    def verify(name, fn):
        try:
            result=fn(); checks[name]='PASS'; return result
        except Exception as exc:
            checks[name]=f'FAIL: {type(exc).__name__}: {exc}'
            return None
    b=make_geometry(); ob=b.object('FRESHMAN_Body',mats); apply_uv(ob)
    rig=make_rig(); skin(ob,b,rig); add_morphs(ob,b)
    counts[ob.name]=tri_count(ob)
    verify('Body source hierarchy, pivots, weights, UVs, slots, morphs and triangle budget',lambda:check_body(ob,rig))
    path=out/'base_body.glb'; export(path,[ob,rig]); produced.append(path)
    verify('Body exported structure and morphs',lambda:check_export(path,True))
    checks['Body GLB size < 400 KiB']='PASS' if path.stat().st_size<400*1024 else 'FAIL'
    doc=read_glb(path)
    head_world=node_world(doc,'head')
    metadata={'units':'meters','coordinate_system':'glTF Y-up, +Z forward','base_height_m':HEIGHT,
        'bones':[{'name':n,'parent':p,'head':list(gltf(h))} for n,(p,h,t) in BONES.items()],
        'morph_targets':list(MORPHS),'material_slots':list(SLOTS),
        'morph_normals_exported':False,
        'bone_rest_world_matrices':{n:[float(node_world(doc,n)[r][c]) for c in range(4) for r in range(4)] for n in BONES},
        'hair_attachment':{'bone':'head','space':'bone-local','translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}}
    (out/'rig.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    produced.append(out/'rig.json')
    hm=material('Hair',(.065,.045,.032))
    for style in HAIRS:
        hair=make_hair(style,rig,hm); hair_to_bone_local(hair,head_world); verify('Hair '+style+' UVs',lambda:check_uv(hair))
        n=tri_count(hair); counts[hair.name]=n
        checks['Hair '+style+' triangles < 800']='PASS' if n<800 else 'FAIL'
        hp=out/f'hair_{style}.glb'; export(hp,[hair]); produced.append(hp)
        verify('Hair '+style+' exported structure',lambda:check_export(hp))
        checks['Hair '+style+' size < 60 KiB']='PASS' if hp.stat().st_size<60*1024 else 'FAIL'
        bpy.data.objects.remove(hair,do_unlink=True)
    if not opt.skip_previews:
        verify('Preview rendering',lambda:preview_all(ob,rig,out,opt.eevee,opt.shoulder_previews))
        expected=[out/f'preview_{name}_{view}.png' for name in ('base',*MORPHS) for view in ('front','side','threequarter')]+[out/'preview_pose.png']
        if opt.shoulder_previews:
            extra=[out/f'preview_abduction_{degrees}.png' for degrees in (55,90)]
            produced.extend(p for p in extra if p.is_file())
            checks['Both shoulder abduction previews']='PASS' if all(p.is_file() for p in extra) else 'FAIL'
        produced.extend(p for p in expected if p.is_file())
        checks['All 19 preview files']='PASS' if all(p.is_file() for p in expected) else 'FAIL'
    else:
        checks['Preview rendering']='SKIP (requested)'
    print('\n========== FRESHMAN VALIDATION SUMMARY ==========')
    print('Blender:',bpy.app.version_string)
    for name,n in counts.items(): print(f'TRIS {name}: {n}')
    for path in sorted(produced): print(f'FILE {path.name}: {path.stat().st_size/1024:.2f} KiB')
    for bone in rig.data.bones: print(f'BONE {bone.name}: {bone.parent.name if bone.parent else None}')
    print('MORPHS:', ', '.join(k.name for k in ob.data.shape_keys.key_blocks if k.name!='Basis'))
    print('SLOTS:', ', '.join(ob.data.materials.keys()))
    uv=ob.data.uv_layers.active.data
    for i,slot in enumerate(SLOTS):
        pairs=[tuple(uv[j].uv) for poly in ob.data.polygons if poly.material_index==i for j in poly.loop_indices]
        if pairs:
            u,v=zip(*pairs)
            print(f'UV {slot}: u=[{min(u):.8f},{max(u):.8f}] v=[{min(v):.8f},{max(v):.8f}] loops={len(pairs)}')
            checks['UV '+slot]='PASS' if min(u)>=0 and max(u)<=1 and min(v)>=0 and max(v)<=1 else 'FAIL'
        else:
            checks['UV '+slot]='FAIL (no loops)'
    for name,status in checks.items(): print(f'{status} | {name}')
    failed=any(status.startswith('FAIL') for status in checks.values())
    print('OVERALL:', 'FAIL' if failed else 'PASS (automated checks only; inspect pose and morph previews visually)')
    print('========== END FRESHMAN VALIDATION SUMMARY ==========')
    if failed: sys.exit(1)

if __name__=='__main__': main()
