#!/bin/bash

#prepare the directory for the dockerfile. this is just a quick way to account for the case where the user has the files in a folder structure instead of flat

#custom dir was passed in
if [[ $1 ]]; then
    cd $1
fi

#TODO: add handling for more files
for f in `find . -name "app_*"`; do
    mv ${f} ./
done
for f in `find . -name "RSS*linux"`; do
    mv ${f} ./
done
for f in `find . -name "lib*.so"`; do
    mv ${f} ./
done
for f in `find . -name "*.jar"`; do
    mv ${f} ./
done
#RCF.xml, other rtf stuff. obviously since this is a mount will be handled differently
#run_system_services.sh
#liveness.sh

#remove lingering empty folder from tar
for d in `ls`; do
    if [[ -d ${d} ]]; then
        rmdir ${d}
    fi
done

#return to prev dir
if [[ $1 ]]; then
    cd -
fi