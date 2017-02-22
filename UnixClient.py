from FSTree import Tree
from File import File
import socket
import subprocess
from os import chdir # for changing directory
import os.path, time
from os.path import isdir

class UnixClient():
	def __init__(self):
		self.__fsTree = Tree()

	def routineCheck(self):
		self.__check(".", "./")
		chdir("Main")

	def __check(self, cwd, path):
		chdir(cwd)
		if cwd != ".":
			path += (cwd + "/")
		proc = subprocess.Popen("ls", stdout = subprocess.PIPE)
		output = proc.stdout.read()
		output = output.decode("utf-8")
		
		if "FSTree.py" in output:
			output = output.replace("FSTree.py\n", "")
		if "File.py" in output:
			output = output.replace("File.py\n", "")
		if "UnixClient.py" in output:
			output = output.replace("UnixClient.py\n", "")
		if "UnixServer.py" in output:
			output = output.replace("UnixServer.py\n", "")
		if "__pycache__" in output:
			output = output.replace("__pycache__\n", "")

		ls = output.split("\n")
		
		if "" in ls:
			ls.remove("")

		for i in range(len(ls)):
			if not isdir(ls[i]): # store all the files in the sub folder into an array as file objects
				obj = File(ls[i], path, time.ctime(os.path.getmtime(ls[i]))) # constructing the file obj with its name, path and date time
				self.__fsTree.add(obj)


		for i in range(len(ls)): # if not a file then go into the sub folder using recursive calls
			if isdir(ls[i]): 
				self.__check(ls[i], path) 
		
		chdir("..") # end of each instance of the function you cd .. out of the folder you were in

	def printFS(self):
		self.__fsTree.print()

	def findInFS(self, obj):
		return self.__fsTree.find(obj)


def main():
	client = UnixClient()
	client.routineCheck()

	client.printFS()


if __name__ == '__main__':
	main()