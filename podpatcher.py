#!/usr/bin/python3

#// Author: Thomas Grothe, grothedev@gmail.com
#// 2024/2/22

import os
import sys
#from werkzeug.utils import secure_filename #this was used for inputname sanitization when uploading tar via http
import subprocess
#import filetype
import chardet
import random
from hashlib import md5
import json
from datetime import datetime
import time
import dotenv

'''
##############################
# PodPatcher: a python module to help patch pods 

.. variables:
    .. verbose
    .. pchs
    .. error

.. constants:
    .. NAMESPACE
    .. REGISTRY
    .. QUAY_URL
    .. QUAY_USER
    .. QUAY_PASSWORD


.. classes:
    .. Patch

.. functions:
    .. do_patch(tarpath, images, tag_to, tag_from=TAG_BASE)
    .. extract_tar(tarpath, overwrite=False)
    .. write_dockerfile(pchID, image, tag)
    .. build_image(image, pchID, tag)
    .. build_image_from_dockerfile(path_dockerfiledir, tag)
    .. push_image(imageID, imageName, tag)
    .. set_tags(images, tag)
    .. set_tag(images, tag)
    .. get_deployments_of_image(image)
    .. get_tag_of_deployment(depl)
    .. pull_quay(images, tag, registry=REGISTRY, namespace=NAMESPACE)
    .. quay_login()
    .. runcmd(cmdstr,v=False)
    .. get_existing_patches()

Authors: Thomas Grothe, thomas.grothe@gd-ms.com
Version: 1.1
'''
verbose=False
pchs = dict() #patches. assoc id with filename for now
error = dict() #reported errors

### init ###
dotenv.load_dotenv()
if os.getenv('REGISTRY'): #local registry of cluster
    REGISTRY=os.getenv('REGISTRY')
else:
    REGISTRY='DEFAULTREGISTRY:PORT' #previously was including the namespace, but no longer for future supportability
if os.getenv('NAMESPACE'):
    NAMESPACE=os.getenv('NAMESPACE')
else:
    NAMESPACE='' #NOTE default namespace
if os.getenv('QUAY_URL'):
    QUAY_URL=os.getenv('QUAY_URL')
else:
    QUAY_URL='QUAYHOST:QUAYPORT' #NOTE default quay url
if os.getenv('QUAY_USER'):
    QUAY_USER=os.getenv('QUAY_USER')
else:
    QUAY_USER='QUAYUSER' #NOTE default quay user
if os.getenv('TAG_BASE'): #the current tag already being used in the system 
    TAG_BASE=os.getenv('TAG_BASE')
else:    
    TAG_BASE='DEFAULTTAG' #NOTE default tag
if os.getenv('QUAY_PASSWORD'):
    QUAY_PASSWORD=os.getenv('QUAY_PASSWORD')
quay_logged_in = False

#fix potential trailing/leading slashes
REGISTRY=REGISTRY.rstrip('/')
NAMESPACE=NAMESPACE.strip('/')
QUAY_URL=QUAY_URL.rstrip('/')


def do_patch(tarpath, images, tag_to, tag_from=TAG_BASE):
    '''
    do a whole patch: extract tarball, write Dockerfile, build image, push image to registry, set pods to use new image
    params:
        tarpath (string) : path to .tar.gz file, relative to current working directory
        images (list<string>) : images to apply the patch to
        tag_to (string) : tag to apply to the new image
        tag_from (string) : tag from which to base the new image (can have default) 
    return:
    '''
    log(f'Patching!')
    pchID = extract_tar(tarpath) 
    if pchID == -1:
        log('there was an error with the tar file upload')
        return error
    log(f'pchID={pchID}; images={",".join(images)}; from tag {tag_from} to {tag_to}')
    #return write_dockerfile(pchID, image, imagetag)
    for i in images:
        write_dockerfile(pchID, i, tag_from)
        imageID = build_image(i, pchID, tag_to)
        if not imageID: #is there ever any case where continue after image build failure?
            return error
        push_image(imageID, i, tag_to)
    set_tags(images, tag_to)



def extract_tar(tarpath, overwrite=False):
    '''
    take the md5sum of the tarball, use this as the "patch ID" and folder name in which to stage the files.
    make the folder if doesn't exist and extract the tar there.
    then run 'prepareForDockerfile.sh' which just arranges files so that 'makeDockerfile.sh' works. (see scripts for more info)
    params:
        tarpath (string) : path to .tar.gz file, relative to current working directory
        overwrite (bool) : if true, overwrite files if patch already exists (default = False)
    return:
        ID of the patch, generated from md5sum of tar file,
        or -1 on failure
    '''

    pchID = -1
    if '.tar.gz' not in tarpath: #for the purposes of this simple tool, it ok to check filetype like this
        error['extract_tar()'] = 'file not .tar.gz. this is currently a test tool and will support other archive formats in the future'
        return pchID
    with open(tarpath, 'rb') as tf:
        fb = tf.read() #get the file bytes
        pchID = md5(fb).hexdigest()
        log(f'md5 patch id: {pchID}')
        tf.close()
        if not os.path.exists(f"./patches/{pchID}"):
            os.makedirs(f"./patches/{pchID}")
        else:
            print(f'!! patch already exists: ./patches/{pchID}\n')
            if not overwrite:
                return pchID
            #intentionally choosing not to delete files in the patch folder here in the case of overwrite
        log(f'extracting tar for {pchID}')
        pchdir = f"patches/{pchID}/" #working dir
        sp_tar = runcmd(f'tar -xvf {tarpath} -C {pchdir}')
        sp_prep = runcmd(f'./prepareForDockerfile.sh {pchdir}')
        return pchID
    
#TODO non-tarball-based patches. maybe just pass in folder name
def write_dockerfile(pchID, image, tag):
    '''
    generate a dockerfile for this patch, in the dir named as the patch id
    params:
        pchID (string) : the ID that was generated for the patch, which is the md5sum of the tarball from which it came
        image (string) : the image from which to base this image
        tag (string) : the tag from which to base this image
    return:
        stdout of executing the makeDockerfile.sh script
    '''
    log(f'writing dockerfile {image}:{tag}')
    wd = f"patches/{pchID}/" #working dir
    #os.chdir(wd)
    return runcmd(f'./makeDockerfile.sh -d {wd} -i {image} -t {tag}')
    #sp = subprocess.run(['./makeDockerfile.sh', '-d', wd, '-i', image, '-t', tag], stdout=subprocess.PIPE)
    #return sp.stdout

def build_image(image, pchID, tag):
    '''
    calls a script to build the image. current implementation uses podman. 
    params:
        image (string) : image name
        pchID (string) : patch ID. used to find the directory with dockerfile, where tar was extracted. 
        tag (string) : tag to give to the new image
    return:
        boolean of success
    '''
    log(f'building image {image}:{tag}')
    wd = f"patches/{pchID}/" #working dir
    #run build image script, handling possible trailing slash on registry string
    res = runcmd(f'./buildImage.sh {REGISTRY}/{NAMESPACE}/{image} {tag} {wd}').splitlines()
    #verify the image built and get its id
    success = False
    for l in res: 
        if 'Successfully tagged' in str(l, encoding='utf-8'):
            success = True
            break
    if success:
        return str(res[len(res)-1], encoding='utf-8') #image id, last line of podman build command output
    else:
        error['build_image()'] = 'failed to build image'
        log('image building unsuccessful')
        return success

def build_image_from_dockerfile(path_dockerfiledir, tag):
    '''
    calls a script to build the image. current implementation uses podman. 
    params:
        path_dockerfiledir (string) : path to folder containing Dockerfile
        tag (string) : tag to give to the new image
    return:
        boolean of success
    '''

    f_df = open(f'{path_dockerfiledir}/Dockerfile', 'r')
    imagename = '' #registry/namespace/image:tag, from the dockerfile
    for i,line in enumerate(f_df):
        if 'FROM' in line: #get the image name from the Dockerfile
            tmp = line.strip().split(' ')[1].split('/')
            imagename = tmp[len(tmp)-1].split(':')[0]
    if imagename != '':
        res = runcmd(f'./buildImage.sh {imagename} {tag} {path_dockerfiledir}').splitlines()
        success = False
        if res == None:
            log('image build failed')
            return success
        for l in res:
            if 'Successfully tagged' in str(l, encoding='utf-8'):
                success = True
                break
        if success:
            return str(res[len(res)-1], encoding='utf-8') #image id, last line of podman build command output
        else:
            error['build_image()'] = 'failed to build image'
            log('image building unsuccessful')
            return success


def push_image(imageID, imageName, tag):
    '''
    calls a script to push the image to the registry defined in .env. current implementation uses podman.
    params:
        imageID (string) : podman iamge ID of the local patched image
        imageName (string) : name of image
        tag (string) : tag to apply to the image in registry
    return:
        stdout of executing the pushImage.sh script
    '''
    log(f'pushing {imageName}:{tag} to registry')
    return runcmd(f'./pushImage.sh {imageID} {REGISTRY}/{NAMESPACE} {imageName} {tag}')

def set_tags(images, tag):
    for i in images:
        set_tag(i, tag)

def set_tag(image, tag):
    '''
    updates the tag used by all deployments using a given image. 
    params:
        image (string) : name of image
        tag (string) : tag to apply to these images
    return:
        stdout of executing the setTag.sh script
    '''
    log(f'setting tag of {image} to {tag}')
    depls = get_deployments_of_image(image)
    for d in depls:
        log(f'setting depl {d}')
        runcmd(f'./setTag.sh {image} {d} {tag} {REGISTRY}/{NAMESPACE}')

def get_deployments_of_image(image):
    '''
    get all the deployments that are currently using a given image
    params:
        image (string) : name of image
    return: (list) names of deployments
    '''
    res = []
    jsonstr = runcmd('kubectl get deployment -o json')
    jo = json.loads(jsonstr)
    for d in jo['items']:
        if d['kind'] != 'Deployment': continue
        if image in d['spec']['template']['spec']['containers'][0]['image']:
            for envvar in d['spec']['template']['spec']['containers'][0]['env']:
                if envvar['name'] == 'HOSTNAME': #hostname is the same as deployment name
                    if 'value' in envvar.keys():
                        res.append(envvar['value']) 
                    break
    return res

#get the current tag of some image
def get_tag_of_deployment(depl):
    return None #TODO

def pull_quay(images, tag, registry=REGISTRY, namespace=NAMESPACE):
    '''
    pull images from quay AND push them to the local cluster registry
    params:
        images (list<str> or str): a single image or a list of images
        tag (str) : 
        registry (str) :
        namespace (str) : 
    '''
    if registry != REGISTRY: registry=registry.rstrip('/')
    if namespace != NAMESPACE: namespace=namespace.strip('/')
    if not quay_logged_in:
        quay_login()
    if type(images) is list:
        for img in images:
            runcmd(f'podman image pull {QUAY_URL}/{namespace}/{img}:{tag}')
            runcmd(f'podman image push {img}:{tag} {REGISTRY}/{namespace}/{img}:{tag}')
    elif type(images) is str:
            runcmd(f'podman image pull {QUAY_URL}/{namespace}/{images}:{tag}')
            runcmd(f'podman image push {images}:{tag} {REGISTRY}/{namespace}/{images}:{tag}')


def quay_login():
    '''
    login to quay, using the env vars defined in .env: QUAY_URL, QUAY_USER, QUAY_PASSWORD
    '''
    res = runcmd(f'podman login {QUAY_URL} -u={QUAY_USER} -p={QUAY_PASSWORD}')
    if 'Login Succeeded' in str(res) or 'Already logged in' in str(res):
        quay_logged_in = True


def runcmd(cmdstr,v=False):
    '''
    execute a command using the python subprocess module
    params:
        cmdstr (str) : the command to run
    return: stdout of command
    '''
    cmdarray = cmdstr.split(' ')
    log(f'runcmd: {cmdstr}')
    if '|' in cmdarray:
        i = cmdarray.index('|')
        proc0 = subprocess.check_output(cmdstr, shell=True)
    proc = subprocess.run(cmdarray, stdout=subprocess.PIPE)
    if proc.returncode == 0:
        res = proc.stdout
        if v: #output of kubectl cmds can be very messy and get in the way of meaningful output
            log(f'result: {res}')
    else:
        log(f'returncode = {proc.returncode}')
        res = proc.stderr
    return res


def get_existing_patches():
    '''
    scan patch folder to build the map of existing patches (previous patches that have been applied)
    populates the global variable pchs
    '''
    for pchdir in os.listdir('./patches/'):
        if os.path.isdir(f'./patches/{pchdir}'):
            for f in os.listdir(f'./patches/{pchdir}'):
                if '.tar.gz' in f: #for the purposes of this simple tool, it ok to check filetype like this
                    pchs[pchdir] = f
                    break

def log(msg):
    t = tnow()
    with open('podpatcher.log', 'a') as lf:
        lf.write(f'{t}: {msg}\n')
        lf.close()
    if verbose: print(f'LOG: {msg}')
    
    
def tnow():
    '''
    return: current time, formatted as %Y%m%d-%H%M%S
    ''' 
    return datetime.now().strftime('%Y%m%d-%H%M%S')


class Patch:
    '''
    to associate the important pieces of information related to a single "patch"
    attribute:: hash
    attribute:: filename
    attribute:: tag

    '''
    def __init__(self, h,f,t):
        self.hash=h
        self.filename=f
        self.tag=t