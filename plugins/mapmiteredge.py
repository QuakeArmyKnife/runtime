"""   QuArK  -  Quake Army Knife Bezier shape makers


"""


# THIS FILE IS PROTECTED BY THE GNU GENERAL PUBLIC LICENCE
# FOUND IN FILE "COPYING.TXT"
#
#
# $Header$
#

Info = {
   "plug-in":       "Mitered Edge Plugin",
   "desc":          "Make nice mitered edges where 2 faces join to make a surface",
   "date":          "5 Sept 2001",
   "author":        "tiglari",
   "author e-mail": "tiglari@planetquake.com",
   "quark":         "Quark 6.3" }


from tagging import *

import quarkpy.mapentities
import quarkpy.qmovepal
import quarkpy.mapduplicator
import mapdups
from mapextruder import make_edge
#from maptagside import colinear
from mapdupspath import evaluateDuplicators

#
# These should go to maputils someday
#

SMALL = .01

def colinear(list):
    "first 2 should not be coincident"
    if len(list) < 3:
       return 1
    norm = (list[1]-list[0]).normalized
    v0 = list[0]
    for v in list[2:]:
        if abs(v0 - v)>SMALL:
            if abs(norm-(v-v0).normalized)>SMALL:
                return 0
    return 1

def flatContainedWithin(list1, list2):
    "every vertex in list1 lies on the face defined by list2"
    len1 = len(list1)
    cross = (list2[1]-list2[0])^(list2[2]-list2[1]).normalized
    for i in range(len1):
        v = list1[(i+1)%len1]-list1[i]
        inward = cross^v
        for w in list2:
            if abs(list1[i]-w)<SMALL: #almost coincident == in
                continue
            if (w-list1[i])*inward>0:
                return 0
    return 1

def nextInList(list, current, incr=1):
    return list[(current+incr)%len(list)]


def overlapEdge(v1, v2, v3, v4):
    if v1-v3:
        if v2-v4:
            return 1
        else:
            return 0
    diff = abs(v1-v2)
    if diff==abs(v3-v1)+abs(v2-v3):
        return 1
    if diff==abs(v4-v1)+abs(v2-v4):
        return 1
    return 0

def overlapEdge(v1, v2, v3, v4):
    if abs(v1-v3)>SMALL:
        if abs(v2-v4)>SMALL:
            return 1
        else:
            return 0
    diff = abs(v1-v2)
    if math.fabs(diff-abs(v3-v1)-abs(v2-v3))<SMALL:
        return 1
    if math.fabs(diff-abs(v4-v1)-abs(v2-v4))<SMALL:
        return 1
    return 0

#
# Every 'facet' (face of a poly) of face2 is contained
#   within some facet of face1
#
def facetsContained(face1, face2):
    for vtxes2 in face2.vertices:
        for vtxes1 in face1.vertices:
            if not flatContainedWithin(vtxes2, vtxes1):
                return 0
    return 1
        

#
# The two faces share an edge, and the shared vertices are
#   appearing in opposite order on their lists (implies the
#   two faces form a surface)
#
def findEdgePoints(f1, f2):
    if f2 is None:
        return 0
    for poly1 in f1.faceof:
        vtxlist1 = f1.verticesof(poly1)
        for poly2 in f2. faceof:
            vtxlist2 = f2.verticesof(poly2)
            if poly1 is poly2:
                continue

            for i in range(len(vtxlist1)):
                nexti=nextInList(vtxlist1,i)
                for j in range(len(vtxlist2)):
                    if colinear([vtxlist1[i], nexti, vtxlist2[j]]):
                        prevj=nextInList(vtxlist2,j,-1)
                        if colinear([vtxlist1[i], nexti, prevj]):
                            if overlapEdge(vtxlist1[i], nexti, vtxlist2[(j-1)%len(vtxlist2)], vtxlist2[j]):
                                return (poly1, i), (poly2, (j-1)%len(vtxlist2))

#
# previous code requiring edge coincidence
#
#            for i in range(len(vtxlist1)):
#                for j in  range(len(vtxlist2)):
#                    if not (vtxlist1[i]-vtxlist2[j]): # the two faces share a vertex
#                        if not (nextInList(vtxlist1,i,1)-nextInList(vtxlist2,j,-1)):
#                            return (poly1, i), (poly2, (j-1)%len(vtxlist2))


def findAdjoiningFace(poly, face, i):
    vtxes = face.verticesof(poly)
    vtx=vtxes[i]
    for face2 in poly.faces:
        if face2 is face:
            continue
        vtxes2 = face2.verticesof(poly)
        for j in range(len(vtxes2)):
            if not (vtx - vtxes2[j]):
                if not (nextInList(vtxes,i)-nextInList(vtxes2,j,-1)):
                    return face2


def findOppositeFace(poly, face):
    for face2 in poly.faces:
        if face2 is face:
            continue
        if abs(face.normal+face2.normal)<SMALL:
            return face2

def findSharedVertex(face1, face2, poly):
    for vtx in face1.verticesof(poly):
        for vtx2 in face2.verticesof(poly):
            if not (vtx-vtx2):
                return vtx

def faceCenter(face, poly):
    vtxes = face.verticesof(poly)
    return reduce(lambda x,y:x+y, vtxes)/len(vtxes)

#    center = quarkx.vect(0,0,0)
#    for vtx in face.verticesof(poly):
#        center = center+vtx
#    return center/len(face.verticesof(poly))


#
# for edgepoint format see return line of findEdgePoints
# returns old, new list for substitution
#
def miterEdgeFaces(f1, f2, ((poly1, i1), (poly2, i2)), local_faces=[]):
    face1 = findAdjoiningFace(poly1, f1, i1)
    face2 = findAdjoiningFace(poly2, f2, i2) 
    if face1 is None or face2 is None:
        return
    #
    # We're looking for paralell faces on the opposite side to
    #   make a smooth join on that side if possible
    #
    oppface1 = findOppositeFace(poly1, f1)
    oppface2 = findOppositeFace(poly2, f2)
    vtxes = f1.verticesof(poly1)
    vtx = vtxes[i1]
    vtx2 = nextInList(vtxes,i1)
    #
    # get the 'extended faces' (backing onto the ones we're moving)
    #
    extendedfaces=[face1,face2]
    quarkx.extendcoplanar(extendedfaces,local_faces)
    ext2 = []
    for face in extendedfaces:
        if not(face is face1 or face is face2 or face in ext2) and (facetsContained(face, face1) or facetsContained(face, face2)):
            ext2.append(face)
    matched=0
    #
    # Try a technique which will line up the back faces nicely
    #
    
    if oppface1 is not None and oppface2 is not None:
        sharedvtx = findSharedVertex(face1, oppface1, poly1)
        if sharedvtx is not None:
            #
            # find a point where the two opposite faces intersect
            #
            center=faceCenter(oppface1, poly1)
            point = projectpointtoplane(center, sharedvtx-center,
                     oppface2.dist*oppface2.normal,oppface2.normal)
            oldlist = [face1, face2]+ext2
            newlist=[]
            for face in oldlist:
                newface=face.copy()
                newface.setthreepoints((vtx, vtx2, point),1)
                newface['tex']=CaulkTexture()
                newlist.append(newface)
            matched=1
    #
    # Well that won't work so Plan B
    #
    if not matched:
        newface1 = face1.copy()
        newface2 = face2.copy()
        edge = (vtx2-vtx)
        plane1 = edge^f1.normal
        plane2 = edge^f2.normal
        mitredir = make_edge(plane2, -plane1)
        mat = matrix_rot_u2v(mitredir, plane1)
        if mat is None:
            return [face1, face2], [face1, face2]
        newnormal = mat*f1.normal
        newface1.distortion(newnormal,vtx)
        newface2.distortion(-newnormal,vtx)
        oldlist = [face1, face2]
        newlist = [newface1, newface2]
    for i in range(len(oldlist)):
        p1, p2, p3 = oldlist[i].threepoints(1)
        q1, q2, q3 = newlist[i].threepoints(1)
        cross = ((p2-p1)^(p3-p2))*((q2-q1)^(q3-q1))
        if cross<0:
            newlist[i].setthreepoints((q1, q3, q2),1)
#        elif cross==0:
#            debug('zero cross')
        newlist[i].rebuildall()
    return oldlist, newlist

def miterEdge(f1, f2, edgepoints, editor):
    oldlist, newlist = miterEdgeFaces(f1, f2, edgepoints, editor.Root.findallsubitems("",":f"))
    undo = quarkx.action()
    for i in range(len(oldlist)):
        if newlist[i].normal*oldlist[i].normal<0:
            newlist[i].swapsides()
        undo.exchange(oldlist[i], newlist[i])
    editor.ok(undo, "mitre edge")
#    editor.layout.explorer.sellist=[f1]
    editor.layout.explorer.sellist=newlist
    



def mitrefacemenu(o, editor, oldmenu=quarkpy.mapentities.FaceType.menu.im_func):
    "the new right-mouse menu for polys"
    menu = oldmenu(o, editor)
    
    tagged = gettagged(editor)
    
    edgepoints = findEdgePoints(o, tagged)
    
    def miterEdgeClick(m, o=o, editor=editor, tagged=tagged, edgepoints=edgepoints):
        miterEdge(o, tagged, edgepoints, editor)
    
    mitreitem = qmenu.item("Mitre Edge",miterEdgeClick)
    
    if edgepoints is None:
        mitreitem.state=qmenu.disabled

    menu[:0] = [mitreitem]
    
    return menu
    
quarkpy.mapentities.FaceType.menu = mitrefacemenu


def match_vertices(vtxes1, vtxes2):
    len1 = len(vtxes1)
    if len==len(vtxes2):
        for i in range(len1):
            for j in range(len2):
                if not vtxes1[i]-vtxes2[j]:
                    for k in range(len1-1):
                        if vtxes1[(i+k)%len1]-vtxes2[(j-k)%len1]:
                            return 0
                    else:
                        return 1
    return 0
                     
def makePrism(f, p, wallwidth):                        
    walls = f.extrudeprism(p)
    for wall in walls:
        wall.texturename=f.texturename
    inner = f.copy()
    inner["ext_inner"]='1'
    inner.swapsides()
    outer = f.copy()
    n = f.normal
    n = n.normalized
    outer.translate(abs(wallwidth)*n)
    newp = quarkx.newobj(f.shortname+" wall:p")
    #
    # it's important than the inner one be first (to find
    #   it quickly later)
    #
    for face in [inner, outer] + walls:
        newp.appenditem(face)
    for face in newp.faces:
        for poly in face.faceof:
           poly.rebuildall()
    return newp
                        

#
# copied from plugins.csg, with modifications
#
def wallsFromPoly(plist, wallwidth=None):
    import quarkpy.qmovepal
    if wallwidth is None:
        wallwidth, = quarkpy.qmovepal.readmpvalues("WallWidth", SS_MAP)
    if wallwidth > 0:           #DECKER
        wallwidth = -wallwidth  #DECKER
    result = []
    if wallwidth < 0:           #DECKER
        for p in plist:
            newg = quarkx.newobj(p.shortname+" group:g")
            for f in p.faces:
                newp = makePrism(f, p, wallwidth)
                newg.appenditem(newp)
            result.append(newg)
        return result


def findMiterableFaces(faces):
    fdict = {}
    for fi1 in range(len(faces)):
        face1 = faces[fi1]
        for fi2 in range(fi1+1, len(faces)):
            face2=faces[fi2]
            if face1.normal-face2.normal and face1.normal+face2.normal:
                edgepoints = findEdgePoints(face1, face2)
                if edgepoints is None:
                    continue
                ((poly1, i1), (poly2, i2)) = edgepoints
                if poly1.type==":f" or poly2.type==":f":
                    continue
                if not fdict.has_key(face1):
                    fdict[face1] = {}
                fdict2 = fdict[face1]
                fdict2[face2] = edgepoints
    return fdict

#class NewWallMaker(mapdups.DepthDuplicator):
#    "Extrude the polyhedrons in the group."
        

def buildwallmakerimages(self, singleimage=None):
        if not self.dup["miter"]:
            return mapdups.DepthDuplicator.buildimages(self,singleimage)
            
        if singleimage is not None and singleimage>0:
            return []
        try:
            self.readvalues()
        except:
            print "Note: Invalid Duplicator Specific/Args."
            return
#        wallgroups = mapdups.DepthDuplicator.buildimages(self, singleimage)

        polys = self.sourcelist()
        polys = reduce(lambda x,y:x+y,map(lambda i:i.findallsubitems("",":p"),polys))
        depth=int(self.dup["depth"])
        wallgroups = map(lambda item:item.subitems, wallsFromPoly(polys, depth))
        wallgroup = quarkx.newobj("wallgroup:g")
        for i in range(len(polys)):
            walls = wallgroups[i]
            newwalls = []
            for wall in walls:
                wallbits = [wall]
                for j in range(len(polys)):
                    if i==j:
                        continue
                    if wall.intersects(polys[j]):
                        inner = wall.subitems[0]
                        innerp=inner.threepoints(0)[0]
                        poly = polys[j].copy()
                        for face in poly.faces:
                            if abs(inner.normal-face.normal)<SMALL and math.fabs((face.dist*face.normal-innerp)*inner.normal)<SMALL:
                                face.swapsides()
                                brush=makePrism(face,poly,self.depth)
                                for bface in brush.subitems[:2]:
                                    bface.translate(10*bface.normal)
                                wallbits=brush.subtractfrom(wallbits)
                                break
                newwalls = newwalls+wallbits   
            newgroup=quarkx.newobj(polys[i].shortname+':g')
            for wall in newwalls:
                newgroup.appenditem(wall)
            wallgroup.appenditem(newgroup)
        faces = filter(lambda f:f["ext_inner"]=='1', wallgroup.findallsubitems("",":f"))
#        debug('filtered '+`len(faces)`)
        oldlist = []
        newlist = []
        if self.dup["nobevel"]!='1':
            miterfaces = findMiterableFaces(faces)
            for face1 in miterfaces.keys():
                for face2 in miterfaces[face1].keys():
                    ((poly1, i1), (poly2, i2)) = miterfaces[face1][face2]
    #                debug('faces %s %s'%(face1.name, face2.name))
    #                debug('polys %s %s'%(poly1.name, poly2.name))
                    edgepoints = miterfaces[face1][face2]
                    old, new = miterEdgeFaces(face1, face2, edgepoints)
                    oldlist = oldlist+old
                    newlist = newlist+new
            #
            # seems awkward but doesnt work other wayz
            #
            polylist=wallgroup.findallsubitems("",":p")
            for poly in polylist:
                for i in range(len(oldlist)):
                    for face in poly.subitems:
                        if face is oldlist[i]:
                            poly.removeitem(face)
                            newface = newlist[i].copy()
                            poly.appenditem(newface)
                            poly.rebuildall()
                            if poly.broken:
                                newface.swapsides()
                            poly.rebuildall()
        return [wallgroup]
        
mapdups.WallMaker.buildimages = buildwallmakerimages
        
#
#quarkpy.mapduplicator.DupCodes.update({
#  "new wall maker":       NewWallMaker,})
  



#
# $Log$
# Revision 1.1  2001/09/23 07:00:34  tiglari
# mitered edges for wall maker duplicator
#
#