"""   QuArK  -  Quake Army Knife

OpenGL manager.
"""
#
# Copyright (C) 1996-2000 Armin Rigo
# THIS FILE IS PROTECTED BY THE GNU GENERAL PUBLIC LICENCE
# FOUND IN FILE "COPYING.TXT"
#
#$Header$

#
# NOTE: this module is NEVER actually loaded before an OpenGL
# view must be opened. To check if an OpenGL view is currently
# opened DO NOT import qopengl; instead, check the value of
# qbaselayout.BaseLayout.CurrentOpenGLOwner.
#

import quarkx
from qeditor import *
from qdictionnary import Strings
from qbasemgr import BaseLayout
BaseLayout.CurrentOpenGLOwner = None


#
# Only one real OpenGL window is opened at a time;
# all other map views actually render inside this window (invisibly)
# and then copy the data to their own surface.
#
wnd = None
glview = None
offscreen = 0


def open(editor, minx=0, miny=0, bkgnd=0, force=0):
    # open the OpenGL window. If bkgnd=1, open it in the background.
    # If bkgnd=2, force it in the background.

    global wnd, glview, offscreen
    #quarkx.settimer(deadtest, None, 0)  # cancel this timer if pending
    setup = quarkx.setupsubset(SS_GENERAL, "OpenGL")

    if wnd is not None:
        if force or wnd.owner is not editor.form:
            wnd.onclose = None
            close()
            onclose1(wnd)

    if wnd is None:
        if setup["Warning2"]:
            if quarkx.msgbox(Strings[-104], MT_WARNING, MB_YES|MB_NO) != MR_YES:
                raise quarkx.abort
        floating = editor.form.newfloating(FWF_NOESCCLOSE, "OpenGL 3D")
        view = floating.mainpanel.newmapview()
        view.info = {"type": "3D", "viewname": "opengl3Dview"}
        view.viewmode = "opengl"
        setprojmode(view)
        floating.onclose = onclose1   # so that onclose1 is called when the window is closed
        wnd = floating
        glview = view
        clearviewdeps()
        if bkgnd:
            sw = quarkx.screenrect()[2]   # screen rightmost coordinate
            wnd.windowrect = (sw+128, 0, sw+448, 200)
            wnd.rect = (minx or 320, miny or 200)
        else:
            r = setup["WndRect"]
            if safecheckrect(r):
                wnd.windowrect = r
                r = r[2:]
            else:
                r = (320,200)
            wnd.rect = (max(r[0],minx), max(r[1],miny))
        offscreen = bkgnd
        floating.show()
        if bkgnd:
            editor.form.macro("FOCU")    # gives the focus to the map editor window

    else:
        if not offscreen and bkgnd==2:
            r = wnd.windowrect
            r = r[:2] + wnd.rect
            setup["WndRect"] = r
            sw = quarkx.screenrect()[2]   # screen rightmost coordinate
            wnd.windowrect = (sw+128, 0, sw+448, 200)
            r = r[2:]
            offscreen = 1
        elif offscreen and not bkgnd:
            r = setup["WndRect"]
            if not safecheckrect(r):
                r = (0,0,512,384)
            wnd.windowrect = r
            r = r[2:]
            offscreen = 0
        else:
            r = wnd.rect
        r = (max(r[0],minx), max(r[1],miny))
        if r != wnd.rect:
            wnd.rect = r
            glview.waitforopengl()


def grayimage(view, *args):
    cv = view.canvas()
    cv.brushcolor = 0x604040
    w,h = view.clientarea
    cv.rectangle(-1,-1,w,h)

def clearviewdeps():
    # sets or resets the OpenGL view's parameters
    v = glview
    v.ondrop = v.onmouse = lambda *args: None
    v.ondraw = grayimage
    v.cursor = CR_ARROW

def safecheckrect(r):
    sw = quarkx.screenrect()[2]   # screen rightmost coordinate
    return type(r) is type(()) and r[0]<sw

def close():
    # close the OpenGL window.
    if wnd is not None:
        wnd.close()


#def deadtest(*reserved):
#    # check if the OpenGL window is still in use
#    if BaseLayout.CurrentOpenGLOwner is None:
#        close()


def onclose1(floating):
    # called by the Delphi code when the window is closed
    global wnd, glview
    if BaseLayout.CurrentOpenGLOwner is not None:
        BaseLayout.CurrentOpenGLOwner.releaseOpenGL()
    wnd = glview = None
    setup = quarkx.setupsubset(SS_GENERAL, "OpenGL")
    if not offscreen:
        r = floating.windowrect
        r = r[:2] + floating.rect
        setup["WndRect"] = r
    setup["Warning2"] = ""


def setupchanged(level):
    if level>=5 and wnd is not None:   # change in the configuration dialog box
        setprojmode(glview)

SetupRoutines.append(setupchanged)

# ----------- REVISION HISTORY ------------
#
#
#$Log$
#Revision 1.8  2005/10/15 00:47:57  cdunde
#To reinstate headers and history
#
#Revision 1.5  2000/06/02 16:00:22  alexander
#added cvs headers
#
#
#