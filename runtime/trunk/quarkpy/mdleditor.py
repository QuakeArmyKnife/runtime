"""   QuArK  -  Quake Army Knife

Core of the Model editor.
"""
#
# Copyright (C) 1996-99 Armin Rigo
# THIS FILE IS PROTECTED BY THE GNU GENERAL PUBLIC LICENCE
# FOUND IN FILE "COPYING.TXT"
#

#$Header$

import mdlhandles
import qhandles
import mdlmgr
from qbaseeditor import BaseEditor
import mdlbtns
import mdlentities

import qmenu
import qtoolbar
import qmacro
from qeditor import *

# Globals
HoldObject = None
NewSellist = []
currentview = None
mdleditor = None

#py2.4 indicates upgrade change for python 2.4

class ModelEditor(BaseEditor):
    "The Model Editor."

    MODE = SS_MODEL
    manager = mdlmgr
    ObjectMgr = mdlentities.CallManager
    HandlesModule = mdlhandles
    MouseDragMode = mdlhandles.RectSelDragObject

    picked = []
    skinviewpicked = []
    dragobject = None
    ModelFaceSelList = []
    SkinFaceSelList = []
    

    def OpenRoot(self):
        global mdleditor
        mdleditor = self
        Root = self.fileobject['Root']
     #   if Root is not None: # If you have to open a model to open the Model Editor, how could it be None?
        Root = self.fileobject.findname(Root)
        self.Root = Root
        self.dragobject = None
        self.list = ()
        currentcomponent = self.Root

        if (quarkx.setupsubset(SS_MODEL, "Options")["setLock_X"] is None) and (quarkx.setupsubset(SS_MODEL, "Options")["setLock_Y"] is None) and  (quarkx.setupsubset(SS_MODEL, "Options")["setLock_Z"] is None):
            Lock_X = "0"
            Lock_Y = "0"
            Lock_Z = "0"
            quarkx.setupsubset(SS_MODEL, "Options")["setLock_X"] = Lock_X
            quarkx.setupsubset(SS_MODEL, "Options")["setLock_Y"] = Lock_Y
            quarkx.setupsubset(SS_MODEL, "Options")["setLock_Z"] = Lock_Z
        else:
            Lock_X = quarkx.setupsubset(SS_MODEL, "Options")["setLock_X"]
            Lock_Y = quarkx.setupsubset(SS_MODEL, "Options")["setLock_Y"]
            Lock_Z = quarkx.setupsubset(SS_MODEL, "Options")["setLock_Z"]
        self.lock_x = int(quarkx.setupsubset(SS_MODEL, "Options")["setLock_X"])
        self.lock_y = int(quarkx.setupsubset(SS_MODEL, "Options")["setLock_Y"])
        self.lock_z = int(quarkx.setupsubset(SS_MODEL, "Options")["setLock_Z"])


    def CloseRoot(self):
        picked = []
        self.dragobject = None
        ### To stop crossing of skins from model to model when a new model, even with the same name,
        ### is opened in the Model Editor without closing QuArK completely.
        try:
            from mdlmgr import saveskin
            mdlmgr.saveskin = None
        except:
            pass
                
    def ListComponents(self):
        return self.Root.findallsubitems("", ':mc')   # find all components


    def initmenu(self, form):
        "Builds the menu bar."
        import mdlmenus
        form.menubar, form.shortcuts = mdlmenus.BuildMenuBar(self)
        quarkx.update(form)
        self.initquickkeys(mdlmenus.MdlQuickKeys)


    def setupchanged(self, level):
        BaseEditor.setupchanged(self, level)
        mdlhandles.vertexdotcolor = MapColor("Vertices", SS_MODEL)
        mdlhandles.drag3Dlines = MapColor("Drag3DLines", SS_MODEL)
        mdlhandles.faceseloutline = MapColor("FaceSelOutline", SS_MODEL)
        mdlhandles.backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        mdlhandles.backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        mdlhandles.skinviewmesh = MapColor("SkinLines", SS_MODEL)
        mdlhandles.skinviewdraglines = MapColor("SkinDragLines", SS_MODEL)
        mdlhandles.skinviewpickedcolor = MapColor("SkinViewPickedColor", SS_MODEL)


    def buildhandles(self):
        "Build the handles for all model views."
        "This builds all the model mesh handles when the Model Editor is first opened."
        " It is also used to rebuild the handles by various functions later."
        from qbaseeditor import flagsmouse, currentview
        try:
            if flagsmouse == 1032 or flagsmouse == 1048 or flagsmouse == 2072:
                return
            elif (flagsmouse == 536 or flagsmouse == 544 or flagsmouse == 1056) and currentview.info["viewname"] != "skinview":
                pass
      #      elif currentview.info["viewname"] == "editors3Dview" and (flagsmouse == 2056 or flagsmouse == 2064 or flagsmouse == 2072 or flagsmouse == 2080):
      #          for v in self.layout.views:
      #              v.handles = v.handles
            elif currentview.info["viewname"] == "skinview" and flagsmouse == 2056:
                for v in self.layout.views:
                    v.handles = v.handles
            else:
                for v in self.layout.views:
                    v.handles = mdlhandles.BuildHandles(self, self.layout.explorer, v)
        except:
            for v in self.layout.views:
                v.handles = mdlhandles.BuildHandles(self, self.layout.explorer, v)

         #   delay, = quarkx.setupsubset(SS_MODEL, "Display")["HandlesDelay"]
         # linux issue with single quote
        try:
            delay, = quarkx.setupsubset(SS_MODEL, "Display")["HandlesDelay"]
        except:
            delay = 0.5 # linux issue with single quote

        if delay <= 0.0:
            commonhandles(self, 0)
        else:
#py2.4            quarkx.settimer(commonhandles, self, delay*1000.0)
            delayfactor = delay*1000
            quarkx.settimer(commonhandles, self, int(delayfactor))


    def setupview(self, v, drawmap=None, flags=MV_AUTOFOCUS, copycol=1):
        BaseEditor.setupview(self, v, drawmap, flags, copycol)
        if v.info["type"] == "3D":
            v.cameraposition = (quarkx.vect(150,-100,25), 2.5, 0.0)


    def setlayout(self, form, nlayout):
        BaseEditor.setlayout(self, form, nlayout)
        if nlayout is not None:
            for obj in self.Root.subitems:
                if obj.type == ':mc':      # Expand the Component objects
                     nlayout.explorer.expand(obj)


    def ok(self, undo, msg, autoremove=[]):
      global HoldObject, NewSellist
      NewSellist = []
      HoldObjectList = []
      for Object in self.layout.explorer.sellist:
          HoldObject = Object
          if HoldObject is None:
              Expanded = False
              ParentNames = []
          else:
              ParentNames = [HoldObject.name]
              while HoldObject.parent is not None:
                  HoldObject = HoldObject.parent
                  ParentNames.append(HoldObject.name)

          HoldObjectList.append(ParentNames)

      undo.ok(self.Root, msg)

      for ParentNames in HoldObjectList:
          HoldObject = self.Root
          ParentNames.reverse()
          if len(ParentNames) == 0:
              EditorRoot = 0
          else:
              EditorRoot = ParentNames.index(HoldObject.name)
      
          for x in range(len(ParentNames)-EditorRoot-1):
              if x+EditorRoot == 1:
                  HoldObject = HoldObject.findname(ParentNames[EditorRoot+x+1])
              elif x+EditorRoot == 2:
                  HoldObject = HoldObject.dictitems[ParentNames[EditorRoot+x+1]]
              elif x+EditorRoot == 3:
                  HoldObject = HoldObject.dictitems[ParentNames[EditorRoot+x+1]]

         ### Line below moved to mdlmgr.py, def selectcomponent, using HoldObject as global
         ### to allow Skin-view to complete its new undo mesh and handles, was not working from here.
         # self.layout.explorer.sellist = [HoldObject]

          NewSellist.append(HoldObject)
      try:
          if (NewSellist[0].name.endswith(":mr") or NewSellist[0].name.endswith(":mg") or NewSellist[0].name.endswith(":bone")):
              pass
          else:
              self.layout.explorer.sellist = NewSellist  # go around if bone is in the list
      except:
          pass    

      if len(NewSellist) <= 1:
          if len(NewSellist) == 1 and (NewSellist[0].name.endswith(":mr") or NewSellist[0].name.endswith(":mg")):
              pass
          else:
              for item in self.layout.explorer.sellist:
                  self.layout.explorer.expand(item.parent)
      else:
          HoldObject = None
          for item in self.layout.explorer.sellist:
              self.layout.explorer.expand(item.parent)


    def dropmap(self, view, newlist, x, y, src):
        center = view.space(x, y, view.proj(view.screencenter).z)
        mdlbtns.dropitemsnow(self, newlist, center=center)


    def explorermenu(self, reserved, view=None, origin=None):
        "The pop-up menu for the Explorer and views."

        import mdlmenus

        try:
            if view.info["viewname"] == "skinview":
                return mdlmenus.MdlBackgroundMenu(self, view, origin)
        except:
            pass

        if self.ModelFaceSelList != [] and view is not None:
            from qbaseeditor import cursorpos
            x, y = cursorpos
            choice = mdlhandles.ClickOnView(self, view, x, y)
            for item in choice:
                for face in self.ModelFaceSelList:
                    if item[2] == face:
                        return mdlhandles.ModelFaceHandle(qhandles.GenericHandle).menu(self, view)
                    
        
        sellist = self.layout.explorer.sellist
        if len(sellist)==0:
            return mdlmenus.MdlBackgroundMenu(self, view, origin)
        try:
            if view is not None and (sellist[0].type != ':mr' and sellist[0].type != ':mg' and sellist[0].type != ':bone'):
                return mdlmenus.MdlBackgroundMenu(self, view, origin)
        except:
            pass
        if view is None:
            extra = []
        else:
            extra = [qmenu.sep] + mdlmenus.TexModeMenu(self, view)
        if len(sellist)==1:
            if sellist[0].type == ':mf':
                import mdlcommands
                mdlcommands.NewFrame.state = qmenu.normal
                return [mdlcommands.NewFrame , qmenu.sep] + mdlentities.CallManager("menu", sellist[0], self) + extra
            else:
                return mdlentities.CallManager("menu", sellist[0], self) + extra
        return mdlmenus.MultiSelMenu(sellist, self) + extra


    def explorerdrop(self, ex, list, text):
        return mdlbtns.dropitemsnow(self, list, text)


    def explorerinsert(self, ex, list):
        for obj in list:
            mdlbtns.prepareobjecttodrop(self, obj)


    def editcmdclick(self, m):
        # dispatch the command to mdlbtns' "edit_xxx" procedure
        getattr(mdlbtns, "edit_" + m.cmd)(self, m)


    def deleteitems(self, list):
        mdlbtns.deleteitems(self.Root, list)


    def ForceEverythingToGrid(self, m):
        mdlbtns.ForceToGrid(self, self.gridstep, self.layout.explorer.sellist)


    def moveby(self, text, delta):
        mdlbtns.moveselection(self, text, delta)
        
        
def modelaxis(view):
    "Creates and draws the models axis for all of the editors views."
    
    editor = mdleditor
    for v in editor.layout.views:
        if v.info["viewname"] == "editors3Dview":
            modelcenter = v.info["center"]
    if view.info["viewname"] == "editors3Dview" or view.info["viewname"] == "3Dwindow":
        mc = view.proj(view.info["center"])
        Xend = view.proj(view.info["center"]+quarkx.vect(10,0,0))
        Yend = view.proj(view.info["center"]+quarkx.vect(0,-10,0))
        Zend = view.proj(view.info["center"]+quarkx.vect(0,0,10))
    else:
        mc = view.proj(modelcenter)
        Xend = view.proj(modelcenter+quarkx.vect(10,0,0))
        Yend = view.proj(modelcenter+quarkx.vect(0,-10,0))
        Zend = view.proj(modelcenter+quarkx.vect(0,0,10))
    cv = view.canvas()
    
    try:
        cv.penwidth = float(quarkx.setupsubset(SS_MODEL,"Options")['linethickness'])
    except:
        cv.penwidth = 2
        
    cv.pencolor = WHITE
    cv.ellipse(int(mc.x)-2, int(mc.y)-2, int(mc.x)+2, int(mc.y)+2)
    
    cv.fontsize = 5 * cv.penwidth
    cv.fontbold = 1
    cv.fontname = "MS Serif"
    cv.brushstyle = BS_CLEAR

    if view.info["viewname"] == "YZ":
        pass
    else:
        # X axis settings
        cv.pencolor = MapColor("ModelAxisX", SS_MODEL)
        cv.fontcolor = MapColor("ModelAxisX", SS_MODEL)
        cv.line(int(mc.x), int(mc.y), int(Xend.x), int(Xend.y))
        cv.textout(int(Xend.x-5), int(Xend.y+5), "X")
    if view.info["viewname"] == "XZ":
        pass
    else:
        # Y axis settings
        cv.pencolor = MapColor("ModelAxisY", SS_MODEL)
        cv.fontcolor = MapColor("ModelAxisY", SS_MODEL)
        cv.line(int(mc.x), int(mc.y), int(Yend.x), int(Yend.y))
        cv.textout(int(Yend.x-5), int(Yend.y+5), "Y")
    if view.info["viewname"] == "XY":
        pass
    else:
        # Z axis settings
        cv.pencolor = MapColor("ModelAxisZ", SS_MODEL)
        cv.fontcolor = MapColor("ModelAxisZ", SS_MODEL)
        cv.line(int(mc.x), int(mc.y), int(Zend.x), int(Zend.y))
        cv.textout(int(Zend.x-5), int(Zend.y-20), "Z")
        
        
def faceselfilllist(view, fillcolor=None):
    editor = mdleditor
    if view.info["viewname"] == "XY":
        fillcolor = MapColor("Options3Dviews_fillColor2", SS_MODEL)
    if view.info["viewname"] == "XZ":
        fillcolor = MapColor("Options3Dviews_fillColor4", SS_MODEL)
    if view.info["viewname"] == "YZ":
        fillcolor = MapColor("Options3Dviews_fillColor3", SS_MODEL)
    if view.info["viewname"] == "editors3Dview":
        fillcolor = MapColor("Options3Dviews_fillColor1", SS_MODEL)
    if view.info["viewname"] == "3Dwindow":
        fillcolor = MapColor("Options3Dviews_fillColor5", SS_MODEL)
    filllist = []

    if editor.ModelFaceSelList != []:
        comp = editor.Root.currentcomponent
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        filllist = [(None,None)]*len(comp.triangles)
        templist = None
        for triangleindex in editor.ModelFaceSelList:
            if quarkx.setupsubset(SS_MODEL,"Options")['NOSF'] == "1":
                pass                                                   # This will not fill in either the front or back faces, only lets the selected model mesh faces outlines to show (if on).
            elif quarkx.setupsubset(SS_MODEL,"Options")['FFONLY'] == "1":
                templist = (fillcolor,None)                            # This only fills in the front face color of the selected model mesh faces.
            elif quarkx.setupsubset(SS_MODEL,"Options")['BFONLY'] == "1":
                templist = (None,(backfacecolor1,backfacecolor2))      # This only fills in the backface pattern of the selected model mesh faces.
            else:
                templist = (fillcolor,(backfacecolor1,backfacecolor2)) # This fills in both the front face color and backface pattern of the selected model mesh faces.
            filllist[triangleindex] = templist
    return filllist



def setsingleframefillcolor(self, view):

    if self.Root.currentcomponent is None and self.Root.name.endswith(":mr"):
        componentnames = []
        for item in self.Root.dictitems:
            if item.endswith(":mc"):
                componentnames.append(item)
        componentnames.sort()
        self.Root.currentcomponent = self.Root.dictitems[componentnames[0]]

    comp = self.Root.currentcomponent
    
    if view.info["viewname"] == "XY":
        fillcolor = MapColor("Options3Dviews_fillColor2", SS_MODEL)
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh2"] == "1":
            comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
        else:
            if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                if self.ModelFaceSelList != []:
                    comp.filltris = faceselfilllist(view)
                else:
                    comp.filltris = [(None,None)]*len(comp.triangles)
            else:
                comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)

    if view.info["viewname"] == "XZ":
        fillcolor = MapColor("Options3Dviews_fillColor4", SS_MODEL)
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh4"] == "1":
            comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
        else:
            if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                if self.ModelFaceSelList != []:
                    comp.filltris = faceselfilllist(view)
                else:
                    comp.filltris = [(None,None)]*len(comp.triangles)
            else:
                comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)

    if view.info["viewname"] == "YZ":
        fillcolor = MapColor("Options3Dviews_fillColor3", SS_MODEL)
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh3"] == "1":
            comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
        else:
            if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                if self.ModelFaceSelList != []:
                    comp.filltris = faceselfilllist(view)
                else:
                    comp.filltris = [(None,None)]*len(comp.triangles)
            else:
                comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)

    if view.info["viewname"] == "editors3Dview":
        fillcolor = MapColor("Options3Dviews_fillColor1", SS_MODEL)
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh1"] == "1":
            comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
        else:
            if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                if self.ModelFaceSelList != []:
                    comp.filltris = faceselfilllist(view)
                else:
                    comp.filltris = [(None,None)]*len(comp.triangles)
            else:
                comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
  
    if view.info["viewname"] == "3Dwindow":
        fillcolor = MapColor("Options3Dviews_fillColor5", SS_MODEL)
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh5"] == "1":
            comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
        else:
            if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                if self.ModelFaceSelList != []:
                    comp.filltris = faceselfilllist(view)
                else:
                    comp.filltris = [(None,None)]*len(comp.triangles)
            else:
                comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)



def setframefillcolor(self, view):
    from qbaseeditor import currentview
    if self.Root.currentcomponent is None and self.Root.name.endswith(":mr"):
        componentnames = []
        for item in self.Root.dictitems:
            if item.endswith(":mc"):
                componentnames.append(item)
        componentnames.sort()
        self.Root.currentcomponent = self.Root.dictitems[componentnames[0]]

    comp = self.Root.currentcomponent
    
    if (view.info["viewname"] == "XY" or view.info["viewname"] == "XZ" or view.info["viewname"] == "YZ"):
        for v in self.layout.views:
            if v.info["viewname"] == "XY":
                if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh2"] == "1":
                    fillcolor = MapColor("Options3Dviews_fillColor2", SS_MODEL)
                    backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
                    backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
                    comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                else:
                    if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                        if self.ModelFaceSelList != []:
                            comp.filltris = faceselfilllist(v)
                        else:
                            comp.filltris = [(None,None)]*len(comp.triangles)
                    else:
                        comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)

            if v.info["viewname"] == "YZ":
                fillcolor = MapColor("Options3Dviews_fillColor3", SS_MODEL)
                backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
                backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
                if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh3"] == "1":
                    comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                else:
                    if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                        if self.ModelFaceSelList != []:
                            comp.filltris = faceselfilllist(v)
                        else:
                            comp.filltris = [(None,None)]*len(comp.triangles)
                    else:
                        comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)

            if v.info["viewname"] == "XZ":
                fillcolor = MapColor("Options3Dviews_fillColor4", SS_MODEL)
                backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
                backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
                if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh4"] == "1":
                    comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                else:
                    if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                        if self.ModelFaceSelList != []:
                            comp.filltris = faceselfilllist(v)
                        else:
                            comp.filltris = [(None,None)]*len(comp.triangles)
                    else:
                        comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)

    if view.info["viewname"] == "editors3Dview":
        currentview = view
        fillcolor = MapColor("Options3Dviews_fillColor1", SS_MODEL)
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh1"] == "1":
            comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
        else:
            if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                if self.ModelFaceSelList != []:
                    comp.filltris = faceselfilllist(view)
                else:
                    comp.filltris = [(None,None)]*len(comp.triangles)
            else:
                comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
  
    if view.info["viewname"] == "3Dwindow":
        currentview = view
        fillcolor = MapColor("Options3Dviews_fillColor5", SS_MODEL)
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh5"] == "1":
            comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
        else:
            if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                if self.ModelFaceSelList != []:
                    comp.filltris = faceselfilllist(view)
                else:
                    comp.filltris = [(None,None)]*len(comp.triangles)
            else:
                comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)


def paintframefill(self, v):


    if self.Root.currentcomponent is None and self.Root.name.endswith(":mr"):
        componentnames = []
        for item in self.Root.dictitems:
            if item.endswith(":mc"):
                componentnames.append(item)
        componentnames.sort()
        self.Root.currentcomponent = self.Root.dictitems[componentnames[0]]

    comp = self.Root.currentcomponent

    try:
        for v in self.layout.views:
            if ((v.info["viewname"] == "editors3Dview" or v.info["viewname"] == "3Dwindow") and self.dragobject != None):
                pass
            else:
                try:
                    if v.info["viewname"] == "XY":
                        fillcolor = MapColor("Options3Dviews_fillColor2", SS_MODEL)
                        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
                        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
                        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh2"] == "1":
                            comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                            v.repaint()
                        else:
                            if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                                if self.ModelFaceSelList != []:
                                    comp.filltris = faceselfilllist(v)
                                else:
                                    comp.filltris = [(None,None)]*len(comp.triangles)
                            else:
                                comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                            v.repaint()
                except:
                    pass

                if v.info["viewname"] == "XZ":
                    fillcolor = MapColor("Options3Dviews_fillColor4", SS_MODEL)
                    backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
                    backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
                    if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh4"] == "1":
                        comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                        v.repaint()
                    else:
                        if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                            if self.ModelFaceSelList != []:
                                comp.filltris = faceselfilllist(v)
                            else:
                                comp.filltris = [(None,None)]*len(comp.triangles)
                        else:
                            comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                        v.repaint()

                if v.info["viewname"] == "YZ":
                    fillcolor = MapColor("Options3Dviews_fillColor3", SS_MODEL)
                    backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
                    backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
                    if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh3"] == "1":
                        comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                        v.repaint()
                    else:
                        if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                            if self.ModelFaceSelList != []:
                                comp.filltris = faceselfilllist(v)
                            else:
                                comp.filltris = [(None,None)]*len(comp.triangles)
                        else:
                            comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                        v.repaint()

                if v.info["viewname"] == "3Dwindow":
                    pass

                ### Allows the drawing of the gridscale when actually panning.
                plugins.mdlgridscale.gridfinishdrawing(self, v)
    except:
        pass

    if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh2"] == "1":
        fillcolor = MapColor("Options3Dviews_fillColor2", SS_MODEL)
        backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
        backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
        comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
    else:
        if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
            if self.ModelFaceSelList != []:
                comp.filltris = faceselfilllist(v)
            else:
                comp.filltris = [(None,None)]*len(comp.triangles)
        else:
            backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
            backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
            comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)


def commonhandles(self, redraw=1):
    from qbaseeditor import flagsmouse, currentview
    import qhandles
    from mdlmgr import treeviewselchanged

    try:
        if flagsmouse == 536:
            return
            
     #   if flagsmouse == 2072: ## This FINNALLY STOPS EVERYTHING
     #       return
            
        if flagsmouse == 2072 and isinstance(self.dragobject, qhandles.FreeZoomDragObject):
            self.dragobject = None
        
        if flagsmouse == 2072 and isinstance(self.dragobject, mdlhandles.VertexHandle):
    #        self.dragobject = None
            return

        if currentview.info["viewname"] =="3Dwindow":
            if flagsmouse == 1048 or flagsmouse == 1056:
                cv = currentview.canvas()
                for h in currentview.handles:
                    h.draw(currentview, cv, None)
                return

        if flagsmouse == 16384:
            if isinstance(self.dragobject, qhandles.ScrollViewDragObject):
                if treeviewselchanged == 1:
                    mdlmgr.treeviewselchanged = 0
                    self.dragobject = None
                else:
                    return
            if isinstance(self.dragobject, qhandles.FreeZoomDragObject):
                if treeviewselchanged == 1:
                    mdlmgr.treeviewselchanged = 0
                    self.dragobject = None
                else:
                    return

        if flagsmouse == 16384:
            if self.dragobject is None:
                pass
            else:
                if isinstance(self.dragobject.handle, mdlhandles.SkinHandle):
                    pass
                elif isinstance(self.dragobject, qhandles.HandleDragObject):
                    pass
                else:
                    if currentview.info["viewname"] == "XY" or currentview.info["viewname"] == "XZ" or currentview.info["viewname"] == "YZ" or currentview.info["viewname"] == "editors3Dview" or currentview.info["viewname"] == "3Dwindow" or currentview.info["viewname"] == "skinview":
                        pass
                    else:
                        return
    except:
        pass

    if self.Root.currentcomponent is None and self.Root.name.endswith(":mr"):
        componentnames = []
        for item in self.Root.dictitems:
            if item.endswith(":mc"):
                componentnames.append(item)
        componentnames.sort()
        self.Root.currentcomponent = self.Root.dictitems[componentnames[0]]

    comp = self.Root.currentcomponent

    try:
        if isinstance(self.dragobject, qhandles.HandleDragObject):
            pass
        else:
            if (flagsmouse == 1032 or flagsmouse == 1040 or flagsmouse == 1048 or flagsmouse == 1056 or flagsmouse == 2056 or flagsmouse == 2064 or flagsmouse == 2080):
                if currentview.info["viewname"] == "editors3Dview":
                    if (quarkx.setupsubset(SS_MODEL, "Options")["DHWR"] == "1") and (flagsmouse == 2056):
                        return
                    else:
                        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_nohandles1"] == "1":
                            return
                        else:
                            hlist = mdlhandles.BuildCommonHandles(self, self.layout.explorer)   # model handles
                        currentview.handles = hlist
                        cv = currentview.canvas()
                        for h in hlist:
                            h.draw(currentview, cv, None)
                        return
                else:
                    pass
    except:
        pass

    try:
        if isinstance(self.dragobject, qhandles.HandleDragObject):
            pass
        else:
            if (flagsmouse == 1032 or flagsmouse == 1040 or flagsmouse == 1048 or flagsmouse == 1056 or flagsmouse == 2056 or flagsmouse == 2064 or flagsmouse == 2080):
                if currentview.info["viewname"] == "3Dwindow":
                    if (quarkx.setupsubset(SS_MODEL, "Options")["DHWR"] == "1") and (flagsmouse == 2056):
                        return
                    else:
                        if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_nohandles5"] == "1":
                            return
                        else:
                            hlist = mdlhandles.BuildCommonHandles(self, self.layout.explorer)   # model handles
                        currentview.handles = hlist
                        cv = currentview.canvas()
                        for h in hlist:
                            h.draw(currentview, cv, None)
                        return
                else:
                    pass
    except:
        pass

    if flagsmouse == 2056:
        return

    for v in self.layout.views:
        if v.info["viewname"] == "skinview":
            continue
        ### To update only those views that are in 'Textured' mode after a Skin-view drag has been done.
        try:
            if flagsmouse == 16384 and currentview.info["viewname"] == "skinview" and isinstance(self.dragobject.handle, mdlhandles.SkinHandle):
                if v.viewmode != "tex":
                    continue
                else:
                    v.invalidate(1)
        except:
            pass

        if v.info["viewname"] == "XY":
            fillcolor = MapColor("Options3Dviews_fillColor2", SS_MODEL)
            backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
            backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
            if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh2"] == "1":
                comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                v.repaint()
            else:
                if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                    if self.ModelFaceSelList != []:
                        comp.filltris = faceselfilllist(v)
                    else:
                        comp.filltris = [(None,None)]*len(comp.triangles)
                else:
                    comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                v.repaint()


        if v.info["viewname"] == "XZ":
            fillcolor = MapColor("Options3Dviews_fillColor4", SS_MODEL)
            backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
            backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
            if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh4"] == "1":
                comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                v.repaint()
            else:
                if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                    if self.ModelFaceSelList != []:
                        comp.filltris = faceselfilllist(v)
                    else:
                        comp.filltris = [(None,None)]*len(comp.triangles)
                else:
                    comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                v.repaint()


        if v.info["viewname"] == "YZ":
            fillcolor = MapColor("Options3Dviews_fillColor3", SS_MODEL)
            backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
            backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
            if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh3"] == "1":
                comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                v.repaint()
            else:
                if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                    if self.ModelFaceSelList != []:
                        comp.filltris = faceselfilllist(v)
                    else:
                        comp.filltris = [(None,None)]*len(comp.triangles)
                else:
                    comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                v.repaint()

        try:
            if (currentview.info["viewname"] != "editors3Dview") and flagsmouse == 1040:
                pass
            else:
                if v.info["viewname"] == "editors3Dview" and flagsmouse != 2064:
                    fillcolor = MapColor("Options3Dviews_fillColor1", SS_MODEL)
                    backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
                    backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
                    if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh1"] == "1":
                        comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                        v.repaint()
                    else:
                        if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                            if self.ModelFaceSelList != []:
                                comp.filltris = faceselfilllist(v)
                            else:
                                comp.filltris = [(None,None)]*len(comp.triangles)
                        else:
                            comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                        v.repaint()
                else:
                    pass
        except:
            pass

        try:
            if (currentview.info["viewname"] != "3Dwindow") and (flagsmouse == 1040 or flagsmouse == 1048 or flagsmouse == 1056 or flagsmouse == 2072 or flagsmouse == 2080):
                pass
            else:
                if v.info["viewname"] == "3Dwindow" and flagsmouse != 2064:
                    fillcolor = MapColor("Options3Dviews_fillColor5", SS_MODEL)
                    backfacecolor1 = MapColor("BackFaceColor1", SS_MODEL)
                    backfacecolor2 = MapColor("BackFaceColor2", SS_MODEL)
                    if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_fillmesh5"] == "1":
                        comp.filltris = [(fillcolor,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                        v.repaint()
                    else:
                        if quarkx.setupsubset(SS_MODEL, "Options")["DBF"] != "1":
                            if self.ModelFaceSelList != []:
                                comp.filltris = faceselfilllist(v)
                            else:
                                comp.filltris = [(None,None)]*len(comp.triangles)
                        else:
                            comp.filltris = [(None,(backfacecolor1,backfacecolor2))]*len(comp.triangles)
                        v.repaint()
                else:
                    pass
        except:
            pass

    if flagsmouse == 1048 or flagsmouse == 1056:
        hlist = []
    else:
        hlist = mdlhandles.BuildCommonHandles(self, self.layout.explorer)   # model handles common to all views

    for v in self.layout.views:
        if v.info["viewname"] == "editors3Dview" or v.info["viewname"] == "3Dwindow" or v.info["viewname"] == "skinview":
            continue
        else:
            plugins.mdlgridscale.gridfinishdrawing(self, v)
            plugins.mdlaxisicons.newfinishdrawing(self, v)

    try:
        for v in self.layout.views:
            if v.info["viewname"] == "skinview":
                continue
    
            ### To update only those views that are in 'Textured' mode after a Skin-view drag has been done.
            try:
                if flagsmouse == 16384 and currentview.info["viewname"] == "skinview" and isinstance(self.dragobject.handle, mdlhandles.SkinHandle):
                    if v.viewmode != "tex":
                        v.handles = hlist
                        continue
                    else:
                        if quarkx.setupsubset(SS_MODEL, "Options")["MAIV"] == "1":
                            modelaxis(v)
            except:
                pass
            
            try:
                if (currentview.info["viewname"] != "editors3Dview") and (flagsmouse == 1040 or flagsmouse == 1048 or flagsmouse == 1056):
                    pass
                else:
                    if v.info["viewname"] == "editors3Dview" and flagsmouse != 2064:
                        if currentview is None or currentview.info["viewname"] == "editors3Dview" or self.layout.selchange:
                            if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_nohandles1"] == "1":
                                pass
                            else:
                                v.handles = hlist
                                cv = v.canvas()
                                for h in hlist:
                                    h.draw(v, cv, None)
            except:
                pass    

            if v.info["viewname"] == "XY":
                if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_nohandles2"] == "1":
                    pass
                else:
                    v.handles = hlist
                    cv = v.canvas()
                    for h in hlist:
                        h.draw(v, cv, None)

            if v.info["viewname"] == "YZ":
                if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_nohandles3"] == "1":
                    pass
                else:
                    v.handles = hlist
                    cv = v.canvas()
                    for h in hlist:
                        h.draw(v, cv, None)

            if v.info["viewname"] == "XZ":
                if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_nohandles4"] == "1":
                    pass
                else:
                    v.handles = hlist
                    cv = v.canvas()
                    for h in hlist:
                        h.draw(v, cv, None)

            try:
                if (currentview.info["viewname"] != "3Dwindow") and (flagsmouse == 1040 or flagsmouse == 1048 or flagsmouse == 1056 or flagsmouse == 2072 or flagsmouse == 2080):
                    pass
                else:
                    if v.info["viewname"] == "3Dwindow" and flagsmouse != 2064:
                        if currentview is None or currentview.info["viewname"] == "3Dwindow" or self.layout.selchange:
                            if quarkx.setupsubset(SS_MODEL, "Options")["Options3Dviews_nohandles5"] == "1":
                                pass
                            else:
                                v.handles = hlist
                                cv = v.canvas()
                                for h in hlist:
                                    h.draw(v, cv, None)
            except:
                pass
        if currentview.info["viewname"] == "skinview":
            self.dragobject = None
    except:
        pass

    mdlmgr.treeviewselchanged = 0
    if flagsmouse == 16384 and self.dragobject is not None:
        self.dragobject.handle = None
        self.dragobject = None
               

# ----------- REVISION HISTORY ------------
#
#
#$Log$
#Revision 1.49  2007/06/24 22:27:08  cdunde
#To fix model axis not redrawing in textured views after Skin-view drag is made.
#
#Revision 1.48  2007/06/19 06:16:05  cdunde
#Added a model axis indicator with direction letters for X, Y and Z with color selection ability.
#Added model mesh face selection using RMB and LMB together along with various options
#for selected face outlining, color selections and face color filltris but this will not fill the triangles
#correctly until needed corrections are made to either the QkComponent.pas or the PyMath.pas
#file (for the TCoordinates.Polyline95f procedure).
#Also setup passing selected faces from the editors views to the Skin-view on Options menu.
#
#Revision 1.47  2007/06/09 08:13:25  cdunde
#Fixed 3D views nohandles option that got broken.
#
#Revision 1.46  2007/06/07 04:23:21  cdunde
#To setup selected model mesh face colors, remove unneeded globals
#and correct code for model colors.
#
#Revision 1.45  2007/06/03 23:45:58  cdunde
#Started mdlhandles.ClickOnView function for the Model Editor instead of using maphandles.py file.
#
#Revision 1.44  2007/06/03 22:50:21  cdunde
#To add the model mesh Face Selection RMB menus.
#(To add the RMB Face menu when the cursor is over one of the selected model mesh faces)
#
#Revision 1.43  2007/06/03 21:58:13  cdunde
#Added new Model Editor lists, ModelFaceSelList and SkinFaceSelList,
#Implementation of the face selection function for the model mesh.
#(To setup the ModelFaceSelList and SkinFaceSelList lists as attributes of the editor)
#
#Revision 1.42  2007/05/28 06:13:22  cdunde
#To stop 'Panning' (scrolling) from doing multiple handle drawings.
#
#Revision 1.41  2007/05/28 05:33:01  cdunde
#To stop 'Zoom' from doing multiple handle drawings.
#
#Revision 1.40  2007/05/26 07:07:32  cdunde
#Commented out code causing complete mess up in all views after drag in editors 3D view.
#Added code to allow 2D views to complete handle drawing process after zoom.
#
#Revision 1.39  2007/05/26 07:00:57  cdunde
#To allow rebuild and handle drawing after selection has changed
#of all non-wireframe views when currentview is the 'skinview'.
#
#Revision 1.38  2007/05/25 07:27:41  cdunde
#Removed blocked out dead code and tried to stabilize view handles being lost, going dead.
#
#Revision 1.37  2007/05/25 07:21:52  cdunde
#To try to get a stable global for 'mdleditor'.
#
#Revision 1.36  2007/05/20 22:08:03  cdunde
#To fix 3D views not drawing handles using the timer during zoom.
#
#Revision 1.35  2007/05/20 09:13:13  cdunde
#Substantially increased the drawing speed of the
#Model Editor Skin-view mesh lines and handles.
#
#Revision 1.34  2007/05/20 08:42:43  cdunde
#New methods to stop over draw of handles causing massive program slow down.
#
#Revision 1.33  2007/05/18 18:16:44  cdunde
#Reset items added.
#
#Revision 1.32  2007/05/18 16:56:23  cdunde
#Minor file cleanup and comments.
#
#Revision 1.31  2007/05/18 04:57:38  cdunde
#Fixed individual view modelfill color to display correctly during a model mesh vertex drag.
#
#Revision 1.30  2007/05/17 23:56:54  cdunde
#Fixed model mesh drag guide lines not always displaying during a drag.
#Fixed gridscale to display in all 2D view(s) during pan (scroll) or drag.
#General code proper rearrangement and cleanup.
#
#Revision 1.29  2007/05/16 20:59:03  cdunde
#To remove unused argument for the mdleditor paintframefill function.
#
#Revision 1.28  2007/05/16 19:39:46  cdunde
#Added the 2D views gridscale function to the Model Editor's Options menu.
#
#Revision 1.27  2007/04/27 17:27:42  cdunde
#To setup Skin-view RMB menu functions and possable future MdlQuickKeys.
#Added new functions for aligning, single and multi selections, Skin-view vertexes.
#To establish the Model Editors MdlQuickKeys for future use.
#
#Revision 1.26  2007/04/19 03:20:06  cdunde
#To move the selection retention code for the Skin-view vertex drags from the mldhandles.py file
#to the mdleditor.py file so it can be used for many other functions that cause the same problem.
#
#Revision 1.25  2007/04/16 16:55:58  cdunde
#Added Vertex Commands to add, remove or pick a vertex to the open area RMB menu for creating triangles.
#Also added new function to clear the 'Pick List' of vertexes already selected and built in safety limit.
#Added Commands menu to the open area RMB menu for faster and easer selection.
#
#Revision 1.24  2007/04/12 13:31:44  cdunde
#Minor cleanup.
#
#Revision 1.23  2007/04/04 21:34:17  cdunde
#Completed the initial setup of the Model Editors Multi-fillmesh and color selection function.
#
#Revision 1.22  2007/04/01 23:12:09  cdunde
#To remove Model Editor code no longer needed and
#improve Model Editor fillmesh color control when panning.
#
#Revision 1.21  2007/03/30 04:40:02  cdunde
#To stop console error when changing layouts in the Model Editor.
#
#Revision 1.20  2007/03/30 03:57:25  cdunde
#Changed Model Editor's FillMesh function to individual view settings on Views Options Dialog.
#
#Revision 1.19  2007/03/22 19:10:24  cdunde
#To stop crossing of skins from model to model when a new model, even with the same name,
#is opened in the Model Editor without closing QuArK completely.
#
#Revision 1.18  2007/03/04 19:38:04  cdunde
#To stop unneeded redrawing of handles in other views
#when LMB is released at end of rotation in a Model Editor's 3D view.
#
#Revision 1.17  2007/01/30 05:58:41  cdunde
#To remove unnecessary code and to get mdlaxisicons to be displayed consistently.
#
#Revision 1.16  2007/01/22 20:40:36  cdunde
#To correct errors of previous version that stopped vertex drag lines from drawing.
#
#Revision 1.15  2007/01/21 19:49:17  cdunde
#To cut down on lines and all handles being drawn when
#mouse button is 1st pressed and zooming in Skin-view
#and to add new Model Editor Views Options button and funcitons.
#
#Revision 1.14  2006/12/18 05:38:14  cdunde
#Added color setting options for various Model Editor mesh and drag lines.
#
#Revision 1.13  2006/12/13 04:46:15  cdunde
#To draw the 2D and 3D view model vertex handle lines while dragging
#but not the handles that substantially reduces redraw speed.
#
#Revision 1.12  2006/11/30 01:19:34  cdunde
#To fix for filtering purposes, we do NOT want to use capital letters for cvs.
#
#Revision 1.11  2006/11/29 07:00:27  cdunde
#To merge all runtime files that had changes from DanielPharos branch
#to HEAD for QuArK 6.5.0 Beta 1.
#
#Revision 1.10.2.3  2006/11/08 09:24:20  cdunde
#To setup and activate Model Editor XYZ Commands menu items
#and make them interactive with the Lock Toolbar.
#
#Revision 1.10.2.2  2006/11/04 21:40:30  cdunde
#To stop Python 2.4 Depreciation message in console.
#
#Revision 1.10.2.1  2006/11/03 23:38:10  cdunde
#Updates to accept Python 2.4.4 by eliminating the
#Depreciation warning messages in the console.
#
#Revision 1.10  2006/03/07 04:51:41  cdunde
#Setup model frame outlining and options for solid and color selection.
#
#Revision 1.9  2006/01/30 08:20:00  cdunde
#To commit all files involved in project with Philippe C
#to allow QuArK to work better with Linux using Wine.
#
#Revision 1.8  2005/10/15 00:47:57  cdunde
#To reinstate headers and history
#
#Revision 1.5  2001/03/15 21:07:49  aiv
#fixed bugs found by fpbrowser
#
#Revision 1.4  2000/08/21 21:33:04  aiv
#Misc. Changes / bugfixes
#
#Revision 1.2  2000/06/02 16:00:22  alexander
#added cvs headers
#
#
#