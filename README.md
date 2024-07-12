PodPatcher: a tool to patch some kubernetes pods running on some cluster. 

This is based on a tool that I wrote for one of my previous employers to help developers patch and test software changes. 
Here is some background info on how it solves that problem. We have a kubernetes cluster that uses a variety of different container images. In order to test and debug software changes, we need to swap out some of the files on the container with new versions that we want to test. These are mostly executable binary files and library files. Without any extra tool, you could replace the files individually on the container with kubectl commands and then restart the processes within the container, but it is easier and more dependable to make an extended image of the image of interest by making a Dockerfile that just adds the necessary files where they need to go. So this is what we did. We would upload our files onto the host machine, make a Dockerfile that copies the files and sets the correct permissions, build the image, push the image to the podman cluster registry, modify the relevant kubernetes manifest files to have the container use the new image tag (or use the kubectl command), then restart the relevant containers. 
Since this became a repetitive process, I of course wrote some scripts to automate most of the steps, such as generating a Dockerfile based on what files I have. 
Eventually I realized that it could help other developers out a lot if I made this into a seemless, easy to use, tool. So I used python flask to make a simple website where we could upload the patch files and then have it automatically call the appropriate scripts to do everything behind the scenes. The core functionality is contained within a python module so that it can be used by other python programs, and there is of course the option to use CLI instead of an http server.

Since I am releasing this version to the public, I have removed some of the business logic of the original use case. And anyone who wishes to use this tool will have to configure it for their specific use case. 

Instructions to adapt this tool to your scenario:

* make a file '.env' to set the following environment variables:
	* REGISTRY : url to cluster registry (host:port)
	* NAMESPACE : registry namespace to use if applicable (between slashes after registry port and before image name)
	* TAG_BASE : tag to base new images off of by default (usually the tag currently in use by the containers)
		* note that this assumes that you have one base tag for all images in a given "version of the cluster".  
	* QUAY_URL : if applicable https://www.projectquay.io/
	* QUAY_USER : if applicable
	* QUAY_PASSWORD : if applicable
* in makeDockerfile.sh, add your own logic for where to place the files
* look at the TODOs and NOTEs in the code to see if you need to change anything
* the purpose of prepareForDockerfile.sh is to perform any file modifications to the files from the tar before making the Dockerfile, such as arranging a folder structure. you might not need it or might have to modify it. 
