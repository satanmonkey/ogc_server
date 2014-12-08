# -*- coding: utf-8 -*-

import codecs
import os, sys
import copy
import random
import json
import math
import decimal
import datetime
import threading
import exceptions
import time
import base64
#import numpy as np
import socket
import urllib, urllib2, urlparse
from socket import error
import errno
import subprocess
from multiprocessing import Process, Queue, current_process, freeze_support
import shutil
import re
#from PIL import Image
import StringIO
import cgi
import uuid
from contextlib import contextmanager

from gevent import pywsgi
import gevent
import gevent.fileobject
from gevent.local import local
try:
    import geventwebsocket
    from geventwebsocket.handler import WebSocketHandler
except:
    print('geventwebsocket import error')
try:
    from pysimplesoap.server import SoapDispatcher, WSGISOAPHandler
    from pysimplesoap.client import SoapClient, SoapFault
except:
    print('pysimplesoap import error')
    
from lxml import etree
try:
    import czml
except:
    print('czml import error')

    

try:
    from geventhttpclient import HTTPClient, URL
except:
    print('geventhttpclient import error')

from werkzeug.wrappers import Request, BaseResponse
from werkzeug.local import LocalProxy
from werkzeug.contrib.sessions import FilesystemSessionStore
from werkzeug.utils import dump_cookie, parse_cookie
from werkzeug.routing import Map, Rule, BaseConverter, ValidationError, HTTPException


from sessions import MongoClient, MongodbSessionStore
import configobj
import db_util
from module_locator import module_path, dec, dec1, enc, enc1





ENCODING = None
ENCODING1 = None
STATICRESOURCE_DIR = None

    

STATICRESOURCE_CSS_DIR = None
STATICRESOURCE_JS_DIR = None
STATICRESOURCE_IMG_DIR = None
UPLOAD_PHOTOS_DIR = None
UPLOAD_VOICE_DIR = None

gConfig = None
gStaticCache = {}
gTileCache = {}

#deprecated
gSatTileCache = {}
gMapTileCache = {}
gTerrainCache = {}

gGreenlets = {}
gClusterProcess = {}
gLoginToken = {}
gSecurityConfig = {}

_SPECIAL = re.escape('()<>@,;:\\"/[]?={} \t')
_RE_SPECIAL = re.compile('[%s]' % _SPECIAL)
_QSTR = '"(?:\\\\.|[^"])*"' # Quoted string
_VALUE = '(?:[^%s]+|%s)' % (_SPECIAL, _QSTR) # Save or quoted string
_OPTION = '(?:;|^)\s*([^%s]+)\s*=\s*(%s)' % (_SPECIAL, _VALUE)
_RE_OPTION = re.compile(_OPTION) # key=value part of an Content-Type like header



gSessionStore = None

gRequests = None
gRequest = None

@contextmanager
def session_manager(environ):
    global gRequests, gRequest
    if gRequests is None:
        gRequests = local()
        gRequest = LocalProxy(lambda: gRequests.request)
    gRequests.request = Request(environ)
    yield
    gRequests.request = None



def init_global():
    global ENCODING, ENCODING1, STATICRESOURCE_DIR, STATICRESOURCE_CSS_DIR, STATICRESOURCE_JS_DIR, STATICRESOURCE_IMG_DIR, UPLOAD_PHOTOS_DIR, UPLOAD_VOICE_DIR
    global gConfig, gStaticCache, gGreenlets, gClusterProcess, gSecurityConfig
    ENCODING = 'utf-8'
    ENCODING1 = 'gb18030'
    
    STATICRESOURCE_DIR = os.path.join(module_path(), 'static')
    
    #CONFIGFILE = os.path.join(module_path(), 'ogc-config.ini')
    #gConfig = configobj.ConfigObj(db_util.CONFIGFILE, encoding='UTF8')
    gConfig = db_util.gConfig
    
    if gConfig['web'].has_key('webroot') and len(gConfig['web']['webroot'])>0:
        if os.path.exists(gConfig['web']['webroot']):
            STATICRESOURCE_DIR = gConfig['web']['webroot']
        
    
    STATICRESOURCE_CSS_DIR = os.path.join(STATICRESOURCE_DIR, 'css')
    STATICRESOURCE_JS_DIR = os.path.join(STATICRESOURCE_DIR, 'js')
    STATICRESOURCE_IMG_DIR = os.path.join(STATICRESOURCE_DIR, 'img')
    UPLOAD_PHOTOS_DIR = os.path.join(STATICRESOURCE_DIR,'photos', 'upload')
    UPLOAD_VOICE_DIR = os.path.join(STATICRESOURCE_DIR,'voice')
    
    if gConfig['authorize_platform']['enable'].lower() in ['true',u'true','1', u'1']:
        gSecurityConfig = db_util.mongo_find_one(gConfig['authorize_platform']['mongodb']['database'],
                                             gConfig['authorize_platform']['mongodb']['collection_security_config'],
                                             {},
                                             'authorize_platform'
                                             )
        if gSecurityConfig is None:
            gSecurityConfig = {}
    


def handle_static(environ, aUrl):
    global ENCODING, gConfig
    global STATICRESOURCE_DIR, STATICRESOURCE_JS_DIR, STATICRESOURCE_CSS_DIR, STATICRESOURCE_IMG_DIR, UPLOAD_VOICE_DIR
    statuscode, contenttype, body = '404 Not Found', 'text/plain;charset=' + ENCODING, '404 Not Found'
    surl = dec(aUrl)#.replace('//', '').replace('/', os.path.sep)
    if surl[0:2] == '//':
        surl = surl[2:]
    if surl[0] == '/':
        surl = surl[1:]
    p = os.path.join(STATICRESOURCE_DIR , surl)
    isBin = False
    ext = os.path.splitext(p)[1]
    if '.' in surl:
        ext = surl[surl.rindex('.'):]
    else:
        ext = os.path.splitext(p)[1]
    print('handle_static p=%s' % p)
    
    if len(ext)>0:
        if gConfig['mime_type'].has_key(ext):
            if 'image/' in gConfig['mime_type'][ext]:
                isBin = True
            contenttype = gConfig['mime_type'][ext]
            if ext == '.js':
                if not os.path.exists(p):
                    p = os.path.join(STATICRESOURCE_JS_DIR, aUrl[aUrl.rindex('/')+1:])
            elif ext == '.css':
                if not os.path.exists(p):
                    p = os.path.join(STATICRESOURCE_CSS_DIR, aUrl[aUrl.rindex('/')+1:])
            elif 'image/' in gConfig['mime_type'][ext]:
                if not os.path.exists(p):
                    p = os.path.abspath(os.path.join(STATICRESOURCE_IMG_DIR, aUrl[aUrl.rindex('/')+1:]))
            
            if not os.path.exists(p):
                p = os.path.join(STATICRESOURCE_DIR ,  aUrl)
                #p = os.path.abspath(p)
                p = dec(p)
            if os.path.exists(p):
                statuscode = '200 OK'
                mode = 'r'
                if isBin:
                    mode = 'rb'
                with open(p, mode) as f:
                    f1 = gevent.fileobject.FileObjectThread(f, mode)
                    body = f1.read()
            else:
                statuscode = '404 Not Found'
                body = '404 Not Found'
            
                
        else:
            contenttype = 'application/octet-stream'
            if os.path.exists(p):
                statuscode = '200 OK'
                with open(p, 'rb') as f:
                    f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                    body = f1.read()
            else:
                if ext == '.3gp':
                    id = surl[surl.rindex('/') + 1:]
                    id = id.replace('.3gp', '')
                    fn = get_voice_file_latest(id)
                    if fn:
                        with open(os.path.join(UPLOAD_VOICE_DIR, fn), 'rb') as f:
                            f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                            body = f1.read()
                            statuscode = '200 OK'
                        
                    
            
    else:
        contenttype = 'text/plain;charset=' + ENCODING
        statuscode = '500 Internal Server Error'
        body = '500 Internal Server Error'
    headers = {}
    headers['Content-Type'] = str(contenttype)
    return statuscode, headers, body

def handle_wfs_GetCapabilities(params):
    headers = {}
    headers['Content-Type'] = 'text/xml;charset=' + ENCODING
    s = create_wfs_GetCapabilities()
    return '200 OK', headers, s

def handle_wfs_GetFeature(params):
    headers = {}
    headers['Content-Type'] = 'text/xml;charset=' + ENCODING
    s = create_wfs_GetFeature()
    return '200 OK', headers, s


def create_wfs_GetCapabilities():
    namespace = {'ows':"http://www.opengis.net/ows",
                 'ogc':"http://www.opengis.net/ogc",
                 'wfs':"http://www.opengis.net/wfs", 
                 'gml':"http://www.opengis.net/gml", 
                 'xlink':"http://www.w3.org/1999/xlink", 
                 'xsi':"http://www.w3.org/2001/XMLSchema-instance", 
                 'schemaLocation':"http://www.opengis.net/wfs/1.1.0/WFS.xsd",
                 'my':"http://localhost:88/my"
                 }
    wfs = '{%s}' % namespace['wfs']
    ogc = '{%s}' % namespace['ogc']
    ows = '{%s}' % namespace['ows']
    xlink = '{%s}' % namespace['xlink']
    root = etree.Element(wfs+"WFS_Capabilites", xmlns="http://www.opengis.net/wfs", nsmap=namespace, version="1.1.0", updateSequence="0")
    #ServiceIdentification
    ServiceIdentification = etree.SubElement(root, ows + "ServiceIdentification")
    Title = etree.SubElement(ServiceIdentification, ows + "Title").text = gConfig['wfs']['ServiceIdentification_Title']
    ServiceType = etree.SubElement(ServiceIdentification, ows + "ServiceType").text = 'WFS'
    ServiceTypeVersion = etree.SubElement(ServiceIdentification, ows + "ServiceTypeVersion").text = '1.1.0'
    
    #OperationsMetadata
    OperationsMetadata = etree.SubElement(root, ows + "OperationsMetadata")
    Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="GetCapabilities")
    DCP= etree.SubElement(Operation, ows + "DCP")
    HTTP= etree.SubElement(DCP, ows + "HTTP")
    href = xlink + 'href'
    Get= etree.SubElement(HTTP, ows + "Get", {href:gConfig['wfs']['url']})
    #Constraint= etree.SubElement(Get, ows + "Constraint", name="GetEncoding")
    #AllowedValues= etree.SubElement(Constraint, ows + "AllowedValues")
    #Value= etree.SubElement(AllowedValues, ows + "Value").text = 'KVP'
    
    #Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="GetTile")
    #DCP= etree.SubElement(Operation, ows + "DCP")
    #HTTP= etree.SubElement(DCP, ows + "HTTP")
    #Get= etree.SubElement(HTTP, ows + "Get", {href:gConfig['wmts']['url']})
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="AcceptVersions")
    Value = etree.SubElement(Parameter, ows + "Value").text = "1.1.0"
    Value = etree.SubElement(Parameter, ows + "Value").text = "1.0.0"
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="AcceptFormats")
    Value = etree.SubElement(Parameter, ows + "Value").text = "text/xml"
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="Sections")
    Value = etree.SubElement(Parameter, ows + "Value").text = "ServiceIdentification"
    Value = etree.SubElement(Parameter, ows + "Value").text = "OperationsMetadata"
    Value = etree.SubElement(Parameter, ows + "Value").text = "FeatureTypeList"
    Value = etree.SubElement(Parameter, ows + "Value").text = "ServesGMLObjectTypeList"
    Value = etree.SubElement(Parameter, ows + "Value").text = "SupportsGMLObjectTypeList"
    Value = etree.SubElement(Parameter, ows + "Value").text = "Filter_Capabilities"
    
    Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="DescribeFeatureType")
    DCP= etree.SubElement(Operation, ows + "DCP")
    HTTP= etree.SubElement(DCP, ows + "HTTP")
    Get= etree.SubElement(HTTP, ows + "Get", {href:gConfig['wfs']['url']})#+'/wfs.cgi?'})
    Post= etree.SubElement(HTTP, ows + "Post", {href:gConfig['wfs']['url']})#+'/wfs.cgi'})
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="outputFormat")
    Value = etree.SubElement(Parameter, ows + "Value").text = "text/xml; subtype=gml/3.1.1"
    
    Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="GetFeature")
    DCP= etree.SubElement(Operation, ows + "DCP")
    HTTP= etree.SubElement(DCP, ows + "HTTP")
    Get= etree.SubElement(HTTP, ows + "Get", {href:gConfig['wfs']['url']})#+'/wfs.cgi?'})
    Post= etree.SubElement(HTTP, ows + "Post", {href:gConfig['wfs']['url']})#+'/wfs.cgi'})
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="resultType")
    Value = etree.SubElement(Parameter, ows + "Value").text = "results"
    Value = etree.SubElement(Parameter, ows + "Value").text = "hits"
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="outputFormat")
    Value = etree.SubElement(Parameter, ows + "Value").text = "text/xml; subtype=gml/3.1.1"
    
    Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="GetFeatureWithLock")
    DCP= etree.SubElement(Operation, ows + "DCP")
    HTTP= etree.SubElement(DCP, ows + "HTTP")
    Post= etree.SubElement(HTTP, ows + "Post", {href:gConfig['wfs']['url']})
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="resultType")
    Value = etree.SubElement(Parameter, ows + "Value").text = "results"
    Value = etree.SubElement(Parameter, ows + "Value").text = "hits"
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="outputFormat")
    Value = etree.SubElement(Parameter, ows + "Value").text = "text/xml; subtype=gml/3.1.1"
    
    Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="GetGMLObject")
    DCP= etree.SubElement(Operation, ows + "DCP")
    HTTP= etree.SubElement(DCP, ows + "HTTP")
    Post= etree.SubElement(HTTP, ows + "Post", {href:gConfig['wfs']['url']})
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="outputFormat")
    Value = etree.SubElement(Parameter, ows + "Value").text = "text/xml; subtype=gml/3.1.1"
    Value = etree.SubElement(Parameter, ows + "Value").text = "text/xhtml"
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="LocalTraverseXLinkScope")
    Value = etree.SubElement(Parameter, ows + "Value").text = "0"
    Value = etree.SubElement(Parameter, ows + "Value").text = "*"
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="RemoteTraverseXLinkScope")
    Value = etree.SubElement(Parameter, ows + "Value").text = "0"
    Value = etree.SubElement(Parameter, ows + "Value").text = "*"
    
    Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="LockFeature")
    DCP= etree.SubElement(Operation, ows + "DCP")
    HTTP= etree.SubElement(DCP, ows + "HTTP")
    Post= etree.SubElement(HTTP, ows + "Post", {href:gConfig['wfs']['url']})
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="lockAction")
    Value = etree.SubElement(Parameter, ows + "Value").text = "ALL"
    Value = etree.SubElement(Parameter, ows + "Value").text = "SOME"
    
    Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="Transaction")
    DCP= etree.SubElement(Operation, ows + "DCP")
    HTTP= etree.SubElement(DCP, ows + "HTTP")
    Post= etree.SubElement(HTTP, ows + "Post", {href:gConfig['wfs']['url']})
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="inputFormat")
    Value = etree.SubElement(Parameter, ows + "Value").text = "text/xml; subtype=gml/3.1.1"
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="idgen")
    Value = etree.SubElement(Parameter, ows + "Value").text = "GenerateNew"
    Value = etree.SubElement(Parameter, ows + "Value").text = "UseExisting"
    Value = etree.SubElement(Parameter, ows + "Value").text = "ReplaceDuplicate"
    Parameter = etree.SubElement(Operation, ows + "Parameter", name="releaseAction")
    Value = etree.SubElement(Parameter, ows + "Value").text = "ALL"
    Value = etree.SubElement(Parameter, ows + "Value").text = "SOME"
    
    Parameter = etree.SubElement(OperationsMetadata, ows + "Parameter", name="srsName")
    Value = etree.SubElement(Parameter, ows + "Value").text = "EPSG:4326"
    Constraint = etree.SubElement(OperationsMetadata, ows + "Constraint", name="DefaultMaxFeatures")
    Value = etree.SubElement(Constraint, ows + "Value").text = "10000"
    Constraint = etree.SubElement(OperationsMetadata, ows + "Constraint", name="LocalTraverseXLinkScope")
    Value = etree.SubElement(Constraint, ows + "Value").text = "0"
    Value = etree.SubElement(Constraint, ows + "Value").text = "*"
    Constraint = etree.SubElement(OperationsMetadata, ows + "Constraint", name="RemoteTraverseXLinkScope")
    Value = etree.SubElement(Constraint, ows + "Value").text = "0"
    Value = etree.SubElement(Constraint, ows + "Value").text = "*"
    Constraint = etree.SubElement(OperationsMetadata, ows + "Constraint", name="DefaultLockExpiry")
    Value = etree.SubElement(Constraint, ows + "Value").text = "5"
    
    
    FeatureTypeList = etree.SubElement(root, wfs + "FeatureTypeList")
    FeatureType = etree.SubElement(FeatureTypeList, wfs + "FeatureType")
    Name = etree.SubElement(FeatureType, wfs + "Name").text = "PointType"
    Title = etree.SubElement(FeatureType, wfs + "Title").text = "Point Type"
    DefaultSRS = etree.SubElement(FeatureType, wfs + "DefaultSRS").text = "EPSG:4326"
    OutputFormats = etree.SubElement(FeatureType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    WGS84BoundingBox = etree.SubElement(FeatureType, ows + "WGS84BoundingBox")
    LowerCorner = etree.SubElement(WGS84BoundingBox, ows + "LowerCorner").text = "-180 -90"
    UpperCorner = etree.SubElement(WGS84BoundingBox, ows + "UpperCorner").text = "180 90"
    
    ServesGMLObjectTypeList = etree.SubElement(root, wfs + "ServesGMLObjectTypeList")
    GMLObjectType = etree.SubElement(ServesGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "PointType"
    Title = etree.SubElement(GMLObjectType, wfs + "Title").text = "Point Type"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    
    SupportsGMLObjectTypeList = etree.SubElement(root, wfs + "SupportsGMLObjectTypeList")
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:AbstractGMLFeatureType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:PointType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:LineStringType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:PolygonType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:MultiPointType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:MultiCurveType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:MultiSurfaceType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:AbstractMetaDataType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    GMLObjectType = etree.SubElement(SupportsGMLObjectTypeList, wfs + "GMLObjectType")
    Name = etree.SubElement(GMLObjectType, wfs + "Name").text = "gml:AbstractTopologyType"
    OutputFormats = etree.SubElement(GMLObjectType, wfs + "OutputFormats")
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xml; subtype=gml/3.1.1"
    Format = etree.SubElement(OutputFormats, wfs + "Format").text = "text/xhmtl"
    
    
    Filter_Capabilities = etree.SubElement(root, ogc + "Filter_Capabilities")
    Spatial_Capabilities = etree.SubElement(Filter_Capabilities, ogc + "Spatial_Capabilities")
    GeometryOperands = etree.SubElement(Spatial_Capabilities, ogc + "GeometryOperands")
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Envelope"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Point"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:LineString"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Polygon"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:ArcByCenterPoint"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:CircleByCenterPoint"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Arc"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Circle"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:ArcByBulge"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Bezier"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Clothoid"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:CubicSpline"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Geodesic"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:OffsetCurve"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Triangle"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:PolyhedralSurface"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:TriangulatedSurface"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Tin"
    GeometryOperand = etree.SubElement(GeometryOperands, ogc + "GeometryOperand").text = "gml:Solid"
    SpatialOperators = etree.SubElement(Spatial_Capabilities, ogc + "SpatialOperators")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="BBOX")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Equals")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Disjoint")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Intersects")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Touches")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Crosses")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Within")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Contains")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Overlaps")
    SpatialOperator = etree.SubElement(GeometryOperands, ogc + "SpatialOperator", name="Beyond")

    Scalar_Capabilities = etree.SubElement(Filter_Capabilities, ogc + "Scalar_Capabilities")
    LogicalOperators = etree.SubElement(Scalar_Capabilities, ogc + "LogicalOperators")
    ComparisonOperators = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperators")
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "LessThan"
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "GreaterThan"
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "LessThanEqualTo"
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "GreaterThanEqualTo"
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "EqualTo"
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "NotEqualTo"
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "Like"
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "Between"
    ComparisonOperator = etree.SubElement(Scalar_Capabilities, ogc + "ComparisonOperator").text = "NullCheck"
    ArithmeticOperators = etree.SubElement(Scalar_Capabilities, ogc + "ArithmeticOperators")
    SimpleArithmetic = etree.SubElement(ArithmeticOperators, ogc + "SimpleArithmetic")
    Functions = etree.SubElement(ArithmeticOperators, ogc + "Functions")
    FunctionNames = etree.SubElement(Functions, ogc + "FunctionNames")
    FunctionName = etree.SubElement(FunctionNames, ogc + "FunctionName", nArgs="1").text = "MIN"
    FunctionName = etree.SubElement(FunctionNames, ogc + "FunctionName", nArgs="1").text = "MAX"
    FunctionName = etree.SubElement(FunctionNames, ogc + "FunctionName", nArgs="1").text = "SIN"
    FunctionName = etree.SubElement(FunctionNames, ogc + "FunctionName", nArgs="1").text = "COS"
    FunctionName = etree.SubElement(FunctionNames, ogc + "FunctionName", nArgs="1").text = "TAN"

    Id_Capabilities = etree.SubElement(Filter_Capabilities, ogc + "Id_Capabilities")
    EID = etree.SubElement(Id_Capabilities, ogc + "EID")
    FID = etree.SubElement(Id_Capabilities, ogc + "FID")
    #WGS84BoundingBox = etree.SubElement(Layer, ows + "WGS84BoundingBox")
    #SupportedCRS = etree.SubElement(TileMatrixSet, ows + "SupportedCRS" ).text = gConfig['wmts']['SupportedCRS']
    
    ret = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding=ENCODING)
    print(ret)
    return ret


def handle_wmts_GetCapabilities(params={}):
    headers = {}
    mimetype = 'text/xml;charset=' + ENCODING
    s = ''
    if params.has_key('TILETYPE') and params.has_key('SUBTYPE'):
        s = create_wmts_GetCapabilities(params['TILETYPE'], params['SUBTYPE'])
    return mimetype, s
    
def create_wmts_GetCapabilities(tiletype, subtype):
    global gConfig
    #'''
    #namespace = {'ows':"http://www.opengis.net/ows/1.1", 'xlink':"http://www.w3.org/1999/xlink", 'xsi':"http://www.w3.org/2001/XMLSchema-instance", 'gml':"http://www.opengis.net/gml", 'schemaLocation':"http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd"}
    #ows = '{%s}' % namespace['ows']
    #xlink = '{%s}' % namespace['xlink']
    #root = etree.Element("Capabilities", xmlns="http://www.opengis.net/wmts/1.0", nsmap=namespace, version="1.0.0")
    ##ServiceIdentification
    #ServiceIdentification = etree.SubElement(root, ows + "ServiceIdentification")
    #Title = etree.SubElement(ServiceIdentification, ows + "Title").text = gConfig['wmts']['ServiceIdentification_Title']
    #ServiceType = etree.SubElement(ServiceIdentification, ows + "ServiceType").text = 'OGC WMTS'
    #ServiceTypeVersion = etree.SubElement(ServiceIdentification, ows + "ServiceTypeVersion").text = '1.0.0'
    
    ##OperationsMetadata
    #OperationsMetadata = etree.SubElement(root, ows + "OperationsMetadata")
    #Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="GetCapabilities")
    #DCP= etree.SubElement(Operation, ows + "DCP")
    #HTTP= etree.SubElement(DCP, ows + "HTTP")
    #href = xlink + 'href'
    #Get= etree.SubElement(HTTP, ows + "Get", {href:gConfig['wmts']['url'] + '?'})
    #Constraint= etree.SubElement(Get, ows + "Constraint", name="GetEncoding")
    #AllowedValues= etree.SubElement(Constraint, ows + "AllowedValues")
    #Value= etree.SubElement(AllowedValues, ows + "Value").text = 'KVP'
    #Operation= etree.SubElement(OperationsMetadata, ows + "Operation", name="GetTile")
    #DCP= etree.SubElement(Operation, ows + "DCP")
    #HTTP= etree.SubElement(DCP, ows + "HTTP")
    #Get= etree.SubElement(HTTP, ows + "Get", {href:gConfig['wmts']['url'] + '?'})
    
    ##Contents
    #Contents = etree.SubElement(root, "Contents")
    #Layer = etree.SubElement(Contents, "Layer")
    #Title = etree.SubElement(Layer, ows + "Title").text = gConfig['wmts']['Layer_Title']
    #WGS84BoundingBox = etree.SubElement(Layer, ows + "WGS84BoundingBox")
    #LowerCorner = etree.SubElement(WGS84BoundingBox, ows + "LowerCorner").text = gConfig['wmts']['WGS84BoundingBox']['LowerCorner']
    #UpperCorner = etree.SubElement(WGS84BoundingBox, ows + "UpperCorner").text = gConfig['wmts']['WGS84BoundingBox']['UpperCorner']
    #Identifier = etree.SubElement(Layer, ows + "Identifier").text = gConfig['wmts']['Layer_Identifier']
    #Style = etree.SubElement(Layer, "Style", isDefault="true")
    #Title = etree.SubElement(Style, ows + "Title" ).text = 'Default'
    #Identifier = etree.SubElement(Style, ows + "Identifier" ).text = 'default'
    #Format = etree.SubElement(Layer, "Format" ).text = gConfig['mime_type'][gConfig['wmts']['format']]
    #TileMatrixSetLink = etree.SubElement(Layer, "TileMatrixSetLink" )
    #TileMatrixSet = etree.SubElement(TileMatrixSetLink, "TileMatrixSet" ).text = gConfig['wmts']['TileMatrixSet']
        
    #TileMatrixSet = etree.SubElement(Contents, "TileMatrixSet")
    #Identifier = etree.SubElement(TileMatrixSet, ows + "Identifier" ).text = gConfig['wmts']['TileMatrixSet']
    #SupportedCRS = etree.SubElement(TileMatrixSet, ows + "SupportedCRS" ).text = gConfig['wmts']['SupportedCRS']
    #WellKnownScaleSet = etree.SubElement(TileMatrixSet, "WellKnownScaleSet" ).text = gConfig['wmts']['WellKnownScaleSet']
    
    #max_zoom_level, min_zoom_level = int(gConfig['wmts']['max_zoom_level']), int(gConfig['wmts']['min_zoom_level'])
    #if max_zoom_level < min_zoom_level:
        #max_zoom_level, min_zoom_level =  min_zoom_level, max_zoom_level  
    ##zoomlist = range(max_zoom_level,min_zoom_level, -1)
    #zoomlist = range(min_zoom_level, max_zoom_level+1, 1)
    
    
    #pixelSize = float(gConfig['wmts']['pixelSize'])
    #tileWidth,tileHeight = int(gConfig['wmts']['TileWidth']), int(gConfig['wmts']['TileHeight'])
    #minLonLat,maxLonLat  = (float(gConfig['wmts']['minLonLat'][0]), float(gConfig['wmts']['minLonLat'][1])), (float(gConfig['wmts']['maxLonLat'][0]), float(gConfig['wmts']['maxLonLat'][1]))
    ##tileMatrixMinX, tileMatrixMaxX = (26.0, 102.0), (26.0, 104.0)
    ##tileMatrixMinY, tileMatrixMaxY = (24.0, 102.0), (26.0, 102.0)
    #tileMatrixMinX, tileMatrixMaxX = (maxLonLat[1], minLonLat[0]), (maxLonLat[1], maxLonLat[0])
    #tileMatrixMinY, tileMatrixMaxY = (minLonLat[1], minLonLat[0]), (maxLonLat[1], minLonLat[0])
    
    #metersPerUnit = 0.0
    #if gConfig['wmts'].has_key('metersPerUnit'):
        #metersPerUnit = float(gConfig['wmts']['metersPerUnit'])
    #else:
        #metersPerUnitX = mapUtils.countDistanceFromLatLon(tileMatrixMaxX , tileMatrixMinX)/2*1000
        ##print('metersPerUnitX=%f' % metersPerUnitX)
        #metersPerUnitY = mapUtils.countDistanceFromLatLon(tileMatrixMaxY , tileMatrixMinY)/2*1000
        ##print('metersPerUnitY=%f' % metersPerUnitY)
        #metersPerUnit = metersPerUnitY 
    ##print('metersPerUnit=%f' % metersPerUnit)
    #for i in zoomlist:
        ##matrixHeight = matrixWidth = mapUtils.tiles_on_level(i)
        #matrixHeight = matrixWidth = mapUtils.tiles_on_level(max_zoom_level-(i-1))
        ##print('%d=%d' % (i , matrixHeight))
        ##scaleDenominatorX   = metersPerUnit/pixelSize * mapUtils.countDistanceFromLatLon(tileMatrixMaxX , tileMatrixMinX) * 1000./(tileWidth * matrixWidth)
        ##scaleDenominatorY   = metersPerUnit/pixelSize * mapUtils.countDistanceFromLatLon(tileMatrixMaxY , tileMatrixMinY) * 1000./(tileHeight * matrixHeight)
        ##print('scaleDenominatorX=%f, scaleDenominatorY=%f' % (scaleDenominatorX, scaleDenominatorY))
        ##scaleDenominator   = metersPerUnit/pixelSize * mapUtils.countDistanceFromLatLon(tileMatrixMaxY , tileMatrixMinY) * 1000. /(tileHeight * matrixHeight)
        #scaleDenominator   = metersPerUnit/pixelSize * mapUtils.countDistanceFromLatLon(tileMatrixMaxY , tileMatrixMinY)  /(tileHeight * matrixHeight)
        #TileMatrix = etree.SubElement(TileMatrixSet, "TileMatrix" )
        ##Identifier = etree.SubElement(TileMatrix, ows + "Identifier" ).text = "ynsat_" + str(i)
        #Identifier = etree.SubElement(TileMatrix, ows + "Identifier" ).text = str(i)
        #ScaleDenominator = etree.SubElement(TileMatrix, "ScaleDenominator" ).text = '%.8f' % scaleDenominator
        #TopLeftCorner = etree.SubElement(TileMatrix, "TopLeftCorner" ).text = gConfig['wmts']['TopLeftCorner']
        #TileWidth = etree.SubElement(TileMatrix, "TileWidth" ).text = str(tileWidth)
        #TileHeight = etree.SubElement(TileMatrix, "TileHeight" ).text = str(tileHeight)
        #MatrixWidth = etree.SubElement(TileMatrix, "MatrixWidth" ).text = str(matrixWidth)
        #MatrixHeight = etree.SubElement(TileMatrix, "MatrixHeight" ).text = str(matrixHeight)
    
    #ret = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding=ENCODING)
    #print(ret)
    #return ret
    #'''
    ret = '''<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0"
xmlns:ows="http://www.opengis.net/ows/1.1"
xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns:gml="http://www.opengis.net/gml" xsi:schemaLocation="http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd"
version="1.0.0">
<ows:ServiceIdentification>
  <ows:Title>%s</ows:Title>
  <ows:ServiceType>OGC WMTS</ows:ServiceType>
  <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
</ows:ServiceIdentification>
<ows:OperationsMetadata>
  <ows:Operation name="GetCapabilities">
    <ows:DCP>
      <ows:HTTP>
        <ows:Get xlink:href="http://%s:%s/wmts?REQUEST=getcapabilities">
          <ows:Constraint name="GetEncoding">
            <ows:AllowedValues>
              <ows:Value>KVP</ows:Value>
            </ows:AllowedValues>
          </ows:Constraint>
        </ows:Get>
      </ows:HTTP>
    </ows:DCP>
  </ows:Operation>
  <ows:Operation name="GetTile">
    <ows:DCP>
      <ows:HTTP>
        <ows:Get xlink:href="http://%s:%s/wmts?REQUEST=gettile">
          <ows:Constraint name="GetEncoding">
            <ows:AllowedValues>
              <ows:Value>KVP</ows:Value>
            </ows:AllowedValues>
          </ows:Constraint>
        </ows:Get>
      </ows:HTTP>
    </ows:DCP>
  </ows:Operation>
</ows:OperationsMetadata>
<Contents>
  <Layer>
    <ows:Title>%s</ows:Title>
    <ows:WGS84BoundingBox>
      <ows:LowerCorner>-180.0 -90.0</ows:LowerCorner>
      <ows:UpperCorner>180.0 90.0</ows:UpperCorner>
    </ows:WGS84BoundingBox>
    <ows:Identifier>%s</ows:Identifier>
    <Style isDefault="true">
      <ows:Identifier>_null</ows:Identifier>
    </Style>
    <Format>%s</Format>
    <TileMatrixSetLink>
      <TileMatrixSet>%s</TileMatrixSet>
    </TileMatrixSetLink> 
  </Layer>

  <TileMatrixSet>
    <ows:Identifier>%s</ows:Identifier>
    <ows:SupportedCRS>urn:ogc:def:crs:EPSG::900913</ows:SupportedCRS>
    <TileMatrix>
      <ows:Identifier>0</ows:Identifier>
      <ScaleDenominator>5.590822639508929E8</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>1</MatrixWidth>
      <MatrixHeight>1</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>1</ows:Identifier>
      <ScaleDenominator>2.7954113197544646E8</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>2</MatrixWidth>
      <MatrixHeight>2</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>2</ows:Identifier>
      <ScaleDenominator>1.3977056598772323E8</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>4</MatrixWidth>
      <MatrixHeight>4</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>3</ows:Identifier>
      <ScaleDenominator>6.988528299386162E7</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>8</MatrixWidth>
      <MatrixHeight>8</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>4</ows:Identifier>
      <ScaleDenominator>3.494264149693081E7</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>16</MatrixWidth>
      <MatrixHeight>16</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>5</ows:Identifier>
      <ScaleDenominator>1.7471320748465404E7</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>32</MatrixWidth>
      <MatrixHeight>32</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>6</ows:Identifier>
      <ScaleDenominator>8735660.374232702</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>64</MatrixWidth>
      <MatrixHeight>64</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>7</ows:Identifier>
      <ScaleDenominator>4367830.187116351</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>128</MatrixWidth>
      <MatrixHeight>128</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>8</ows:Identifier>
      <ScaleDenominator>2183915.0935581755</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>256</MatrixWidth>
      <MatrixHeight>256</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>9</ows:Identifier>
      <ScaleDenominator>1091957.5467790877</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>512</MatrixWidth>
      <MatrixHeight>512</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>10</ows:Identifier>
      <ScaleDenominator>545978.7733895439</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>1024</MatrixWidth>
      <MatrixHeight>1024</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>11</ows:Identifier>
      <ScaleDenominator>272989.38669477194</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>2048</MatrixWidth>
      <MatrixHeight>2048</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>12</ows:Identifier>
      <ScaleDenominator>136494.69334738597</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>4096</MatrixWidth>
      <MatrixHeight>4096</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>13</ows:Identifier>
      <ScaleDenominator>68247.34667369298</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>8192</MatrixWidth>
      <MatrixHeight>8192</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>14</ows:Identifier>
      <ScaleDenominator>34123.67333684649</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>16384</MatrixWidth>
      <MatrixHeight>16384</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>15</ows:Identifier>
      <ScaleDenominator>17061.836668423246</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>32768</MatrixWidth>
      <MatrixHeight>32768</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>16</ows:Identifier>
      <ScaleDenominator>8530.918334211623</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>65536</MatrixWidth>
      <MatrixHeight>65536</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>17</ows:Identifier>
      <ScaleDenominator>4265.4591671058115</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>131072</MatrixWidth>
      <MatrixHeight>131072</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>18</ows:Identifier>
      <ScaleDenominator>2132.7295835529058</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>262144</MatrixWidth>
      <MatrixHeight>262144</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>19</ows:Identifier>
      <ScaleDenominator>1066.3647917764529</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>524288</MatrixWidth>
      <MatrixHeight>524288</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>20</ows:Identifier>
      <ScaleDenominator>533.1823958882264</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>1048576</MatrixWidth>
      <MatrixHeight>1048576</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>21</ows:Identifier>
      <ScaleDenominator>266.5911979441132</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>2097152</MatrixWidth>
      <MatrixHeight>2097152</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>22</ows:Identifier>
      <ScaleDenominator>133.2955989720566</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>4194304</MatrixWidth>
      <MatrixHeight>4194304</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>23</ows:Identifier>
      <ScaleDenominator>66.6477994860283</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>8388608</MatrixWidth>
      <MatrixHeight>8388608</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>24</ows:Identifier>
      <ScaleDenominator>33.32389974301415</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>16777216</MatrixWidth>
      <MatrixHeight>16777216</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>25</ows:Identifier>
      <ScaleDenominator>16.661949871507076</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>33554432</MatrixWidth>
      <MatrixHeight>33554432</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>26</ows:Identifier>
      <ScaleDenominator>8.330974935753538</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>67108864</MatrixWidth>
      <MatrixHeight>67108864</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>27</ows:Identifier>
      <ScaleDenominator>4.165487467876769</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>134217728</MatrixWidth>
      <MatrixHeight>134217728</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>28</ows:Identifier>
      <ScaleDenominator>2.0827437339383845</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>268435456</MatrixWidth>
      <MatrixHeight>268435456</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>29</ows:Identifier>
      <ScaleDenominator>1.0413718669691923</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>536870912</MatrixWidth>
      <MatrixHeight>536870912</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
      <ows:Identifier>30</ows:Identifier>
      <ScaleDenominator>0.5206859334845961</ScaleDenominator>
      <TopLeftCorner>-2.003750834E7 2.0037508E7</TopLeftCorner>
      <TileWidth>256</TileWidth>
      <TileHeight>256</TileHeight>
      <MatrixWidth>1073741824</MatrixWidth>
      <MatrixHeight>1073741824</MatrixHeight>
    </TileMatrix>
  </TileMatrixSet>
</Contents>
</Capabilities>''' % (
            str(tiletype),
            str(gConfig['wmts']['host']), 
            str(gConfig['wmts']['port']),
            str(gConfig['wmts']['host']), 
            str(gConfig['wmts']['port']),
            str(subtype),
            str(subtype),
            str(gConfig['mime_type'][gConfig[tiletype][subtype]['mimetype']]),
            str(subtype),
            str(subtype),
                   )
#<ServiceMetadataURL xlink:href="http://%s:%s/wmts?REQUEST=getcapabilities"/>
    return ret
    
    
 
def download_callback(*args, **kwargs):
    global gConfig,  gMapTileCache, gSatTileCache, gTerrainCache
    global STATICRESOURCE_IMG_DIR
    zoom, col, row = args[1][2], args[1][0], args[1][1]
    root = os.path.abspath(gConfig['wmts']['tiles_map_root'])
    if args[2] == mapConst.LAYER_SAT:
        root = os.path.abspath(gConfig['wmts']['tiles_sat_root'])
    if args[2] == mapConst.LAYER_MAP:
        root = os.path.abspath(gConfig['wmts']['tiles_map_root'])
        
    p = os.path.join(root,
                    str(zoom),
                    str(col / 1024),
                    str(col % 1024),
                    str(row / 1024),
                    str(row % 1024) + gConfig['wmts']['format']
                    )
    if os.path.exists(p):
        key = '%d-%d-%d' % (zoom, col, row)
        with open(p, 'rb') as f:
            f1 = gevent.fileobject.FileObjectThread(f, 'rb')
            if args[2] == mapConst.LAYER_SAT:
                gSatTileCache[key] = f1.read()
            if args[2] == mapConst.LAYER_MAP:
                gMapTileCache[key] = f1.read()
    
    
def handle_wmts_GetTile(params):
    global gConfig
    mimetype, ret = None, None
    tiletype = 'tiles'
    subtype = None
    if params.has_key('TILEMATRIXSET'):
        subtype = params['TILEMATRIXSET']
    level, y, x = None, None, None
    if params.has_key('TILEMATRIX'):
        level = int(params['TILEMATRIX'])
    if params.has_key('TILEROW'):
        y = int(params['TILEROW'])
    if params.has_key('TILECOL'):
        x = int(params['TILECOL'])
    if subtype is not None and level is not None and y is not None and x is not None:
        tilepath = '%d/%d/%d%s' % (level, x, y, str(gConfig[tiletype][subtype]))
        d = {}
        d['x'] = [str(x)]
        d['y'] = [str(y)]
        d['level'] = [str(level)]
        mimetype, ret = db_util.gridfs_tile_find(tiletype, subtype, tilepath, d)
    return mimetype, ret

def handle_tiles(environ):
    global gConfig, gTileCache
    def get_blank_tile(image_type):
        blank_tile = ''
        picpath = os.path.join(STATICRESOURCE_IMG_DIR,  gConfig['tiles'][image_type]['missing'])
        with open(picpath, 'rb') as f:
            f1 = gevent.fileobject.FileObjectThread(f, 'rb')
            blank_tile = f1.read()
        return blank_tile
    headers = {}    
    path_info = environ['PATH_INFO']
    d = cgi.parse(None, environ)
    ret = None
    mimetype = 'image/png'
    image_type = None
    #key = path_info.replace('/tiles/','')
    if d.has_key('image_type') and d.has_key('x') and d.has_key('y') and d.has_key('level'):
        image_type = d['image_type'][0]
        x, y, level = d['x'][0], d['y'][0], d['level'][0]
        tilepath = '%s/%s/%s%s' % (level, x, y, gConfig['tiles'][image_type]['mimetype'])
        if not gTileCache.has_key(image_type):
            gTileCache[image_type] = {}
        if not gTileCache[image_type].has_key('missing'):
            gTileCache[image_type]['missing'] = get_blank_tile(image_type)
        if gTileCache[image_type].has_key(tilepath):
            ret = gTileCache[image_type][tilepath]
        else:
            try:
                mimetype, ret = db_util.gridfs_tile_find('tiles', image_type, tilepath, d)
                gTileCache[image_type][tilepath] = ret
            except:
                ret = gTileCache[image_type]['missing']
    else:
        if image_type:
            if not gTileCache.has_key(image_type):
                gTileCache[image_type] = {}
            if not gTileCache[image_type].has_key('missing'):
                gTileCache[image_type]['missing'] = get_blank_tile(image_type)
            ret = gTileCache[image_type]['missing']
    if ret is None:
        ret = gTileCache[image_type]['missing']
    headers['Content-Type'] = mimetype
    return '200 OK', headers, ret
        
            

def handle_terrain(environ):
    global gConfig, gTileCache
    path_info = environ['PATH_INFO']
    d = cgi.parse(None, environ)
    ret = None
    headers = {}
    mimetype = str('application/octet-stream')
    key = path_info.replace('/terrain/','')
    terrain_type = 'quantized_mesh'
    if d.has_key('terrain_type'):
        terrain_type = d['terrain_type'][0]
    
    if not gTileCache.has_key(terrain_type):
        gTileCache[terrain_type] = {}
    if gTileCache[terrain_type].has_key(key):
        ret = gTileCache[terrain_type][key]
    else:
        tilepath = key
        if tilepath == 'layer.json':
            mimetype, ret = db_util.gridfs_tile_find('terrain', terrain_type, tilepath, d)
            gTileCache[terrain_type][key] = ret
            headers['Content-Type'] = mimetype
            return '200 OK', headers, ret
        else:
            print('tilepath:%s' % tilepath)
            mimetype, ret = db_util.gridfs_tile_find('terrain', terrain_type, tilepath, d)
            if ret:
                gTileCache[terrain_type][key] = ret
                headers['Content-Type'] = mimetype
                return '200 OK', headers, ret
            else:
                if not gTileCache[terrain_type].has_key('missing'):
                    print('reading mongo blank_terrain...')
                    tilepath = gConfig['terrain'][terrain_type]['missing'] #'0/0/0.terrain'
                    mimetype, ret = db_util.gridfs_tile_find('terrain', terrain_type, tilepath, d)
                    gTileCache[terrain_type]['missing'] = ret
                ret = gTileCache[terrain_type]['missing']
                
    headers['Content-Type'] = mimetype
    return '200 OK', headers, ret

        
def handle_terrain1(environ):
    global gConfig,  gMapTileCache, gSatTileCache, gTerrainCache
    path_info = environ['PATH_INFO']
    #d = cgi.parse(None, environ)
    ret = None
    headers = {}
    key = path_info.replace('/terrain/','')
    if gTerrainCache.has_key(key):
        ret = gTerrainCache[key]
    else:
        arr = key.split('/')
        tilepath = gConfig['terrain']['tiles_dir']
        for i in arr:
            tilepath = os.path.join(tilepath, i)
        tilepath = os.path.abspath(tilepath)
        ret = '' 
        if os.path.exists(tilepath):
            #print('reading %s...' % tilepath)
            with open(tilepath, 'rb') as f:
                f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                ret = f1.read()
            gTerrainCache[key] = ret
        else:
            if gTerrainCache.has_key('missing'):
                ret = gTerrainCache['missing']
            else:
                print('reading blank_terrain...')
                with open(gConfig['terrain']['blank_terrain'], 'rb') as f:
                    f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                    ret = f1.read()
                gTerrainCache['missing'] = ret
    headers['Content-Type'] = 'application/octet-stream'
    return '200 OK', headers, ret
    
    
def handle_arcgistile(environ):
    global gConfig, gMapTileCache, gSatTileCache
    global STATICRESOURCE_IMG_DIR
    ret = None
    headers = {}
    dd = cgi.parse(None, environ)
    d = {}
    for k in dd.keys():
        d[k] = dd[k][0]
    if d.has_key('zoom') and d.has_key('col')  and d.has_key('row'):
        zoom  = int(d['zoom'])
        col = int(d['col'])
        row = int(d['row'])
        key = '%d-%d-%d' % (zoom, col, row)
        if not gSatTileCache.has_key(key):
            try:
                #picpath = os.path.join(gConfig['wmts']['arcgis_tiles_root'], '_alllayers', 'L%02d' % zoom, 'R%08x' % row, 'C%08x%s' % (col, gConfig['wmts']['format']))
                picpath = os.path.join(gConfig['wmts']['arcgis_tiles_root'],   '%d' % zoom, '%d' % col, '%d%s' % (row, gConfig['wmts']['format']))
                print('%s, %s' % (key, picpath))
                with open(picpath, 'rb') as f:
                    f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                    gSatTileCache[key] = f1.read()
                
            except:
                foundit = False
                if not foundit:
                    key = 'missing'
                if not gSatTileCache.has_key(key):
                    picpath = os.path.join(STATICRESOURCE_IMG_DIR,  gConfig['wmts']['missing'])
                    with open(picpath, 'rb') as f:
                        f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                        gSatTileCache[key] = f1.read()
        
        ret = gSatTileCache[key]
    elif d.has_key('is_esri') :
        key = environ['PATH_INFO'].replace('/arcgistile/','')
        if not gSatTileCache.has_key(key):
            try:
                #picpath = os.path.join(gConfig['wmts']['arcgis_tiles_root'], '_alllayers', 'L%02d' % zoom, 'R%08x' % row, 'C%08x%s' % (col, gConfig['wmts']['format']))
                picpath = os.path.join(gConfig['wmts']['arcgis_tiles_root'],   key)
                print('%s, %s' % (key, picpath))
                with open(picpath, 'rb') as f:
                    f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                    gSatTileCache[key] = f1.read()
                
            except:
                foundit = False
                if not foundit:
                    key = 'missing'
                if not gSatTileCache.has_key(key):
                    picpath = os.path.join(STATICRESOURCE_IMG_DIR,  gConfig['wmts']['missing'])
                    with open(picpath, 'rb') as f:
                        f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                        gSatTileCache[key] = f1.read()
        
        ret = gSatTileCache[key]
    else:
        if not gSatTileCache.has_key('missing'):
            picpath = os.path.join(STATICRESOURCE_IMG_DIR,  gConfig['wmts']['missing'])
            with open(picpath, 'rb') as f:
                f1 = gevent.fileobject.FileObjectThread(f, 'rb')
                gSatTileCache['missing'] = f1.read()
        ret = gSatTileCache['missing']
        
    headers['Content-Type'] = str(gConfig['mime_type'][gConfig['wmts']['format']])
    return '200 OK', headers, ret   
        
    
def handle_wmts(environ):
    dd = cgi.parse(None, environ)
    d = {}
    headers = {}
    mimetype, ret = None, None
    for k in dd.keys():
        d[k.upper()] = dd[k][0]
    ret, mimetype = None, None
    if d.has_key('REQUEST') :
        d['REQUEST'] = d['REQUEST'].replace('/1.0.0/WMTSCapabilities.xml', '')
        if d.has_key('TILETYPE'):
            d['TILETYPE'] = d['TILETYPE'].replace('/1.0.0/WMTSCapabilities.xml', '')
        if d.has_key('SUBTYPE'):
            d['SUBTYPE'] = d['SUBTYPE'].replace('/1.0.0/WMTSCapabilities.xml', '')
        if d['REQUEST'].lower() in ['getcapabilities']:
            mimetype, ret = handle_wmts_GetCapabilities(d)
        elif d['REQUEST'].lower() in ['gettile']:
            mimetype, ret = handle_wmts_GetTile(d)
    headers['Content-Type'] = mimetype
    return '200 OK', headers, ret

    
def handle_cluster(environ):
    global gConfig
    headers = {}
    headers['Content-Type'] = 'text/json;charset=' + ENCODING
    if int(environ['SERVER_PORT'])==int(gConfig['cluster']['manager_port']) and gConfig['cluster']['enable_cluster'] in ['true','True']:
        op = ''
        if environ['PATH_INFO']=='/create_cluster':
            if len(get_pid_from_name('nginx'))==0:
                op = 'create ok'
                create_cluster()
        elif environ['PATH_INFO']=='/kill_cluster':
            op = 'kill ok'
            kill_cluster()
        #print(environ)
        return '200 OK', headers, json.dumps({'result':op})
    else:
        return '200 OK', headers, json.dumps({'result':'cluster is disabled or not by manager'})
    
    
    
def handle_test(environ):
    s = '测试OK'
    headers = {}
    d = cgi.parse(None, environ)
    #print(d)
    headers['Content-Type'] = 'text/json;charset=' + ENCODING
    #print(s)
    return '200 OK', headers, s
    
    
def get_condition_from_dict(dct):
    cond = '1=1'            
    for k in dct.keys():
        if k in ['voltage', 'line_id', 'id', 'tower_id', 'start_tower_id', 'end_tower_id', 'model_code', 'side', 'position']:
            if k == 'side':
                if dct[k][0]=='1':
                    cond += " AND %s='%s'" % (k, u'正')
                elif dct[k][0]=='0':
                    cond += " AND %s='%s'" % (k, u'反')
            else:    
                cond += " AND %s='%s'" % (k, dct[k][0])
        else:
            cond += " AND %s=%s" % (k, dct[k][0])
    print(cond)
    return cond

def mongo_get_condition_from_dict(dct):
    ret = {}            
    for k in dct.keys():
        ret[k] =  dct[k][0]
    print(ret)
    return ret
    
def handle_get_method(environ):
    global ENCODING
    global STATICRESOURCE_DIR, UPLOAD_PHOTOS_DIR, UPLOAD_VOICE_DIR
    global gConfig
    ret = {}
    s = ''
    d = cgi.parse(None, environ)
    isgrid = False
    area = ''
    data = {}
    headers = {}
    if d.has_key('grid'):
        isgrid = True
        del d['grid']
    if d.has_key('area'):
        area = d['area'][0]
        del d['area']
    if d.has_key('geojson'):
        if d['geojson'][0]=='line_towers':
            data = db_util.gen_geojson_by_lines(area)
            s = json.dumps(data, ensure_ascii=True, indent=4)        
        elif d['geojson'][0]=='tracks':
            data = db_util.gen_geojson_tracks(area)
            s = json.dumps(data, ensure_ascii=True, indent=4)        
        else:
            k = d['geojson'][0]
            p = os.path.abspath(STATICRESOURCE_DIR)
            if k == 'potential_risk':
                k = 'geojson_%s_%s' % (k, area)
            p = os.path.join(p, 'geojson', area, '%s.json' % k)
            print(p)
            if os.path.exists(p):
                with open(p) as f:
                    f1 = gevent.fileobject.FileObjectThread(f, 'r')
                    s = f1.read()
            else:
                p = os.path.abspath(STATICRESOURCE_DIR)
                p = os.path.join(p, 'geojson', '%s.json' % k)
                if os.path.exists(p):
                    with open(p) as f:
                        f1 = gevent.fileobject.FileObjectThread(f, 'r')
                        s = f1.read()
        del d['geojson']
        
        
    if d.has_key('table'):
        table = d['table'][0]
        del d['table']
        #cond = '1=1'
        dbtype = 'odbc'
        if d.has_key('dbtype'):
            dbtype = d['dbtype'][0]
            del d['dbtype']
        if  dbtype == 'pg':
            data = db_util.pg_get_records(table, get_condition_from_dict(d))
            
        else:
            data = db_util.odbc_get_records(table, get_condition_from_dict(d), area)
            if table in ['TABLE_TOWER']:
                if d.has_key('line_id'):
                    data = db_util.odbc_get_sorted_tower_by_line(d['line_id'][0], area)
                
        if isgrid:
            data = {'Rows':data}
        s = json.dumps(data, ensure_ascii=True, indent=4)
        
    if d.has_key('check_file'):
        fn = dec(d['check_file'][0])
        dir_name = dec(d['dir_name'][0])
        del d['check_file']
        del d['dir_name']
        ret["result"] = {}
        ret["result"]["filename"] = fn
        if dir_name == 'voice':
            if check_voice_file_by_fault(fn):
                ret["result"]["exist"] = "true"
            else:
                ret["result"]["exist"] = "false"
        else:
            if os.path.exists(os.path.join(UPLOAD_PHOTOS_DIR, dir_name, fn)):
                ret["result"]["exist"] = "true"
            else:
                ret["result"]["exist"] = "false"
        s = json.dumps(ret, ensure_ascii=True, indent=4)
    if d.has_key('delete_file'):
        fn = dec(d['delete_file'][0])
        dir_name = dec(d['dir_name'][0])
        del d['delete_file']
        del d['dir_name']
        ret["result"] = {}
        ret["result"]["filename"] = fn
        if dir_name == 'voice':
            pl = get_voice_file_by(fn)
            if len(pl)>0:
                for i in pl:
                    p = os.path.join(UPLOAD_VOICE_DIR, fn)
                    if os.path.exists(p):
                        os.remove(p)
                ret["result"]["removed"] = "true"
            else:
                ret["result"]["removed"] = "false"
                
        else:
            p = os.path.join(UPLOAD_PHOTOS_DIR, dir_name, fn)
            if os.path.exists(p):
                os.remove(p)
                ret["result"]["removed"] = "true"
            else:
                ret["result"]["removed"] = "false"
        s = json.dumps(ret, ensure_ascii=True, indent=4)
    if d.has_key('list_file_dir_name'):
        dir_name = dec(d['list_file_dir_name'][0])
        del d['list_file_dir_name']
        ret["result"] = {}
        ret["result"]["dirs"] = [dir_name, ]
        p = os.path.join(UPLOAD_PHOTOS_DIR, dir_name)
        if os.path.exists(p):
            l = os.listdir(p)
            ret["result"]["files"] = l
        else:
            ret["result"]["files"] = []
        s = json.dumps(ret, ensure_ascii=True, indent=4)
    if d.has_key('get_voice_files'):
        get_voice_files = d['get_voice_files'][0]
        ret["result"] = {}
        ret["result"]["ids"] = get_voice_file_all()
        s = json.dumps(ret, ensure_ascii=True, indent=4)
    if d.has_key('op'):
        op = d['op'][0]
        del d['op']
        if op == "gridfs":
            ret = db_util.gridfs_find(d)
            if isinstance(ret, tuple) and ret[0] and ret[1]:
                headers['Content-Type'] = str(ret[0])
                if d.has_key('attachmentdownload'):
                    headers['Content-Disposition'] = 'attachment;filename="' + enc(ret[2]) + '"'
                s = ret[1]
                return '200 OK', headers , s
            if isinstance(ret, list):
                s = json.dumps(ret, ensure_ascii=True, indent=4)
        elif op == "gridfs_delete":
            try:
                db_util.gridfs_delete(d)
                ret = ''
            except:
                ret["result"] = sys.exc_info()[1].message
            s = json.dumps(ret, ensure_ascii=True, indent=4)
        
    headers['Content-Type'] = 'text/json;charset=' + ENCODING
    if isinstance(ret, dict) and len(ret.keys())==0:
        ret["result"] = "ok"
    if isinstance(s, list) and len(s)==0:
        s = json.dumps(ret, ensure_ascii=True, indent=4)
    return '200 OK', headers, s

def create_upload_xls_dir():
    global STATICRESOURCE_DIR
    p = os.path.join(STATICRESOURCE_DIR, 'upload')
    if not os.path.exists(p):
        os.mkdir(p)
    p = os.path.join(p, 'xls')
    if not os.path.exists(p):
        os.mkdir(p)
    return p
        
def create_voice_dir():
    global STATICRESOURCE_DIR, UPLOAD_VOICE_DIR
    if not os.path.exists(UPLOAD_VOICE_DIR):
        os.mkdir(UPLOAD_VOICE_DIR)

def check_voice_file_by_fault(id):
    global STATICRESOURCE_DIR, UPLOAD_VOICE_DIR
    create_voice_dir()
    ret = False
    for fn in os.listdir(UPLOAD_VOICE_DIR):
        if id in fn:
            ret = True
            break
    return ret

def get_voice_file_latest(id):
    global STATICRESOURCE_DIR, UPLOAD_VOICE_DIR
    create_voice_dir()
    l = []
    for fn in os.listdir(UPLOAD_VOICE_DIR):
        if id in fn:
            l.append(fn)
    ret = None
    if len(l)>0:
        l.sort()
        ret = l[-1]
    return ret

def get_voice_file_by(id):
    global STATICRESOURCE_DIR, UPLOAD_VOICE_DIR
    create_voice_dir()
    l = []
    for fn in os.listdir(UPLOAD_VOICE_DIR):
        if id in fn:
            l.append(fn)
    return l

def get_voice_file_all():
    global STATICRESOURCE_DIR, UPLOAD_VOICE_DIR
    s = set()
    for fn in os.listdir(UPLOAD_VOICE_DIR):
        p = os.path.join(UPLOAD_VOICE_DIR, fn)
        if os.path.isfile(p):
            arr = fn.split('@')
            if len(arr)==3:
                id = arr[1]
                s.add(id)
    return list(s)
    


def create_pic_dir():
    global STATICRESOURCE_DIR, UPLOAD_PHOTOS_DIR
    if not os.path.exists(os.path.join(STATICRESOURCE_DIR,'photos')):
        os.mkdir(os.path.join(STATICRESOURCE_DIR,'photos'))
    if not os.path.exists(UPLOAD_PHOTOS_DIR):
        os.mkdir(UPLOAD_PHOTOS_DIR)

def handle_upload_file(environ, qsdict, filedata):
    global STATICRESOURCE_DIR, UPLOAD_PHOTOS_DIR, UPLOAD_VOICE_DIR
    
    def parse_options_header(header, options=None):
        if ';' not in header:
            return header.lower().strip(), {}
        ctype, tail = header.split(';', 1)
        options = options or {}
        for match in _RE_OPTION.finditer(tail):
            key = match.group(1).lower()
            value = header_unquote(match.group(2), key=='filename')
            options[key] = value
        return ctype, options
    def header_quote(val):
        if not _RE_SPECIAL.search(val):
            return val
        return '"' + val.replace('\\','\\\\').replace('"','\\"') + '"'
    
    def header_unquote(val, filename=False):
        if val[0] == val[-1] == '"':
            val = val[1:-1]
            if val[1:3] == ':\\' or val[:2] == '\\\\': 
                val = val.split('\\')[-1] # fix ie6 bug: full path --> filename
            return val.replace('\\\\','\\').replace('\\"','"')
        return val
    
    def tob(data, encode='utf8'): # Convert strings to bytes (py2 and py3)
        return data.encode(encode) if isinstance(data, unicode) else data
    def parse_form_data(environ, mimetype, filedata):
        filename, ret = None, None
        try:
            if environ.get('REQUEST_METHOD','GET').upper() not in ('POST', 'PUT'):
                raise Exception("Request method other than POST or PUT.")
            content_length = int(environ.get('CONTENT_LENGTH', '-1'))
            content_type = environ.get('CONTENT_TYPE', '')
            if not content_type:
                raise Exception("Missing Content-Type header.")
            content_type, options = parse_options_header(content_type)
            if content_type == 'multipart/form-data':
                boundary = options.get('boundary','')
            content_type_token = tob('Content-Type: ' + mimetype)
            if boundary:
                _bcrnl = tob('\r\n')
                s = content_type_token + _bcrnl * 2
                s1 = _bcrnl + tob('--') + boundary + tob('--') + _bcrnl
                ret = filedata[filedata.index(s)+len(s):-len(s1)]
                head = filedata[:filedata.index(s)]
                arr = head.split(_bcrnl)
                for i in arr:
                    if 'Content-Disposition' in i:
                        arr1 = i.split(';')
                        for ii in arr1:
                            if 'filename=' in ii:
                                arr2 = ii.split('=')
                                filename = dec(arr2[1].strip().replace('"',''))
                                break
                        break
        except:
            raise
        return filename, ret
    
    ret = False
    root = os.path.abspath(STATICRESOURCE_DIR)
    create_pic_dir()
    create_voice_dir()
    try:
        #task item picture
        if qsdict.has_key('pic_file_name'):
            fn = dec(qsdict['pic_file_name'][0])
            dir_name = dec(qsdict['dir_name'][0])
            #pic_type = qsdict['pic_type'][0]
            p = os.path.join(root, 'photos')
            if not os.path.exists(p):
                os.mkdir(p)
            p = os.path.join(root, 'photos', 'upload')
            if not os.path.exists(p):
                os.mkdir(p)
            save_file_to(UPLOAD_PHOTOS_DIR, dir_name,  fn, filedata)
            ret = True
        elif qsdict.has_key('voice_file_name'):
            fn = qsdict['voice_file_name'][0]
            p = os.path.join(root, 'voice')
            if not os.path.exists(p):
                os.mkdir(p)
            save_file_to(UPLOAD_VOICE_DIR, None, fn, filedata)
            ret = True
        elif qsdict.has_key('import_xls'):
            root = create_upload_xls_dir()
            area = urllib.unquote_plus( qsdict['area'][0])
            line_name = urllib.unquote_plus( qsdict['line_name'][0])
            voltage = urllib.unquote_plus( qsdict['voltage'][0])
            category = urllib.unquote_plus( qsdict['category'][0])
            fn = str(uuid.uuid4()) + '.xls'
            import_xls(os.path.join(root, fn), filedata, dec(area), dec(line_name), dec(voltage),  dec(category))
            ret = True
        elif qsdict.has_key('db'):
            mimetype = urllib.unquote_plus(qsdict['mimetype'][0])
            filename, filedata1 = parse_form_data(environ, mimetype, filedata)
            #with open(ur'd:\aaa.png','wb') as f:
                #f.write(filedata)
            db_util.gridfs_save(qsdict, filename, filedata1)
            ret = True
    except:
        #print(sys.exc_info()[1])
        raise
    return ret


def import_xls(path, fileobj, area, line_name, voltage,  category):
    with open(path, 'wb') as f:
        f.write(fileobj)
    return db_util.import_tower_xls_file(area, line_name, voltage,  category, path)

    
def save_file_to(category, dir_id, filename, fileobj):
    root = os.path.abspath(category)
    if not os.path.exists(root):
        os.mkdir(root)
        
    p = os.path.join(root, filename)
    if dir_id:
        p = os.path.join(root, dir_id)
        if not os.path.exists(p):
            os.mkdir(p)
        p = os.path.join(root, dir_id, filename)
    with open(p, 'wb') as f:
        f1 = gevent.fileobject.FileObjectThread(f, 'wb')
        f1.write(fileobj)
    
    
    
    
#def save_upload_file1(buf):
    #ret = False
    #try:
        #arr = buf.split('\r\n')
        #ds_plus = urllib.unquote_plus(arr[0])
        #print(ds_plus)
        #obj = json.loads(ds_plus)
        #op = ''
        #if obj.has_key('op'):
            #op = obj['op']
            #if op=='upload_task':
                #filename = 'unknown.zip'
                #if obj.has_key('filename'):
                    #filename = obj['filename']
                #save_upload_task(filename, buf[buf.index('\r\n')+2:], obj)
        #if obj.has_key('filename') and op != 'upload_task':
            #save_upload_image(obj['filename'], buf[buf.index('\r\n')+2:], obj)
            #ret = True
    #except:
        #print(sys.exc_info()[1])
    #return ret
    

def geojson_to_czml(aList):
    cz = czml.CZML()
    for i in aList:
        if i.has_key('properties') and i['properties'].has_key('id'):
            packet = czml.CZMLPacket(id=i['properties']['id'])
            #tower
            if i['properties'].has_key('tower_code'):
                packet = czml.CZMLPacket(id=i['properties']['id'], name=i['properties']['tower_name'])
                packet.position = czml.Position(cartographicDegrees = [i['geometry']['coordinates'][0], i['geometry']['coordinates'][1], i['geometry']['coordinates'][2],])
                packet.point = czml.Point(show=True, color={'rgba': [255, 255, 0, 255]}, pixelSize=10, outlineColor={'rgba': [0, 0, 0, 255]}, outlineWidth=1)
                #packet.label = czml.Label(text=i['properties']['tower_name'], show=True, scale=0.5)
                packet.description = i['properties']['tower_name']
                #packet.billboard = czml.Billboard(image='http://localhost:88/img/tower.png')
                cz.append(packet)
    return cz
        
    
def handle_post_method(environ):
    global ENCODING
    global gRequest, gLoginToken
    buf = environ['wsgi.input'].read()
    
    querydict = {}
    if environ.has_key('QUERY_STRING'):
        querydict = urlparse.parse_qs(environ['QUERY_STRING'])
    #for k in d.keys():
        #kv = pair.split('=')
        #try:
            #d[kv[0]] = eval(kv[1])
        #except:
            #d[kv[0]] = kv[1]
    ret = {}
    is_upload = False
    is_mongo = False
    use_czml = False
    get_extext = False
    headers = {}
    try:
        ds_plus = urllib.unquote_plus(buf)
        obj = json.loads(dec(ds_plus))
        if obj.has_key(u'db') and obj.has_key(u'collection'):
            is_mongo = True
            dbname = obj[u'db']
            collection = obj[u'collection']
            action = None
            data = None
            if obj.has_key(u'action'):
                action = obj[u'action']
                del obj[u'action']
            if obj.has_key(u'data'):
                data = obj[u'data']
                del obj[u'data']
            if obj.has_key(u'use_czml') and obj[u'use_czml']:
                use_czml = True
                del obj[u'use_czml']
            if obj.has_key(u'get_extext') and obj[u'get_extext']:
                get_extext = True
                del obj[u'get_extext']
            del obj[u'db']
            del obj[u'collection']
            if action:
                if 'markdown_' in action or u'markdown_' in action:
                    l = db_util.mongo_action(dbname, collection, action, data, obj, 'markdown')
                else:
                    l = db_util.mongo_action(dbname, collection, action, data, obj)
            else:
                l = db_util.mongo_find(dbname, collection, obj)
            if get_extext:
                l = db_util.find_extent(l)
            if use_czml:
                l = geojson_to_czml(l)
            if isinstance(l, list) and len(l) >= 0:
                ret = l
            elif isinstance(l, dict) and len(l.keys()) > 0:
                ret = l
            elif isinstance(l, czml.CZML):
                headers['Content-Type'] = 'text/json;charset=' + ENCODING
                return '200 OK', headers, enc(l.dumps())
            #else:
                #ret["result"] = "%s.%s return 0 record" % (dbname, collection)
        else:
            ret["result"] = "unknown query operation"
        
    except:
        if len(querydict.keys())>0:
            try:
                is_upload = handle_upload_file(environ, querydict, buf)
                ret['result'] = ''
            except:
                ret['result'] = sys.exc_info()[1]
        obj = {}
    if not is_mongo:
        if obj.has_key('thunder_counter'):
            try:
                ret = handle_thunder_soap(obj)
            except:
                e = sys.exc_info()[1]
                if hasattr(e, 'message'):
                    ret['result'] = e.message
                else:
                    ret['result'] = str(e)
                
        elif obj.has_key('op'):
            if obj.has_key('area') and obj['area'] and len(obj['area'])>0:
                if obj['op'] in ['save','delete','update']:
                    ret = db_util.odbc_save_data_to_table(obj['table'], obj['op'], obj['data'], obj['line_id'], obj['start_tower_id'], obj['end_tower_id'], obj['area'])
                else:
                    ret = handle_requset_sync(obj)
            elif obj['op'] in ['alt','height'] :
                if obj.has_key('lng') and obj.has_key('lat') and isinstance(obj['lng'], float) and isinstance(obj['lat'], float):
                    ret = db_util.extract_one_altitude(obj['lng'], obj['lat'])
                if obj.has_key('data')  and isinstance(obj['data'], list):
                    ret = db_util.extract_many_altitudes(obj['data'])
            else:
                ret["result"] = "unknown area"
        elif obj.has_key('tracks') and obj.has_key('area'):
            ret = db_util.save_tracks(obj['tracks'], obj['area'])
        elif obj.has_key('mobile_action') and obj.has_key('area') and obj.has_key('data'):
            ret = db_util.mobile_action(obj['mobile_action'], obj['area'], obj['data'])
        
    if isinstance(ret, list): 
        pass
    elif isinstance(ret, str) or isinstance(ret, unicode) or isinstance(ret, int) or isinstance(ret, float):
        pass
    elif isinstance(ret, dict):
        if len(ret.keys())==0:
            pass
        elif ret.has_key('result'):
            if isinstance(ret['result'], exceptions.Exception):
                if hasattr(ret['result'], 'message'):
                    ret['result'] = ret['result'].message
                else:
                    ret['result'] = str(ret['result'])
            elif isinstance(ret['result'], str) or isinstance(ret['result'], unicode) or isinstance(ret['result'], int) or isinstance(ret['result'], float):
                pass
            elif isinstance(ret['result'], list) or isinstance(ret['result'], dict):
                pass
        else:    
            ret["result"] = "unknown operation"
    else:    
        ret["result"] = "unknown operation"
    headers['Content-Type'] = 'text/json;charset=' + ENCODING
    #time.sleep(6)
    #print(ret)
    #return [urllib.quote(enc(json.dumps(ret)))]
    return '200 OK', headers, json.dumps(ret, ensure_ascii=True, indent=4)


def register_authorize_platform(username, password):
    ret = None
    try:
        db_util.mongo_init_client('authorize_platform')
        db = db_util.gClientMongo['authorize_platform'][gConfig['authorize_platform']['mongodb']['database']]
        collection = db[gConfig['authorize_platform']['mongodb']['collection_user_account']]
        existone = collection.find_one({'username':username})
        if existone:
            raise Exception('username_exist')
        ret = collection.save({'username':username, 'password':password})
    except:
        raise
    return ret
def unregister_authorize_platform(username):
    ret = None
    try:
        db_util.mongo_init_client('authorize_platform')
        db = db_util.gClientMongo['authorize_platform'][gConfig['authorize_platform']['mongodb']['database']]
        collection = db[gConfig['authorize_platform']['mongodb']['collection_user_account']]
        existone = collection.find_one({'username':username})
        if existone is None:
            raise Exception('username_not_exist')
        ret = collection.remove({'_id':existone['_id']})
    except:
        raise
    return ret

def reset_password_authorize_platform(username, password):
    ret = None
    db_util.mongo_init_client('authorize_platform')
    db = db_util.gClientMongo['authorize_platform'][gConfig['authorize_platform']['mongodb']['database']]
    collection = db[gConfig['authorize_platform']['mongodb']['collection_user_account']]
    ret = collection.update({'username':username}, {'$set':{'password':password}},  multi=True, upsert=False)
    return ret
    

def login_authorize_platform(username, password, session):
    global gRequest, gSessionStore
    ret = None
    try:
        if gSessionStore and session:
            db_util.mongo_init_client('authorize_platform')
            db = db_util.gClientMongo['authorize_platform'][gConfig['authorize_platform']['mongodb']['database']]
            collection = db[gConfig['authorize_platform']['mongodb']['collection_user_account']]
            ret = collection.find_one({'username':username, 'password':password})
    except:
        raise
    return ret
    
    
    
    
    
    
def handle_login(environ):
    global ENCODING
    global gRequest
    buf = environ['wsgi.input'].read()
    ret = None
    try:
        ds_plus = urllib.unquote_plus(buf)
        obj = json.loads(dec(ds_plus))
        if obj.has_key(u'db') and obj.has_key(u'collection'):
            is_mongo = True
            dbname = obj[u'db']
            collection = obj[u'collection']
            action = None
            data = None
            if obj.has_key(u'action'):
                action = obj[u'action']
                del obj[u'action']
            if obj.has_key(u'data'):
                data = obj[u'data']
                del obj[u'data']
            if obj.has_key(u'url'):
                del obj[u'url']
            if obj.has_key(u'redirect'):
                del obj[u'redirect']
            del obj[u'db']
            del obj[u'collection']
            if action:
                ret = db_util.mongo_action(dbname, collection, action, data, obj)
    except:
        raise
    return ret

def handle_thunder_soap(obj):
    ret = {}
    if obj['thunder_counter'] == 'GetFlashofDate':
        ret = soap_GetFlashofDate(obj['start_time'], obj['end_time'])
    if obj['thunder_counter'] == 'GetFlashofEnvelope':
        ret = soap_GetFlashofEnvelope(obj['start_time'], obj['end_time'], obj['lng1'], obj['lng2'], obj['lat1'], obj['lat2'])
    return ret    

def dishen_ws_loop(aWebSocket, aHash):
    while 1:
        #now = time.strftime('%Y-%m-%d %H:%M:%S')[:10]
        #ws.send("%d,%f\n" % ((time.time() - time.timezone)*1000, random.random()*10))
        #t = (time.time() - time.timezone) * 1000
        t = time.time()  * 1000
        if aWebSocket:
            #message = aWebSocket.receive()
            #print("message=%s" % message)
            aWebSocket.send( '%s\n%d' % (str(aHash),int(t)) )
        else:
            break
        gevent.sleep(1.0)

def handle_websocket(environ):
    global gCapture, gGreenlets
    #for k, v in environ.iteritems():
        #print('%s=%s' % (k,str(v)))
    headers = {}
    ws = environ["wsgi.websocket"]
    print(dir(ws))
    #print(dir(ws.rfile))
    #print(dir(ws.socket))
    if environ['PATH_INFO'] == '/dishen_ws':
        glet = gevent.getcurrent()
        ghash = glet.__hash__()
        gGreenlets[str(ghash)] = (glet, ws)
        dishen_ws_loop(ws, ghash)
    s = 'version=%s' % ( environ['wsgi.websocket_version'])
    headers['Content-Type'] = 'text/plain;charset=' + ENCODING
    return '200 OK', headers, s



def check_session(environ, request, session_store):
    global gConfig
    
        
    def set_cookie(key, value):
        secure = False
        if gConfig['listen_port']['enable_ssl'].lower() == 'true':
            secure = True
        max_age = int(gConfig['authorize_platform']['session']['session_age'])
        cookie = ('Set-Cookie', dump_cookie(key, value, domain=str(gConfig['authorize_platform']['session']['session_domain']), max_age=max_age, secure=secure))
        return cookie
    
    sid = request.cookies.get('authorize_platform_session_id')
    cookie = None
    is_expire = False
    sess = None
    
    #session_store.delete_expired_list()
    if sid is None:
        request.session = session_store.new({})
        session_store.save(request.session)
        is_expire = True
        cookie = set_cookie('authorize_platform_session_id', request.session.sid )
        sess = request.session
    else:
        request.session = session_store.get(sid)
        if request.session:
            cookie = set_cookie('authorize_platform_session_id', request.session.sid)
            session_store.save_if_modified(request.session)
        else:
            cookie = set_cookie('authorize_platform_session_id', '')
            is_expire = True
        sess = request.session
    return sess, cookie, is_expire


def session_handle(environ, request, session_store):
    global gConfig
    def set_cookie(key, value):
        secure = False
        if gConfig['listen_port']['enable_ssl'].lower() == 'true':
            secure = True
        max_age = int(gConfig['web']['cookie']['max_age'])
        cookie = ('Set-Cookie', dump_cookie(key, value, max_age=max_age, secure=secure))
        return cookie
    
    sid = request.cookies.get('session_id')
    
    is_expire = False
    if sid is None:
        request.session = session_store.new()
        session_store.save(request.session)
        is_expire = True
    else:
        request.session = session_store.get(sid)
    cookie = set_cookie('session_id', request.session.sid)
    if request.session.should_save:
        #print('should_save')
        session_store.save(request.session)
    return cookie, is_expire
        
def get_token_from_env(environ):
    global gConfig, gLoginToken
    cookie = parse_cookie(environ)
    session_id = None
    ret = None
    if cookie.has_key('session_id'):
        session_id = cookie['session_id']
        if gLoginToken.has_key(session_id):
            ret = gLoginToken[session_id]
    return session_id, ret

def get_session_from_env(environ):
    global gSessionStore
    cookie = parse_cookie(environ)
    session_id = None
    ret = None
    if cookie.has_key('session_id'):
        session_id = cookie['session_id']
        ret = gSessionStore.get(session_id)
    return ret

def get_userinfo_from_env(environ):
    global gConfig, gLoginToken
    cookie = parse_cookie(environ)
    session_id = None
    ret = None
    if cookie.has_key('session_id'):
        session_id = cookie['session_id']
        if gLoginToken.has_key(session_id):
            ret = gLoginToken[session_id]
    return session_id, ret
    

def auth_check(session, username, isnew):
    global ENCODING
    global gRequest, gSessionStore
    headers = {}
    headers['Content-Type'] = 'text/json;charset=' + ENCODING
    statuscode = '200 OK'
    body = ''
    if session :
        if username and len(username.strip())>0:
            if isnew is True:
                session['username'] = username.strip()
                gSessionStore.save(session)
                body = json.dumps({'result':u'auth_check_ok_session_saved'}, ensure_ascii=True, indent=4)
            else:
                if session.sid:
                    user = gSessionStore.get_data_by_username(session.sid, username.strip())
                    if user:
                        body = json.dumps({'result':u'auth_check_ok_user_exist'}, ensure_ascii=True, indent=4)
                    else:
                        body = json.dumps({'result':u'auth_check_fail_session_expired'}, ensure_ascii=True, indent=4)
                else:
                    body = json.dumps({'result':u'auth_check_fail_session_expired'}, ensure_ascii=True, indent=4)
        else:
            body = json.dumps({'result':u'auth_check_fail_username_require'}, ensure_ascii=True, indent=4)
    else:
        body = json.dumps({'result':u'auth_check_fail_session_expired'}, ensure_ascii=True, indent=4)
    return statuscode, headers, body    
    
    
    
    


class BooleanConverter(BaseConverter):
    def __init__(self, url_map, randomify=False):
        super(BooleanConverter, self).__init__(url_map)
        self.regex = '(?:true|false)'

    def to_python(self, value):
        return value == 'true'

    def to_url(self, value):
        return value and 'true' or 'false'

    
def handle_authorize_platform(environ, session):
    global ENCODING
    global gConfig, gRequest, gSessionStore, gUrlMapAuth, gSecurityConfig
    
    def get_username_password_by_GET_POST(environ):
        username = None
        password = None
        querydict = {}
        if environ.has_key('QUERY_STRING'):
            querydict = urlparse.parse_qs(environ['QUERY_STRING'])
            if querydict.has_key('username'):
                username = querydict['username']
                if isinstance(username, list):
                    username = username[0]
            if querydict.has_key('password'):
                password = querydict['password']
                if isinstance(password, list):
                    password = password[0]
                
        else:
            try:
                buf = environ['wsgi.input'].read()
                ds_plus = urllib.unquote_plus(buf)
                obj = json.loads(dec(ds_plus))
                if obj.has_key('username'):
                    username = obj['username']
                if obj.has_key('password') :
                    password = obj['password']
            except:
                pass
        return username, password    
    
    
    headers = {}
    headers['Content-Type'] = 'text/json;charset=' + ENCODING
    statuscode = '200 OK'
    body = ''
    username = None
    password = None
    isnew = False
    urls = gUrlMapAuth.bind_to_environ(environ)
    try:
        endpoint, args = urls.match()
        #print('-------')
        #print(endpoint)
        #print(args)
        #body = endpoint
        if args.has_key('username'):
            username = args['username']
        if args.has_key('password'):
            password = args['password']
        if username is None and password is None:
            username, password = get_username_password_by_GET_POST(environ)
        
        if endpoint == 'auth_check':
            if username is not None:
                statuscode, headers, body = auth_check(session, username, False)
            else:
                body = json.dumps({'result':u'auth_check_fail_username_required'}, ensure_ascii=True, indent=4)
        elif endpoint == 'get_salt':
            if len(gSecurityConfig.keys())>0:
                body = json.dumps({'result':'get_salt_ok','salt':gSecurityConfig['password_salt']}, ensure_ascii=True, indent=4)
            else:
                body = json.dumps({'result':'get_salt_fail'}, ensure_ascii=True, indent=4)
        elif endpoint == 'register':
            if username is not None and password is not None:
                _id = None
                try:
                    _id = register_authorize_platform(username, password)
                except:
                    if hasattr(sys.exc_info()[1], 'message') and sys.exc_info()[1].message == 'username_exist':
                        body = json.dumps({'result':u'register_fail_username_exist'}, ensure_ascii=True, indent=4)
                    _id = None    
                if _id:
                    body = json.dumps({'result':u'register_ok'}, ensure_ascii=True, indent=4)
                    if gConfig['authorize_platform']['register']['login_when_register_success'].lower() == 'true':
                        session['username'] = username.strip()
                else:
                    if len(body)==0:
                        body = json.dumps({'result':u'register_fail'}, ensure_ascii=True, indent=4)
            else:
                body = json.dumps({'result':u'register_fail_username_password_required'}, ensure_ascii=True, indent=4)
        elif endpoint == 'unregister':
            if username is not None:
                wr = None
                try:
                    wr = unregister_authorize_platform(username, password)
                except:
                    if hasattr(sys.exc_info()[1], 'message') and sys.exc_info()[1].message == 'username_not_exist':
                        body = json.dumps({'result':u'unregister_fail_username_not_exist'}, ensure_ascii=True, indent=4)
                    
                if wr and wr['n']>0:
                    body = json.dumps({'result':u'unregister_ok'}, ensure_ascii=True, indent=4)
                else:
                    if len(body)==0:
                        body = json.dumps({'result':u'unregister_fail'}, ensure_ascii=True, indent=4)
            else:
                body = json.dumps({'result':u'unregister_fail_username_required'}, ensure_ascii=True, indent=4)
            
        elif endpoint == 'reset_password':
            if username is not None and password is not None:
                wr = reset_password_authorize_platform(username, password)
                if wr :
                    if wr['n']>0:
                        body = json.dumps({'result':u'reset_password_ok'}, ensure_ascii=True, indent=4)
                    else:
                        body = json.dumps({'result':u'reset_password_fail_username_not_exist'}, ensure_ascii=True, indent=4)
                else:
                    if len(body)==0:
                        body = json.dumps({'result':u'reset_password_fail'}, ensure_ascii=True, indent=4)
            else:
                body = json.dumps({'result':u'reset_password_fail_username_password_required'}, ensure_ascii=True, indent=4)
        elif endpoint == 'login':
            if username is not None and password is not None:
                obj = login_authorize_platform(username, password, session)
                if obj:
                    body = json.dumps({'result':u'login_ok'}, ensure_ascii=True, indent=4)
                    session['username'] = username.strip()
                else:
                    body = json.dumps({'result':u'login_fail_wrong_user_or_password'}, ensure_ascii=True, indent=4)
            else:
                body = json.dumps({'result':u'login_fail_username_password_required'}, ensure_ascii=True, indent=4)
        elif endpoint == 'logout':
            if gSessionStore and session:
                gSessionStore.delete(session)
                session = None
            body = json.dumps({'result':u'logout_ok'}, ensure_ascii=True, indent=4)
        else:
            body = json.dumps({'result':u'access_deny'}, ensure_ascii=True, indent=4)
    except HTTPException, e:
        body = json.dumps({'result':u'access_deny'}, ensure_ascii=True, indent=4)
    if session:
        gSessionStore.save(session)
        
    return statuscode, headers, body


gUrlMapAuth = Map([
    Rule('/', endpoint='firstaccess'),
    #Rule('/auth_check/<username>/isnew/<bool:isnew>', endpoint='saveuser'),
    Rule('/get_salt', endpoint='get_salt'),
    Rule('/auth_check/<username>', endpoint='auth_check'),
    Rule('/auth_check', endpoint='auth_check'),
    Rule('/register/<username>/<password>', endpoint='register'),
    Rule('/register/<username>', endpoint='register'),
    Rule('/register', endpoint='register'),
    Rule('/unregister/<username>', endpoint='unregister'),
    Rule('/unregister', endpoint='unregister'),
    Rule('/login/<username>/<password>', endpoint='login'),
    Rule('/login/<username>', endpoint='login'),
    Rule('/login', endpoint='login'),
    Rule('/logout', endpoint='logout'),
    Rule('/reset_password/<username>/<password>', endpoint='reset_password'),
    Rule('/reset_password/<username>', endpoint='reset_password'),
    Rule('/reset_password', endpoint='reset_password'),
], converters={'bool': BooleanConverter})



def application_authorize_platform(environ, start_response):
    global STATICRESOURCE_DIR
    global gConfig, gRequest, gSessionStore
    
    def check_is_static(aUrl):
        ret = False
        surl = dec(aUrl)
        if surl[0:2] == '//':
            surl = surl[2:]
        if surl[0] == '/':
            surl = surl[1:]
        p = os.path.join(STATICRESOURCE_DIR , surl)
        isBin = False
        ext = os.path.splitext(p)[1]
        if '.' in surl:
            ext = surl[surl.rindex('.'):]
        else:
            ext = os.path.splitext(p)[1]
        if len(ext)>0 and  gConfig['mime_type'].has_key(ext):
            ret = True
        return ret
        
    
    
    
    headers = {}
    headers['Access-Control-Allow-Origin'] = '*'
    headerslist = []
    cookie_header = None
    body = None
    statuscode = '200 OK'
    
    path_info = environ['PATH_INFO']
    
    if gSessionStore is None:
        gSessionStore = MongodbSessionStore(host=gConfig['authorize_platform']['mongodb']['host'], 
                                            port=int(gConfig['authorize_platform']['mongodb']['port']), 
                                            replicaset=gConfig['authorize_platform']['mongodb']['replicaset'],
                                            db = gConfig['authorize_platform']['mongodb']['database'],
                                            collection = gConfig['authorize_platform']['mongodb']['collection_session'],
                                            )
    is_expire = False
    
    headerslist.append(('Content-Type', 'text/json;charset=' + ENCODING))
    statuscode = '200 OK'
    if path_info[-1:] == '/':
        #path_info += gConfig['web']['indexpage']
        #statuscode, headers, body =  handle_static(environ, path_info)
        body = json.dumps({'result':u'access_deny'}, ensure_ascii=True, indent=4)
    elif check_is_static(path_info):
        statuscode, headers, body =  handle_static(environ, path_info)
    else:    
        with session_manager(environ):
            sess, cookie_header, is_expire = check_session(environ, gRequest, gSessionStore)
            if is_expire:
                headerslist.append(('Content-Type', 'text/json;charset=' + ENCODING))
                statuscode = '200 OK'
                body = json.dumps({'result':u'session_expired'}, ensure_ascii=True, indent=4)
                if sess:
                    gSessionStore.save_if_modified(sess)
            else:
                statuscode, headers, body = handle_authorize_platform(environ, sess)
                
    if cookie_header:
        headerslist.append(cookie_header)
    for k in headers:
        headerslist.append((k, headers[k]))
    #print(headerslist)
    start_response(statuscode, headerslist)
    return [body]
    
    
    
def application(environ, start_response):
    global gConfig, gRequest, gSessionStore
    headers = {}
    headers['Access-Control-Allow-Origin'] = '*'
    headerslist = []
    cookie_header = None
        
    path_info = environ['PATH_INFO']
    if 'proxy.cgi' in path_info:
        statuscode, headers, body = handle_proxy_cgi(environ)
    elif path_info == '/test':
        statuscode, headers, body = handle_test(environ)
    elif path_info == '/get':
        statuscode, headers, body = handle_get_method(environ)
    elif path_info == '/post':
        statuscode, headers, body = handle_post_method(environ)
    elif path_info == '/wmts':
        statuscode, headers, body = handle_wmts(environ)
    elif path_info == '/tiles':
        statuscode, headers, body = handle_tiles(environ)
    elif '/arcgistile' in path_info:
        statuscode, headers, body = handle_arcgistile(environ)
    elif path_info == '/terrain/layer.json' or path_info[-8:] == '.terrain':
        statuscode, headers, body = handle_terrain(environ)
    #elif path_info[-8:] == '.terrain':
        #return handle_terrain1(environ)
    elif path_info == '/wfs':
        statuscode, headers, body = handle_wfs(environ)
    elif path_info =='/create_cluster' or  path_info =='/kill_cluster':
        statuscode, headers, body = handle_cluster(environ)
    elif path_info == gConfig['websocket']['services']:
        #if p=='/control':
            #print('websocket_version=%s' % environ['wsgi.websocket_version'])
        try:
            statuscode, headers, body = handle_websocket(environ)
        except geventwebsocket.WebSocketError,e:
            print('application Exception:%s' % str(e))
        
    else:
        if gConfig['web']['session']['enable_session'].lower() == 'true' :
            #return handle_session(environ, start_response)
            if gSessionStore is None:
                gSessionStore = FilesystemSessionStore()
            is_expire = False
            with session_manager(environ):
                cookie_header, is_expire = session_handle(environ, gRequest, gSessionStore)
                
                for k in headers:
                    headerslist.append((k, headers[k]))
                
                if is_expire:
                    headerslist.append(('Location', str(gConfig['web']['expirepage'])))
                    headerslist.append(cookie_header)
                    start_response('302 Redirect', headerslist)        
                    return ['']
                if path_info == '/logout':
                    #session_id, token = get_token_from_env(environ)
                    #if session_id and gLoginToken.has_key(session_id):
                        #del gLoginToken[session_id]
                    sess = get_session_from_env(environ)
                    if sess:
                        gSessionStore.delete(sess)
                    headerslist.append(cookie_header)
                    headerslist.append(('Content-Type', 'text/json;charset=' + ENCODING))
                    start_response('200 OK', headerslist)        
                    return [json.dumps({'result':u'ok'}, ensure_ascii=True, indent=4)]
                if path_info == '/login':
                    sess = get_session_from_env(environ)
                    if sess is None:
                        sess = gSessionStore.new()
                    objlist = handle_login(environ)
                    if len(objlist)>0:
                        #sess = gSessionStore.new()
                        sess = gSessionStore.session_class(objlist[0], sess.sid, False)
                        gSessionStore.save(sess)
                        start_response('200 OK', headerslist)
                        return [json.dumps(sess, ensure_ascii=True, indent=4)]
                    else:
                        headerslist.append(cookie_header)
                        headerslist.append(('Content-Type', 'text/json;charset=' + ENCODING))
                        start_response('200 OK', headerslist)        
                        return [json.dumps({'result':u'用户名或密码错误'}, ensure_ascii=True, indent=4)]
                            
                    #else:
                        #headerslist.append(cookie_header)
                        #headerslist.append(('Content-Type', 'text/json;charset=' + ENCODING))
                        #start_response('200 OK', headerslist)        
                        #return [json.dumps(copy.copy(sess), ensure_ascii=True, indent=4)]
                        
                        
                    ##session_id, token = get_token_from_env(environ)
                    #objlist = handle_login(environ)
                    #if session_id and len(objlist)>0:
                        ##gLoginToken[session_id] = objlist[0]
                        #headerslist.append(cookie_header)
                        #headerslist.append(('Content-Type', 'text/json;charset=' + ENCODING))
                        #start_response('200 OK', headerslist)        
                        #return [json.dumps(objlist[0], ensure_ascii=True, indent=4)]
                    #else:
                        #headerslist.append(cookie_header)
                        #headerslist.append(('Content-Type', 'text/json;charset=' + ENCODING))
                        #start_response('200 OK', headerslist)        
                        #return [json.dumps({'result':u'用户名或密码错误'}, ensure_ascii=True, indent=4)]
                        
                if path_info == gConfig['web']['mainpage']:
                    #session_id, token = get_token_from_env(environ)
                    sess = get_session_from_env(environ)
                    #401 Unauthorized
                    #if session_id is None or token is None:
                    if sess is None or len(sess.keys())==0:
                        headerslist.append(('Content-Type', str(gConfig['mime_type']['.html'])))
                        headerslist.append(cookie_header)
                        statuscode, headers, body =  handle_static(environ, gConfig['web']['unauthorizedpage'])
                        statuscode = '401 Unauthorized'
                        start_response(statuscode, headerslist) 
                        return [body]
        if path_info[-1:] == '/':
            path_info += gConfig['web']['indexpage']
        if path_info == '/login' and not gConfig['web']['session']['enable_session'].lower() == 'true':
            path_info = gConfig['web']['mainpage']
        statuscode, headers, body =  handle_static(environ, path_info)
        
    #headkeys = set([i[0] for i in headerslist])
    if cookie_header:
        headerslist.append(cookie_header)
    for k in headers:
        headerslist.append((k, headers[k]))
    #print(headerslist)
    start_response(statuscode, headerslist)
    return [body]

#def handle_session(environ, start_response):
    
    
    
    
def handle_proxy_cgi(environ):
    global gConfig
    method = environ['REQUEST_METHOD']
    post_data = ''
    if method == "POST":
        qs = environ['PATH_INFO']
        buf = environ['wsgi.input'].read()
        post_data = urllib.unquote_plus(buf)
        
        d = cgi.parse(None, environ)
        
        if d.has_key("url"):
            url = d["url"][0]
        else:
            url = 'http://XIEJUN-DESKTOP:88'
    else:
        fs = cgi.FieldStorage()
        url = fs.getvalue('url', "http://XIEJUN-DESKTOP:88")
    s = ''
    headers = {'Content-Type': 'text/plain;charset=' + ENCODING}
    try:
        #host = url.split("/")[2]
        #if allowedHosts and not host in allowedHosts:
            #s += "Status: 502 Bad Gateway"
            #s += "Content-Type: text/plain"
            #s += "This proxy does not allow you to access that location (%s)." % (host,)
            
      
        if url.startswith("http://") or url.startswith("https://"):
            request = None
            response = None
            http = None
            urlobj = URL(url)
            if method == "POST":
                #length = int(environ["CONTENT_LENGTH"])
                headers["Content-Type"] = environ["CONTENT_TYPE"]
                #body = sys.stdin.read(length)
                #r = urllib2.Request(url, body, headers)
                #request = urllib2.Request(url, post_data, headers=headers)
                #request = urllib2.Request(url, post_data, headers=headers)
                #y = urllib2.urlopen(request, data=post_data)
                http = HTTPClient.from_url(urlobj)
                #y = http.post(urlobj.request_uri, post_data, headers)
                g = gevent.spawn(http.post, urlobj.request_uri, post_data, headers)
                g.start()
                while not g.ready():
                    if g.exception:
                        break
                    gevent.sleep(0.1)
                response = g.value
            else:
                http = HTTPClient.from_url(urlobj)
                #y = http.get(urlobj.request_uri)
                g = gevent.spawn(http.get, urlobj.request_uri)
                g.start()
                while not g.ready():
                    if g.exception:
                        break
                    gevent.sleep(0.1)
                response = g.value
                
            
            if response:
                h = str(response.info())
                #if i.has_key("Content-Type"):
                    #print("Content-Type: %s" % (i["Content-Type"]))
                hh = eval(h)
                responseh = []
                for i in hh:
                    if i[0] in ['Content-Type', 'Date', 'Server', ]:
                        responseh.append(i)
                s = response.read()
                #response.release()
                http.close()
                headers['Content-Length'] = str(len(s))
                #print(responseh)
        else:
            #print("Content-Type: text/plain")
            s += "Illegal request."
    
    except Exception, E:
        s += "Status: 500 Unexpected Error"
        s += "Content-Type: text/plain"
        s += "Some unexpected error occurred. Error text was:%s" % E.message
    return '200 OK', headers, s
    
            


def get_host_ip():
    ret = []
    if sys.platform == 'win32':
        ret.append('127.0.0.1')
        localIP = socket.gethostbyname(socket.gethostname())
        #print ("local ip:%s " % localIP)
        ipList = socket.gethostbyname_ex(socket.gethostname())
        for i in ipList:
            if i != localIP:
                #if isinstance(i, str):
                    #print(re.findall('\d+\.\d+\.\d+\.\d+',i))
                if isinstance(i, list):
                    for ii in i:
                        if len(re.findall('\d+\.\d+\.\d+\.\d+',ii))>0:
                            ret.append(ii)
                #print("external IP:%s" % i )
    elif 'linux' in sys.platform:
        import commands
        ips = commands.getoutput("/sbin/ifconfig | grep -i \"inet\" | grep -iv \"inet6\" |  awk {'print $2'} | sed -ne 's/addr\:/ /p'")
        arr = ips.split('\n')
        for i in arr:
            ret.append(i.strip())
    return ret
           
        
def clear_tmp():
    tmp_dir = r'C:\Users\Jeffrey\AppData\Local\ESRI\Local Caches\MapCacheV1'
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    tmp_dir = r'C:\Users\Jeffrey\AppData\Local\ESRI\Local Caches\GlobeCache'
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

def get_scaleDenominator(zoomlist):
    #tileMatrixMaxX = tileMatrixMinX +  tileWidth * (scaleDenominator * pixelSize / metersPerUnit) * matrixWidth 
    #tileMatrixMinY = tileMatrixMaxY -  tileHeight * (scaleDenominator * pixelSize / metersPerUnit) * matrixHeight
    
    #tileWidth * (scaleDenominator * pixelSize / metersPerUnit) * matrixWidth    = tileMatrixMaxX - tileMatrixMinX   
    #tileHeight * (scaleDenominator * pixelSize / metersPerUnit) * matrixHeight  = tileMatrixMaxY - tileMatrixMinY
    
    #scaleDenominator * pixelSize / metersPerUnit     = (tileMatrixMaxX - tileMatrixMinX)/(tileWidth * matrixWidth)
    #scaleDenominator * pixelSize / metersPerUnit   = (tileMatrixMaxY - tileMatrixMinY)/(tileHeight * matrixHeight)
    
    #scaleDenominator * pixelSize  = metersPerUnit * (tileMatrixMaxX - tileMatrixMinX)/(tileWidth * matrixWidth)
    #scaleDenominator * pixelSize  = metersPerUnit * (tileMatrixMaxY - tileMatrixMinY)/(tileHeight * matrixHeight)
    
    #scaleDenominator   = metersPerUnit/pixelSize * (tileMatrixMaxX - tileMatrixMinX)/(tileWidth * matrixWidth)
    #scaleDenominator   = metersPerUnit/pixelSize * (tileMatrixMaxY - tileMatrixMinY)/(tileHeight * matrixHeight)
    
    metersPerUnit = float(gConfig['wmts']['metersPerUnit'])
    pixelSize = float(gConfig['wmts']['pixelSize'])
    tileWidth,tileHeight = 256.0, 256.0
    tileMatrixMinX, tileMatrixMaxX = (26.0, 102.0), (26.0, 104.0)
    tileMatrixMinY, tileMatrixMaxY = (24.0, 102.0), (26.0, 102.0)
    for i in zoomlist:
        #print('%d=%d' % (i , mapUtils.tiles_on_level(i)))
        #mapUtils.countDistanceFromLatLon()
        matrixHeight = matrixWidth = mapUtils.tiles_on_level(i)
        print('%d=%d' % (i , matrixHeight))
        #scaleDenominatorX   = metersPerUnit/pixelSize * mapUtils.countDistanceFromLatLon(tileMatrixMaxX , tileMatrixMinX) * 1000./(tileWidth * matrixWidth)
        #scaleDenominatorY   = metersPerUnit/pixelSize * mapUtils.countDistanceFromLatLon(tileMatrixMaxY , tileMatrixMinY) * 1000./(tileHeight * matrixHeight)
        #print('scaleDenominatorX=%f, scaleDenominatorY=%f' % (scaleDenominatorX, scaleDenominatorY))
        #scaleDenominator   = metersPerUnit/pixelSize * mapUtils.countDistanceFromLatLon(tileMatrixMaxY , tileMatrixMinY) * 1000. /(tileHeight * matrixHeight)
        scaleDenominator   = metersPerUnit/pixelSize * mapUtils.countDistanceFromLatLon(tileMatrixMaxY , tileMatrixMinY)  /(tileHeight * matrixHeight)
        print('scaleDenominator=%f' % scaleDenominator)
    

def ToGeographic(mercatorX_lon, mercatorY_lat):
    if abs(mercatorX_lon) < 180 and  abs(mercatorY_lat) < 90:
        return 0, 0
    if abs(mercatorX_lon) > 20037508.3427892 or abs(mercatorY_lat) > 20037508.3427892 :
        return 0, 0

    x = mercatorX_lon;
    y = mercatorY_lat;
    num3 = x / 6378137.0;
    num4 = num3 * 57.295779513082323;
    num5 = math.floor(float(num4 + 180.0) / 360.0)
    num6 = num4 - (num5 * 360.0)
    num7 = 1.5707963267948966 - (2.0 * math.atan(math.exp((-1.0 * y) / 6378137.0)))
    lon = num6
    lat = num7 * 57.295779513082323
    return lon, lat


def ToWebMercator(lon, lat):
    if abs(lon) > 180 or abs(lat) > 90:
        return 0, 0
    num = lon * 0.017453292519943295
    x = 6378137.0 * num
    a = lat * 0.017453292519943295

    mercatorX_lon = x
    mercatorY_lat = 3189068.5 * math.log((1.0 + math.sin(a)) / (1.0 - math.sin(a)))
    return mercatorX_lon, mercatorY_lat




            
def handle_requset_sync(obj):
    ret = {'result':''}
    if obj.has_key('area') and obj['area'] and len(obj['area'])>0:
        kmgd, kmgdgeo, kmgdgeotmp = db_util.create_sde_conn(obj['area'])
        if obj.has_key('odbc'):
            if obj['odbc'] == 'TABLE_LINE':
                l = db_util.odbc_get_records('TABLE_LINE', '1=1', obj['area'])
                ret['result']= l
                    
            elif obj['odbc'] == 'TABLE_TOWER':
                l = db_util.odbc_get_records('TABLE_TOWER', '1=1', obj['area'])
                ret['result']= l
        elif obj.has_key('op'):
            if obj['op']=='download_task':
                condition = '1=1'
                if obj.has_key('team_id'):
                    condition += " AND team_id='%s'" % obj['team_id']
                l = db_util.odbc_get_records('VIEW_TASK_ITEM', condition, obj['area'])
                ret['result']= l
            #elif obj['op']=='get_latest_stamp':
                #f = '%Y-%m-%d %H:%M:%S'
                #if obj.has_key('format'):
                    #f  = obj['format']
                #ret['result']= db_util.get_latest_stamp(f, obj['area'])
            #elif obj['op']=='get_latest_3dd_stamp':
                #f = '%Y-%m-%d %H:%M:%S'
                #if obj.has_key('format'):
                    #f  = obj['format']
                #ret['result']= db_util.get_latest_3dd_stamp(f, obj['area'])
    else:
        print('unknown area')
        ret['result'] = []
    return ret




def soap_login():
    client = SoapClient(wsdl='%s?wsdl' % gConfig['webservice']['location'], namespace = gConfig['webservice']['namespace'], timeout=int(gConfig['webservice']['timeout']))
    response = client.login(username='', password='')
    result = response['Result']
    return result

def parse_thunder_counter_xml(xml):
    ret = []
    root = etree.fromstring(xml)
    if root:
        for Flash in root:
            obj = {}
            for child in Flash:
                obj[child.tag] = child.text
            ret.append(obj)
    return ret
    
    
def soap_GetFlashofDate(start_time, end_time):
    ret = {}
    try:
        client = SoapClient(wsdl='%s?wsdl' % gConfig['webservice']['location'], namespace = gConfig['webservice']['namespace'], timeout=int(gConfig['webservice']['timeout']))
        response = client.GetFlashofDate(in0=start_time, in1=end_time)
        result = response['Result']
        ret = parse_thunder_counter_xml(result)
    except:
        if hasattr(sys.exc_info()[1], 'message'):
            ret['err'] = sys.exc_info()[1].message
        if hasattr(sys.exc_info()[1], 'reason'):
            ret['err'] = str(sys.exc_info()[1].reason)
    return ret




def soap_GetFlashofEnvelope(start_time, end_time, lng1, lng2, lat1, lat2):
    ret = {}
    try:
        client = SoapClient(wsdl='%s?wsdl' % gConfig['webservice']['location'], namespace = gConfig['webservice']['namespace'], timeout=int(gConfig['webservice']['timeout']))
        response = client.GetFlashofEnvelope(in0=start_time, in1=end_time, in2=lng1, in3=lng2, in4=lat1, in5=lat2)
        result = response['Result']
        ret = parse_thunder_counter_xml(result)
    except:
        if hasattr(sys.exc_info()[1], 'message'):
            ret['err'] = sys.exc_info()[1].message
        if hasattr(sys.exc_info()[1], 'reason'):
            ret['err'] = str(sys.exc_info()[1].reason)
    return ret


def delete_expired_session(interval):
    global gSessionStore
    while 1:
        gevent.sleep(interval)
        if gSessionStore:
            #print('session recycle checking')
            gSessionStore.delete_expired_list()
    
    
    
def cycles_task():
    global gConfig
    gevent.spawn(delete_expired_session, int(gConfig['authorize_platform']['session']['session_cycle_check_interval']))
    
    
    
def mainloop_single( port=None, enable_cluster=False, enable_ssl=False):
    global gConfig
    gen_model_app_cache()
    server = None
    app = application
    if gConfig['authorize_platform']['enable'].lower() in ['true',u'true','1', u'1']:
        app = application_authorize_platform
        cycles_task()
    if port and not enable_cluster:
        if enable_ssl:
            print('listening at host 127.0.0.1, port %d with ssl crypted' % port)
            server = pywsgi.WSGIServer(('127.0.0.1', port), app, handler_class = WebSocketHandler, keyfile = gConfig['listen_port']['keyfile'], certfile = gConfig['listen_port']['certfile'])
        else:    
            print('listening at host 127.0.0.1, port %d' % port)
            server = pywsgi.WSGIServer(('127.0.0.1', port), app, handler_class = WebSocketHandler)
            
        server.start()
        server.serve_forever()
    else:
        if enable_ssl:
            pport = port
            if not pport:
                pport = gConfig['listen_port']['ssl_port']
        else:
            pport = port
            if not pport:
                pport = gConfig['listen_port']['port']
            
        host_list = get_host_ip()
        admin = ''
        if enable_cluster:
            admin = 'cluster manager '
        print('%slistening at host %s, port %s' % (admin, str(host_list), str(pport)))
        
        
        servers = []
        #if gConfig['webservice']['enable']  in [u'true', u'TRUE']:
            #h, p = gConfig['webservice']['host'], int(gConfig['webservice']['port'])
            #print('listening webservice at http://%s:%d/webservice' % (h, p))
            #server = pywsgi.WSGIServer((h, p), get_wsapplication())
            #servers.append(server)
            #server.start()
        
        if len(host_list)>0:
            idx = 0
            if isinstance(pport, int):
                for i in host_list:
                    if enable_ssl:
                        server = pywsgi.WSGIServer((i, pport), app, handler_class = WebSocketHandler, keyfile = gConfig['listen_port']['keyfile'], certfile = gConfig['listen_port']['certfile'])
                    else:
                        server = pywsgi.WSGIServer((i, pport), app, handler_class = WebSocketHandler)
                    servers.append(server)
                        
                    if idx < len(host_list)-1:
                        server.start()
    
                    idx += 1
                servers[-1].serve_forever()
            elif isinstance(pport, unicode):
                for i in host_list:
                    if enable_ssl:
                        server = pywsgi.WSGIServer((i, int(pport)), app, handler_class = WebSocketHandler, keyfile = gConfig['listen_port']['keyfile'], certfile = gConfig['listen_port']['certfile'])
                    else:
                        server = pywsgi.WSGIServer((i, int(pport)), app, handler_class = WebSocketHandler)
                        #server = pywsgi.WSGIServer((i, int(pport)), application)
                    servers.append(server)
                    if idx < len(host_list)-1:
                        server.start()
    
                    idx += 1
                servers[-1].serve_forever()
            elif isinstance(pport, list):
                for i in host_list:
                    for j in pport:
                        if enable_ssl:
                            server = pywsgi.WSGIServer((i, int(j)), app, handler_class = WebSocketHandler, keyfile = gConfig['listen_port']['keyfile'], certfile = gConfig['listen_port']['certfile'])
                        else:    
                            server = pywsgi.WSGIServer((i, int(j)), app, handler_class = WebSocketHandler)
                        servers.append(server)
                        if idx < len(host_list) * len(pport)-1:
                            server.start()
                        
                        idx += 1
                servers[-1].serve_forever()
        else:
            print('wrong host or port in %s' % db_util.CONFIGFILE)
    return server


def mainloop_nginx(popen):
    while True:
        stdoutdata, stderrdata = popen.communicate()
        #if stdoutdata:
            #queue.put(stdoutdata)
        gevent.sleep(0.01)
    
    
def mainloop_manager(queue):
    while True:
        qget = q.get()
        if qget:
            print(qget)
        gevent.sleep(0.01)
    
    
    
def create_cluster():
    #global gConfig,  gClusterProcess
    conf = ''
    with open(gConfig['cluster']['nginx_conf_template']) as f:
        conf = f.read()
    rg = gConfig['cluster']['port_range']
    node_list = '\n'
    for port in range(int(rg[0]), int(rg[1]), int(rg[2])):
        node_list += '        server 127.0.0.1:%d;\n' % port
    listen_port = gConfig['listen_port']['port']
    access_log = gConfig['cluster']['nginx_log']
    host = get_host_ip()
    host.append('localhost')
    server_name = ' '.join(host)
    conf = conf.replace('[node_list]', str(node_list))
    conf = conf.replace('[listen_port]', str(listen_port))
    conf = conf.replace('[access_log]', str(access_log))
    conf = conf.replace('[server_name]', str(server_name))
    p = os.path.abspath(gConfig['cluster']['nginx_conf_template'])
    p = os.path.join(os.path.dirname(p), 'nginx.conf')
    #print(conf)
    with open(p, 'w') as f:
        f.write(conf)
    
    idx = 0
    for port in range(int(rg[0]), int(rg[1]), int(rg[2])):
        print('process%d is starting...' % idx)
        proc = Process(target=mainloop_single, args=(port, False, False))
        proc.start()
        #gClusterProcess[str(proc.pid)] = proc
        idx += 1
    print('nginx is starting...')
    popen = subprocess.Popen([os.path.abspath(gConfig['cluster']['nginx_exe']), '-c', p ])
    #g1 = gevent.spawn(mainloop_nginx, popen)
    
    
    
        
def get_pid_from_name(name):
    out = subprocess.check_output(['tasklist','/SVC'])
    #print(out)
    l = out.split('\r\n')
    findlist = []
    for i in l:
        arr = i.split(' ')
        for j in arr:
            if len(j)>0 and name in j:
                for k in arr:
                    if arr.index(k)==0:
                        continue
                    if len(k)>0:
                        try:
                            pid = int(k)
                            findlist.append(pid)
                            break
                        except:
                            continue
                break
            
    #print(findlist)
    if current_process().pid in findlist:
        findlist.remove(current_process().pid)
    return findlist
    
    
def kill_cluster():
    #global gClusterProcess
    print('kill nginx...')
    for pid in get_pid_from_name('nginx'):
        try:
            out = subprocess.check_output(['taskkill', '/F',  '/PID', str(pid), '/T'])
            print(out)
        except:
            pass

    for pid in get_pid_from_name('python'):
        print('kill python.exe[%s]...' % pid)
        out = subprocess.check_output(['taskkill', '/F',  '/PID', str(pid), '/T'])
        print(out)
    #for pid in gClusterProcess.keys():
        #print('kill python.exe[%s]...' % pid)
        #gClusterProcess[pid].terminate()
    print('kill done')
    
    
def create_self_signed_cert(cert_dir, year=10):
    from OpenSSL import crypto, SSL
 
    CERT_FILE = "ssl_certificate.crt"    
    KEY_FILE = "ssl_self_signed.key"
    if not os.path.exists(os.path.join(cert_dir, CERT_FILE))  or not os.path.exists(os.path.join(cert_dir, KEY_FILE)):
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)
        cert = crypto.X509()
        cert.get_subject().C = "AQ"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Company"
        cert.get_subject().OU = "Organization"
        cert.get_subject().CN = socket.gethostname()
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(year*365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha1')
 
        with open(os.path.join(cert_dir, CERT_FILE), "wt") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        with open(os.path.join(cert_dir, KEY_FILE), "wt") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
 
        #create_self_signed_cert('.')
        print('Create SSL key and cert done')
    else:
        print('SSL key and cert already exist')
 
    
    
def gen_model_app_cache():
    global gConfig
    s = 'CACHE MANIFEST\n'
    s += '#' + gConfig['web_cache']['version'] + '\n'
    
    if gConfig['web_cache']['gltf_cache_enable'].lower() == u'true':
        modelsdir = os.path.join(STATICRESOURCE_DIR, 'gltf')
        if not os.path.exists(modelsdir):
            return
        l = os.listdir(modelsdir)
        for i in l:
            s += '/gltf/' + i + '\n'
    file_or_dir_cache = gConfig['web_cache']['file_or_dir_cache']        
    if len(file_or_dir_cache) > 0 :
        for root, dirs, files  in os.walk(STATICRESOURCE_DIR, topdown=False):
            for name in dirs:
                if name in file_or_dir_cache:
                    p = os.path.join(root, name)
                    for root1, dirs1, files1  in os.walk(p, topdown=False):
                        for name1 in files1:
                            p1 = os.path.join(root1, name1)
                            p1 = p1.replace(STATICRESOURCE_DIR, '').replace('\\', '/')
                            s += p1 + '\n'
            for name in files:
                if name in file_or_dir_cache:
                    p = os.path.join(root, name)
                    p = p.replace(STATICRESOURCE_DIR, '').replace('\\', '/')
                    s += p + '\n'
                
            
    s += 'NETWORK:\n'
    s += '*\n'
    with open(os.path.join(STATICRESOURCE_DIR, 'kmgd.appcache'), 'w') as f:
        f.write(s)
   




if __name__=="__main__":
    freeze_support()
    options = db_util.init_global()
    #print(options)
    init_global()
    if options.signcert_enable:
        create_self_signed_cert( options.signcert_directory,  options.signcert_year)
    elif options.batch_download_tile_enable:
        db_util.command_batch_tile_download(options)
    else:
        if options.cluster_enable:
            mainloop_single(int(gConfig['cluster']['manager_port']), True, False)
        else:
            if gConfig['listen_port']['enable_ssl'].lower() == u'true':
                port = 443
                try:
                    port = int(gConfig['listen_port']['ssl_port'])
                except:
                    pass
                mainloop_single(port, False, True)
            else:
                mainloop_single()
    
    
class Win32ServiceHandler(object):

    # no parameters are permitted; all configuration should be placed in the
    # configuration file and handled in the Initialize() method
    def __init__(self):
        pass

    # called when the service is starting
    def Initialize(self, configFileName):
        self.server = None
        self.stopEvent = threading.Event()
        self.stopRequestedEvent = threading.Event()

    # called when the service is starting immediately after Initialize()
    # use this to perform the work of the service; don't forget to set or check
    # for the stop event or the service GUI will not respond to requests to
    # stop the service
    def Run(self):
        #self.stopRequestedEvent.wait()
        self.stopEvent.set()
        init_global()
        self.server = mainloop_single()

    # called when the service is being stopped by the service manager GUI
    def Stop(self):
        self.stopRequestedEvent.set()
        self.stopEvent.wait()
        if self.server:
            self.server.stop()
    
    
    
    
    
    