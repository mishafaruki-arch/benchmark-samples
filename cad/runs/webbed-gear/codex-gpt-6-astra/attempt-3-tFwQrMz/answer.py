"""Parametric webbed involute spur gear for FreeCAD 1.1.
Run with FreeCAD's Python interpreter. The neighboring FCStd is the output.
"""
import os
import sys
import math
import FreeCAD as App
import Part
import Sketcher

# Keep Python feature classes importable when the document is reopened.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if __name__ == '__main__':
    sys.modules['answer'] = sys.modules[__name__]


def polar(r, a):
    return App.Vector(r * math.cos(a), r * math.sin(a), 0)


class InvoluteProfile:
    """Regenerates editable sketch geometry from gear dimensions.

    OCC has no analytic involute primitive. Degree-15 Bezier representations
    of its exact analytic equations have sub-nanometer error here; these are
    smooth flanks, with exact base/tip endpoints, not faceted polylines.
    """
    def __init__(self, obj):
        obj.Proxy = self
        self.signature = None

    def execute(self, obj):
        n = obj.NumberOfTeeth
        m, pa = obj.Module.Value, math.radians(obj.PressureAngle.Value)
        rt, rr = obj.TipDiameter.Value / 2, obj.RootDiameter.Value / 2
        signature = (n, m, pa, rt, rr)
        if getattr(self, 'signature', None) == signature and obj.GeometryCount:
            return False
        rb = n * m / 2 * math.cos(pa)
        assert rr < rb < rt
        halfbase = math.pi / (2*n) + math.tan(pa) - pa
        tmax = math.sqrt((rt/rb)**2 - 1)
        tiphalf = halfbase - (tmax - math.atan(tmax))
        degree = 15
        # Power coefficients of x=rb(cos(t)+t sin(t)),
        # y=rb(sin(t)-t cos(t)), t=tmax*u.
        cx, cy = [0.0]*16, [0.0]*16
        cx[0] = rb
        for k in range(1, 8):
            cx[2*k] = rb * (-1)**(k-1) * (2*k-1) * tmax**(2*k) / math.factorial(2*k)
            cy[2*k+1] = rb * (-1)**(k+1) * (2*k) * tmax**(2*k+1) / math.factorial(2*k+1)
        poles = []
        for i in range(16):
            poles.append((sum(cx[j]*math.comb(i,j)/math.comb(degree,j) for j in range(i+1)),
                          sum(cy[j]*math.comb(i,j)/math.comb(degree,j) for j in range(i+1))))
        geometry = []
        for i in range(n):
            a = i * 2*math.pi/n
            lowerbase, upperbase = polar(rb,a-halfbase), polar(rb,a+halfbase)
            lowertip, uppertip = polar(rt,a-tiphalf), polar(rt,a+tiphalf)
            geometry.append(Part.LineSegment(polar(rr,a-halfbase),lowerbase))
            for side in (-1, 1):
                if side == 1:
                    geometry.append(Part.Arc(lowertip,polar(rt,a),uppertip))
                rot = a + side*halfbase
                pp = [App.Vector(x*math.cos(rot)+side*y*math.sin(rot),
                                 x*math.sin(rot)-side*y*math.cos(rot),0) for x,y in poles]
                pp[0] = lowerbase if side == -1 else upperbase
                pp[-1] = lowertip if side == -1 else uppertip
                if side == 1:
                    pp.reverse()
                bez = Part.BezierCurve()
                bez.setPoles(pp)
                geometry.append(bez.toBSpline())
            geometry.append(Part.LineSegment(upperbase,polar(rr,a+halfbase)))
            end = a+2*math.pi/n-halfbase
            geometry.append(Part.Arc(polar(rr,a+halfbase),polar(rr,(a+halfbase+end)/2),polar(rr,end)))
        if obj.GeometryCount:
            obj.delGeometries(list(range(obj.GeometryCount)))
        obj.addGeometry(geometry, False)
        self.signature = signature
        return False

    def dumps(self):
        return None

    def loads(self, state):
        self.signature = None

InvoluteProfile.__module__ = 'answer'


def build():
    doc = App.newDocument('WebbedSpurGear')
    params = doc.addObject('App::FeaturePython','Dimensions')
    body = doc.addObject('PartDesign::Body','GearBody')
    for name,value in [('FaceWidth',20),('WebThickness',8),('RimInnerDiameter',56),
                       ('HubDiameter',30),('BoreDiameter',16),('LighteningHoleDiameter',10),
                       ('LighteningHolePCD',43),('KeyWidth',5),('KeyFloorRadius',10.3)]:
        params.addProperty('App::PropertyLength',name,'Dimensions')
        setattr(params,name,value)
    profile = body.newObject('Sketcher::SketchObjectPython','InvoluteToothProfile')
    profile.Label = '36 teeth • full-depth involute profile'
    for typ,name,value in [('App::PropertyInteger','NumberOfTeeth',36),
                           ('App::PropertyLength','Module',2),
                           ('App::PropertyAngle','PressureAngle',20),
                           ('App::PropertyLength','TipDiameter',76),
                           ('App::PropertyLength','RootDiameter',67)]:
        profile.addProperty(typ,name,'Gear parameters')
        setattr(profile,name,value)
    InvoluteProfile(profile)
    doc.recompute()
    pad = body.newObject('PartDesign::Pad','ToothedBlank')
    pad.Profile = profile
    pad.setExpression('Length','Dimensions.FaceWidth')
    doc.recompute()
    profile.Visibility = False

    def sketch(name, top=False):
        s = body.newObject('Sketcher::SketchObject',name)
        if top:
            s.setExpression('Placement.Base.z','Dimensions.FaceWidth')
        return s

    def circle(s, radius, expression, x=0, y=0):
        g = s.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),radius),False)
        c = s.addConstraint(Sketcher.Constraint('Radius',g,radius))
        s.setExpression('Constraints[%d]'%c,expression)
        if x == 0 and y == 0:
            s.addConstraint(Sketcher.Constraint('Coincident',g,3,-1,1))
        return g

    def pocket(name, s, length, reversed=False):
        doc.recompute()
        previous = body.Tip
        p = body.newObject('PartDesign::Pocket',name)
        p.Profile = s
        p.setExpression('Length',length)
        p.Reversed = reversed
        doc.recompute()
        s.Visibility = False
        if previous:
            previous.Visibility = False
        pad.Visibility = False
        return p

    for name,top in [('LowerRecess',False),('UpperRecess',True)]:
        s = sketch(name+'Sketch',top)
        circle(s,28,'Dimensions.RimInnerDiameter / 2')
        circle(s,15,'Dimensions.HubDiameter / 2')
        pocket(name,s,'(Dimensions.FaceWidth - Dimensions.WebThickness) / 2',not top)

    s = sketch('LighteningHoleSketch',True)
    g = circle(s,5,'Dimensions.LighteningHoleDiameter / 2',21.5,0)
    c = s.addConstraint(Sketcher.Constraint('DistanceX',g,3,21.5))
    s.setExpression('Constraints[%d]'%c,'Dimensions.LighteningHolePCD / 2')
    s.addConstraint(Sketcher.Constraint('DistanceY',g,3,0.0))
    hole = pocket('FirstLighteningHole',s,'Dimensions.FaceWidth')
    pattern = body.newObject('PartDesign::PolarPattern','SixLighteningHoles')
    pattern.Originals = [hole]
    pattern.Axis = (s,['N_Axis'])
    pattern.Angle = 360
    pattern.Occurrences = 6
    body.Tip = pattern
    doc.recompute()
    hole.Visibility = False

    s = sketch('BoreSketch',True)
    circle(s,8,'Dimensions.BoreDiameter / 2')
    pocket('ThroughBore',s,'Dimensions.FaceWidth')
    pattern.Visibility = False

    s = sketch('KeywaySketch',True)
    # Bottom edge lies inside the bore, leaving a single open keyed bore.
    pts = [(-2.5,0),(2.5,0),(2.5,10.3),(-2.5,10.3)]
    for i in range(4):
        p,q = pts[i],pts[(i+1)%4]
        s.addGeometry(Part.LineSegment(App.Vector(*p,0),App.Vector(*q,0)),False)
    for i in range(4):
        s.addConstraint(Sketcher.Constraint('Coincident',i,2,(i+1)%4,1))
        s.addConstraint(Sketcher.Constraint('Horizontal' if i%2==0 else 'Vertical',i))
    for constraint,expression in [
        (Sketcher.Constraint('DistanceX',0,1,-2.5),'-Dimensions.KeyWidth / 2'),
        (Sketcher.Constraint('Distance',0,5.0),'Dimensions.KeyWidth'),
        (Sketcher.Constraint('Distance',1,10.3),'Dimensions.KeyFloorRadius')]:
        idx = s.addConstraint(constraint)
        s.setExpression('Constraints[%d]'%idx,expression)
    s.addConstraint(Sketcher.Constraint('DistanceY',0,1,0.0))
    final = pocket('Keyway',s,'Dimensions.FaceWidth')
    body.Tip = final
    for obj in body.Group:
        if hasattr(obj,'Visibility'):
            obj.Visibility = False
    final.Visibility = True
    doc.recompute()
    assert not final.Shape.isNull(), 'Empty final feature'
    assert final.Shape.isValid(), 'Invalid final solid'
    assert len(final.Shape.Solids) == 1, 'Expected exactly one solid'
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    output = os.path.splitext(os.path.abspath(__file__))[0] + '.FCStd'
    doc.recompute()
    doc.saveAs(output)
    print('Saved',output,'volume',final.Shape.Volume,'solids',len(final.Shape.Solids))
    return doc


if __name__ == '__main__':
    build()
