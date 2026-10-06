import os
import math
import FreeCAD as App
import Part
import Sketcher


def build():
    doc = App.newDocument('MotorMount')
    body = doc.addObject('PartDesign::Body', 'MotorMountBody')
    controls = doc.addObject('App::FeaturePython', 'Parameters')
    params = {
        'overall_length':110.0, 'overall_width':62.0,
        'plate_thickness':25.0, 'bore_diameter':50.25,
        'corner_radius':3.5, 'mounting_hole_pcd':70.0,
        'front_hole_diameter':4.2, 'front_hole_depth':11.138,
        'back_hole_diameter':3.3, 'back_hole_depth':9.109,
        'ear_hole_diameter':5.5,
        'plate_half_height':30.0, 'ear_width':10.0,
        'jaw_half_opening':20.0, 'jaw_chamfer_run':5.0,
        'ear_end_radius':0.5, 'ear_hole_y':51.0,
        'ear_hole_z_low':6.5, 'ear_hole_z_high':18.5,
    }
    for name, value in params.items():
        controls.addProperty('App::PropertyLength', name, 'Dimensions')
        setattr(controls, name, value)
    controls.addProperty('App::PropertyInteger','number_mounting_holes','Dimensions')
    controls.number_mounting_holes = 4
    controls.addProperty('App::PropertyAngle','drill_point_angle','Dimensions')
    controls.drill_point_angle = 118
    def expr(s):
        import re
        return re.sub(r'\b('+'|'.join(params)+r'|number_mounting_holes|drill_point_angle)\b', r'Parameters.\1', s)
    def dim(sk, con, expression):
        n=sk.addConstraint(con)
        sk.setExpression('Constraints[%d]' % n, expr(expression))
    def point_dims(sk, i, p, x, y, ex, ey):
        dim(sk, Sketcher.Constraint('DistanceX',i,p,x),ex)
        dim(sk, Sketcher.Constraint('DistanceY',i,p,y),ey)
    profile=body.newObject('Sketcher::SketchObject','PlateOutline')
    r=params['bore_diameter']/2
    j=math.sqrt(r*r-400)
    # Keep the left datum at -30; overall_width drives the ear outer edge.
    left='-plate_half_height'
    outer='overall_width - plate_half_height'
    inner=outer+' - ear_width'
    shoulder=outer+' - jaw_chamfer_run'
    jaw='sqrt((bore_diameter / 2)^2 - jaw_half_opening^2)'
    pts=[(-30,30,left,'plate_half_height'),(22,30,inner,'plate_half_height'),
         (22,55,inner,'overall_length / 2'),(32,55,outer,'overall_length / 2'),
         (32,25,outer,'jaw_half_opening + jaw_chamfer_run'),
         (27,20,shoulder,'jaw_half_opening'),(j,20,jaw,'jaw_half_opening'),
         (j,-20,jaw,'-jaw_half_opening'),(27,-20,shoulder,'-jaw_half_opening'),
         (32,-25,outer,'-jaw_half_opening - jaw_chamfer_run'),
         (32,-55,outer,'-overall_length / 2'),(22,-55,inner,'-overall_length / 2'),
         (22,-30,inner,'-plate_half_height'),(-30,-30,left,'-plate_half_height')]
    for k,a in enumerate(pts):
        b=pts[(k+1)%len(pts)]
        if k==6:
            t=math.asin(20/r)
            i=profile.addGeometry(Part.ArcOfCircle(Part.Circle(App.Vector(),App.Vector(0,0,1),r),t,2*math.pi-t),False)
            profile.addConstraint(Sketcher.Constraint('Coincident',i,3,-1,1))
            dim(profile,Sketcher.Constraint('Radius',i,r),'bore_diameter / 2')
            dim(profile,Sketcher.Constraint('DistanceY',i,1,20),'jaw_half_opening')
            dim(profile,Sketcher.Constraint('DistanceY',i,2,-20),'-jaw_half_opening')
        else:
            i=profile.addGeometry(Part.LineSegment(App.Vector(a[0],a[1],0),App.Vector(b[0],b[1],0)),False)
            point_dims(profile,i,1,*a)
            point_dims(profile,i,2,*b)
    doc.recompute()
    pad=body.newObject('PartDesign::Pad','PlateThickness')
    pad.Profile=profile
    pad.setExpression('Length','Parameters.plate_thickness')
    doc.recompute()
    def vertical_edges(feature, coords):
        chosen=[]
        for n,e in enumerate(feature.Shape.Edges,1):
            v=e.Vertexes
            if len(v)==2:
                a,b=[w.Point for w in v]
                if abs(a.x-b.x)<1e-6 and abs(a.y-b.y)<1e-6 and abs(abs(a.z-b.z)-25)<1e-6:
                    if any(math.hypot(a.x-x,a.y-y)<1e-5 for x,y in coords):
                        chosen.append('Edge%d'%n)
        return chosen
    corners=[(-30,30),(-30,-30),(22,30),(22,-30),(32,25),(32,-25),(27,20),(27,-20),(j,20),(j,-20)]
    fillet=body.newObject('PartDesign::Fillet','ProfileCornerRounds')
    fillet.Base=(pad,vertical_edges(pad,corners))
    fillet.setExpression('Radius','Parameters.corner_radius')
    doc.recompute()
    end=body.newObject('PartDesign::Fillet','EarEndRounds')
    end.Base=(fillet,vertical_edges(fillet,[(22,55),(32,55),(22,-55),(32,-55)]))
    end.setExpression('Radius','Parameters.ear_end_radius')
    doc.recompute()
    def circle(sk,x,y,diam,ex,ey,ed):
        i=sk.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),diam/2),False)
        point_dims(sk,i,3,x,y,ex,ey)
        dim(sk,Sketcher.Constraint('Diameter',i,diam),ed)
    for side in ['Front','Back']:
        low=side.lower()
        sk=body.newObject('Sketcher::SketchObject',side+'DrillingCenters')
        if side=='Back':
            sk.setExpression('Placement.Base.z','Parameters.plate_thickness')
        for k in range(controls.number_mounting_holes):
            angle=45+360*k/controls.number_mounting_holes
            a=math.radians(angle)
            ea='(45deg + %d * 360deg / number_mounting_holes)'%k
            circle(sk,35*math.cos(a),35*math.sin(a),params[low+'_hole_diameter'],
                   'mounting_hole_pcd / 2 * cos('+ea+')',
                   'mounting_hole_pcd / 2 * sin('+ea+')',low+'_hole_diameter')
        doc.recompute()
        h=body.newObject('PartDesign::Hole',side+'BlindDrillings')
        h.Profile=sk
        h.Reversed=(side=='Front')
        h.DepthType='Dimension'
        h.setExpression('Diameter','Parameters.'+low+'_hole_diameter')
        h.setExpression('Depth','Parameters.'+low+'_hole_depth')
        h.DrillPoint='Angled'
        h.setExpression('DrillPointAngle','Parameters.drill_point_angle')
        h.DrillForDepth=False
        h.Refine=True
        doc.recompute()
    ear=body.newObject('Sketcher::SketchObject','EarCrossHoleCenters')
    ear.Placement=App.Placement(App.Vector(32,0,0),App.Rotation(App.Vector(0,1,0),90))
    ear.setExpression('Placement.Base.x',expr(outer))
    for sign in [1,-1]:
        for zname in ['ear_hole_z_low','ear_hole_z_high']:
            circle(ear,-params[zname],sign*51,5.5,'-'+zname,('' if sign==1 else '-')+'ear_hole_y','ear_hole_diameter')
    doc.recompute()
    pocket=body.newObject('PartDesign::Pocket','EarThroughHoles')
    pocket.Profile=ear
    pocket.setExpression('Length','Parameters.ear_width')
    pocket.Refine=True
    doc.recompute()
    for obj in body.Group:
        if hasattr(obj,'Visibility'): obj.Visibility=False
    pocket.Visibility=True
    body.Tip=pocket
    doc.recompute()
    for obj in [pad,fillet,end,doc.FrontBlindDrillings,doc.BackBlindDrillings,pocket]:
        if obj.Shape.isNull() or not obj.Shape.isValid() or len(obj.Shape.Solids)!=1:
            raise RuntimeError('Invalid feature: '+obj.Name+' '+str(obj.State))
    if App.GuiUp:
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
    path=os.path.splitext(os.path.abspath(__file__))[0]+'.FCStd'
    doc.recompute()
    doc.saveAs(path)
    print('Saved',path,'Volume',pocket.Shape.Volume)
    return doc

if __name__=='__main__':
    build()
