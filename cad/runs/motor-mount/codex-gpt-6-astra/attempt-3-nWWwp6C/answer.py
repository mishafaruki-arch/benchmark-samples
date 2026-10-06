import os, math
import FreeCAD as App
import Part, Sketcher


def build():
    doc = App.newDocument('MotorMount')
    body = doc.addObject('App::FeaturePython', 'Dimensions')
    body.Label = 'Aluminum motor mount'
    parameters = {
        'overall_length':110.0, 'overall_width':62.0, 'plate_thickness':25.0,
        'bore_diameter':50.25, 'corner_radius':3.5, 'mounting_hole_pcd':70.0,
        'front_hole_diameter':4.2, 'front_hole_depth':11.138,
        'back_hole_diameter':3.3, 'back_hole_depth':9.109,
        'ear_hole_diameter':5.5,
    }
    for name, value in parameters.items():
        body.addProperty('App::PropertyLength', name, 'Dimensions')
        setattr(body, name, value)
    body.addProperty('App::PropertyInteger', 'number_mounting_holes', 'Dimensions')
    body.number_mounting_holes = 4
    body.addProperty('App::PropertyAngle', 'drill_point_angle', 'Dimensions')
    body.drill_point_angle = 118
    body.addProperty('App::PropertyLength', 'ear_end_radius', 'Dimensions')
    body.ear_end_radius = 0.5
    params = body
    body = doc.addObject('PartDesign::Body', 'MotorMountBody')
    def expr(prop):
        return 'Dimensions.' + prop

    sketch = body.newObject('Sketcher::SketchObject', 'PlateOutline')
    sketch.Label = 'C profile with open motor bore'
    jaw = math.sqrt((params.bore_diameter.Value/2)**2 - 20**2)
    # Coordinates travel clockwise around the outside, then return along the bore.
    coords = [(jaw,20),(27,20),(32,25),(32,55),(22,55),(22,30),
              (-30,30),(-30,-30),(22,-30),(22,-55),(32,-55),
              (32,-25),(27,-20),(jaw,-20)]
    xexpr = ['sqrt((Dimensions.bore_diameter / 2)^2 - (20 mm)^2)',
             '27 mm','Dimensions.overall_width - 30 mm']
    def coordinate_expression(x,y):
        if abs(x-jaw)<1e-8: ex=xexpr[0]
        elif x==32: ex=xexpr[2]
        else: ex=str(x)+' mm'
        ey= ('Dimensions.overall_length / 2' if y==55 else
             '-Dimensions.overall_length / 2' if y==-55 else str(y)+' mm')
        return ex,ey
    for i in range(len(coords)-1):
        a,c = coords[i],coords[i+1]
        idx=sketch.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*c,0)),False)
        for pos,pt in [(1,a),(2,c)]:
            for typ,val,ex in zip(['DistanceX','DistanceY'],pt,coordinate_expression(*pt)):
                ci=sketch.addConstraint(Sketcher.Constraint(typ,idx,pos,val))
                sketch.setExpression('Constraints[%d]'%ci,ex)
    arc=sketch.addGeometry(Part.Arc(App.Vector(jaw,20,0),App.Vector(-25.125,0,0),App.Vector(jaw,-20,0)),False)
    sketch.addConstraint(Sketcher.Constraint('Coincident',arc,1,0,1))
    sketch.addConstraint(Sketcher.Constraint('Coincident',arc,2,12,2))
    ci=sketch.addConstraint(Sketcher.Constraint('Radius',arc,25.125))
    sketch.setExpression('Constraints[%d]'%ci,expr('bore_diameter')+' / 2')
    doc.recompute()
    pad=body.newObject('PartDesign::Pad','PlateThickness')
    pad.Profile=sketch
    pad.setExpression('Length',expr('plate_thickness'))
    doc.recompute()
    sketch.Visibility=False

    def vertical_edges(feature,points):
        names=[]
        for i,e in enumerate(feature.Shape.Edges):
            vs=e.Vertexes
            if len(vs)!=2: continue
            a,b=vs[0].Point,vs[1].Point
            if abs(a.x-b.x)<1e-6 and abs(a.y-b.y)<1e-6 and abs(abs(a.z-b.z)-25)<1e-6:
                if any(math.hypot(a.x-x,a.y-y)<1e-5 for x,y in points):
                    names.append('Edge%d'%(i+1))
        return names
    rounded=[(-30,30),(-30,-30),(22,30),(22,-30),(32,25),(32,-25),
             (27,20),(27,-20),(jaw,20),(jaw,-20)]
    fillet=body.newObject('PartDesign::Fillet','ProfileCornerRounds')
    fillet.Base=(pad,vertical_edges(pad,rounded))
    fillet.setExpression('Radius',expr('corner_radius'))
    doc.recompute()
    pad.Visibility=False
    tips=body.newObject('PartDesign::Fillet','EarEndRounds')
    tips.Base=(fillet,vertical_edges(fillet,[(22,55),(32,55),(22,-55),(32,-55)]))
    tips.setExpression('Radius',expr('ear_end_radius'))
    doc.recompute()
    fillet.Visibility=False

    def hole_pattern(name,z,diameter):
        sk=body.newObject('Sketcher::SketchObject',name)
        sk.Placement.Base.z=z
        if z:
            sk.setExpression('Placement.Base.z',expr('plate_thickness'))
        for i in range(params.number_mounting_holes):
            angle=math.radians(45+360*i/params.number_mounting_holes)
            x=35*math.cos(angle); y=35*math.sin(angle)
            g=sk.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),getattr(params,diameter).Value/2),False)
            for kind,value,factor in [('DistanceX',x,'cos'),('DistanceY',y,'sin')]:
                c=sk.addConstraint(Sketcher.Constraint(kind,g,3,value))
                sk.setExpression('Constraints[%d]'%c,expr('mounting_hole_pcd')+' / 2 * '+factor+'(45 deg + 360 deg * %d / Dimensions.number_mounting_holes)'%i)
            c=sk.addConstraint(Sketcher.Constraint('Diameter',g,getattr(params,diameter).Value))
            sk.setExpression('Constraints[%d]'%c,expr(diameter))
        doc.recompute()
        return sk
    previous=tips
    for side,z,reverse in [('front',0,True),('back',25,False)]:
        sk=hole_pattern(side.title()+'DrillCenters',z,side+'_hole_diameter')
        hole=body.newObject('PartDesign::Hole',side.title()+'BlindDrillings')
        hole.Profile=sk
        hole.setExpression('Diameter',expr(side+'_hole_diameter'))
        hole.setExpression('Depth',expr(side+'_hole_depth'))
        hole.DepthType='Dimension'
        hole.DrillPoint='Angled'
        hole.setExpression('DrillPointAngle',expr('drill_point_angle'))
        hole.DrillForDepth=False
        hole.Reversed=reverse
        hole.Refine=True
        doc.recompute()
        previous.Visibility=False
        sk.Visibility=False
        previous=hole

    ear=body.newObject('Sketcher::SketchObject','EarCrossDrillCenters')
    # Sketch normal points along +X: local x is -Z, local y is Y.
    ear.Placement=App.Placement(App.Vector(32,0,0),App.Rotation(App.Vector(0,1,0),90))
    ear.setExpression('Placement.Base.x',expr('overall_width')+' - 30 mm')
    for y in [-51,51]:
        for z in [6.5,18.5]:
            g=ear.addGeometry(Part.Circle(App.Vector(-z,y,0),App.Vector(0,0,1),2.75),False)
            ear.addConstraint(Sketcher.Constraint('DistanceX',g,3,-z))
            c=ear.addConstraint(Sketcher.Constraint('DistanceY',g,3,y))
            ear.setExpression('Constraints[%d]'%c,('' if y>0 else '-')+'(Dimensions.overall_length / 2 - 4 mm)')
            c=ear.addConstraint(Sketcher.Constraint('Diameter',g,5.5))
            ear.setExpression('Constraints[%d]'%c,expr('ear_hole_diameter'))
    doc.recompute()
    cross=body.newObject('PartDesign::Pocket','EarThroughHoles')
    cross.Profile=ear
    cross.Type=1
    doc.recompute()
    previous.Visibility=False
    ear.Visibility=False
    body.Tip=cross
    cross.Visibility=True
    doc.recompute()
    for feature in [pad,fillet,tips,cross]:
        if feature.Shape.isNull() or not feature.Shape.isValid():
            raise RuntimeError('Invalid feature: '+feature.Name+' '+str(feature.State))
    if len(cross.Shape.Solids)!=1:
        raise RuntimeError('Expected exactly one solid')
    if App.GuiUp:
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    doc.recompute()
    doc.saveAs(os.path.splitext(os.path.abspath(__file__))[0]+'.FCStd')
    return doc

if __name__=='__main__':
    build()
