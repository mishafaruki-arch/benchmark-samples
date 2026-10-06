"""Parametric webbed involute spur gear; run with FreeCAD's Python interpreter."""
import math
import os
import sys
import FreeCAD as App
import Part
import Sketcher

# Makes the saved sketch's Python proxy importable when this file is run as a macro.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


class InvoluteProfile:
    """Regenerates the editable sketch from the gear's dimensional properties.

    OCC represents non-algebraic involutes by B-splines. These interpolate the
    analytical involute in its roll parameter (96 intervals per flank), including
    the exact base and tip endpoints. Root extensions are lines, not splines.
    """
    def __init__(self, obj):
        obj.addProperty('App::PropertyInteger', 'NumberOfTeeth', 'Gear').NumberOfTeeth = 36
        for name, value in [('Module', 2), ('TipDiameter', 76), ('RootDiameter', 67)]:
            obj.addProperty('App::PropertyLength', name, 'Gear')
            setattr(obj, name, value)
        obj.addProperty('App::PropertyAngle', 'PressureAngle', 'Gear').PressureAngle = 20
        obj.Proxy = self
        self.signature = None

    def execute(self, obj):
        sig = (obj.NumberOfTeeth, obj.Module.Value, obj.TipDiameter.Value,
               obj.RootDiameter.Value, obj.PressureAngle.Value)
        if getattr(self, 'signature', None) == sig and obj.GeometryCount:
            return False
        n, module, tip, root, pressure = sig
        rp, rt, rr = n * module / 2, tip / 2, root / 2
        rb = rp * math.cos(math.radians(pressure))
        assert 0 < rr < rb < rt
        half_base_angle = math.pi / (2*n) + math.tan(math.radians(pressure)) - math.radians(pressure)
        tmax = math.sqrt((rt/rb)**2 - 1)
        pitch = 2*math.pi/n
        def polar(r, a):
            return App.Vector(r*math.cos(a), r*math.sin(a), 0)
        def inv(t, center, side):
            r = rb*math.sqrt(1+t*t)
            a = center + side*(half_base_angle - (t-math.atan(t)))
            return polar(r, a)
        geos = []
        tiphalf = half_base_angle - (tmax-math.atan(tmax))
        for k in range(n):
            a = k*pitch
            geos.append(Part.LineSegment(polar(rr,a-half_base_angle), polar(rb,a-half_base_angle)))
            # Explicit roll parameters prevent chord-length interpolation artifacts at t=0.
            ts = [tmax*j/96 for j in range(97)]
            low = Part.BSplineCurve()
            low.interpolate(Points=[inv(t,a,-1) for t in ts], Parameters=ts, Tolerance=1e-10)
            geos.append(low)
            geos.append(Part.Arc(polar(rt,a-tiphalf), polar(rt,a), polar(rt,a+tiphalf)))
            high = Part.BSplineCurve()
            high.interpolate(Points=[inv(tmax-t,a,1) for t in ts], Parameters=ts, Tolerance=1e-10)
            geos.append(high)
            geos.append(Part.LineSegment(polar(rb,a+half_base_angle), polar(rr,a+half_base_angle)))
            geos.append(Part.Arc(polar(rr,a+half_base_angle),
                                 polar(rr,a+pitch/2), polar(rr,a+pitch-half_base_angle)))
        if obj.GeometryCount:
            obj.delGeometries(list(range(obj.GeometryCount)))
        obj.addGeometry(geos, False)
        self.signature = sig
        return False

    def dumps(self):
        return {'signature': self.signature}

    def loads(self, state):
        self.signature = tuple(state['signature']) if state and state.get('signature') else None


def build():
    doc = App.newDocument('WebbedSpurGear')
    body = doc.addObject('PartDesign::Body', 'GearBody')
    body.Label = 'Webbed spur gear (36 teeth, module 2)'
    dims = doc.addObject('App::VarSet', 'Dimensions')
    for name, val in [('FaceWidth',20), ('WebThickness',8), ('RimInnerDiameter',56),
                      ('HubDiameter',30), ('BoreDiameter',16), ('LighteningHoleDiameter',10),
                      ('LighteningHolePCD',43), ('KeywayWidth',5), ('KeywayFloor',10.3)]:
        dims.addProperty('App::PropertyLength', name, 'Dimensions')
        setattr(dims, name, val)
    dims.addProperty('App::PropertyInteger','NumberLighteningHoles','Dimensions').NumberLighteningHoles=6
    profile = body.newObject('Sketcher::SketchObjectPython','InvoluteToothProfile')
    # Use the importable module name, so proxy persistence also works after reopening.
    import answer
    answer.InvoluteProfile(profile)
    profile.Label = '36 involute teeth — radial roots, circular tips'
    doc.recompute()
    pad = body.newObject('PartDesign::Pad','ToothedBlank')
    pad.Profile = profile
    pad.setExpression('Length','Dimensions.FaceWidth')
    doc.recompute()
    profile.Visibility=False

    def circle(sk, x, y, radius, expression):
        i=sk.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),radius),False)
        c=sk.addConstraint(Sketcher.Constraint('Diameter',i,2*radius))
        sk.setExpression('Constraints[%d]'%c,expression)
        if x==0 and y==0:
            sk.addConstraint(Sketcher.Constraint('Coincident',i,3,-1,1))
        else:
            c=sk.addConstraint(Sketcher.Constraint('DistanceX',i,3,x))
            sk.setExpression('Constraints[%d]'%c, 'Dimensions.LighteningHolePCD / 2 * cos(%g deg)'%math.degrees(math.atan2(y,x)))
            if abs(y)<1e-9:
                sk.addConstraint(Sketcher.Constraint('DistanceY',i,3,0.0))
            else:
                c=sk.addConstraint(Sketcher.Constraint('DistanceY',i,3,y))
                sk.setExpression('Constraints[%d]'%c,'Dimensions.LighteningHolePCD / 2 * sin(%g deg)'%math.degrees(math.atan2(y,x)))

    def pocket(name, sk, length, reverse=False):
        doc.recompute()
        p=body.newObject('PartDesign::Pocket',name)
        p.Profile=sk
        p.setExpression('Length',length)
        p.Reversed=reverse
        doc.recompute()
        sk.Visibility=False
        for ob in body.Group:
            if ob != p: ob.Visibility=False
        return p

    bottom=body.newObject('Sketcher::SketchObject','BottomRecessProfile')
    circle(bottom,0,0,28,'Dimensions.RimInnerDiameter')
    circle(bottom,0,0,15,'Dimensions.HubDiameter')
    pocket('BottomAnnularRecess',bottom,'(Dimensions.FaceWidth - Dimensions.WebThickness) / 2',True)
    top=body.newObject('Sketcher::SketchObject','TopRecessProfile')
    top.setExpression('Placement.Base.z','Dimensions.FaceWidth')
    circle(top,0,0,28,'Dimensions.RimInnerDiameter')
    circle(top,0,0,15,'Dimensions.HubDiameter')
    pocket('TopAnnularRecess',top,'(Dimensions.FaceWidth - Dimensions.WebThickness) / 2')

    # One fully dimensioned hole and a native PartDesign polar pattern.
    holes=body.newObject('Sketcher::SketchObject','LighteningHoleProfile')
    circle(holes,21.5,0,5,'Dimensions.LighteningHoleDiameter')
    cut=pocket('FirstLighteningHole',holes,'Dimensions.FaceWidth',True)
    pattern=body.newObject('PartDesign::PolarPattern','SixLighteningHoles')
    pattern.Originals=[cut]
    pattern.Axis=(doc.getObject('Z_Axis'),[''])
    pattern.Angle=360
    pattern.setExpression('Occurrences','Dimensions.NumberLighteningHoles')
    doc.recompute()
    cut.Visibility=False
    bore=body.newObject('Sketcher::SketchObject','BoreProfile')
    circle(bore,0,0,8,'Dimensions.BoreDiameter')
    pocket('ThroughBore',bore,'Dimensions.FaceWidth',True)

    key=body.newObject('Sketcher::SketchObject','KeywayProfile')
    pts=[(-2.5,0),(2.5,0),(2.5,10.3),(-2.5,10.3)]
    for i in range(4):
        p,q=pts[i],pts[(i+1)%4]
        idx=key.addGeometry(Part.LineSegment(App.Vector(*p,0),App.Vector(*q,0)),False)
    # Corner positions are expressions; the lower edge overlaps the bore void.
    for i,(x,y) in enumerate(pts):
        key.addConstraint(Sketcher.Constraint('Coincident',i,2,(i+1)%4,1))
        c=key.addConstraint(Sketcher.Constraint('DistanceX',i,1,x))
        key.setExpression('Constraints[%d]'%c, ('-' if x<0 else '')+'Dimensions.KeywayWidth / 2')
        c=key.addConstraint(Sketcher.Constraint('DistanceY',i,1,y))
        if y:
            key.setExpression('Constraints[%d]'%c,'Dimensions.KeywayFloor')
    final=pocket('KeywayThrough',key,'Dimensions.FaceWidth',True)
    body.Tip=final
    doc.recompute()
    assert not final.Shape.isNull(), 'Final feature is null'
    assert final.Shape.isValid(), 'Invalid final solid'
    assert len(final.Shape.Solids)==1, 'Expected exactly one solid'
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    output=os.path.splitext(os.path.abspath(__file__))[0]+'.FCStd'
    doc.recompute()
    doc.saveAs(output)
    print('Saved:',output, 'Volume:',final.Shape.Volume,'Solids:',len(final.Shape.Solids))
    return doc


if __name__ == '__main__':
    build()
