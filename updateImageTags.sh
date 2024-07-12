#!/bin/bash

# this is NOT used for the podpatcher tool. keeping just in case it is useful.  

if [[ -z $1 ]]; then
	echo "what tag use?"
	exit 0
fi

tag=$1

#TODO list your deployments and images here
deployments=(d1 d2 d3)
images=(i1 i2 i3)



for depl in ${deployments[*]}; do
	container=`kubectl get pod |grep ${depl}"-"|awk '{print $1}'`
	image=`kubectl describe pod ${container}|grep Image:|tail -n 1 | sed 's/Image: //g' | sed 's,\(.*\):.*,\1,g' | sed 's/ //g' `
	imagename=`echo ${image} | sed 's,.*/\(.*\),\1,g'`
	echo "setting ${imagename}=${image}:${tag} on ${depl}"
	kubectl set image deployment/${depl} ${imagename}=${image}:${tag}
done

