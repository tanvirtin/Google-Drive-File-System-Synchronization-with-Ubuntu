from Drive import GDrive
from UnixClient import UnixClient
import time
import threading
import socket
import logging
import os

logging.basicConfig(level = logging.DEBUG) # debug level highest level of logging, can log everything

class DriveControl:
	def __init__(self):
		self.__appIntro()
		self.__initialStart = True # constructing the object will make the initialStart True by default
		self.__lock = threading.Lock()
		self.__connection = False
		self.__googleDrive = None
		self.__fileSystem = None
		self.__justDownloaded = [] # list keeps track of recent downloads
		self.__checkConnection() # thread in the background which checks for connection
		self.__initSystem() # initializes the system
		self.__forbidden = ["Drive.py", "DriveControl.py", "FSTree.py", "File.py", "UnixClient.py", "client_secrets.json", "__main__.py"]
		self.__justDownloaded2 = []
		os.chdir("..") # changes to outer directory on initial start up!

	def __appIntro(self):
		os.system("notify-send Connecting...")
		time.sleep(10)
		os.system("notify-send Connected!")

	# method that spawns a daemon thread which checks the connection continously
	def __checkConnection(self):
		conCheckThread = threading.Thread(target = self.__internetCheck) # cleans up empty folders
		conCheckThread.daemon = True # terminates with the normal termination of program
		conCheckThread.start()

	# initiliazes the entire system
	def __initSystem(self):
		if not self.__connection: # if connection variable is false that means, no internet therefore sleep a second and call this function again to try and connect
			logging.info("Houston we have a problem...")
			time.sleep(1)
			return self.__initSystem() # needs to return this statement to prevent the stack from building up
		self.__googleDrive = GDrive() # needed to keep track of what I am deleting and first launch, hence googleDrive data structure is required
		self.__fileSystem = UnixClient()

	def launch(self):
		self.__populateFS()
		self.__initialize()
		self.__routineCheck()

	# function responsible for checking connection by pinging google every 3 seconds
	# if a reply is found sleep for 3 seconds and then call the function again and check
	# if not then catch the error by spawning the function again after 3 seconds of sleeping
	# thread runs forever
	def __internetCheck(self): # spawn a thread now that keeps on checking it constantly
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			sock.connect(("www.google.com", 0))
		except:
			time.sleep(3)
			logging.info("Waiting for a connection...")
			self.__lock.acquire()
			self.__connection = False
			self.__lock.release()
			sock.close()
			return self.__internetCheck() # ends function here
		self.__lock.acquire() # lock the thread while modding the value
		self.__connection = True
		self.__lock.release() # release the lock
		sock.close()
		time.sleep(3)
		return self.__internetCheck() # even though this statement is the last thing to be executed call return to prevent stack from building up # ends function here

	# intial start was here causing an issue as I had routine check only running if initialStart was False
	def __initialize(self):
		stopwatch = time.time() # starts the stopwatch
		# sync done when initial load occurs
		# next goal is to download what is on google drive but not your computer
		self.__googleDrive.createTree() # creates google drive
		gFiles = self.__googleDrive.getFileList()
		fsFileList = self.__fileSystem.getFileList() # prevFileList is also the file list that gets created for the very first time

		# downloads the file (SOME FILES DONT GET DOWNLOADED FIX!!!)
		# after downloading I have to make sure that the FsFileList gets updated again and
		# filled with new files if not then whatever you download will get uploaded again
		for i in range(len(gFiles)):
			if not self.__fileSystem.findInFS(gFiles[i]): # if one of the google file is not found in the file system then download it
				self.__download(gFiles[i])
				self.__addToFS(gFiles[i]) # updates the file system
				self.__justDownloaded.append(gFiles[i]) # appends to justDownloaded indicating that alright I just downloaded the files you no longer need to delete it

		# delete files that are here but not in google drive, this makes sure that if a new user logs only the new
		# user files is shown and nothing else

		toBeDeleted = [] # a list to keep track of the files that need to be deleted from the list
		for i in range(len(fsFileList)): # as we are in the loop and the range of i is set we will run into index out of bound when one of the elements pointed to a memory location gets deleted
		# natuarally the fsFileList's size will decrease as one of the elements is removed but the range is set before entering the loop and cannot be changed, therefore you get an index out of bounds error
			if not self.__googleDrive.findInDrive(fsFileList[i]):
				self.__deleteFromFs(fsFileList[i]) # deletes from google drive needs to delete from file system
				self.__fileSystem.deleteFileInTree(fsFileList[i])
				toBeDeleted.append(fsFileList[i])

		# need to loop and delete here because deleting it directly inside the loop above it will permanently delete the object from location in memory for all variables pointing to it
		# result in index out of bounds error
		for i in range(len(toBeDeleted)):
			self.__fileSystem.deleteFileInList(toBeDeleted[i])

		endtime = time.time() - stopwatch # finds the end time
		logging.info("\n\nSYNCHRONIZING THE DRIVE TOOK: %s SECONDS\n\n" %(endtime))

	def __populateFS(self):
		self.__fileSystem.createTree()

	def __upload(self, file):
		if file.getName not in self.__forbidden:
			self.__googleDrive.uploadFile(file)

	def __addToFS(self, obj): # changed one thing here if something doesn't work look back
		return self.__fileSystem.addToFS(obj)

	def __download(self, file):
		if file.getName not in self.__forbidden:
			self.__googleDrive.downloadFile(file)

	def __delete(self, file):
		if file.getName not in self.__forbidden:
			self.__googleDrive.deleteFile(file)

	def __deleteFromFs(self, file):
		if file.getName not in self.__forbidden:
			self.__fileSystem.deleteFileInFs(file)

	def __update(self, oldFile, newFile):
		# need to check whether the file where changes are made is one of the scripting files
		if newFile.getName not in self.__forbidden: # newFile or oldFile doesn't matter both have the same name
			logging.info("\nUpdating changes...\n")
			self.__googleDrive.deleteFile(oldFile) # deletes old file
			self.__googleDrive.uploadFile(newFile) # uploads new modified file

	def __justDownloadChecker(self, file):
		for i in range(len(self.__justDownloaded)):
			if file.getName == self.__justDownloaded[i].getName:
				return True # return true immedietly and exit function if names match
		return False # return False after iteration

	def __justDownloadChecker2(self, file):
		for i in range(len(self.__justDownloaded2)):
			if file.getName == self.__justDownloaded2[i].getName:
				return True # return true immedietly and exit function if names match
		return False # return False after iteration

	# problem finding the file last modified between googleDrive file and currentFile systems file
	def __updateSystem(self):
		tempFs = UnixClient()
		tempFs.createTree()

		currFileList = tempFs.getFileList()

		for i in range(len(currFileList)):
			newFile = currFileList[i] # current files in the file system
			oldFile = self.__fileSystem.findInFS(newFile) # old files in google drive
			if oldFile: # If the oldFile with the same name and directory exists in the current FS, then compare last modified dates of the newFile in the current FS
				if oldFile.getLastModified != newFile.getLastModified and not self.__justDownloadChecker(oldFile) and not self.__justDownloadChecker2(oldFile): # checks differences in last modified date and whether the file was just downloaded or not
					self.__update(oldFile, newFile) # update the file then
		self.__justDownloaded = [] # reset just downloaded so that it doesn't check again

	def __routineCheck(self):
		logging.info("\nPRINTING CURRENT WORKING DIRECTORY THE PROGRAM IS IN: %s\n" %(os.getcwd()))

		stopwatch = time.time() # starts the timer

		logging.info("Routine Check")

		while not self.__connection: # wait for connection to resume
			time.sleep(1)

		# house keeping thread
		hkThread = threading.Thread(target = self.__houseKeeping) # cleans up empty folders
		hkThread.daemon = True # terminates with the normal termination of program
		hkThread.start()

		self.__fileSystem.houseKeeping() # deletes empty folders in file system

		tempFs = UnixClient()
		tempFs.createTree()

		prevFileList = self.__fileSystem.getFileList() # prevFileList is also the file list that gets created for the very first time
		currFileList = tempFs.getFileList()

		self.__googleDrive.deleteTree()
		self.__googleDrive.createTree()

		gFiles = self.__googleDrive.getFileList()
 
		logging.info("\nStarting checks!\n")

		# deletes whats not there in google drive
		logging.info("\nChecking for deletes in Google Drive....\n")
		for i in range(len(prevFileList)):
			if not tempFs.findInFS(prevFileList[i]) and not self.__justDownloadChecker2(prevFileList[i]):
				self.__delete(prevFileList[i]) # if previous files don't exist in the new tree generated then delete the old ones
				size = len(gFiles)
				j = 0 # needs a new variable j because i is currently in this for loop which is being used by to find the index of prevFileList at i
				while j < size: # j needs to be less than the size, before it was j != size, this caused an issue as j would become +1 and size would be 0,
								# then iteration would continue till j become 0 which would never happen
					if gFiles[j].getName == prevFileList[i].getName:
						del gFiles[j]
						size -= 1
					j += 1 # increase j as it has to match size in order to break the loop

		self.__justDownloaded2 = []

		# uploads whats not there in google drive
		logging.info("\nChecking for uploads....\n")
		for i in range(len(currFileList)):
			if not self.__fileSystem.findInFS(currFileList[i]):
				self.__upload(currFileList[i]) # if previous files don't exist in the new tree generated then delete the old ones

		# download whats not there in file system
		logging.info("\nChecking for downloads....\n")
		for i in range(len(gFiles)):
			if not tempFs.findInFS(gFiles[i]):
				self.__download(gFiles[i])
				self.__justDownloaded2.append(gFiles[i])

		if self.__justDownloaded2 != []: # create a new tempFs just in case there was a recent download to keep the system upto date
			tempFs = UnixClient()
			tempFs.createTree()

		# update changes
		logging.info("\nChecking for updates....\n")
		if not self.__initialStart: # first call to this function will always make initialStart = True
			self.__updateSystem() # changes made

		# delete files that are here but not in google drive, this makes sure that if a new user logs only the new
		# user files is shown and nothing else
		logging.info("\nChecking for deletes in File System....\n")
		i = 0
		while i != len(prevFileList): # len gets calculated everytime and checked, so once an item gets deleted its okay, we don't run into index out of bound
			if prevFileList[i].getName not in self.__forbidden and not self.__googleDrive.findInDrive(prevFileList[i]):
				self.__deleteFromFs(prevFileList[i]) # deletes from google drive needs to delete from file system
				tempFs.deleteFileInTree(prevFileList[i])
				tempFs.deleteFileInList(prevFileList[i])
			i += 1

		self.__fileSystem.copyTree(tempFs) # assign the newly created tempFs to the old tempFs
		self.__initialStart = False # initialStart is made False everytime

		endtime = time.time() - stopwatch # time taken to go through the entire code

		logging.info("\n\nROUTINE CHECK TOOK: %s SECONDS\n\n" %(endtime))

		time.sleep(10)
		self.__routineCheck() # run forever


	# run this function every 5 minutes
	def __houseKeeping(self):
		logging.info("House Keeping!")
		self.__googleDrive.houseKeeping()
		time.sleep(1)
