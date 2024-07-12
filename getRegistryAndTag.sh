#!/bin/bash
# gets registry and tag of some deployment 
# not used by podpatcher tool.

deplname="TODO set deployment name to use to probe cluster to get registry address" #TODO

kubectl describe deployment/${deplname} |grep Image:.*${deplname} |awk '{print $2}'| sed 's/${deplname}:/,/g'
