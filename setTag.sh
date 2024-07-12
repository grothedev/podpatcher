#!/bin/bash
#args: [image] [deployment] [tag] [(optional) registry/namespace]
#sets the tag of given deployment/image and registry to the tag
if [[ $# -lt 3 ]]; then
	echo "give [image] [deployment] [tag] [(optional) registry/namespace]"
	exit 0
fi
if [[ -z $4 ]]; then
	registry=`./getRegistryAndTag.sh | cut -d',' -f 1`
else
	registry=${4}
fi

#handle possible trailing slash
if [[ ${registry: -1} == '/' ]]; then
	kubectl set image deployment/${2} ${1}=${registry}${1}:${3}
else
	kubectl set image deployment/${2} ${1}=${registry}/${1}:${3}
fi
