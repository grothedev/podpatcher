#!/bin/bash

#write a Dockerfile for an extended image

function printHelp {
	echo "write a Dockerfile for an extended image."
	echo "options: (with defaults)"
	echo "	-r [registry] (TODO default)"
	echo "	-i [image] (TODO default)"
	echo "	-t [tag]"
	echo "	-d [build directory] (.)"
}

registry="DEFAULT"
image="DEFAULT"
tag=""
dfiledir="." #dir within which to make dockerfile

#if [[ -z $1 ]]; then
#	echo "?"
#	exit 0
#fi
while getopts "r:i:t:d:h" opt; do
	case $opt in
		r)
			registry=$OPTARG
			;;
		i)
			image=$OPTARG
			;;
		t)
			tag=$OPTARG
			;;
		d)
			dfiledir=$OPTARG
			;;
		h)
			printHelp
			exit 0
			;;
	esac
done

cd ${dfiledir}

#use existing tag to base image from if none passed in
#if [[ ${tag} == "" ]]; then
	#TODO
#fi

#scan dir for bins+libs and write dockerfile cmds
if [[ -f ./Dockerfile ]]; then
	d=`date +%s`
	echo "backing up old Dockerfile"
	cp Dockerfile Dockerfile.${d}.bak
fi

echo "Making Dockerfile!"

echo "FROM ${registry}${image}:${tag}" > Dockerfile
echo "" >> Dockerfile
echo "USER root" >> Dockerfile
echo "" >> Dockerfile

#TODO: insert the logic for your specific application
# below is a sample of a hypothetical file placement 
# use a for loop for each string pattern search
# better yet, define a map of search string to path in a config file and use that

for f in `ls libfile*.so 2>/dev/null`; do
#for f in `find . -name "something_*"`; do
	echo "COPY ${f} /path/for/${f}" >> Dockerfile
	echo "RUN chmod 755 /path/for/${f}" >> Dockerfile
	echo "RUN chown user1:group1 /path/for/${f}" >> Dockerfile
done

echo "" >> Dockerfile
echo "USER user1" >> Dockerfile

cd -
