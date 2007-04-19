"""   QuArK  -  Quake Army Knife

Various Model editor utilities.
"""
#
# Copyright (C) 1996-99 Armin Rigo
# THIS FILE IS PROTECTED BY THE GNU GENERAL PUBLIC LICENCE
# FOUND IN FILE "COPYING.TXT"
#

#$Header$



import quarkx
from qeditor import *
from math import *


#
# Calculate Position of a Point along the vector AC, Keeping L (Length)
#
def ProjectKeepingLength(A,C,L):
    def NormaliseVect(v1, v2):
        le = sqrt( pow(v2.x - v1.x, 2) + 
                   pow(v2.y - v1.y, 2) + 
                   pow(v2.z - v1.z, 2) )
        if (le <> 0): 
            v = quarkx.vect( \
                (v2.x - v1.x) / le, \
                (v2.y - v1.y) / le, \
                (v2.z - v1.z) / le  )
        else:
            v = quarkx.vect(0,0,0)
        return v
    n = NormaliseVect(A, C)
    xxx = quarkx.vect(
        A.x + (L * n.x),
        A.y + (L * n.y),
        A.z + (L * n.z)
        )
    return xxx


#
# Invalidate all views
#
def invalidateviews():
    editor = mapeditor()
    if editor is None: return
    editor.invalidateviews(1)


#
#  Find a triangle based on vertex indexs
#
def findTriangle(comp, v1, v2, v3):
    tris = comp.triangles
    index = -1
    for tri in tris:
        index = index + 1
        b = 0
        for c in tri:
            if ((c[0] == v1) | (c[0] == v2) | (c[0] == v3)):
                b = b + 1
            else:
                b = 0
        if b==3:
            return index
    return None


#
# Remove a triangle from a given component
#
def removeTriangle_v3(comp, v1, v2, v3):
    removeTriangle(comp, findTriangle(comp, v1,v2,v3))
  
  
#
# Remove a triangle from a given component
#
def removeTriangle(comp, index):
    if (index is None):
        return
    editor = mapeditor()
    new_comp = comp.copy()
    old_tris = new_comp.triangles
    tris = old_tris[:index] + old_tris[index+1:]
    new_comp.triangles = tris
    undo = quarkx.action()
    undo.exchange(comp, new_comp)
    editor.ok(undo, "remove triangle")
    editor.picked = []
    invalidateviews()


#
# Add a frame to a given component (ie duplicate last one)
#
def addframe(comp):
    if (comp is None):
        return

    editor = mapeditor()
    if (editor.layout.explorer.uniquesel is None) or (editor.layout.explorer.uniquesel.type != ":mf"):
        quarkx.msgbox("You need to select a\nsingle frame to duplicate.", MT_ERROR, MB_OK)
        return

    newframe = editor.layout.explorer.uniquesel.copy()
    new_comp = comp.copy(1)

    for obj in new_comp.dictitems['Frames:fg'].subitems:
       if obj.name == editor.layout.explorer.uniquesel.name:
            count = new_comp.dictitems['Frames:fg'].subitems.index(obj)+1
            break

    newframe.shortname = newframe.shortname + " copy"
    new_comp.dictitems['Frames:fg'].insertitem(count, newframe)
  #  new_comp.dictitems['Frames:fg'].appenditem(newframe) # This will just append the new frame copy at the end of the frames list.

    undo = quarkx.action()
    undo.exchange(comp, new_comp)
    editor.ok(undo, "add frame")
    invalidateviews()


#
# Add a triangle to a given component
#
def addtriangle(comp,v1,v2,v3,s1,t1,s2,t2,s3,t3):
    if (comp is None) or (v1 is None) or (v2 is None) or (v3 is None):
        return
    if (s1 is None) or (s2 is None) or (s3 is None):
        return
    if (t1 is None) or (t2 is None) or (t3 is None):
        return
    tris = comp.triangles
    tris = tris + [((v1,s1,t1),(v2,s2,t2),(v3,s3,t3))]
    new_comp = comp.copy()
    new_comp.triangles = tris

    undo = quarkx.action()
    undo.exchange(comp, new_comp)
    mapeditor().ok(undo, "add triangle")
    invalidateviews()


#
# Add a vertex to a given component at origin specified
#
def addvertex(comp, org):
    if (comp is None) or (org is None):
        return
    new_comp = comp.copy()
    frames = new_comp.findallsubitems("", ':mf')   # find all frames
    for frame in frames:
        vtxs = frame.vertices
        vtxs = vtxs + [org]
        frame.vertices = vtxs

    undo = quarkx.action()
    undo.exchange(comp, new_comp)
    mapeditor().ok(undo, "add vertex")
    invalidateviews()


#
# Checks triangle for vertex [index]
#
def checkTriangle(tri, index):
    for c in tri:
        if ( c[0] == index): # c[0] is the 'vertexno'
            return 1
    return 0


#
# Find other triangles containing a vertex at the same location
# as the one selected creating a VertexHandle instance.
# For example call this function like this (for clarity):
#    component = editor.layout.explorer.uniquesel
#    handlevertex = self.index
#    if component.name.endswith(":mc"):
#        tris = findTriangles(component, handlevertex)
# or like this (to be brief):
#    comp = editor.layout.explorer.uniquesel
#    if comp.name.endswith(":mc"):
#        tris = findTriangles(comp, self.index)
#
def findTriangles(comp, index):
    tris = comp.triangles
    tris_out = [ ]
    for tri in tris:
        isit = checkTriangle(tri, index)
        if (isit == 1):
            tris_out = tris_out + [ tri ]
    return tris_out



def fixTri(tri, index):
    new_tri = [ ]
    for c in tri:
        v = 0
        if ( c[0] > index):
            v = c[0]-1
        else:
            v = c[0]
        s = c[1]
        t = c[2]
        new_tri = new_tri + [(v,s,t)]
    return (new_tri[0], new_tri[1], new_tri[2])


#
# goes through tri list: if greaterthan index then takes 1 away from vertexno
#
def fixUpVertexNos(tris, index):
    new_tris = [ ]
    for tri in tris:
         x = fixTri(tri, index)
         new_tris = new_tris + [x]
    return new_tris

def checkinlist(tri, toberemoved):
  for tbr in toberemoved:
    if (tri == tbr):
      return 1
  return 0


#
# remove a vertex from a component
#
def removevertex(comp, index):
    if (comp is None) or (index is None):
        return
    #### 1) find all triangles that use vertex 'index' and delete them.
    toBeRemoved = findTriangles(comp, index)
    tris = comp.triangles
    new_tris = []
    for tri in tris:
        p = checkinlist(tri, toBeRemoved)
        if (p==0):
            new_tris = new_tris + [ tri ]
    enew_tris = fixUpVertexNos(new_tris, index)
    new_comp = comp.copy() # create a copy to edit (we store the old one in the undo list)
    new_comp.triangles = enew_tris
    #### 2) loop through all frames and delete vertex.
    frames = new_comp.findallsubitems("", ':mf')   # find all frames
    for frame in frames: 
        old_vtxs = frame.vertices
        vtxs = old_vtxs[:index] + old_vtxs[index+1:]
        frame.vertices = vtxs
    #### 3) re-build all views
    undo = quarkx.action()
    undo.exchange(comp, new_comp)
    mapeditor().ok(undo, "remove vertex")
    invalidateviews()


#
# Is a given object still in the tree view, or was it removed ?
#
def checktree(root, obj):
    while obj is not root:
        t = obj.parent
        if t is None or not (obj in t.subitems):
            return 0
        obj = t
    return 1



#
# The UserDataPanel class, overridden to be model-specific.
#
class MdlUserDataPanel(UserDataPanel):


    def btnclick(self, btn):
        #
        # Send the click message to the module mdlbtns.
        #
        import mdlbtns
        mdlbtns.mdlbuttonclick(btn)


    #def drop(self, btnpanel, list, i, source):
        #if len(list)==1 and list[0].type == ':g':
        #    quarkx.clickform = btnpanel.owner
        #    editor = mapeditor()
        #    if editor is not None and source is editor.layout.explorer:
        #        choice = quarkx.msgbox("You are about to create a new button from this group. Do you want the button to display a menu with the items in this group ?\n\nYES: you can pick up individual items when you click on this button.\nNO: you can insert the whole group in your map by clicking on this button.", MT_CONFIRMATION, MB_YES_NO_CANCEL)
        #        if choice == MR_CANCEL:
        #            return
        #        if choice == MR_YES:
        #            list = [group2folder(list[0])]
        #UserDataPanel.drop(self, btnpanel, list, i, source)



def find2DTriangles(comp, tri_index, ver_index):
    "This function returns triangles and their index of a component's"
    "mesh that have a common vertex position of the 2D drag view."
    "This is primarily used for the Skin-view mesh drag option."
    "See the mdlhandles.py file class SkinHandle, drag funciton for its use."
    tris = comp.triangles
    tris_out = {}
    i = 0
    for tri in tris:
        for vtx in tri:
            if str(vtx) == str(tris[tri_index][ver_index]):
              if i == tri_index:
                  break
              else:
                  tris_out[i] = tri
                  break
        i = i + 1
    return tris_out


# ----------- REVISION HISTORY ------------
#
#
#$Log$
#Revision 1.16  2007/04/17 16:01:25  cdunde
#To retain selection of original animation frame when duplicated.
#
#Revision 1.15  2007/04/17 12:55:34  cdunde
#Fixed Duplicate current frame function to stop Model Editor views from crashing
#and updated its popup help and Infobase link description data.
#
#Revision 1.14  2007/04/16 16:55:59  cdunde
#Added Vertex Commands to add, remove or pick a vertex to the open area RMB menu for creating triangles.
#Also added new function to clear the 'Pick List' of vertexes already selected and built in safety limit.
#Added Commands menu to the open area RMB menu for faster and easer selection.
#
#Revision 1.13  2007/04/10 06:00:36  cdunde
#Setup mesh movement using common drag handles
#in the Skin-view for skinning model textures.
#
#Revision 1.12  2007/03/29 15:25:34  danielpharos
#Cleaned up the tabs.
#
#Revision 1.11  2006/12/06 04:05:59  cdunde
#For explanation comment on how to use def findTriangles function.
#
#Revision 1.10  2005/10/15 00:47:57  cdunde
#To reinstate headers and history
#
#Revision 1.7  2001/03/15 21:07:49  aiv
#fixed bugs found by fpbrowser
#
#Revision 1.6  2001/02/01 22:03:15  aiv
#RemoveVertex Code now in Python
#
#Revision 1.5  2000/10/11 19:07:47  aiv
#Bones, and some kinda skin vertice viewer
#
#Revision 1.4  2000/08/21 21:33:04  aiv
#Misc. Changes / bugfixes
#
#Revision 1.2  2000/06/02 16:00:22  alexander
#added cvs headers
#
#