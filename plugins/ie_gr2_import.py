# Two lines below to stop encoding errors in the console.
#!/usr/bin/python
# -*- coding: ascii -*-

"""   QuArK  -  Quake Army Knife

QuArK Model Editor importer for Doom3\Quake4 .md5mesh and .md5anim model files.
"""
#
# THIS FILE IS PROTECTED BY THE GNU GENERAL PUBLIC LICENCE
# FOUND IN FILE "COPYING.TXT"
#

#$Header$


Info = {
   "plug-in":       "ie_md5_importer",
   "desc":          "This script imports a Doom3\Quake4 .md5mesh and .md5anim model file, textures, and animations into QuArK for editing. Original code from Blender, md5Import_0.5.py, author - Bob Holcomb.",
   "date":          "Dec 5 2008",
   "author":        "cdunde & DanielPharos",
   "author e-mail": "cdunde@sbcglobal.net",
   "quark":         "Version 6.6.0 Beta 2" }

######################################################
# Importing modules
######################################################

# Python specific modules import.
import sys, struct, os
from types import *
import quarkx
import quarkpy.qutils
import quarkpy.qhandles
import quarkpy.mdleditor
import quarkpy.mdlhandles
import quarkpy.mdlutils
import ie_utils
from os import path
from ie_utils import tobj
import math
from math import *
from quarkpy.qdictionnary import Strings
from quarkpy.qeditor import MapColor # Strictly needed for QuArK bones MapColor call.

# Globals
SS_MODEL = 3
gr2_mesh_path = None
gr2_anim_path = None
md5_model = None
md5_bones = None
md5_model_comps = []
logging = 0
importername = "ie_md5_import.py"
textlog = "md5_ie_log.txt"
editor = None
progressbar = None



######################################################
# Vector, Quaterion, Matrix math stuff-taken from
# Jiba's blender2cal3d script
######################################################

def quaternion2matrix(q):
    xx = q[0] * q[0]
    yy = q[1] * q[1]
    zz = q[2] * q[2]
    xy = q[0] * q[1]
    xz = q[0] * q[2]
    yz = q[1] * q[2]
    wx = q[3] * q[0]
    wy = q[3] * q[1]
    wz = q[3] * q[2]
    return [[1.0 - 2.0 * (yy + zz),       2.0 * (xy + wz),       2.0 * (xz - wy), 0.0],
            [      2.0 * (xy - wz), 1.0 - 2.0 * (xx + zz),       2.0 * (yz + wx), 0.0],
            [      2.0 * (xz + wy),       2.0 * (yz - wx), 1.0 - 2.0 * (xx + yy), 0.0],
            [0.0                  , 0.0                  , 0.0                  , 1.0]]

def matrix2quaternion(m):
    s = math.sqrt(abs(m[0][0] + m[1][1] + m[2][2] + m[3][3]))
    if s == 0.0:
        x = abs(m[2][1] - m[1][2])
        y = abs(m[0][2] - m[2][0])
        z = abs(m[1][0] - m[0][1])
        if   (x >= y) and (x >= z):
            return 1.0, 0.0, 0.0, 0.0
        elif (y >= x) and (y >= z):
            return 0.0, 1.0, 0.0, 0.0
        else:
            return 0.0, 0.0, 1.0, 0.0
    return quaternion_normalize([
        -(m[2][1] - m[1][2]) / (2.0 * s),
        -(m[0][2] - m[2][0]) / (2.0 * s),
        -(m[1][0] - m[0][1]) / (2.0 * s),
        0.5 * s,
        ])

def quaternion_normalize(q):
    l = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3])
    return q[0] / l, q[1] / l, q[2] / l, q[3] / l

def quaternion_multiply(q1, q2):
    r = [
            q2[3] * q1[0] + q2[0] * q1[3] + q2[1] * q1[2] - q2[2] * q1[1],
            q2[3] * q1[1] + q2[1] * q1[3] + q2[2] * q1[0] - q2[0] * q1[2],
            q2[3] * q1[2] + q2[2] * q1[3] + q2[0] * q1[1] - q2[1] * q1[0],
            q2[3] * q1[3] - q2[0] * q1[0] - q2[1] * q1[1] - q2[2] * q1[2],
        ]
    d = math.sqrt(r[0] * r[0] + r[1] * r[1] + r[2] * r[2] + r[3] * r[3])
    r[0] /= d
    r[1] /= d
    r[2] /= d
    r[3] /= d
    return r

def matrix_translate(m, v):
    v = v.tuple
    m[3][0] += v[0]
    m[3][1] += v[1]
    m[3][2] += v[2]
    return m

def matrix_multiply(b, a):
    return [ [
        a[0][0] * b[0][0] + a[0][1] * b[1][0] + a[0][2] * b[2][0],
        a[0][0] * b[0][1] + a[0][1] * b[1][1] + a[0][2] * b[2][1],
        a[0][0] * b[0][2] + a[0][1] * b[1][2] + a[0][2] * b[2][2],
        0.0,
        ], [
        a[1][0] * b[0][0] + a[1][1] * b[1][0] + a[1][2] * b[2][0],
        a[1][0] * b[0][1] + a[1][1] * b[1][1] + a[1][2] * b[2][1],
        a[1][0] * b[0][2] + a[1][1] * b[1][2] + a[1][2] * b[2][2],
        0.0,
        ], [
        a[2][0] * b[0][0] + a[2][1] * b[1][0] + a[2][2] * b[2][0],
        a[2][0] * b[0][1] + a[2][1] * b[1][1] + a[2][2] * b[2][1],
        a[2][0] * b[0][2] + a[2][1] * b[1][2] + a[2][2] * b[2][2],
         0.0,
        ], [
        a[3][0] * b[0][0] + a[3][1] * b[1][0] + a[3][2] * b[2][0] + b[3][0],
        a[3][0] * b[0][1] + a[3][1] * b[1][1] + a[3][2] * b[2][1] + b[3][1],
        a[3][0] * b[0][2] + a[3][1] * b[1][2] + a[3][2] * b[2][2] + b[3][2],
        1.0,
        ] ]

def matrix_invert(m):
    det = (m[0][0] * (m[1][1] * m[2][2] - m[2][1] * m[1][2])
         - m[1][0] * (m[0][1] * m[2][2] - m[2][1] * m[0][2])
         + m[2][0] * (m[0][1] * m[1][2] - m[1][1] * m[0][2]))
    if det == 0.0:
        return None
    det = 1.0 / det
    r = [ [
        det * (m[1][1] * m[2][2] - m[2][1] * m[1][2]),
      - det * (m[0][1] * m[2][2] - m[2][1] * m[0][2]),
        det * (m[0][1] * m[1][2] - m[1][1] * m[0][2]),
        0.0,
      ], [
      - det * (m[1][0] * m[2][2] - m[2][0] * m[1][2]),
        det * (m[0][0] * m[2][2] - m[2][0] * m[0][2]),
      - det * (m[0][0] * m[1][2] - m[1][0] * m[0][2]),
        0.0
      ], [
        det * (m[1][0] * m[2][1] - m[2][0] * m[1][1]),
      - det * (m[0][0] * m[2][1] - m[2][0] * m[0][1]),
        det * (m[0][0] * m[1][1] - m[1][0] * m[0][1]),
        0.0,
      ] ]
    r.append([
      -(m[3][0] * r[0][0] + m[3][1] * r[1][0] + m[3][2] * r[2][0]),
      -(m[3][0] * r[0][1] + m[3][1] * r[1][1] + m[3][2] * r[2][1]),
      -(m[3][0] * r[0][2] + m[3][1] * r[1][2] + m[3][2] * r[2][2]),
      1.0,
      ])
    return r

def matrix_rotate_x(angle):
    cos = math.cos(angle)
    sin = math.sin(angle)
    return [
        [1.0,  0.0, 0.0, 0.0],
        [0.0,  cos, sin, 0.0],
        [0.0, -sin, cos, 0.0],
        [0.0,  0.0, 0.0, 1.0],
    ]

def matrix_rotate_y(angle):
    cos = math.cos(angle)
    sin = math.sin(angle)
    return [
        [cos, 0.0, -sin, 0.0],
        [0.0, 1.0,  0.0, 0.0],
        [sin, 0.0,  cos, 0.0],
        [0.0, 0.0,  0.0, 1.0],
    ]

def matrix_rotate_z(angle):
    cos = math.cos(angle)
    sin = math.sin(angle)
    return [
        [ cos, sin, 0.0, 0.0],
        [-sin, cos, 0.0, 0.0],
        [ 0.0, 0.0, 1.0, 0.0],
        [ 0.0, 0.0, 0.0, 1.0],
    ]

def matrix_rotate(axis, angle):
    vx  = axis[0]
    vy  = axis[1]
    vz  = axis[2]
    vx2 = vx * vx
    vy2 = vy * vy
    vz2 = vz * vz
    cos = math.cos(angle)
    sin = math.sin(angle)
    co1 = 1.0 - cos
    return [
        [vx2 * co1 + cos,          vx * vy * co1 + vz * sin, vz * vx * co1 - vy * sin, 0.0],
        [vx * vy * co1 - vz * sin, vy2 * co1 + cos,          vy * vz * co1 + vx * sin, 0.0],
        [vz * vx * co1 + vy * sin, vy * vz * co1 - vx * sin, vz2 * co1 + cos,          0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]

def matrix_scale(fx, fy, fz):
  return [
        [ fx, 0.0, 0.0, 0.0],
        [0.0,  fy, 0.0, 0.0],
        [0.0, 0.0,  fz, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]

def point_by_matrix(p, m):
  return [
        p[0] * m[0][0] + p[1] * m[1][0] + p[2] * m[2][0] + m[3][0],
        p[0] * m[0][1] + p[1] * m[1][1] + p[2] * m[2][1] + m[3][1],
        p[0] * m[0][2] + p[1] * m[1][2] + p[2] * m[2][2] + m[3][2]
    ]

def point_distance(p1, p2):
  return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2 + (p2[2] - p1[2]) ** 2)

def vector_by_matrix(p, m):
  return [
        p[0] * m[0][0] + p[1] * m[1][0] + p[2] * m[2][0],
        p[0] * m[0][1] + p[1] * m[1][1] + p[2] * m[2][1],
        p[0] * m[0][2] + p[1] * m[1][2] + p[2] * m[2][2]
    ]

def vector_length(v):
    v = v.tuple
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length == 0.0:
        length = 1.0
    return length

def vector_normalize(v):
    v = v.tuple
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    try:
        return v[0] / l, v[1] / l, v[2] / l
    except:
        return 1, 0, 0

def vector_dotproduct(v1, v2):
    v1 = v1.tuple
    v2 = v2.tuple
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]

def vector_crossproduct(v1, v2):
    v1 = v1.tuple
    v2 = v2.tuple
    return [
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0],
    ]

def vector_angle(v1, v2):
    s = vector_length(v1) * vector_length(v2)
    f = vector_dotproduct(v1, v2) / s
    if f >=  1.0:
        return 0.0
    if f <= -1.0:
        return math.pi / 2.0
    return math.atan(-f / math.sqrt(1.0 - f * f)) + math.pi / 2.0


######################################################
# MD5 Data structures
######################################################


class md5_vert:
    vert_index=0
    co=[]
    uvco=[]
    blend_index=0
    blend_count=0

    def __init__(self):
        self.vert_index=0
        self.co=[0.0]*3
        self.uvco=[0.0]*2
        self.blend_index=0
        self.blend_count=0

    def dump(self):
        print "vert index: ", self.vert_index
        print "co: ", self.co
        print "uvco: ", self.uvco
        print "blend index: ", self.blend_index
        print "belnd count: ", self.blend_count

class md5_weight:
    weight_index=0
    bone_index=0
    bias=0.0
    weights=[]

    def __init__(self):
        self.weight_index=0
        self.bone_index=0
        self.bias=0.0
        self.weights=[0.0]*3

    def dump(self):
        print "weight index: ", self.weight_index
        print "bone index: ", self.bone_index
        print "bias: ", self.bias
        print "weighst: ", self.weights

class md5_bone:
    bone_index=0
    name=""
    bindpos=[]
    bindmat=[]
    parent=""
    parent_index=0
    blenderbone=None
    roll=0

    def __init__(self):
        self.bone_index=0
        self.name=""
        self.bindpos=[0.0]*3
        self.bindmat=[None]*3 # This how you initilize a 2d-array.
        for i in range(3):
            self.bindmat[i] = [0.0]*3
        self.parent=""
        self.parent_index=0
        self.blenderbone=None

    def dump(self):
        print "bone index: ", self.bone_index
        print "name: ", self.name
        print "bind position: ", self.bindpos
        print "bind translation matrix (mat): ", self.bindmat
        print "parent: ", self.parent
        print "parent index: ", self.parent_index
        print "blenderbone: ", self.blenderbone


class md5_tri:
    tri_index=0
    vert_index=[]

    def __init__(self):
        self.tri_index=0;
        self.vert_index=[0]*3

    def dump(self):
        print "tri index: ", self.tri_index
        print "vert index: ", self.vert_index

class md5_mesh:
    mesh_index=0
    verts=[]
    tris=[]
    weights=[]
    shader=""

    def __init__(self):
        self.mesh_index=0
        self.verts=[]
        self.tris=[]
        self.weights=[]
        self.shader=""

    def dump(self):
        print "mesh index: ", self.mesh_index
        print "verts: ", self.verts
        print "tris: ", self.tris
        print "weights: ", self.weights
        print "shader: ", self.shader

######################################################
# IMPORT A FILE
######################################################


# def load_gr2mesh(md5_filename, basepath): # Change md5_filename to gr2_filename where needed below, then remove this reminder.
def load_gr2mesh(gr2_filename, basepath):
    global md5_model, md5_model_comps, md5_bones, progressbar, tobj, logging, Strings # Change global names where needed.

    ### This area is where we make the different elements of a QuArK Component, for each Component.
    # First we check for any other "Import Component"s,
    # if so we name the first component 1 more then the largest number
    # and increase each following component by 1.
    CompNbr = "None"
    comparenbr = 0
    for item in editor.Root.dictitems:
        if editor.Root.dictitems[item].shortname.startswith('Import Component'):
            getnbr = editor.Root.dictitems[item].shortname
            getnbr = getnbr.replace('Import Component', '')
            if getnbr == "":
               nbr = 0
            else:
                nbr = int(getnbr)
            if nbr > comparenbr:
                comparenbr = nbr
            nbr = comparenbr + 1
            CompNbr = nbr
    if CompNbr != "None":
        pass
    else:
        CompNbr = 1

    ComponentList = []
    message = ""
    QuArK_bones = []         # A list to store all QuArK bones created from the .md5mesh file "joints" section.
                             # [ bone1, bone2,...]
    QuArK_weights_list = {}  # A list to store all QuArK  "weights" created from the .md5mesh "verts" section for each mesh.
                             # {mesh_index : vert_index :[weight_index, nbr_of_weights]}

    # Use grnreader.exe in QuArK's dll folder to create the temoary output.ms file and place it there also to be read in below.
    filename = "\"" + gr2_filename + "\""
    cmdline = 'grnreader ' + filename
    fromdir = quarkx.exepath + "dlls"
    process = quarkx.runprogram(cmdline, fromdir)
    # read the file in
    # md5_filename = the full path and file name of the .md5mesh file being imported, ex.
    # "C:\Program Files\Doom 3\base\models\md5\monsters\pinky\pinky.md5mesh"
    tempfile = quarkx.exepath + "dlls/output.ms"
    tempfile = tempfile.replace("\\", "/")
    goahead = 0
    while not goahead:
        try:
            file = open(tempfile,"rw")
        except:
            quarkx.wait(100)
        else:
            goahead = 1
    file = open(tempfile,"r")
    lines = file.readlines()
    file.close()
    # Comment out the line below to save the output.ms file,
    # but the file needs to be renamed or deleted before new import.
    os.remove(quarkx.exepath + "dlls/output.ms")

    md5_model = []
    md5_bones = []

    num_lines = len(lines)

    filename = filename.strip("\"")
    filename = filename.split("\\")[-1]
    filename = filename.replace(".gr2", "")
    mesh_counter = 0
    comp_mesh = ()
    frame = framesgroup = skinsize = Tris = Component = sdogroup = skingroup = None
    for line_counter in range(0,num_lines):
        current_line = lines[line_counter]
        words = current_line.split()
        if len(words) < 3:
            continue
        ### New component starts here.
        if words and words[2] == "mesh":
            if frame is not None and len(frame_vertices) != 0:
                frame['Vertices'] = frame_vertices
                framesgroup.appenditem(frame)
                Component['skinsize'] = skinsize
                Component['Tris'] = Tris
                Component['show'] = chr(1)
                sdogroup = quarkx.newobj('SDO:sdo')
                Component.appenditem(sdogroup)
                Component.appenditem(skingroup)
                Component.appenditem(framesgroup)
                ComponentList = ComponentList + [Component]
                mesh_counter += 1
            frame_vertices = ()
            conversion_list = {}
            Component = quarkx.newobj(filename + "_" + str(mesh_counter) + ':mc')
            framesgroup = quarkx.newobj('Frames:fg') # QuArK Frames group made here.
            frame = quarkx.newobj(filename + "_" + str(mesh_counter) + ' meshframe' + ':mf') # QuArK frame made here.
            comp_mesh = ()
            comp_vertsUV = []
            Tris = ''
            ### Creates this component's Skins:sg group.
            skinsize = (256, 256)
            skingroup = quarkx.newobj('Skins:sg')
            skingroup['type'] = chr(2)
        # QuArK Component Vertices U,V list (for Tris below) made here.
        elif words and words[0] == "setTVert":
            U, V, W = words[3].split(",") # W is not used for 2D texture coordinates.
            U = U.replace("[", "")
            # As a percentage of the QuArK Skinview1.clientarea for X and Y.
            U = float(U) * skinsize[0]
            V = -float(V) * skinsize[1]
            v = (U, V)
            comp_vertsUV = comp_vertsUV + [v]
        # QuArK frame Vertices made here.
        elif words and words[0] == "setVert":
            x, y, z = words[3].split(",")
            x = x.replace("[", "")
            z = z.replace("]", "")
            x = float(x)
            y = float(y)
            z = float(z)
            comp_mesh = comp_mesh + (x, y, z)
        # QuArK Tris made here.
        elif words and words[0] == "setFace":
            vert_index0, vert_index1, vert_index2 = words[3].split(",")
            vert_index0 = vert_index0.replace("[", "")
            vert_index2 = vert_index2.replace("]", "")
            vert_index0 = int(vert_index0)-1
            if not conversion_list.has_key(vert_index0):
                fixed_vert_index0 = len(frame_vertices) / 3
                frame_vertices = frame_vertices + (comp_mesh[vert_index0*3],comp_mesh[vert_index0*3+1],comp_mesh[vert_index0*3+2],)
                conversion_list[vert_index0] = fixed_vert_index0
            else:
                fixed_vert_index0 = conversion_list[vert_index0]
            vert_index1 = int(vert_index1)-1
            if not conversion_list.has_key(vert_index1):
                fixed_vert_index1 = len(frame_vertices) / 3
                frame_vertices = frame_vertices + (comp_mesh[vert_index1*3],comp_mesh[vert_index1*3+1],comp_mesh[vert_index1*3+2],)
                conversion_list[vert_index1] = fixed_vert_index1
            else:
                fixed_vert_index1 = conversion_list[vert_index1]
            vert_index2 = int(vert_index2)-1
            if not conversion_list.has_key(vert_index2):
                fixed_vert_index2 = len(frame_vertices) / 3
                frame_vertices = frame_vertices + (comp_mesh[vert_index2*3],comp_mesh[vert_index2*3+1],comp_mesh[vert_index2*3+2],)
                conversion_list[vert_index2] = fixed_vert_index2
            else:
                fixed_vert_index2 = conversion_list[vert_index2]
            Tris = Tris + struct.pack("Hhh", fixed_vert_index0, comp_vertsUV[vert_index0][0], comp_vertsUV[vert_index0][1])
            Tris = Tris + struct.pack("Hhh", fixed_vert_index1, comp_vertsUV[vert_index1][0], comp_vertsUV[vert_index1][1])
            Tris = Tris + struct.pack("Hhh", fixed_vert_index2, comp_vertsUV[vert_index2][0], comp_vertsUV[vert_index2][1])

   # os.remove(tempfile) ### Uncomment this line when importer is completed.
    ### Line below just temp while making importer.
    return ComponentList, QuArK_bones, message

    #figure out the base pose for each vertex from the weights
    bone_vtx_list = {} # { bone_index : { mesh_index : [ vtx, vtx, vtx ...] } }
    ModelComponentList = {} # { mesh_index : { bone_index : {vtx_index : {'color': '\x00\x00\xff', weight: 1.0} } } }
    for mesh in md5_model:
       # mesh.dump()
        for vert_counter in range(0, len(mesh.verts)):
            blend_index=mesh.verts[vert_counter].blend_index
            for blend_counter in range(0, mesh.verts[vert_counter].blend_count):
                #get the current weight info
                w=mesh.weights[blend_index+blend_counter]
                weight_index = blend_index+blend_counter
                weight_value = md5_model[mesh.mesh_index].weights[weight_index].bias
                bonename = md5_bones[w.bone_index].name + ":bone"
                # QuArK code.
                if md5_model[mesh.mesh_index].verts[vert_counter].blend_count != 1:
                    if not QuArK_weights_list.has_key(mesh.mesh_index):
                        QuArK_weights_list[mesh.mesh_index] = {}
                    if not QuArK_weights_list[mesh.mesh_index].has_key(vert_counter):
                        QuArK_weights_list[mesh.mesh_index][vert_counter] = {}
                    QuArK_weights_list[mesh.mesh_index][vert_counter][bonename] = {}
                    QuArK_weights_list[mesh.mesh_index][vert_counter][bonename]['weight_value'] = weight_value
                    color = quarkpy.mdlutils.weights_color(editor, weight_value)
                    QuArK_weights_list[mesh.mesh_index][vert_counter][bonename]['color'] = color
                    QuArK_weights_list[mesh.mesh_index][vert_counter][bonename]['weight_index'] = weight_index

                #w.dump()
                #the bone that the current weight is refering to
                b=md5_bones[w.bone_index]
                if not mesh.mesh_index in ModelComponentList.keys():
                    ModelComponentList[mesh.mesh_index] = {}
                if not w.bone_index in ModelComponentList[mesh.mesh_index].keys():
                    ModelComponentList[mesh.mesh_index][w.bone_index] = {}
                if not vert_counter in ModelComponentList[mesh.mesh_index][w.bone_index].keys():
                    ModelComponentList[mesh.mesh_index][w.bone_index][vert_counter] = {}
                if not w.bone_index in bone_vtx_list.keys():
                    bone_vtx_list[w.bone_index] = {}
                if not mesh.mesh_index in bone_vtx_list[w.bone_index].keys():
                    bone_vtx_list[w.bone_index][mesh.mesh_index] = []
                if not vert_counter in bone_vtx_list[w.bone_index][mesh.mesh_index]:
                    bone_vtx_list[w.bone_index][mesh.mesh_index] = bone_vtx_list[w.bone_index][mesh.mesh_index] + [vert_counter]
                #print "b: "
                #b.dump()
                #a position is the weight position * bone transform matrix (or position)
                pos=[0.0]*3
                #print "pos: ", pos
                pos= vector_by_matrix(w.weights, b.bindmat)
                #print "pos: ", pos
                #print "w.bias: ", w.bias
                #print "b.bindpos: ", b.bindpos
                pos=((pos[0]+b.bindpos[0])*w.bias, (pos[1]+b.bindpos[1])*w.bias, (pos[2]+b.bindpos[2])*w.bias)
                #print "pos: ", pos
                #vertex position is sum of all weight info adjusted for bias
                mesh.verts[vert_counter].co[0]+=pos[0]
                mesh.verts[vert_counter].co[1]+=pos[1]
                mesh.verts[vert_counter].co[2]+=pos[2]

    # Used for QuArK progressbar.
    firstcomp = str(CompNbr)
    lastcomp = str(CompNbr + len(md5_model)-1)

    # basepath = The full path to the game folder, ex: "C:\Program Files\Doom 3\base\"
    for mesh in md5_model: # A new QuArK component needs to be made for each mesh.
        ### Creates this component's Skins:sg group.
        # Checks if the model has textures specified with it.
        skinsize = (256, 256)
        skingroup = quarkx.newobj('Skins:sg')
        skingroup['type'] = chr(2)
        if(mesh.shader!=""): # Make the QuArK Skins here
            path = mesh.shader.split("\\")
            path = path[len(path)-1] # This is the full shader we are looking for, ex: "models/monsters/pinky/pinky_metal"
            shaderspath = basepath + "materials"
            shaderfiles = os.listdir(shaderspath)
            for shaderfile in shaderfiles:
                noimage = ""
                foundshader = foundtexture = foundimage = imagefile = None
                mesh_shader = shader_file = shader_name = shader_keyword = qer_editorimage = diffusemap = map = bumpmap = addnormals = heightmap = specularmap = None
                #read the file in
                try: # To by pass sub-folders, should make this to check those also.
                    file=open(shaderspath+"/"+shaderfile,"r")
                except:
                    continue
                lines=file.readlines()
                file.close()
                left_cur_braket = 0
                for line in range(len(lines)):
                    if foundshader is None and lines[line].startswith(mesh.shader+"\n"):
                        shaderline = lines[line].replace(chr(9), "    ")
                        shaderline = shaderline.rstrip()
                        mesh_shader = "\r\n" + shaderline + "\r\n"
                        shader_file = shaderspath + "/" + shaderfile
                        shader_name = mesh.shader
                        foundshader = mesh.shader
                        left_cur_braket = 0
                        continue
                    if foundshader is not None and lines[line].find("{") != -1:
                        left_cur_braket = left_cur_braket + 1
                    if foundshader is not None and lines[line].find("}") != -1:
                        left_cur_braket = left_cur_braket - 1
                    if foundshader is not None:
                        if lines[line].find("qer_editorimage") != -1 or lines[line].find("diffusemap") != -1:
                            words = lines[line].split()
                            for word in words:
                                if word.endswith(".tga"):
                                    foundtexture = word
                                    if lines[line].find("qer_editorimage") != -1:
                                        shader_keyword = "qer_editorimage"
                                    else:
                                        shader_keyword = "diffusemap"
                                    skinname = foundtexture
                                    skin = quarkx.newobj(skinname)
                                    break
                                elif word.find("/") != -1 and (word.startswith("models") or word.startswith("textures")):
                                    foundtexture = word + ".tga"
                                    if lines[line].find("qer_editorimage") != -1:
                                        shader_keyword = "qer_editorimage"
                                    else:
                                        shader_keyword = "diffusemap"
                                    skinname = foundtexture
                                    skin = quarkx.newobj(skinname)
                                    break
                            if foundtexture is not None:
                                if os.path.isfile(basepath + foundtexture):
                                    foundimage = basepath + foundtexture
                                    image = quarkx.openfileobj(foundimage)
                                    skin['Image1'] = image.dictspec['Image1']
                                    skin['Size'] = image.dictspec['Size']
                                    skin['shader_keyword'] = shader_keyword
                                    skingroup.appenditem(skin)
                                    if skinsize == (256, 256):
                                        skinsize = skin['Size']
                                    foundtexture = None
                                else: # Keep looking in the shader files, the shader may be in another one.
                                    imagefile = basepath + foundtexture
                                    noimage = noimage + "\r\nFound needed shader for Import Component " + str(CompNbr) + ":\r\n    " + mesh.shader + "\r\n" + "in\r\n    " + shaderspath+"/"+shaderfile + "\r\n" + "and the 'diffusemap' image to display.\r\n    " + foundtexture + "\r\n" + "But that image file does not exist.\r\n"
                        if lines[line].find("bumpmap") != -1 and (not lines[line].find("addnormals") != -1 and not lines[line].find("heightmap") != -1):
                            words = lines[line].replace("("," ")
                            words = words.replace(")"," ")
                            words = words.replace(","," ")
                            words = words.split()
                            for word in words:
                                if word.endswith(".tga"):
                                    bumpmap = word
                                elif word.find("/") != -1 and (word.startswith("models") or word.startswith("textures")):
                                    bumpmap = word + ".tga"
                        if lines[line].find("addnormals") != -1 or lines[line].find("heightmap") != -1:
                            words = lines[line].replace("("," ")
                            words = words.replace(")"," ")
                            words = words.replace(","," ")
                            words = words.split()
                            for word in range(len(words)):
                                if words[word].find("addnormals") != -1 and words[word+1].find("/") != -1 and (words[word+1].startswith("models") or words[word+1].startswith("textures")):
                                    addnormals = words[word+1]
                                    if not addnormals.endswith(".tga"):
                                        addnormals = addnormals + ".tga"
                                if words[word].find("heightmap") != -1 and words[word+1].find("/") != -1 and (words[word+1].startswith("models") or words[word+1].startswith("textures")):
                                    heightmap = words[word+1]
                                    if not heightmap.endswith(".tga"):
                                        heightmap = heightmap + ".tga"
                        elif lines[line].find("specularmap") != -1:
                            words = lines[line].split()
                            for word in words:
                                if word.endswith(".tga"):
                                    specularmap = word
                                elif word.find("/") != -1 and (word.startswith("models") or word.startswith("textures")):
                                    specularmap = word + ".tga"
                        # Dec character code for space = chr(32), for tab = chr(9)
                        elif lines[line].find(chr(32)+"map") != -1 or lines[line].find(chr(9)+"map") != -1:
                            words = lines[line].split()
                            for word in words:
                                if word.endswith(".tga") and (word.startswith("models") or word.startswith("textures")) and ((not word.endswith("_dis.tga") and not word.endswith("_dis")) and (not word.endswith("dis2.tga") and not word.endswith("dis2"))):
                                    map = word
                                elif word.find("/") != -1 and (word.startswith("models") or word.startswith("textures")) and ((not word.endswith("_dis.tga") and not word.endswith("_dis")) and (not word.endswith("dis2.tga") and not word.endswith("dis2"))):
                                    map = word + ".tga"
                            if map is not None and not map in skingroup.dictitems.keys():
                                imagefile = basepath + map
                                if os.path.isfile(basepath + map):
                                    skinname = map
                                    foundimage = basepath + skinname
                                    shader_keyword = "map"
                                    # Make the skin and add it.
                                    skin = quarkx.newobj(skinname)
                                    image = quarkx.openfileobj(foundimage)
                                    skin['Image1'] = image.dictspec['Image1']
                                    skin['Size'] = image.dictspec['Size']
                                    skin['shader_keyword'] = shader_keyword
                                    skingroup.appenditem(skin)
                                    if skinsize == (256, 256):
                                        skinsize = skin['Size']
                                else:
                                    noimage = noimage + "\r\nFound needed shader for Import Component " + str(CompNbr) + ":\r\n    " + mesh.shader + "\r\n" + "in\r\n    " + shaderspath+"/"+shaderfile + "\r\n" + "but the texture image file it calls to display\r\n    " + imagefile + "\r\nis not there or has a different name.\r\nMake a copy of the file and rename it or\r\ncheck the shader and make a correction to add it.\r\n"
                        else:
                            if lines[line].find("/") != -1:
                                if lines[line-1].find("qer_editorimage") != -1 or lines[line-1].find("diffusemap") != -1 or lines[line-1].find("bumpmap") != -1 or lines[line-1].find("addnormals") != -1 or lines[line-1].find("heightmap") != -1 or lines[line-1].find("specularmap") != -1 or lines[line].find(chr(32)+"map") != -1 or lines[line].find(chr(9)+"map") != -1:
                                    words = lines[line].replace("("," ")
                                    words = words.replace(")"," ")
                                    words = words.replace(","," ")
                                    words = words.split()
                                    image = None
                                    for word in words:
                                        if word.endswith(".tga") and (word.startswith("models") or word.startswith("textures")) and ((not word.endswith("_dis.tga") and not word.endswith("_dis")) and (not word.endswith("dis2.tga") and not word.endswith("dis2"))):
                                            image = word
                                        elif word.find("/") != -1 and (word.startswith("models") or word.startswith("textures")) and ((not word.endswith("_dis.tga") and not word.endswith("_dis")) and (not word.endswith("dis2.tga") and not word.endswith("dis2"))):
                                            image = word + ".tga"
                                    if (image is not None) and (not image in skingroup.dictitems.keys()):
                                        words = lines[line-1].replace("("," ")
                                        words = words.replace(")"," ")
                                        words = words.replace(","," ")
                                        words = words.split()
                                        keys = [qer_editorimage, diffusemap, bumpmap, addnormals, heightmap, specularmap, map]
                                        words.reverse() # Work our way backwards to get the last key name first.
                                        for word in range(len(words)):
                                            if words[word] in keys:
                                                imagefile = basepath + image
                                                if os.path.isfile(basepath + image):
                                                    skinname = image
                                                    foundimage = basepath + skinname
                                                    shader_keyword = words[word]
                                                    # Make the skin and add it.
                                                    skin = quarkx.newobj(skinname)
                                                    image = quarkx.openfileobj(foundimage)
                                                    skin['Image1'] = image.dictspec['Image1']
                                                    skin['Size'] = image.dictspec['Size']
                                                    skin['shader_keyword'] = shader_keyword
                                                    skingroup.appenditem(skin)
                                                    if skinsize == (256, 256):
                                                        skinsize = skin['Size']
                                                else:
                                                    noimage = noimage + "\r\nFound needed shader for Import Component " + str(CompNbr) + ":\r\n    " + mesh.shader + "\r\n" + "in\r\n    " + shaderspath+"/"+shaderfile + "\r\n" + "but the texture image file it calls to display\r\n    " + imagefile + "\r\nis not there or has a different name.\r\nMake a copy of the file and rename it or\r\ncheck the shader and make a correction to add it.\r\n"
                        shaderline = lines[line].replace(chr(9), "    ")
                        shaderline = shaderline.rstrip()
                        if mesh_shader is not None:
                            mesh_shader = mesh_shader + shaderline + "\r\n"
                        if lines[line].find("}") != -1 and left_cur_braket == 0: # Done reading shader so break out of reading this file.
                            break
                if mesh_shader is not None:
                    if bumpmap is not None:
                        imagefile = basepath + bumpmap
                        if os.path.isfile(basepath + bumpmap):
                            skinname = bumpmap
                            foundimage = basepath + skinname
                            shader_keyword = "bumpmap"
                            # Make the skin and add it.
                            skin = quarkx.newobj(skinname)
                            image = quarkx.openfileobj(foundimage)
                            skin['Image1'] = image.dictspec['Image1']
                            skin['Size'] = image.dictspec['Size']
                            skin['shader_keyword'] = shader_keyword
                            skingroup.appenditem(skin)
                            if skinsize == (256, 256):
                                skinsize = skin['Size']
                        else:
                            noimage = noimage + "\r\nFound needed shader for Import Component " + str(CompNbr) + ":\r\n    " + mesh.shader + "\r\n" + "in\r\n    " + shaderspath+"/"+shaderfile + "\r\n" + "but the texture image file it calls to display\r\n    " + imagefile + "\r\nis not there or has a different name.\r\nMake a copy of the file and rename it or\r\ncheck the shader and make a correction to add it.\r\n"
                    if addnormals is not None:
                        imagefile = basepath + addnormals
                        if os.path.isfile(basepath + addnormals):
                            skinname = addnormals
                            foundimage = basepath + skinname
                            shader_keyword = "addnormals"
                            # Make the skin and add it.
                            skin = quarkx.newobj(skinname)
                            image = quarkx.openfileobj(foundimage)
                            skin['Image1'] = image.dictspec['Image1']
                            skin['Size'] = image.dictspec['Size']
                            skin['shader_keyword'] = shader_keyword
                            skingroup.appenditem(skin)
                            if skinsize == (256, 256):
                                skinsize = skin['Size']
                        else:
                            noimage = noimage + "\r\nFound needed shader for Import Component " + str(CompNbr) + ":\r\n    " + mesh.shader + "\r\n" + "in\r\n    " + shaderspath+"/"+shaderfile + "\r\n" + "but the texture image file it calls to display\r\n    " + imagefile + "\r\nis not there or has a different name.\r\nMake a copy of the file and rename it or\r\ncheck the shader and make a correction to add it.\r\n"
                    if heightmap is not None:
                        imagefile = basepath + heightmap
                        if os.path.isfile(basepath + heightmap):
                            skinname = heightmap
                            foundimage = basepath + skinname
                            shader_keyword = "heightmap"
                            # Make the skin and add it.
                            skin = quarkx.newobj(skinname)
                            image = quarkx.openfileobj(foundimage)
                            skin['Image1'] = image.dictspec['Image1']
                            skin['Size'] = image.dictspec['Size']
                            skin['shader_keyword'] = shader_keyword
                            skingroup.appenditem(skin)
                            if skinsize == (256, 256):
                                skinsize = skin['Size']
                        else:
                            noimage = noimage + "\r\nFound needed shader for Import Component " + str(CompNbr) + ":\r\n    " + mesh.shader + "\r\n" + "in\r\n    " + shaderspath+"/"+shaderfile + "\r\n" + "but the texture image file it calls to display\r\n    " + imagefile + "\r\nis not there or has a different name.\r\nMake a copy of the file and rename it or\r\ncheck the shader and make a correction to add it.\r\n"
                    if specularmap is not None:
                        imagefile = basepath + specularmap
                        if os.path.isfile(basepath + specularmap):
                            skinname = specularmap
                            foundimage = basepath + skinname
                            shader_keyword = "specularmap"
                            # Make the skin and add it.
                            skin = quarkx.newobj(skinname)
                            image = quarkx.openfileobj(foundimage)
                            skin['Image1'] = image.dictspec['Image1']
                            skin['Size'] = image.dictspec['Size']
                            skin['shader_keyword'] = shader_keyword
                            skingroup.appenditem(skin)
                            if skinsize == (256, 256):
                                skinsize = skin['Size']
                        else:
                            noimage = noimage + "\r\nFound needed shader for Import Component " + str(CompNbr) + ":\r\n    " + mesh.shader + "\r\n" + "in\r\n    " + shaderspath+"/"+shaderfile + "\r\n" + "but the texture image file it calls to display\r\n    " + imagefile + "\r\nis not there or has a different name.\r\nMake a copy of the file and rename it or\r\ncheck the shader and make a correction to add it.\r\n"
                    if imagefile is None:
                        imagefile = "NO IMAGE FILE FOUND AT ALL, CHECK THE SHADER."
                    break
                if foundshader is not None: # Found the shader so break out of the shader files loop.
                    break
            if len(noimage) > 0:
                message = message + noimage
            if mesh.shader is not None and foundshader is None: # This component has an image but no shader was found, so...
                texturepath = basepath + "/" + mesh.shader + ".tga"
                if os.path.isfile(texturepath): # May not be a shader so we look for a texture with the same image name.
                    skinname = mesh.shader + ".tga"
                    skin = quarkx.newobj(skinname)
                    foundimage = basepath + skinname
                    image = quarkx.openfileobj(foundimage)
                    skin['Image1'] = image.dictspec['Image1']
                    skin['Size'] = image.dictspec['Size']
                    skingroup.appenditem(skin)
                    if skinsize == (256, 256):
                        skinsize = skin['Size']
                else: # If no texture is found then we are missing the shader.
                    message = message + "\r\nImport Component " + str(CompNbr) + " calls for the shader:\r\n    " + mesh.shader + "\r\n" + "but it could not be located in\r\n    " + shaderspath + "\r\n" + "Extract shader file to this folder\r\nor create a shader file if needed.\r\n"

        # QuArK Frames group, frames and frame vertices section.
        framesgroup = quarkx.newobj('Frames:fg') # QuArK Frames group made here.
        frame = quarkx.newobj('meshframe' + ':mf') # QuArK frame made here.
        comp_mesh = ()
        comp_verts = []
        for vert in mesh.verts: # QuArK frame Vertices made here.
                comp_mesh = comp_mesh + (vert.co[0], vert.co[1], vert.co[2])
                #add the uv coords to the vertex
                # As a percentage of the QuArK Skinview1.clientarea for X and Y.
                U = int(skinsize[0] * vert.uvco[0])
                V = int(skinsize[1] * vert.uvco[1])
                V = -V + skinsize[1]
                v = (U, V)
                #add the vertex to the mesh
                comp_verts = comp_verts + [v]
        frame['Vertices'] = comp_mesh
        framesgroup.appenditem(frame)

        # Now we start creating our Import Component and name it.
        if shader_name is not None:
            Comp_name = shader_name.split("/")
            Comp_name = Comp_name[len(Comp_name)-1]
            Component = quarkx.newobj(Comp_name + ':mc')
        else:
            Component = quarkx.newobj("Import Component " + str(CompNbr) + ':mc')
            CompNbr = CompNbr + 1
        md5_model_comps = md5_model_comps + [Component.name]
        if mesh.mesh_index == 0:
            for bone in QuArK_bones:
                bone['component'] = Component.name
                # This next line preserves origianl handle scale setting for each bone.
                bone['org_scale'] = bone.dictspec['scale']
        if shader_file is not None:
            Component['shader_file'] = shader_file
        if shader_name is not None:
            Component['shader_name'] = shader_name
        if mesh_shader is not None:
            Component['mesh_shader'] = mesh_shader
        Component['skinsize'] = skinsize
        Component['Tris'] = Tris
        Component['show'] = chr(1)
        sdogroup = quarkx.newobj('SDO:sdo')
        Component.appenditem(sdogroup)
        Component.appenditem(skingroup)
        Component.appenditem(framesgroup)
        ComponentList = ComponentList + [Component]
    #    progressbar.close() # un-comment this line once progress bar is set up
    #    if len(polynames) > 1:
    #        Strings[2454] = Strings[2454].replace("Processing Components " + firstcomp + " to " + lastcomp + "\n" + "Import Component " + str(CompNbr) + "\n\n", "")
    #    else:
    #        Strings[2454] = Strings[2454].replace("Import Component " + str(CompNbr) + "\n", "")

    # Section below gives all the bones their bone.vtxlist and bone.vtx_pos is set to an empty dictionary to keep from pulling the bone off of its set position.
    for bone_index in range(len(QuArK_bones)):
        if bone_vtx_list.has_key(bone_index):
            temp_vtxlist = {}
            for mesh_index in bone_vtx_list[bone_index].keys():
                compkey = ComponentList[mesh_index].name
                temp_vtxlist[compkey] = bone_vtx_list[bone_index][mesh_index]
            QuArK_bones[bone_index].vtxlist = temp_vtxlist
            vtxcount = 0
            usekey = None
            for key in QuArK_bones[bone_index].vtxlist.keys():
                if len(QuArK_bones[bone_index].vtxlist[key]) > vtxcount:
                    usekey = key
                    vtxcount = len(QuArK_bones[bone_index].vtxlist[key])
            if usekey is not None:
                print "line 985 bone", QuArK_bones[bone_index].name
                print "line 986 vtxlist", QuArK_bones[bone_index].vtxlist
                print "line 987 vtxlist[usekey]", QuArK_bones[bone_index].vtxlist[usekey]
                temp = {}
                temp[usekey] = QuArK_bones[bone_index].vtxlist[usekey]
                QuArK_bones[bone_index].vtx_pos = temp
                for item in ComponentList:
                    if item.name == usekey:
                        comp = item
                        break
                vtxpos = quarkx.vect(0, 0, 0)
                frame = comp.dictitems['Frames:fg'].subitems[0]
                print "line 995 bone", QuArK_bones[bone_index].name
                print "line 996 vtx_pos", QuArK_bones[bone_index].vtx_pos
                for vtx in range(len(QuArK_bones[bone_index].vtx_pos[usekey])):
                    vtxpos = vtxpos + frame.vertices[QuArK_bones[bone_index].vtx_pos[usekey][vtx]]
                vtxpos = vtxpos/float(len(QuArK_bones[bone_index].vtx_pos[usekey]))
                print "line 1002 vtxpos", vtxpos, type(vtxpos)
                print "line 1003 position", QuArK_bones[bone_index].position, type(QuArK_bones[bone_index].position)
                QuArK_bones[bone_index]['draw_offset'] = (QuArK_bones[bone_index].position - vtxpos).tuple
                QuArK_bones[bone_index]['component'] = usekey
                print "line 1006 draw_offset", QuArK_bones[bone_index].dictspec['draw_offset']
                print "line 1007 component", QuArK_bones[bone_index].dictspec['component']
                    
    # Section below sets up the QuArK editor.ModelComponentList for each mesh.
    for mesh_index in ModelComponentList.keys():
        compname = ComponentList[mesh_index].name
        if not editor.ModelComponentList.has_key(compname):
            editor.ModelComponentList[compname] = {}
            editor.ModelComponentList[compname]['bonevtxlist'] = {}
        for bone_index in ModelComponentList[mesh_index].keys():
            bonename = QuArK_bones[bone_index].name
            if not editor.ModelComponentList[compname]['bonevtxlist'].has_key(bonename):
                editor.ModelComponentList[compname]['bonevtxlist'][bonename] = {}
            for vtx_index in ModelComponentList[mesh_index][bone_index].keys():
                editor.ModelComponentList[compname]['bonevtxlist'][bonename][vtx_index] = ModelComponentList[mesh_index][bone_index][vtx_index]
                editor.ModelComponentList[compname]['bonevtxlist'][bonename][vtx_index]['color'] = QuArK_bones[bone_index].dictspec['_color']
        if QuArK_weights_list.has_key(mesh_index) and len(QuArK_weights_list[mesh_index].keys()) != 0:
            if not editor.ModelComponentList[compname].has_key("weightvtxlist"):
                editor.ModelComponentList[compname]['weightvtxlist'] = {}
            for vertex in QuArK_weights_list[mesh_index].keys():
                if not editor.ModelComponentList[compname]['weightvtxlist'].has_key(vertex):
                    editor.ModelComponentList[compname]['weightvtxlist'][vertex] = QuArK_weights_list[mesh_index][vertex]

    return ComponentList, QuArK_bones, message # Gives a list of ALL bone as they are created, same as in the .md5mesh file.

class md5anim_bone:
    name = ""
    parent_index = 0
    flags = 0
    frameDataIndex = 0
    bindpos = []
    bindquat = []
    
    def __init__(self):
        name = ""
        self.bindpos=[0.0]*3
        self.bindquat=[0.0]*4
        self.parent_index = 0
        self.flags = 0
        self.frameDataIndex = 0

        
class md5anim:
    num_bones = 0
    md5anim_bones = []
    frameRate = 24
    numFrames = 0
    numAnimatedComponents = 0
    baseframe = []
    framedata = []

    def __init__(self):
        num_bones = 0
        md5anim_bones = []
        baseframe = []
        framedata = []
        
    def load_md5anim(self, md5_filename, bones=None): # bones = QuArK's "Skeleton:bg" folder to get our current bones from.
        file=open(md5_filename,"r")
        lines=file.readlines()
        file.close()

        num_lines=len(lines)

        for line_counter in range(0,num_lines):
            current_line=lines[line_counter]
            words=current_line.split()

            if words and words[0]=="numJoints":
                self.num_bones=int(words[1])

            elif words and words[0]=="numFrames":
                self.numFrames=int(words[1])
                self.framedata = [[]]*self.numFrames

            elif words and words[0]=="frameRate":
                self.frameRate=int(words[1])

            elif words and words[0]=="numAnimatedComponents":
                self.numAnimatedComponents=int(words[1])

            elif words and words[0]=="hierarchy":
                for bone_counter in range(0,self.num_bones):
                    #make a new bone
                    self.md5anim_bones.append(md5anim_bone())
                    #next line
                    line_counter+=1
                    current_line=lines[line_counter]
                    words=current_line.split()
                    #skip over blank lines
                    while not words:
                        line_counter+=1
                        current_line=lines[line_counter]
                        words=current_line.split()

                    #get rid of the quotes on either side
                    temp_name=str(words[0])
                    temp_name=temp_name[1:-1]
                    self.md5anim_bones[bone_counter].name=temp_name
                    self.md5anim_bones[bone_counter].parent_index = int(words[1])
                    self.md5anim_bones[bone_counter].flags = int(words[2])
                    self.md5anim_bones[bone_counter].frameDataIndex=int(words[3])

            elif words and words[0]=="baseframe":
                for bone_counter in range(0,self.num_bones):
                    line_counter+=1
                    current_line=lines[line_counter]
                    words=current_line.split()
                    #skip over blank lines
                    while not words:
                        line_counter+=1
                        current_line=lines[line_counter]
                        words=current_line.split()
                    self.md5anim_bones[bone_counter].bindpos[0]=float(words[1])
                    self.md5anim_bones[bone_counter].bindpos[1]=float(words[2])
                    self.md5anim_bones[bone_counter].bindpos[2]=float(words[3])
                    qx = float(words[6])
                    qy = float(words[7])
                    qz = float(words[8])
                    qw = 1 - qx*qx - qy*qy - qz*qz
                    if qw<0:
                        qw=0
                    else:
                        qw = -sqrt(qw)
                    self.md5anim_bones[bone_counter].bindquat = [qx,qy,qz,qw]

            elif words and words[0]=="frame":
                framenumber = int(words[1])
                self.framedata[framenumber]=[]
                line_counter+=1
                current_line=lines[line_counter]
                words=current_line.split()
                while words and not(words[0]=="frame" or words[0]=="}"):
                    for i in range(0, len(words)):
                        self.framedata[framenumber].append(float(words[i]))
                    line_counter+=1
                    current_line=lines[line_counter]
                    words=current_line.split()

    def apply(self, skelgroup, animfile):
        global editor
        filename = animfile.replace(".md5anim", "")
        #Construct baseframe data
        QuArK_baseframe_position_raw = [[]]*self.num_bones
        QuArK_baseframe_matrix_raw = [[]]*self.num_bones
        for bone_counter in range(0,self.num_bones):
            QuArK_baseframe_position_raw[bone_counter] = quarkx.vect((self.md5anim_bones[bone_counter].bindpos[0], self.md5anim_bones[bone_counter].bindpos[1], self.md5anim_bones[bone_counter].bindpos[2]))
            tempmatrix = quaternion2matrix(self.md5anim_bones[bone_counter].bindquat)
            QuArK_baseframe_matrix_raw[bone_counter] = quarkx.matrix(((tempmatrix[0][0], tempmatrix[1][0], tempmatrix[2][0]), (tempmatrix[0][1], tempmatrix[1][1], tempmatrix[2][1]), (tempmatrix[0][2], tempmatrix[1][2], tempmatrix[2][2])))
        #Construct animation frame data
        QuArK_frame_position_raw = [[]]*self.numFrames
        QuArK_frame_matrix_raw = [[]]*self.numFrames
        for frame_counter in range(0,self.numFrames):
            QuArK_frame_position_raw[frame_counter] = [[]]*self.num_bones
            QuArK_frame_matrix_raw[frame_counter] = [[]]*self.num_bones
            for bone_counter in range(0,self.num_bones):
                currentbone = self.md5anim_bones[bone_counter]
                lx, ly, lz = currentbone.bindpos
                (qx, qy, qz, qw) = currentbone.bindquat
                frameDataIndex = currentbone.frameDataIndex
                if (currentbone.flags & 1):
                    lx = self.framedata[frame_counter][frameDataIndex]
                    frameDataIndex+=1
                if (currentbone.flags & 2):
                    ly = self.framedata[frame_counter][frameDataIndex]
                    frameDataIndex+=1
                if (currentbone.flags & 4):
                    lz = self.framedata[frame_counter][frameDataIndex]
                    frameDataIndex+=1
                if (currentbone.flags & 8):
                    qx = self.framedata[frame_counter][frameDataIndex]
                    frameDataIndex+=1
                if (currentbone.flags & 16):
                    qy = self.framedata[frame_counter][frameDataIndex]
                    frameDataIndex+=1
                if (currentbone.flags & 32):
                    qz = self.framedata[frame_counter][frameDataIndex]
                qw = 1 - qx*qx - qy*qy - qz*qz
                if qw<0:
                    qw=0
                else:
                    qw = -sqrt(qw)
                QuArK_frame_position_raw[frame_counter][bone_counter] = quarkx.vect((lx, ly, lz))
                tempmatrix = quaternion2matrix([qx, qy, qz, qw])
                QuArK_frame_matrix_raw[frame_counter][bone_counter] = quarkx.matrix(((tempmatrix[0][0], tempmatrix[1][0], tempmatrix[2][0]), (tempmatrix[0][1], tempmatrix[1][1], tempmatrix[2][1]), (tempmatrix[0][2], tempmatrix[1][2], tempmatrix[2][2])))
        #Process baseframe data
        QuArK_baseframe_position = [[]]*self.num_bones
        QuArK_baseframe_matrix = [[]]*self.num_bones
        for bone_counter in range(0,self.num_bones):
            currentbone = self.md5anim_bones[bone_counter]
            if currentbone.parent_index < 0:
                QuArK_baseframe_position[bone_counter] = QuArK_baseframe_position_raw[bone_counter]
                QuArK_baseframe_matrix[bone_counter] = QuArK_baseframe_matrix_raw[bone_counter]
            else:
                MatrixParent = QuArK_baseframe_matrix[currentbone.parent_index]
                temppos = MatrixParent * QuArK_baseframe_position_raw[bone_counter]
                QuArK_baseframe_position[bone_counter] = QuArK_baseframe_position[currentbone.parent_index] + temppos
                QuArK_baseframe_matrix[bone_counter] = MatrixParent * QuArK_baseframe_matrix_raw[bone_counter]
        #Process animation frame data
        QuArK_frame_position = [[]]*self.numFrames
        QuArK_frame_matrix = [[]]*self.numFrames
        for frame_counter in range(0,self.numFrames):
            QuArK_frame_position[frame_counter] = [[]]*self.num_bones
            QuArK_frame_matrix[frame_counter] = [[]]*self.num_bones
            for bone_counter in range(0,self.num_bones):
                currentbone = self.md5anim_bones[bone_counter]
                if currentbone.parent_index < 0:
                    QuArK_frame_position[frame_counter][bone_counter] = QuArK_frame_position_raw[frame_counter][bone_counter]
                    QuArK_frame_matrix[frame_counter][bone_counter] = QuArK_frame_matrix_raw[frame_counter][bone_counter]
                else:
                    MatrixParent = QuArK_frame_matrix[frame_counter][currentbone.parent_index]
                    temppos = MatrixParent * QuArK_frame_position_raw[frame_counter][bone_counter]
                    QuArK_frame_position[frame_counter][bone_counter] = QuArK_frame_position[frame_counter][currentbone.parent_index] + temppos
                    QuArK_frame_matrix[frame_counter][bone_counter] = MatrixParent * QuArK_frame_matrix_raw[frame_counter][bone_counter]
        #Create baseframe
        for mesh_counter in range(len(md5_model)):
            currentmesh = md5_model[mesh_counter]
            oldframe = editor.Root.dictitems[md5_model_comps[mesh_counter]].dictitems['Frames:fg'].dictitems['meshframe:mf']
            baseframe = oldframe.copy()
            baseframe.shortname = filename + " baseframe"
            oldverts = baseframe.vertices
            if len(oldverts) != len(currentmesh.verts):
                #Invalid frame! Wrong number of vertices! Skip it...
                continue
            newverts = oldverts
            for vert_counter in range(len(currentmesh.verts)):
                currentvertex = currentmesh.verts[vert_counter]
                newpos = quarkx.vect((0.0, 0.0, 0.0))
                for blend_counter in range(0, currentvertex.blend_count):
                    weight_counter = currentvertex.blend_index + blend_counter
                    currentweight = currentmesh.weights[weight_counter]
                    tempmatrix = md5_bones[currentweight.bone_index].bindmat
                    temppos = QuArK_baseframe_matrix[currentweight.bone_index] * quarkx.vect((currentweight.weights[0], currentweight.weights[1], currentweight.weights[2]))
                    newpos = newpos + ((QuArK_baseframe_position[currentweight.bone_index] + temppos) * currentweight.bias)
                newverts[vert_counter] = newpos
            baseframe.vertices = newverts
            editor.Root.dictitems[md5_model_comps[mesh_counter]].dictitems['Frames:fg'].appenditem(baseframe)
        #Apply animation data to frame vertices
        for frame_counter in range(0,self.numFrames):
            for mesh_counter in range(len(md5_model)):
                currentmesh = md5_model[mesh_counter]
                oldframe = editor.Root.dictitems[md5_model_comps[mesh_counter]].dictitems['Frames:fg'].dictitems['meshframe:mf']
                newframe = oldframe.copy()
                newframe.shortname = filename + " frame "+str(frame_counter+1)
                oldverts = newframe.vertices
                if len(oldverts) != len(currentmesh.verts):
                    #Invalid frame! Wrong number of vertices! Skip it...
                    continue
                newverts = oldverts
                for vert_counter in range(len(currentmesh.verts)):
                    currentvertex = md5_model[mesh_counter].verts[vert_counter]
                    newpos = quarkx.vect((0.0, 0.0, 0.0))
                    for blend_counter in range(0, currentmesh.verts[vert_counter].blend_count):
                        weight_counter = currentvertex.blend_index + blend_counter
                        currentweight = md5_model[mesh_counter].weights[weight_counter]
                        temppos = QuArK_frame_matrix[frame_counter][currentweight.bone_index] * quarkx.vect((currentweight.weights[0], currentweight.weights[1], currentweight.weights[2]))
                        newpos = newpos + ((QuArK_frame_position[frame_counter][currentweight.bone_index] + temppos) * currentweight.bias)
                    newverts[vert_counter] = newpos
                newframe.vertices = newverts
                editor.Root.dictitems[md5_model_comps[mesh_counter]].dictitems['Frames:fg'].appenditem(newframe)


# gr2anim_filename = QuArK's full path and file name.
# bones = QuArK's "Skeleton:bg" folder to get our current bones from.
def load_gr2anim(gr2anim_filename, bones):
    return # Nothing setup to read in the .gr2 animation file yet.
    theanim = md5anim() # Making an "instance" of this class.
    theanim.load_md5anim(gr2anim_filename, bones) # Calling this class function to open and completely read the ,gr2 animation file.

    if bones:
        pth, actionname = os.path.split(gr2anim_filename)
        theanim.apply(bones, actionname) # Calling this class function to create the amimation frames,
                                         # "bones" is QuArK's "Skeleton:bg" folder, "actionname" is the full ,gr2 animation file name only.
    else:
        quarkx.beep() # Makes the computer "Beep" once if no bones are found.
        quarkx.msgbox("Could not apply animation.\nNo bones in the scene.", quarkpy.qutils.MT_ERROR, quarkpy.qutils.MB_OK)
    return

########################
# To run this file
########################

def import_gr2_model(basepath, gr2_filename):
    # basepath just the path to the "game" folder.
    # gr2_filename is the full path and file name.
    editor = quarkpy.mdleditor.mdleditor
    if gr2_filename.endswith(".gr2") and not gr2_filename.find("animations") != -1: # Calls to load the .gr2 mesh file.
        RetComponentList, RetQuArK_bone_list, message = load_gr2mesh(gr2_filename, basepath) # Loads the model using list of ALL bones as they are created.
        ### Use the 'ModelRoot' below to test opening the QuArK's Model Editor with, needs to be qualified with main menu item.
        ModelRoot = quarkx.newobj('Model:mr')
      #  ModelRoot.appenditem(Component)

        return ModelRoot, RetComponentList, RetQuArK_bone_list, message # Using list of ALL bones as they are created.
    else: # Calls to load the .gr2 animation file.
        bones = editor.Root.dictitems['Skeleton:bg']
        load_gr2anim(gr2_filename, bones)

def loadmodel(root, filename, gamename, nomessage=0):
    #   Loads the model file: root is the actual file,
    #   filename is the full path and name of the .gr2 mesh or .gr2 animation file selected,
    #   for example:  C:\Program Files\Utherverse Digital Inc\Utherverse 3D Client\resources\female\HF_Dancer1.gr2
    #   gamename is None.

    global gr2_mesh_path, gr2_anim_path, editor, progressbar, tobj, logging, importername, textlog, Strings
    if editor is None:
        editor = quarkpy.mdleditor.mdleditor

    ### First we get the base path from the model path.
    basepath = None
    basepath = filename.rsplit('\\', 1)[0]
    basepath = basepath.replace("\\", "/")
    if basepath is None:
        editor = None   #Reset the global again
        return

    if filename.endswith(".gr2") and not filename.find("animations") != -1: # Calls to load the .gr2 mesh file.
        logging, tobj, starttime = ie_utils.default_start_logging(importername, textlog, filename, "IM") ### Use "EX" for exporter text, "IM" for importer text.

    ### Lines below here loads the model into the opened editor's current model.
        ModelRoot, RetComponentList, RetQuArK_bone_list, message = import_gr2_model(basepath, filename)

        if ModelRoot is None or RetComponentList is None or RetComponentList == []:
            quarkx.beep() # Makes the computer "Beep" once if a file is not valid.
            quarkx.msgbox("Invalid .md5 model.\n\n    " + filename + "\n\nEditor can not import it.", quarkpy.qutils.MT_ERROR, quarkpy.qutils.MB_OK)
            try:
                progressbar.close()
            except:
                pass
            editor = None   #Reset the global again
            return

        QuArK_mesh_counter = 0
        undo = quarkx.action()
        newbones = []
        for bone in range(len(RetQuArK_bone_list)): # Using list of ALL bones.
            boneobj = RetQuArK_bone_list[bone]
            parent_index = int(boneobj.dictspec['parent_index'])
            if parent_index < 0:
                newbones = newbones + [boneobj]
            else:
                RetQuArK_bone_list[parent_index].appenditem(boneobj)
        for bone in newbones:
            undo.put(editor.Root.dictitems['Skeleton:bg'], bone)
        for Component in RetComponentList:
            undo.put(editor.Root, Component)
            editor.Root.currentcomponent = Component
            compframes = editor.Root.currentcomponent.findallsubitems("", ':mf')   # get all frames
            for compframe in compframes:
                compframe.compparent = editor.Root.currentcomponent # To allow frame relocation after editing.

            QuArK_mesh_counter = QuArK_mesh_counter + 1

             #   progressbar.progress() # un-comment this line once progress bar is set up

            try:
                progressbar.close()
                Strings[2454] = Strings[2454].replace(Component.shortname + "\n", "")
                ie_utils.default_end_logging(filename, "IM", starttime) ### Use "EX" for exporter text, "IM" for importer text.
            except:
                pass

            # This needs to be done for each component or bones will not work if used in the editor.
            quarkpy.mdlutils.make_tristodraw_dict(editor, Component)
        editor.ok(undo, str(len(RetComponentList)) + " .md5 Components imported") # Let the ok finish the new components before going on.

        editor.Root.currentcomponent = RetComponentList[0]  # Sets the current component.
        comp = editor.Root.currentcomponent
        skins = comp.findallsubitems("", ':sg')      # Gets the skin group.
        if len(skins[0].subitems) != 0:
            comp.currentskin = skins[0].subitems[0]      # To try and set to the correct skin.
            quarkpy.mdlutils.Update_Skin_View(editor, 2) # Sends the Skin-view for updating and center the texture in the view.
        else:
            comp.currentskin = None

        editor = None   #Reset the global again
        if message != "":
            message = message + "================================\r\n\r\n"
            message = message + "You need to find and supply the proper texture(s) and folder(s) above.\r\n"
            message = message + "Extract the required folder(s) and file(s) to the 'game' folder.\r\n\r\n"
            message = message + "If a texture does not exist it may be a .dds or some other type of image file.\r\n"
            message = message + "If so then you need to make a .tga file copy of that texture, perhaps in PaintShop Pro.\r\n\r\n"
            message = message + "You may also need to rename it to match the exact name above.\r\n"
            message = message + "Either case, it would be for editing purposes only and should be placed in the proper folder.\r\n\r\n"
            message = message + "Once this is done, then delete the imported components and re-import the model."
            quarkx.textbox("WARNING", "Missing Skin Textures:\r\n\r\n================================\r\n" + message, quarkpy.qutils.MT_WARNING)

        gr2_mesh_path = filename.rsplit('\\', 1)

    else: # Calls to load the .gr2 animation file.
        gr2_anim_path = filename.rsplit('\\', 1)
        if gr2_mesh_path is None:
            quarkx.beep() # Makes the computer "Beep" once if a animation file not loaded. 
            gr2_anim_path = gr2_anim_path[0].rsplit('\\animations', 1)
            quarkx.msgbox(".gr2 animation file not loaded\n\nFirst load .gr2 mesh file in:\n    " + gr2_anim_path[0] + "\n\nbefore any .gr2 animation files from its animation folder.", quarkpy.qutils.MT_ERROR, quarkpy.qutils.MB_OK)
            try:
                progressbar.close()
            except:
                pass
            editor = None   #Reset the global again
            return
        if gr2_anim_path[0].find(gr2_mesh_path[0]) == -1:
            quarkx.beep() # Makes the computer "Beep" once if a file is not valid.
            quarkx.msgbox(".gr2 mesh and .gr2 animation files incompatible.\nThey need to come from same model folder.\n\nLast .gr2 mesh loaded from:\n    " + gr2_mesh_path[0] + "\n\nYou selected:\n    " + gr2_anim_path[0] + "\\" + gr2_anim_path[1], quarkpy.qutils.MT_ERROR, quarkpy.qutils.MB_OK)
            try:
                progressbar.close()
            except:
                pass
            editor = None   #Reset the global again
            return
        if gr2_anim_path[0].find("\\animations") == -1:
            quarkx.beep() # Makes the computer "Beep" once if a file's path is not valid.
            animationfile = filename.rsplit('\\', 1)[1]
            quarkx.msgbox("Improper path for .gr2 animation file.\nThey need to come from a folder named\n'animations' located in the model's folder.\n\n    " + gr2_mesh_path[0] + "\n\nCreate the folder and move the animation file\n    " + animationfile + "\nto that location.", quarkpy.qutils.MT_ERROR, quarkpy.qutils.MB_OK)
            try:
                progressbar.close()
            except:
                pass
            editor = None   #Reset the global again
            return
        import_gr2_model(basepath, filename)
        quarkpy.mdlutils.Update_Editor_Views(editor)
        editor = None   #Reset the global again

### To register this Python plugin and put it on the importers menu.
import quarkpy.qmdlbase
import ie_gr2_import # This imports itself to be passed along so it can be used in mdlmgr.py later for the Specifics page.
quarkpy.qmdlbase.RegisterMdlImporter(".gr2 Importer", ".gr2 mesh or anim file", "*.gr2", loadmodel, ie_gr2_import)


def vtxcolorclick(btn):
    global editor
    if editor is None:
        editor = quarkpy.mdleditor.mdleditor # Get the editor.
    if quarkx.setupsubset(SS_MODEL, "Options")["LinearBox"] == "1":
        editor.ModelVertexSelList = []
        editor.linearbox = "True"
        editor.linear1click(btn)
    else:
        if editor.ModelVertexSelList != []:
            editor.ModelVertexSelList = []
            quarkpy.mdlutils.Update_Editor_Views(editor)


def colorclick(btn):
    global editor
    import quarkpy.qtoolbar # Get the toolbar functions to make the button with.
    if editor is None:
        editor = quarkpy.mdleditor.mdleditor # Get the editor.
    if not quarkx.setupsubset(SS_MODEL, "Options")['VertexUVColor'] or quarkx.setupsubset(SS_MODEL, "Options")['VertexUVColor'] == "0":
        quarkx.setupsubset(SS_MODEL, "Options")['VertexUVColor'] = "1"
        quarkpy.qtoolbar.toggle(btn)
        btn.state = quarkpy.qtoolbar.selected
        quarkx.update(editor.form)
        vtxcolorclick(btn)
    else:
        quarkx.setupsubset(SS_MODEL, "Options")['VertexUVColor'] = "0"
        quarkpy.qtoolbar.toggle(btn)
        btn.state = quarkpy.qtoolbar.normal
        quarkx.update(editor.form)

def dataformname(o):
    "Returns the data form for this type of object 'o' (a model's skin texture) to use for the Specific/Args page."
    global editor
    import quarkpy.mdlentities # Used further down in a couple of places.

    # Next line calls for the Shader Module in mdlentities.py to be used.
    external_skin_editor_dialog_plugin = quarkpy.mdlentities.UseExternalSkinEditor()

    # Next line calls for the Vertex U,V Color Module in mdlentities.py to be used.
    vtx_UVcolor_dialog_plugin = quarkpy.mdlentities.UseVertexUVColors()

    # Next line calls for the Vertex Weights Specifics Module in mdlentities.py to be used.
    vertex_weights_specifics_plugin = quarkpy.mdlentities.UseVertexWeightsSpecifics()

    # Next line calls for the Shader Module in mdlentities.py to be used.
    Shader_dialog_plugin = quarkpy.mdlentities.UseShaders()

    dlgdef = """
    {
      Help = "These are the Specific settings for Doom3\Quake4 (.md5mesh) model types."$0D
             "md5 models use 'meshes' the same way that QuArK uses 'components'."$0D
             "Each can have its own special Surface or skin texture settings."$0D
             "These textures may or may not have 'shaders' that they use for special effects."$0D0D22
             "skin name"$22" - The currently selected skin texture name."$0D22
             "edit skin"$22" - Opens this skin texture in an external editor."$0D22
             "Vertex Color"$22" - Color to use for this component's u,v vertex color mapping."$0D
             "            Click the color display button to select a color."$0D22
             "show weight colors"$22" - When checked, if component has vertex weight coloring they will show."$0D
             "          If NOT checked and it has bones with vetexes, those will show."$0D
             "shader file"$22" - Gives the full path and name of the .mtr material"$0D
             "           shader file that the selected skin texture uses, if any."$0D22
             "shader name"$22" - Gives the name of the shader located in the above file"$0D
             "           that the selected skin texture uses, if any."$0D22
             "shader keyword"$22" - Gives the above shader 'keyword' that is used to identify"$0D
             "          the currently selected skin texture used in the shader, if any."$0D22
             "shader lines"$22" - Number of lines to display in window below, max. = 35."$0D22
             "edit shader"$22" - Opens shader below in a text editor."$0D22
             "mesh shader"$22" - Contains the full text of this skin texture's shader, if any."$0D22
             "          This can be copied to a text file, changed and saved."
      skin_name:      = {t_ModelEditor_texturebrowser = ! Txt="skin name"    Hint="The currently selected skin texture name."}
      """ + external_skin_editor_dialog_plugin + """
      """ + vtx_UVcolor_dialog_plugin + """
      """ + vertex_weights_specifics_plugin + """
      """ + Shader_dialog_plugin + """
    }
    """

    from quarkpy.qeditor import ico_dict # Get the dictionary list of all icon image files available.
    import quarkpy.qtoolbar              # Get the toolbar functions to make the button with.
    editor = quarkpy.mdleditor.mdleditor # Get the editor.
    ico_mdlskv = ico_dict['ico_mdlskv']  # Just to shorten our call later.
    icon_btns = {}                       # Setup our button list, as a dictionary list, to return at the end.
    vtxcolorbtn = quarkpy.qtoolbar.button(colorclick, "Color mode||When active, puts the editor vertex selection into this mode and uses the 'COLR' specific setting as the color to designate these types of vertexes.\n\nIt also places the editor into Vertex Selection mode if not there already and clears any selected vertexes to protect from including unwanted ones by mistake.\n\nAny vertexes selected in this mode will become Color UV Vertexes and added to the component as such. Click the InfoBase button or press F1 again for more detail.|intro.modeleditor.dataforms.html#specsargsview", ico_mdlskv, 5)
    # Sets the button to its current status, that might be effected by another importer file, either on or off.
    if quarkx.setupsubset(SS_MODEL, "Options")['VertexUVColor'] == "1":
        vtxcolorbtn.state = quarkpy.qtoolbar.selected
    else:
        vtxcolorbtn.state = quarkpy.qtoolbar.normal
    vtxcolorbtn.caption = "" # Texts shows next to button and keeps the width of this button so it doesn't change.
    icon_btns['color'] = vtxcolorbtn # Put our button in the above list to return.
    # Next line calls for the Vertex Weights system in mdlentities.py to be used.
    vtxweightsbtn = quarkpy.qtoolbar.button(quarkpy.mdlentities.UseVertexWeights, "Open or Update\nVertex Weights Dialog||When clicked, this button opens the dialog to allow the 'weight' movement setting of single vertexes that have been assigned to more then one bone handle.\n\nClick the InfoBase button or press F1 again for more detail.|intro.modeleditor.dataforms.html#specsargsview", ico_mdlskv, 5)
    vtxweightsbtn.state = quarkpy.qtoolbar.normal
    vtxweightsbtn.caption = "" # Texts shows next to button and keeps the width of this button so it doesn't change.
    icon_btns['vtxweights'] = vtxweightsbtn # Put our button in the above list to return.

    if (editor.Root.currentcomponent.currentskin is not None) and (o.name == editor.Root.currentcomponent.currentskin.name): # If this is not done it will cause looping through multiple times.
        if o.parent.parent.dictspec.has_key("shader_keyword") and o.dictspec.has_key("shader_keyword"):
            if o.parent.parent.dictspec['shader_keyword'] != o.dictspec['shader_keyword']:
                o['shader_keyword'] = o.parent.parent.dictspec['shader_keyword']
        if (o.parent.parent.dictspec.has_key("skin_name")) and (o.parent.parent.dictspec['skin_name'] != o.name) and (not o.parent.parent.dictspec['skin_name'] in o.parent.parent.dictitems['Skins:sg'].dictitems.keys()):
            # Gives the newly selected skin texture's game folders path and file name, for example:
            #     models/monsters/cacodemon/cacoeye.tga
            skinname = o.parent.parent.dictspec['skin_name']
            skin = quarkx.newobj(skinname)
            # Gives the full current work directory (cwd) path up to the file name, need to add "\\" + filename, for example:
            #     E:\Program Files\Doom 3\base\models\monsters\cacodemon
            cur_folder = os.getcwd()
            # Gives just the actual file name, for example: cacoeye.tga
            tex_file = skinname.split("/")[-1]
            # Puts the full path and file name together to get the file, for example:
            # E:\Program Files\Doom 3\base\models\monsters\cacodemon\cacoeye.tga
            file = cur_folder + "\\" + tex_file
            image = quarkx.openfileobj(file)
            skin['Image1'] = image.dictspec['Image1']
            skin['Size'] = image.dictspec['Size']
            skin['shader_keyword'] = o.parent.parent.dictspec['shader_keyword']
            skingroup = o.parent.parent.dictitems['Skins:sg']
            undo = quarkx.action()
            undo.put(skingroup, skin)
            editor.ok(undo, o.parent.parent.shortname + " - " + "new skin added")
            editor.Root.currentcomponent.currentskin = skin
            editor.layout.explorer.sellist = [editor.Root.currentcomponent.currentskin]
            quarkpy.mdlutils.Update_Skin_View(editor, 2)

    DummyItem = o
    while (DummyItem.type != ":mc"): # Gets the object's model component.
        DummyItem = DummyItem.parent
    comp = DummyItem

    if comp.type == ":mc": # Just makes sure what we have is a model component.
        formobj = quarkx.newobj("md5_mc:form")
        formobj.loadtext(dlgdef)
        return formobj, icon_btns
    else:
        return None, None

def dataforminput(o):
    "Returns the default settings or input data for this type of object 'o' (a model's skin texture) to use for the Specific/Args page."

    DummyItem = o
    while (DummyItem.type != ":mc"): # Gets the object's model component.
        DummyItem = DummyItem.parent
    if DummyItem.type == ":mc":
        comp = DummyItem
        if not comp.dictspec.has_key('vtx_color'):
            comp['vtx_color'] = "0.75 0.75 0.75"
        # This sections handles the data for this model type skin page form.
        # This makes sure what is selected is a model skin, if so it fills the Skin page data and adds the items to the component.
        # It also handles the shader file which its name is the full path and name of the skin texture.
        if len(comp.dictitems['Skins:sg'].subitems) == 0 or o in comp.dictitems['Skins:sg'].subitems:
            if not comp.dictspec.has_key('shader_file'):
                comp['shader_file'] = "None"
            if not comp.dictspec.has_key('shader_name'):
                comp['shader_name'] = "None"
            if not comp.dictspec.has_key('skin_name'):
                if len(comp.dictitems['Skins:sg'].subitems) != 0:
                   comp['skin_name'] = o.name
                else:
                   comp['skin_name'] = "no skins exist"
            else:
                if len(comp.dictitems['Skins:sg'].subitems) != 0:
                   comp['skin_name'] = o.name
                else:
                   comp['skin_name'] = "no skins exist"
            if not comp.dictspec.has_key('shader_keyword'):
                if o.dictspec.has_key("shader_keyword"):
                    comp['shader_keyword'] = o.dictspec['shader_keyword']
                else:
                    comp['shader_keyword'] = o['shader_keyword'] = "None"
            else:
                if o.dictspec.has_key("shader_keyword"):
                    comp['shader_keyword'] = o.dictspec['shader_keyword']
                else:
                    comp['shader_keyword'] = o['shader_keyword'] = "None"
            if not comp.dictspec.has_key('shader_lines'):
                if quarkx.setupsubset(SS_MODEL, "Options")["NbrOfShaderLines"] is not None:
                    comp['shader_lines'] = quarkx.setupsubset(SS_MODEL, "Options")["NbrOfShaderLines"]
                else:
                    comp['shader_lines'] = "8"
                    quarkx.setupsubset(SS_MODEL, "Options")["NbrOfShaderLines"] = comp.dictspec['shader_lines']
            else:
                quarkx.setupsubset(SS_MODEL, "Options")["NbrOfShaderLines"] = comp.dictspec['shader_lines']
            if not comp.dictspec.has_key('mesh_shader'):
                comp['mesh_shader'] = "None"


# ----------- REVISION HISTORY ------------
#
# $Log$
# Revision 1.1  2009/08/02 12:02:54  cdunde
# Support started for granny .gr2 model importing using QuArK's build and version of grnreader.exe.
# Source code for exe in QuArK's src source\dllsource\QuArKgrnreader folder.
#
#
#


