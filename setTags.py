#!/usr/bin/python3

#// Author: Thomas Grothe, grothedev@gmail.com
#// 2024/2/22

import os
import sys
#from werkzeug.utils import secure_filename
import subprocess
#import filetype
import chardet
import random
from hashlib import md5
import json
from datetime import datetime
import time

usage_info='''
            Usage: ./setTags.py [images (comma-separated)] [tag-to-apply]
            Example: ./setTags.py image1,image2 patchtag

            This script sets the tag of a kubernetes deployment and restarts the pods which are using that deployment. 
            s'''

REGISTRY_NAMESPACE='' #TODO

#args: list of image names, tag
def set_tags(images, tag):
    for i in images:
        set_tag(i, tag)

#updates the tag used by all deployments using a given image
def set_tag(image, tag):
    print(f'setting tag of {image} to {tag}')
    depls = get_deployments_of_image(image)
    for d in depls:
        print(f'setting depl {d}')
        runcmd(f'./setTag.sh {image} {d} {tag} {REGISTRY_NAMESPACE}')

#get all the deployments that are currently using a given image
def get_deployments_of_image(image):  #TODO logic might need adjusting for specific scenario
    res = []
    jsonstr = runcmd('kubectl get deployment -o json')
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
    print(f'runcmd: {cmdstr}')
    res = subprocess.run(cmdarray, stdout=subprocess.PIPE).stdout
    print(f'result: {res}')
    return res

#scan patch folder to build the map of existing patches
def get_existing_patches():
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
    print(f'LOG: {msg}')
    
    
#current time formatted
def tnow():
    return datetime.now().strftime('%Y%m%d-%H%M%S')

########################
#  PROGRAM START HERE  #
########################
if len(sys.argv) < 3:
    print(usage_info)
    sys.exit(0)
else:
    images = sys.argv[1].split(',')
    tag = sys.argv[2]
    set_tags(images, tag)
    print('\n')
    print('Done.')
