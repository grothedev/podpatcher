#!/bin/bash
#args: [local podman image ID] [registry/namespace] [image name] [tag]
if [[ $# -lt 4 ]]; then
    echo "args: [local podman image ID] [registry/namespace] [image name] [tag]"
    exit 0
fi
#handle possible trailing slash
if [[ ${2: -1} == '/' ]]; then
    podman image push ${1} ${2}${3}:${4}
else
    podman image push ${1} ${2}/${3}:${4}
fi