"""FreeCAD 1.1: parametric, single-body webbed spur gear.
Run with FreeCAD's Python interpreter. All lengths are millimetres.
"""
import math
import os
import sys
import FreeCAD as App
import Part
import Sketcher

# Make the sketch's Python proxy importable when the document is reopened.
sys.modules.setdefault('answer', sys.modules[__name__])
V = App.Vector

class InvoluteProfile:
    """Regenerates editable sketch geometry from the gear's design properties.

    OCC represents the transcendental involute with a smooth B-spline,
    interpolating analytic involute coordinates (not straight flank segments).
    Explicit roll-angle parametrization also resolves the base-circle cusp.
    """
    def __init__(self, obj):
        self.signature = None
        obj.Proxy = self

    def execute(self, obj):
        signature = (obj.NumberOfTeeth, obj.Module.Value,
                     obj.PressureAngle.Value, obj.TipDiameter.Value,
                     obj.RootDiameter.Value)
        if signature == self.signature and obj.GeometryCount:
            return False
        n, m, pressure, tip, root = signature
        rb = n*m/2 * math.cos(math.radians(pressure))
        rr, ra = root/2, tip/2
        pitch_roll = math.tan(math.radians(pressure))
        base_half_angle = math.pi/(2*n) + pitch_roll-math.atan(pitch_roll)
        tmax = math.sqrt((ra/rb)**2-1)
        def polar(r, a):
            return V(r*math.cos(a), r*math.sin(a), 0)
        def point(t, center, side):
            return polar(rb*math.sqrt(1+t*t),
                         center+side*(base_half_angle-(t-math.atan(t))))
        # Include the exact pitch-circle parameter among the interpolation nodes.
        ts = sorted(set([tmax*i/100 for i in range(101)] + [pitch_roll]))
        geometry = []
        for k in range(n):
            a = 2*math.pi*k/n
            lower_root = polar(rr, a-base_half_angle)
            upper_root = polar(rr, a+base_half_angle)
            geometry.append(Part.LineSegment(lower_root, point(0,a,-1)))
            lower = Part.BSplineCurve()
            lower.interpolate(Points=[point(t,a,-1) for t in ts], Parameters=ts,
                              Tolerance=1e-10)
            geometry.append(lower)
            tip_angle = base_half_angle-(tmax-math.atan(tmax))
            geometry.append(Part.ArcOfCircle(Part.Circle(V(),V(0,0,1),ra),
                                             a-tip_angle,a+tip_angle))
            upper = Part.BSplineCurve()
            upper.interpolate(Points=[point(t,a,1) for t in ts], Parameters=ts,
                              Tolerance=1e-10)
            upper.reverse()
            geometry.append(upper)
            geometry.append(Part.LineSegment(point(0,a,1), upper_root))
            geometry.append(Part.ArcOfCircle(Part.Circle(V(),V(0,0,1),rr),
                                             a+base_half_angle,
                                             a+2*math.pi/n-base_half_angle))
        if obj.GeometryCount:
            obj.delGeometries(list(range(obj.GeometryCount)))
        obj.addGeometry(geometry, False)
        self.signature = signature
        return False

    def dumps(self):
        return self.signature

    def loads(self, state):
        self.signature = state

InvoluteProfile.__module__ = 'answer'


def build():
    doc = App.newDocument('WebbedSpurGear')
    body = doc.addObject('PartDesign::Body', 'GearBody')
    body.Label = 'Webbed spur gear (36 teeth, module 2)'
    # A non-geometric parameter table avoids feature-dependency cycles.
    params = doc.addObject('Spreadsheet::Sheet', 'Parameters')
    values = [('FaceWidth',20), ('WebThickness',8), ('RimInnerDiameter',56),
              ('HubDiameter',30), ('BoreDiameter',16), ('HoleDiameter',10),
              ('HolePCD',43), ('HoleCount',6), ('KeyWidth',5), ('KeyFloor',10.3)]
    for row,(name,value) in enumerate(values,1):
        params.set('A%d'%row,name)
        params.set('B%d'%row,str(value))
        params.setAlias('B%d'%row,name)
    params.setColumnWidth('A',190)
    profile = body.newObject('Sketcher::SketchObjectPython','InvoluteToothProfile')
    for typ,name,value in [('App::PropertyInteger','NumberOfTeeth',36),
                           ('App::PropertyLength','Module',2),
                           ('App::PropertyAngle','PressureAngle',20),
                           ('App::PropertyLength','TipDiameter',76),
                           ('App::PropertyLength','RootDiameter',67)]:
        profile.addProperty(typ,name,'Gear dimensions')
        setattr(profile,name,value)
    InvoluteProfile(profile)
    doc.recompute()
    pad = body.newObject('PartDesign::Pad','ToothedBlank')
    pad.Profile = profile
    pad.setExpression('Length','Parameters.FaceWidth')
    doc.recompute()
    profile.Visibility = False

    def sketch(name, top=False):
        s = body.newObject('Sketcher::SketchObject',name)
        if top:
            s.setExpression('Placement.Base.z','Parameters.FaceWidth')
        return s

    def circle(s, x, y, radius, radius_expression):
        i = s.addGeometry(Part.Circle(V(x,y,0),V(0,0,1),radius),False)
        ci = s.addConstraint(Sketcher.Constraint('Radius',i,radius))
        s.setExpression('Constraints[%d]'%ci,radius_expression)
        if x == 0 and y == 0:
            s.addConstraint(Sketcher.Constraint('Coincident',i,3,-1,1))
        else:
            for kind,val in [('DistanceX',x),('DistanceY',y)]:
                if abs(val)<1e-8:
                    s.addConstraint(Sketcher.Constraint(kind,i,3,0.0))
                else:
                    ci=s.addConstraint(Sketcher.Constraint(kind,i,3,val))
                    s.setExpression('Constraints[%d]'%ci,
                                    'Parameters.HolePCD * %.16g'% (val/43))
        return i

    def pocket(s,name,length,reverse=False):
        doc.recompute()
        previous=body.Tip
        p=body.newObject('PartDesign::Pocket',name)
        p.Profile=s
        p.setExpression('Length',length)
        p.Reversed=reverse
        doc.recompute()
        s.Visibility=False
        if previous and previous != s:
            previous.Visibility=False
        if p.Shape.isNull():
            raise RuntimeError(name+' did not create a solid: '+str(p.State))
        return p

    for name,top,reverse in [('FrontRecess',False,True),('BackRecess',True,False)]:
        s=sketch(name+'Sketch',top)
        circle(s,0,0,28,'Parameters.RimInnerDiameter / 2')
        circle(s,0,0,15,'Parameters.HubDiameter / 2')
        pocket(s,name,'(Parameters.FaceWidth - Parameters.WebThickness) / 2',reverse)

    s=sketch('LighteningHoleSketch',True)
    circle(s,21.5,0,5,'Parameters.HoleDiameter / 2')
    hole=pocket(s,'FirstLighteningHole','Parameters.FaceWidth')
    pattern=body.newObject('PartDesign::PolarPattern','SixLighteningHoles')
    pattern.Originals=[hole]
    pattern.Axis=(doc.getObject('Z_Axis'),[''])
    pattern.Angle=360
    pattern.Offset=0
    pattern.setExpression('Occurrences','Parameters.HoleCount')
    doc.recompute()
    hole.Visibility=False
    body.Tip=pattern

    s=sketch('BoreSketch',True)
    circle(s,0,0,8,'Parameters.BoreDiameter / 2')
    pocket(s,'ThroughBore','Parameters.FaceWidth')

    s=sketch('KeywaySketch',True)
    # The lower edge is inside the bore, so the pocket opens into the bore.
    pts=[(-2.5,0),(2.5,0),(2.5,10.3),(-2.5,10.3)]
    for i in range(4):
        a,b=pts[i],pts[(i+1)%4]
        s.addGeometry(Part.LineSegment(V(*a,0),V(*b,0)),False)
    for i in range(4):
        s.addConstraint(Sketcher.Constraint('Coincident',i,2,(i+1)%4,1))
        s.addConstraint(Sketcher.Constraint('Horizontal' if i%2==0 else 'Vertical',i))
    c=s.addConstraint(Sketcher.Constraint('DistanceX',0,1,-2.5))
    s.setExpression('Constraints[%d]'%c,'-Parameters.KeyWidth / 2')
    s.addConstraint(Sketcher.Constraint('DistanceY',0,1,0.0))
    c=s.addConstraint(Sketcher.Constraint('Distance',0,5.0))
    s.setExpression('Constraints[%d]'%c,'Parameters.KeyWidth')
    c=s.addConstraint(Sketcher.Constraint('Distance',1,10.3))
    s.setExpression('Constraints[%d]'%c,'Parameters.KeyFloor')
    final=pocket(s,'Keyway','Parameters.FaceWidth')
    for obj in body.Group:
        if hasattr(obj,'Visibility'):
            obj.Visibility=False
    final.Visibility=True
    body.Tip=final
    doc.recompute()
    assert final.Shape.isValid(), 'Invalid final shape'
    assert len(final.Shape.Solids)==1, 'Expected exactly one solid'
    assert abs(final.Shape.BoundBox.ZMin)<1e-6
    assert abs(final.Shape.BoundBox.ZMax-20)<1e-6
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    output=os.path.splitext(os.path.abspath(__file__))[0]+'.FCStd'
    doc.recompute()
    doc.saveAs(output)
    print('Saved',output,'volume',final.Shape.Volume,'solids',len(final.Shape.Solids))
    return doc

if __name__ == '__main__':
    build()
