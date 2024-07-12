#!/usr/bin/python3

import os
import sys
import podpatcher as pp
import time
import json

def check_system():
    '''
    uses podman and kubectl to gather information about the cluster

    '''

    #has the system already been verified recently? (within 2 weeks) 
    if os.path.exists('.podclustercheck') and time.time() - os.path.getmtime('.podclustercheck') > 1209600: 
        cnt = input('system was already checked recently. continue?')
        if cnt not in ['y','Y','']:
            sys.exit(0)

    f_depls = open('depls.cfg', 'w') #save all the pods 
    f_pods = open('pods.cfg', 'w') #save all the deployments 
    f_imgs = open('images.cfg', 'w') #save all the podman images that exist on this host, along with their registry and namespace

    res = pp.runcmd('podman image list --format json')
    jo = json.loads(res)
    print(f'found {len(jo)} images. see images.cfg')
    for img in jo:
        if 'Names' in img.keys():
            f_imgs.write(f"{img['Names'][0]}\n")        

    res = pp.runcmd('kubectl get pod -o json') #NOTE add namespace parameter for your scenario if needed
    jo = json.loads(res)
    #if len(jo['items']) > 0
    n=0
    for pod in jo['items']:
        if pod['kind'] == 'Pod':
            f_pods.write(f"{pod['metadata']['name']},{pod['status']['phase']}\n")
            n+=1
    print(f'found {n} pods. see pods.cfg')

    res = pp.runcmd('kubectl get deployment -o json')
    jo = json.loads(res)
    n=0
    for dpl in jo['items']:
        if dpl['kind'] == 'Deployment':
            f_depls.write(f"{dpl['metadata']['name']}\n")
            n+=1
    print(f'found {n} deployments. see depls.cfg')

    f_checkflag = open('.podclustercheckflag', 'w')
    f_checkflag.close()
    f_imgs.close()
    f_pods.close()
    f_depls.close()

check_system()
