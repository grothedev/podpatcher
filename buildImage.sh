#!/bin/bash
#args: [image string (including registry & image name)] [tag string] [build directory(optional)]
if [[ $# -lt 2 ]]; then
    echo "args: [registry/image string] [tag string] [build directory(optional)]"
    echo "ex: ./buildImage.sh registryhostname:5000/somenamespace/coolimage v1 ."
    exit 0
fi
d="."
if [[ $3 ]]; then
	d=${3}
fi
podman image build --squash -t ${1}:${2} ${d} 
