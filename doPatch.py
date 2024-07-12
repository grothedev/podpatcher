#!/usr/bin/python3

#// Author: Thomas Grothe, grothedev@gmail.com
#// 2024/2/22

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
import getopt

#depends on the following scripts:
#   prepareForDockerfile.sh
#   makeDockerfile.sh
#   buildImage.sh
#   pushImage.sh
#   setTag.sh

usage_info='''
            Usage: 
                ./doPatch.py [.tar.gz file] [images (comma-separated)] [tag-to-apply] [(optional) tag-to-base-from]
                    Example: ./doPatch.py patch21302.tar.gz img1,img2,img3 patch2
                ./doPatch.py -i
                    Interactive mode (prompts the user for information)
                ./doPatch.py -d [Dockerfile path] [tag]
                    Make a patch directly from a Dockerfile. Build the image and apply the given tag to the deployment
            
            This script uses the podpatcher tool to patch software into podman pods, from files from a provided tarball.
            It makes a new extended image from each image to patch, after automatically creating a Dockerfile from the files in the tarball,  
            pushes that new image to the registry, with a custom tag, 
            and updates all relevant images to use the new tag. 
            By default it will base the image off of the already present tag.
            You can also specify a diectory containing a Dockerfile to build the image from, instead of using a .tar.gz,
            or you can just apply a tag to all the pods that use some deployment.'''

dbg=False

pchs = dict() #patches. assoc id with filename for now
error = dict() #reported errors
interactive = False #running in interactive mode (prompt user to choose/skip actions)

TAG_BASE=podpatcher.TAG_BASE #the current base tag

def init():
    #timestamp = tnow()
    #logfile = open(f'podpatcher.{timestamp}.log', 'a')
    #get_existing_patches()
    log(f'existing patches: {str(pchs)}')

#extract tarball, write Dockerfile, build image, push image to registry, set pods to use new image
def do_patch(tarpath, images, tag_to, tag_from):
    log(f'Patching!')
    pchID = podpatcher.extract_tar(tarpath)
    if pchID == -1:
        log('there was an error with the tar file extraction')
        return error
    log(f'pchID={pchID}; images={",".join(images)}; from tag {tag_from} to {tag_to}')
    for i in images:
        podpatcher.write_dockerfile(pchID, i, tag_from)
        imageID = podpatcher.build_image(i, pchID, tag_to)
        if not imageID: #is there ever any case where continue after image build failure?
            return error
        podpatcher.push_image(imageID, i, tag_to)
    podpatcher.set_tags(images, tag_to)


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
opts, args = getopt.getopt(sys.argv[1:], "ivd:")
for o, a in opts:
    if o == '-v': #verbose
        podpatcher.verbose = True
    elif o == '-i': #interactive mode
        interactive = True    
    elif o == '-d': #Dockerfile mode. pass directory containing a dockerfile to build the image. also need to pass in 
        dfdirpath = a

if interactive:
    input_imgs = input('images to patch (seperated by commas):').strip()
    images = input_imgs.split(',')
    if len(images) < 1:
        print('invalid images')
        sys.exit(0)
    inputchoice_newimg = 1
    if len(images) == 1:
        inputchoice_newimg = input('what do? \n \
            (1) build new image from a .tar.gz\n \
            (2) use existing tag\n \
            (3) build new image from Dockerfile in some folder\n ')
    else:
        inputchoice_newimg = input('what do? \n \
            (1) build new image from a .tar.gz\n \
            (2) use existing tag\n')

    #TODO allow Dockerfile mode to be used in non-interactive mode 
    if inputchoice_newimg == '1':
        input_tarfilepath = input('path of the .tar.gz file:').strip()
        input_tagfrom = input(f'tag from which to base new patch image: (blank for {TAG_BASE}) ')
        input_tagto = input('tag to use for patch: ').strip()
        while not os.path.exists(input_tarfilepath):
            input_tarfilepath = input(f'{input_tarfilepath} not found. enter path of .tar.gz file: ')
        if input_tagfrom == '':
            input_tagfrom = TAG_BASE
        print(do_patch(input_tarfilepath, images, input_tagto, input_tagfrom))
    elif inputchoice_newimg == '2':
        input_tag = input(f'existing tag name to apply to {input_imgs}: ').strip()
        podpatcher.set_tags(images, input_tag)
        print(f'applied tag {input_tag} to images: {input_imgs}')
    elif inputchoice_newimg == '3':
        input_dfdirpath = input('path of folder containing Dockerfile and patch files: ').strip()
        while not os.path.exists(input_dfdirpath):
            input_dfdirpath = input(f'{input_dfdirpath} not found. path of folder containing Dockerfile and patch files: ').strip()
        input_tag = input('tag to use for patch: ').strip()
        imageID = podpatcher.build_image_from_dockerfile(input_dfdirpath, input_tag)
        podpatcher.push_image(imageID, images[0], input_tag)
        podpatcher.set_tag(images[0], input_tag) #cause there's only 1 image when using this method

else:            
    if len(sys.argv) < 4:
        print(usage_info)
        sys.exit(0)

    tarfilepath = sys.argv[1]
    images = sys.argv[2].split(',')
    tag_to = sys.argv[3]
    tag_from = TAG_BASE
    if len(sys.argv) > 4:
        tag_from = sys.argv[4]
        
    if not os.path.exists(tarfilepath):
        print(f'{tarfilepath} not found')
        sys.exit(0)
    print(do_patch(tarfilepath, images, tag_to, tag_from))

print('\n')
print('Done.')