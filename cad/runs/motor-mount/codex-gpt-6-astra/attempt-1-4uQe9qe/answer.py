"""Parametric gantry motor mount. Run with FreeCAD's Python interpreter."""
import math
from pathlib import Path
import FreeCAD as App
import Part
import Sketcher


def build():
    doc = App.newDocument('MotorMount')
    body = doc.addObject('PartDesign::Body', 'MotorMountBody')
    params = doc.addObject('App::FeaturePython', 'Dimensions')
    parameters = {
        'overall_length':110.0, 'overall_width':62.0, 'plate_thickness':25.0,
        'bore_diameter':50.25, 'corner_radius':3.5, 'mounting_hole_pcd':70.0,
        'front_hole_diameter':4.2, 'front_hole_depth':11.138,
        'back_hole_diameter':3.3, 'back_hole_depth':9.109,
        'ear_hole_diameter':5.5, 'ear_end_radius':0.5,
        'plate_half_height':30.0, 'jaw_half_opening':20.0,
        'ear_width':10.0, 'jaw_diagonal':5.0, 'ear_hole_end_offset':4.0,
        'ear_hole_face_offset':6.5,
    }
    for name, value in parameters.items():
        params.addProperty('App::PropertyLength', name, 'Dimensions')
        setattr(params, name, value)
    params.addProperty('App::PropertyInteger', 'number_mounting_holes', 'Dimensions')
    params.number_mounting_holes = 4
    params.addProperty('App::PropertyAngle', 'drill_point_angle', 'Dimensions')
    params.drill_point_angle = 118
    prefix = 'Dimensions.'
    def expr(s):
        import re
        return re.sub(r'\b('+'|'.join(parameters.keys())+r'|number_mounting_holes|drill_point_angle)\b', lambda m: prefix+m[0], s)
    def dim(sk, kind, geo, point, value, formula):
        c = sk.addConstraint(Sketcher.Constraint(kind, geo, point, value))
        sk.setExpression('Constraints[%d]' % c, expr(formula))
    def xy(sk, geo, point, x, y, ex, ey):
        dim(sk, 'DistanceX',geo,point,x,ex)
        dim(sk, 'DistanceY',geo,point,y,ey)
    left = '-(overall_width - 32 mm)'
    right = '32 mm'
    inner = '32 mm - ear_width'
    jx = math.sqrt((25.125)**2 - 20**2)
    jexpr = 'sqrt((bore_diameter / 2)^2 - jaw_half_opening^2)'
    # Each endpoint is dimensioned from the origin; shared expressions keep the wire closed.
    pts = [(-30,-30,left,'-plate_half_height'),(-30,30,left,'plate_half_height'),
           (22,30,inner,'plate_half_height'),(22,55,inner,'overall_length / 2'),
           (32,55,right,'overall_length / 2'),(32,25,right,'jaw_half_opening + jaw_diagonal'),
           (27,20,'32 mm - jaw_diagonal','jaw_half_opening'),(jx,20,jexpr,'jaw_half_opening'),
           (jx,-20,jexpr,'-jaw_half_opening'),(27,-20,'32 mm - jaw_diagonal','-jaw_half_opening'),
           (32,-25,right,'-jaw_half_opening - jaw_diagonal'),(32,-55,right,'-overall_length / 2'),
           (22,-55,inner,'-overall_length / 2'),(22,-30,inner,'-plate_half_height')]
    sk = body.newObject('Sketcher::SketchObject','PlateOutline')
    for k,p in enumerate(pts):
        q = pts[(k+1)%len(pts)]
        if k == 7:
            a = math.asin(20/25.125)
            i = sk.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(0,0,0),App.Vector(0,0,1),25.125),a,2*math.pi-a),False)
            sk.addConstraint(Sketcher.Constraint('Coincident',i,3,-1,1))
            c=sk.addConstraint(Sketcher.Constraint('Radius',i,25.125))
            sk.setExpression('Constraints[%d]'%c,expr('bore_diameter / 2'))
            dim(sk,'DistanceY',i,1,20,'jaw_half_opening')
            dim(sk,'DistanceY',i,2,-20,'-jaw_half_opening')
        else:
            i=sk.addGeometry(Part.LineSegment(App.Vector(p[0],p[1],0),App.Vector(q[0],q[1],0)),False)
            xy(sk,i,1,*p)
            xy(sk,i,2,*q)
    doc.recompute()
    pad=body.newObject('PartDesign::Pad','PlatePad')
    pad.Profile=sk
    pad.setExpression('Length',expr('plate_thickness'))
    doc.recompute()
    sk.Visibility=False
    def vertical_edges(shape, locations):
        result=[]
        for n,e in enumerate(shape.Edges,1):
            vs=e.Vertexes
            if len(vs)==2:
                a,b=[v.Point for v in vs]
                if abs(a.x-b.x)<1e-6 and abs(a.y-b.y)<1e-6 and abs(a.z-b.z)>24.9:
                    if any(abs(a.x-x)<1e-5 and abs(a.y-y)<1e-5 for x,y in locations):
                        result.append('Edge%d'%n)
        return result
    rounded=body.newObject('PartDesign::Fillet','ProfileCornerFillets')
    targets=[(p[0],p[1]) for p in pts if abs(p[1])!=55]
    rounded.Base=(pad,vertical_edges(pad.Shape,targets))
    rounded.setExpression('Radius',expr('corner_radius'))
    doc.recompute()
    pad.Visibility=False
    tips=body.newObject('PartDesign::Fillet','EarEndFillets')
    tips.Base=(rounded,vertical_edges(rounded.Shape,[(22,55),(32,55),(22,-55),(32,-55)]))
    tips.setExpression('Radius',expr('ear_end_radius'))
    doc.recompute()
    rounded.Visibility=False
    last=tips
    for side in ['Front','Back']:
        sketch=body.newObject('Sketcher::SketchObject',side+'DrillingCenters')
        if side=='Back':
            sketch.setExpression('Placement.Base.z',expr('plate_thickness'))
        for k in range(params.number_mounting_holes):
            theta=math.radians(45+360*k/params.number_mounting_holes)
            x,y=35*math.cos(theta),35*math.sin(theta)
            i=sketch.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),2),False)
            angle='(45 deg + %d * 360 deg / number_mounting_holes)'%k
            xy(sketch,i,3,x,y,'mounting_hole_pcd / 2 * cos'+angle,'mounting_hole_pcd / 2 * sin'+angle)
            c=sketch.addConstraint(Sketcher.Constraint('Radius',i,2))
            sketch.setExpression('Constraints[%d]'%c,expr(side.lower()+'_hole_diameter / 2'))
        doc.recompute()
        h=body.newObject('PartDesign::Hole',side+'BlindDrillings')
        h.Profile=sketch
        h.Reversed=(side=='Front')
        h.DepthType='Dimension'
        h.setExpression('Diameter',expr(side.lower()+'_hole_diameter'))
        h.setExpression('Depth',expr(side.lower()+'_hole_depth'))
        h.DrillPoint='Angled'
        h.setExpression('DrillPointAngle',expr('drill_point_angle'))
        h.DrillForDepth=False  # Depth measures the full-diameter cylinder, excluding the point.
        doc.recompute()
        sketch.Visibility=False
        last.Visibility=False
        last=h
    ears=body.newObject('Sketcher::SketchObject','EarCrossHoleLayout')
    ears.Placement=App.Placement(App.Vector(32,0,0),App.Rotation(App.Vector(1,1,1),120))
    for sign in [-1,1]:
        for z in [6.5,18.5]:
            y=sign*51
            i=ears.addGeometry(Part.Circle(App.Vector(y,z,0),App.Vector(0,0,1),2.75),False)
            xy(ears,i,3,y,z,('%d * (overall_length / 2 - ear_hole_end_offset)'%sign), 'ear_hole_face_offset' if z==6.5 else 'plate_thickness - ear_hole_face_offset')
            c=ears.addConstraint(Sketcher.Constraint('Radius',i,2.75))
            ears.setExpression('Constraints[%d]'%c,expr('ear_hole_diameter / 2'))
    doc.recompute()
    cross=body.newObject('PartDesign::Pocket','EarCrossDrillings')
    cross.Profile=ears
    cross.setExpression('Length',expr('ear_width'))
    doc.recompute()
    ears.Visibility=False
    last.Visibility=False
    body.Tip=cross
    cross.Visibility=True
    for feature in [pad,rounded,tips,doc.FrontBlindDrillings,doc.BackBlindDrillings,cross]:
        if feature.Shape.isNull() or not feature.Shape.isValid() or len(feature.Shape.Solids)!=1:
            raise RuntimeError('Invalid solid at '+feature.Name+': '+str(feature.State))
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    doc.recompute()
    doc.saveAs(str(Path(__file__).resolve().with_suffix('.FCStd')))
    print('Saved',doc.FileName,'volume',cross.Shape.Volume)
    return doc

if __name__=='__main__':
    build()
