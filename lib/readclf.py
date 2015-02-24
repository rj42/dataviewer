'''
Author: Igor Shovkun
Contains an only  main function: readclf
Reads clf files produced by Terratek setup
'''
import numpy as np
import re


def remove_zeros(dic,par='Time'):
	'''
	Filters data from wierd zero values
	'''
	newdic = {}
	t = dic[par]
	for i in dic.keys():
		newdic[i] =  dic[i][t!=0]
	return newdic

def getNames(string):
	'''
	Parces header of data
	returns lists of names and units
	'''
	splitted = string.split()
	names = []
	units = []
	for i in range(0,len(splitted),2):
		# print splitted[i]
		if i == len(splitted)-1:
			names.append(splitted[i])
		else:
			names.append(splitted[i])
			units.append(splitted[i+1])
	return names,units

def getData(text,names):
	lines = text.split('\n')
	lines = filter(lambda x:x!='',lines)
	m = len(names) # number of entries in a line
	n = len(lines) # number of lines
	values = np.zeros([n,m-1]) # m-1 cause without comments
	# comments = {}
	ctimes = [] ## times of comments
	coms = [] ## comments
	# this code block reads all columns
	# last column is comments
	for i in range(n):
		linelist =  lines[i].split()
		if len(linelist) == m-1:
			values[i,:] = lines[i].split()
		if len(linelist) == m: # if an item in the last column exists for this row
			values[i,:] = lines[i].split()[:-1]
			ctimes.append(linelist[0])
			coms.append(linelist[-1])
	data = {}
	## get dictionary with names keys
	for i in range(m):
		if names[i] == 'Comments': pass
		else: data[names[i]] = values[:,i]
	## get dictionary with comments and comment times
	comments = {}
	for i in range(len(coms)):
		comments['Times'] = ctimes
		comments['Comments'] = np.array(coms)
	return data,comments

def filterList(l):
	'''
	input: list
	loops through a list and filters items 
	from bad characters
	output: filtered list
	'''
	badchatacters = ('-','/','\\','.','\xb0')
	for i in range(len(l)):
		for c in badchatacters:
			l[i] = l[i].replace(c, "")
		a = re.sub(r'[\xc2\x99]'," ",l[i])		
	return l

def findHeader(text,expr="Time.*Sig1[^\n]+"):
	'''
	seeks for a regular expression reg
	in texts. returns header position in text
	'''
	match=re.search(expr,text)
	return [match.start(),match.end()]


def createUnitsDict(names,units):
	'''
	Removes 'Comments' entry from names.
	after this sizes of names and units arrays should be the same.
	creates numpy chararray, which maps names to units
	'''
	names = filter(lambda x:x!='Comments',names)
	n = len(names)
	if len(units) != n: raise ValueError('Something went wrong. length of names and units should be the same.')
	unitsDict = {}
	for i in range(n):
		unitsDict[names[i]] = units[i]
	return unitsDict

def readclf(filename):
	'''
	Main function.
	Reads clf files
	'''
	with open(filename,'r') as f:
		text = f.read()
	headerpos = findHeader(text)
	header = text[headerpos[0]:headerpos[1]]
	names,units = getNames(header)
	names = filterList(names)
	units = filterList(units)
	# the experimantal data is located after the
	# header and to the end of the file
	datatext = text[headerpos[1]:]
	data,comments = getData(datatext,names)
	print 'Not saving comments'
	data = remove_zeros(data)
	unitsDict = createUnitsDict(names,units)
	data['Units'] = unitsDict
	return data
	
# Usage
# filename = "_1_Berea SS #5_Multi-stage 3-axial load_2015-02-16_001.clf"
# filename = "_1_Boise SS #1_1 in hydrostat & triax_2015-02-04_001.clf"
# data = readclf(filename)
