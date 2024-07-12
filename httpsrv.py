#!/usr/bin/python3

#// Author: Thomas Grothe, grothedev@gmail.com
#// 2024/2/22

#this tool does the following
# allow user to upload a .tar.gz containing some files that should placed in a pod of a kubernetes cluster
# makes a new extended image from each image specified by user, with the newly uploaded files replacing the old ones
# pushes that new image to the registry, with a custom tag
# updates all relevant pods to use the new image tag
# maintains a sqlite database of patches (WIP, not essential for desired functionality, but could be useful in future)

import flask
import flask_cors
from flask import request
from flask import render_template
import os
import sys
import subprocess
#import filetype
import chardet
import random
from hashlib import md5
import json
from datetime import datetime
import time
import podpatcher

import patchDB #adapter to the database we're using to store patch data and metadata

dbg=False
verbose=False

db_enabled=True #save patch metadata in database (sqlite)

hs = flask.Flask("Pod Patcher Website", static_folder='./') #http server
cors = flask_cors.CORS(hs)
hs.config['CORS_HEADERS'] = 'Content-type'

pchs = dict() #patches. assoc id with a podpatcher.Patch object 
error = dict() #reported errors
session_cmds = [] #log all commands ran during this session


#podman registry and current image tag
TAG_CURRENT=podpatcher.TAG_BASE
REGISTRY=podpatcher.REGISTRY
NAMESPACE=podpatcher.NAMESPACE
DEPLOYMENTS=['deployment1', 'deployment2', 'orimagename3',
             'set these in httpsrv.py'] #list of deployments that can be patched, to pass to html

def init():
    #timestamp = tnow()
    #logfile = open(f'podpatcher.{timestamp}.log', 'a')
    log('starting podpatcher website')
    get_existing_patches()
    log(f'existing patches: {str(pchs)}')
    log(f"registry: {REGISTRY}")
    log(f"namespace: {NAMESPACE}")
    log(f"tag: {TAG_CURRENT}")

@hs.route("/")
@flask_cors.cross_origin()
def index():
    res = runcmd('./getCurrentPods.sh')
    if len(res) > 0:
        jo = json.loads(res)
        pods = []
        for p in jo['items']:
            if p['kind'] != 'Pod': continue
            for c in p['spec']['containers']:
                if 'env' in c.keys():
                    for ev in c['env']:
                        if ev['name'] == 'HOSTNAME' and 'value' in ev.keys():
                            state = 'n/a'
                            cID = 'n/a'
                            if 'containerStatuses' in p['status'].keys() and len(p['status']['containerStatuses']) > 0:
                                a = 0
                                while 'state' not in p['status']['containerStatuses'][0].keys() and a < 3:
                                    time.sleep(2)
                                    a+=1
                                if a != 3:
                                    state = str( p['status']['containerStatuses'][0]['state'] )
                                a = 0
                                while 'containerID' not in p['status']['containerStatuses'][0].keys() and a < 3:
                                    time.sleep(2)
                                    a+=1
                                if a != 3:
                                    cID = p['status']['containerStatuses'][0]['containerID']
                                
                            #if 'running' in state.keys()
                            pods.append((ev['value'], c['image'], state, cID))

        #passing pods as tuple (name, image, status, container id)
        return render_template("./index.html", deployments=DEPLOYMENTS, pods=pods, patches=pchs)
    else:
        return render_template("./index.html", deployments=DEPLOYMENTS, pods=None, patches=pchs)

#start the process of uploading tarball, extract, write Dockerfile, build image, push image to registry, set pods to use new image
@hs.post("/start")
@flask_cors.cross_origin()
def start():
    session_cmds = []
    log(f'POST /start {request.remote_addr}')
    pchID = upload_tar(request.files['tarball'])
    tag_from = TAG_CURRENT
    if len(request.form['tag_from']) > 0:
        tag_from = request.form['tag_from']
    tag_to = request.form['tag_to'] or f'patch-{pchID[:8]}'
    images = request.form.getlist('images')
    if pchID == -1:
        log('there was an error with the tar file upload')
        return error
    log(f'pchID={pchID}; images={",".join(images)}; from tag {tag_from} to {tag_to}')
    podpatcher.extract_tar(pchID)
    for i in images:
        podpatcher.write_dockerfile(pchID, i, tag_from)
        imageID = podpatcher.build_image(i, pchID, tag_to)
        if not imageID: #is there ever any case where continue after image build failure?
            return error
        podpatcher.push_image(imageID, i, tag_to) 
        if db_enabled: patchDB.set_patch_tag(pchID, tag_to) #after successful image push, write tag to DB
    podpatcher.set_tags(images, tag_to)
    pagedata = dict() #data to display on result webpage
    pagedata['op'] = 'start patching'
    pagedata['pchID'] = pchID
    pagedata['tag_from'] = tag_from
    pagedata['tag_to'] = tag_to
    pagedata['registry'] = REGISTRY
    pagedata['cmds'] = session_cmds
    return render_template('./response_success.html', data=pagedata)

#apply a tag to some images
@hs.post("/set-tag")
@flask_cors.cross_origin()
def setTag():
    session_cmds = []
    log(f'POST /set-tag {request.remote_addr}')
    tag = TAG_CURRENT #by default, set to OG tag
    if len(request.form['tag']) > 0:
        tag = request.form['tag']
    images = request.form.getlist('images')
    podpatcher.set_tags(images, tag)
    pagedata = dict() #data to display on result webpage
    pagedata['op'] = 'set tag'
    pagedata['images'] = ','.join(images)
    pagedata['tag'] = tag
    pagedata['registry'] = REGISTRY
    pagedata['cmds'] = session_cmds
    return render_template('./response_success.html', data=pagedata)
        
#pull from quay and push to local cluster registry
@hs.post("/pull-quay")
@flask_cors.cross_origin()
def pullQuay():
    images = request.form['images'].split(',')
    podpatcher.pull_quay(images, request.form['tag'])
    pagedata = dict() #data to display on result webpage
    pagedata['op'] = 'pull from quay, push to cluster'
    pagedata['images'] = request.form['images']
    pagedata['tag'] = request.form['tag']
    pagedata['registry'] = REGISTRY
    return render_template('./response_success.html', data=pagedata)

#upload the tarball, generate an id for this patch (don't extract tar yet)
# return the id of the patch
def upload_tar(tarfile):
    pchID = -1
    fn = tarfile.filename
    #fn = secure_filename(tarfile.filename)
    log(f'uploading tar {tarfile} as {fn}')
    if '.tar.gz' not in fn: #for the purposes of this simple tool, it ok to check filetype like this
        error['upload_tar()'] = 'file not .tar.gz. this is currently a test tool and will support other archive formats in the future'
        return pchID
    fb = tarfile.read() #get the file bytes
    pchID = md5(fb).hexdigest()
    if pchID in pchs.keys(): #patch already exists
        if os.path.exists(f"./patches/{pchID}/{fn}"):
            return pchID
        else: #patch is in db but files aren't present. just remove it from the database so it can be re-added
            if db_enabled: patchDB.remove_patch(pchID)
    log(f'md5 patch id: {pchID}')
    if not os.path.exists(f"./patches/{pchID}"):
        os.makedirs(f"./patches/{pchID}")
    elif not os.path.isdir(f"./patches/{pchID}"):
        error['upload_tar()'] = f"./patches/{pchID}  already exists and is not a directory"
        return pchID
    tarfile.seek(0) #go back to the beginning of file to save it
    #if dir already does exist, then still rewrite file because the previous process might have been interrupted
    tarfile.save(f"./patches/{pchID}/{fn}")
    p = podpatcher.Patch(pchID,fn,None)
    if db_enabled: patchDB.add_patch(pchID,fn)
    pchs[pchID] = p
    return pchID

#get all the deployments that are currently using a given image
def get_deployments_of_image(image):
    res = []
    jsonstr = runcmd('kubectl get deployment -o json') #TODO need to add a namespace (-n)? or anything else? 
    jo = json.loads(jsonstr)
    for d in jo['items']:
        if d['kind'] != 'Deployment': continue
        if image in d['spec']['template']['spec']['containers'][0]['image']:
            for envvar in d['spec']['template']['spec']['containers'][0]['env']:
                if envvar['name'] == 'HOSTNAME': #hostname is the same as deployment name
                    res.append(envvar['value']) 
                    break
    return res

def runcmd(cmdstr):
    cmdarray = cmdstr.split(' ')
    log(f'runcmd: {cmdstr}')
    proc = subprocess.run(cmdarray, stdout=subprocess.PIPE)
    if proc.returncode == 0:
        res = proc.stdout
        if verbose: #output of kubectl cmds can be very messy and get in the way of meaningful output
            log(f'result: {res}')
    else:
        log(f'returncode = {proc.returncode}')
        res = proc.stderr
    session_cmds.append((cmdstr, res))
    return res

#scan patch folder to build the map of existing patches
def get_existing_patches():
    db_entries = patchDB.get_patches()
    if db_entries == None: #problem with sqlite db
        return -1
    for entry in db_entries: # (hash id str, targz filename)
        if os.path.isdir(f'./patches/{entry[0]}'):
            p = podpatcher.Patch(entry[0],entry[1],entry[2])
            pchs[entry[0]] = p
        else:
            log(f'patch {entry[1]} not found: {entry[0]}')  
    for pchdir in os.listdir('./patches/'):
        if os.path.isdir(f'./patches/{pchdir}'):
            for f in os.listdir(f'./patches/{pchdir}'):
                if '.tar.gz' in f: #for the purposes of this simple tool, it ok to check filetype like this
                    if pchdir not in pchs.keys(): #this patch is not in db
                        p = podpatcher.Patch(pchdir, f, None)
                        patchDB.add_patch(pchdir, f)
                        pchs[pchdir] = p
                    break

def log(msg):
    t = tnow()
    with open('podpatcher.log', 'a') as lf:
        lf.write(f'{t}: {msg}\n')
        lf.close()
    print(f'LOG: {msg}')
    
    
#current time formatted
def tnow():
    return datetime.now().strftime('%Y%m%d-%H%M%S')

########################
#  PROGRAM START HERE  #
########################
init()

host = '127.0.0.1'
if len(sys.argv) > 1:
    host = sys.argv[1]
hs.run(host=host)
