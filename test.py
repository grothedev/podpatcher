#!/usr/bin/python3

#// Author: Thomas Grothe, grothedev@gmail.com
#// 2024/2/22

import pytest
import podpatcher as pp
import json 

#test cases
#would probably be good to verify that files in the pod are the same as ones provided from user

#program-file: podpatcher.py
# test case for each function
#   range of possible args (arg domain)
#   set of args of interest mapped to expected outputs
#   


#system verification
'''
    verify that cluster is in working order
        - kubectl cmd works
        - some pods are running
        - we can restart pods
        - podman cmd works
        - we can build and push images
        - test a patch
        - produce system state/config files containing all the pods, depls, etc.

'''
def test_setup():
    f_depls = open('depls.cfg', 'w') #save all the pods 
    f_pods = open('pods.cfg', 'w') #save all the deployments 
    f_imgs = open('images.cfg', 'w') #save all the podman images that exist on this host

    res = str(pp.runcmd('kubectl'))
    assert 'Command not found' not in res

    res = pp.runcmd('kubectl get pod -o json')
    jo = json.loads(res)
    assert len(jo['items']) > 0
    for pod in jo['items']:
        assert pod['kind'] == 'Pod'
        f_pods.write(f"{pod['metadata']['name']},{pod['status']['phase']}\n")

    res = pp.runcmd('kubectl get deployment -o json')
    jo = json.loads(res)
    for dpl in jo['items']:
        assert dpl['kind'] == 'Deployment'
        f_depls.write(f"{dpl['metadata']['name']}\n")

    res = str(pp.runcmd('podman'))
    assert 'Command not found' not in res

    res = pp.runcmd('podman image list --format json')
    #TODO take a look at checkSystem.py

def test_patch_non_existent_deployment():
    # Test that patching a non-existent deployment returns an error message

def test_patch_one_deployment_no_files():
    # Test that patching one deployment with no provided files returns an error message

def test_patch_one_deployment_non_existent_tag():
    # Test that patching one deployment with a non-existent tag returns an error message

def test_patch_one_deployment_some_files():
    # Test that patching one deployment with some files applies the patch and returns a success message

def test_patch_multiple_deployments_no_files():
    # Test that patching multiple deployments with no provided files returns an error message

def test_patch_multiple_deployments_some_files():
    # Test that patching multiple deployments with some files applies the patch and returns a success message
def test_set_tags_non_existent_tag():
    # Test that setting tags for one or multiple deployments with a non-existent tag returns an error message

def test_set_tags_existent_tag():
    # Test that setting tags for one or multiple deployments with an existing tag returns the k8s result

#program-file: httpsrv.py

#attempt to patch a non-existent deployment ==> do nothing, return error msg

#attempt to patch one deployment, or multiple deployments
#   with no provided files ==> do nothing, return error msg
#   based on a non-existent tag ==> do nothing, return error msg
#   with some files ==> apply patch and return correct msg
#   build to a tag that already exists ==> do nothing, return error msg

#attempt to set tags of one or multiple deployments
#   tag doesn't exist ==> return error msg
#   tag exists ==> set and return k8s result


#verify sqlite db is made and correct data is written/read to/from it

#program: doPatch.py

#program: setTags.py