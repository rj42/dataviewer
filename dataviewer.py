## For build
# from pyqtgraphBundleUtils import *
# from pyqtgraph import setConfigOption
# setConfigOption('useOpenGL', False)
###############
import sys,os
# sys.path.append('dataviewer_lib') # comment this line on build and put files from the lib directly to the same folder
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree import types as pTypes
import numpy as np
from lib import pymat, readclf


Colors = [(255,255,255),(255,0,0),(0,255,0),(0,0,255)];

ModifyingParameters = [
    {'name':'Plot vs.','type':'list','values':['x','y']},
    {'name':'Parameter', 'type':'list'},
    {'name':'Interval', 'type':'list'},
    {'name':'min', 'type':'float', 'value':0.0,'dec':True,'step':1.0},
    {'name':'max', 'type':'float', 'value':1.0,'dec':True,'step':1.0},
    {'name':'Reduce', 'type':'int', 'value':1,'dec':True,'step':1},
    {'name': 'Linear Trend', 'type': 'group', 'children': [
        {'name': 'Show trend', 'type': 'bool', 'value': False, 'tip': "Press to plot trend"},
        {'name':'Trend parameter', 'type':'list'},
        {'name':'a', 'type':'float', 'value':0.0,'dec':True},
        {'name':'b', 'type':'float', 'value':0.0,'dec':True}
    ]}
]

def truncatedata(dic,key,interval):
    '''
    truncates data to values corresponding only to the interval of 
    values in dic[key]
    '''
    newdic = {}
    t = dic[key]
    for i in dic.keys():
        newdic[i] =  dic[i][(t>=interval[0]) & (t<=interval[1])]
    return newdic

def reducedata(dic,order):
    '''
    reduces data. returns data with only n-th (order) datapoint.
    '''
    if order == 1: return dic
    newdic = {}
    for i in dic.keys():
        # ind = np.arange()
        n = len(dic[i])
        newdic[i] =  dic[i][np.arange(0,n,order)]
    return newdic

class DataViewer(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.data = None
        # default plots will be drawn with multiple y and single x
        self.mainAxis = 'x'
        self.setupGUI()
        # create two columns for load and save buttons        
        self.loadsavetree.setColumnCount(2)
        # create buttons
        self.loadbutton = QtGui.QPushButton('Load')
        self.savebutton = QtGui.QPushButton('Save')
        # create container for buttons
        item = QtGui.QTreeWidgetItem(["Item"])
        # add container to the TreeWidget
        self.loadsavetree.addTopLevelItem(item)
        # add buttons to the containee
        self.loadsavetree.setItemWidget(item,0, self.loadbutton)
        self.loadsavetree.setItemWidget(item,1, self.savebutton)
        # set column sizes
        self.loadsavetree.header().resizeSection(0, 100)
        self.loadsavetree.header().resizeSection(0, 100)
        # hide header
        self.loadsavetree.setHeaderHidden(True)
        # connect load button with load function
        # we don't connect save button yet since there is
        # no data to save
        self.loadbutton.clicked.connect(self.load)

        self.legend = None
        # self.legend = False
    def checkForLastDir(self):
        '''
        tries to open file 'lastdir'
        if it exists, returns the contents,
        else returns none
        '''
        try:
            with open('lastdir','r') as f:
                return f.read()
        except IOError:
            return ''
    def makeLastDir(self,filename):
        '''
        gets directory name from file absolute path
        create file 'lastdir' and writes 
        '''
        with open('lastdir','w') as f:
            f.write(os.path.dirname(filename))
    def load(self):
        '''
        opens file manager, reads data from file,
        calls generateList to put into GUI
        '''
        self.lastdir = self.checkForLastDir()
        # second par - name of file dialog window
        # third parameter - default file name
        # forth parameter - file filter. types separated by ';;'
        filename = QtGui.QFileDialog.getOpenFileName(self, "", "%s"%(self.lastdir), "*.clf;;MAT files (*.mat)")
        if filename[0] == '': return
        if filename[1] == 'MAT files (*.mat)':
            self.data = pymat.load(filename[0])
        elif filename[1] == u'*.clf':
            data = readclf.readclf(filename[0])
        else: raise IOError('Cannot read this file format.')
        # this is to remember this name when we wanna save file
        self.makeLastDir(filename[0]) # extract filename from absolute path
        self.filename = os.path.basename(filename[0])
        # remove extension from name
        self.filename = os.path.splitext(self.filename)[0]
        # Separate all digital data and units    
        self.units = data['Units']
        del data['Units']
        self.data = data
        # # we need this attribute for speedup. it coresponds to 
        # # reduced data. see method reduce
        self.reducedData = self.data;self.truncatedData = self.data
        try:
            self.datalength = len(self.data[self.data.keys()[1]])
        except: self.datalength = 1
        self.setParameters()
        self.connect()

    def save(self):
        self.lastdir = self.checkForLastDir()
        # second par - name of file dialog window
        # third parameter - default file name
        # forth parameter - file filter. types separated by ';;'
        filename = pg.QtGui.QFileDialog.getSaveFileName(self, 
            "Save to MATLAB format", "%s%s"%(self.lastdir,self.filename), "MAT files (*.mat)")
        if filename[0] == '': return
        pymat.save(filename[0],self.data)

    def connect(self):
        '''
        Makes new connection of list entries with plot after
        loading a new dataset.
        'Parameter' with name Time is default if it's in the list
        Default Interval variable is set to Time
        '''
        # set default values for modifying parameters
        self.modparams.param('Parameter').setValue('Time')
        self.modparams.param('Interval').setValue('Time')
        # connect signals to updating functions
        self.params.sigTreeStateChanged.connect(self.update)
        self.slider.sigGradientChanged.connect(self.truncate)
        self.modparams.param('Interval').sigValueChanged.connect(self.update)
        self.modparams.param('min').sigValueChanged.connect(self.setTicks)
        self.modparams.param('max').sigValueChanged.connect(self.setTicks)
        self.modparams.param('Parameter').sigValueChanged.connect(self.update)
        self.modparams.param('Reduce').sigValueChanged.connect(self.reduce)
        self.modparams.param('Plot vs.').sigValueChanged.connect(self.setMainAxis)
        # connection with trend computations        
        self.params.sigTreeStateChanged.connect(self.setTrendParameter)
        self.modparams.param('Parameter').sigValueChanged.connect(self.checkTrendUpdates)
        self.modparams.param('Plot vs.').sigValueChanged.connect(self.setTrendParameter)
        self.computeTrendFlag.sigValueChanged.connect(self.checkTrendUpdates)
        self.trendParameter.sigValueChanged.connect(self.setTrendParameter)
        #  Finally enable the save button
        self.savebutton.clicked.connect(self.save)

    def checkTrendUpdates(self):
        if self.computeTrendFlag.value(): self.computeTrend()
        self.update()
    def setTrendParameter(self):
        entries = self.activeEntries() 
        for i in entries: pass
        if entries != []: self.trendParameter.setValue(i)
        self.checkTrendUpdates()

    def reduce(self):
        reduction_order = self.modparams.param('Reduce').value()
        self.reducedData = reducedata(self.data,reduction_order)
        self.truncate()
        # self.update()
    def truncate(self):
        interval_parameter = self.modparams.param('Interval').value()
        interval = self.getSliderState()
        self.truncatedData = truncatedata(self.reducedData,interval_parameter,interval)
        self.checkTrendUpdates()
        self.update()
    def setMainAxis(self):
        self.mainAxis = self.modparams.param('Plot vs.').value()
        self.update()
    def updateLimits(self):
        interval = self.getSliderState()
        self.modparams.param('min').sigValueChanged.disconnect(self.setTicks)
        self.modparams.param('max').sigValueChanged.disconnect(self.setTicks)
        self.modparams.param('min').setValue(interval[0])
        self.modparams.param('max').setValue(interval[1])
        self.modparams.param('min').sigValueChanged.connect(self.setTicks)
        self.modparams.param('max').sigValueChanged.connect(self.setTicks)
    def setTicks(self):
        '''
        sets ticks to state coressponding to  Interval min/max
        values, when they are manually changed
        '''
        interval_parameter = self.modparams.param('Interval').value()
        scale = self.data[interval_parameter].max()
        values = [float(self.modparams.param('min').value())/scale,
                  float(self.modparams.param('max').value())/scale
                 ]
        i = 0
        self.slider.sigGradientChanged.disconnect(self.update)
        for tick in self.slider.ticks:
            self.slider.setTickValue(tick, values[i])
            i += 1
        self.slider.sigGradientChanged.connect(self.update)
        self.update()

    def update(self):
        '''
        updates plot
        '''
        self.setAxisScale()
        self.updateLimits()
        ### Ready to update
        self.clearPlotWindow()
        self.plt.showGrid(x=True, y=True)
        if self.mainAxis == 'x':
            self.plotVersusX()
        if self.mainAxis == 'y':
            self.plotVersusY()
        if self.computeTrendFlag.value():
            self.plotTrend()

    def plotVersusX(self):
        '''
        plot when we have sevaral y's versus of x.
        '''
        # Get variables to plot
        data = self.truncatedData
        plotlist = self.activeEntries()
        xlabel = self.modparams.param('Parameter').value()
        for i in range(len(plotlist)):
            if i>=len(Colors): 
                print 'Are you sure, man???? That\'s a crapload of data!!!'
                color = (255,255,255)
            else:
                color = Colors[i]
            ylabel = plotlist[i]
            self.plt.plot(data[xlabel],data[ylabel], 
                pen=color, name=plotlist[i])
            self.plt.setLabel('left', plotlist[i])
        self.plt.setLabel('bottom', xlabel)
    def plotVersusY(self):
        '''
        plot when we have sevaral y's versus of x.
        '''
        # Get variables to plot
        data = self.truncatedData
        plotlist = self.activeEntries()
        ylabel = self.modparams.param('Parameter').value()
        for i in range(len(plotlist)):
            if i>=len(Colors): 
                print 'Are you sure, man???? That\'s a crapload of data!!!'
                color = (255,255,255)
            else:
                color = Colors[i]
            xlabel = plotlist[i]
            self.plt.plot(data[xlabel],data[ylabel], 
                pen=color, name=plotlist[i])
            self.plt.setLabel('bottom', xlabel)
        self.plt.setLabel('left', ylabel)

    def plotTrend(self):
        '''
        plots linear trend 
        '''
        if self.mainAxis == 'x':
            xpar = self.modparams.param('Parameter').value()
            ypar = self.trendParameter.value()
            self.plt.setLabel('bottom', xpar)
        if self.mainAxis == 'y':
            xpar = self.trendParameter.value()
            ypar = self.modparams.param('Parameter').value()
        x = self.truncatedData[xpar]
        y = self.slope*x + self.intersection
        self.plt.plot(x,y,pen=(72,209,204), name='%s Trend'%(self.trendParameter.value()))
        self.plt.setLabel('bottom', xpar)
        self.plt.setLabel('left', ypar)

    def clearPlotWindow(self):
        '''
        clears plot from data. clears legend.
        if there is no legend creates it
        '''
        # default legend position
        position = [30,30]
        # clear plot area
        self.plt.clear()
        # remove old legend
        if self.legend: 
            position = self.legend.pos()
            self.legend.scene().removeItem(self.legend)
        # creadte new legend
        self.plt.addLegend([90,20],offset=position)
        self.legend = self.plt.legend
        # print self.legend.pos()
    def setAxisScale(self):
        '''
        sets scale to the interval axis. if time, sets minimum value to 0,
        because it could have been cleared
        '''
        interval_parameter = self.modparams.param('Interval').value()
        if interval_parameter == 'Time':
            self.timeaxis.setRange(0,max(self.data['Time']))
        else:
            self.timeaxis.setRange(min(self.data[interval_parameter]),max(self.data[interval_parameter]))

    def getSliderState(self):
        '''
        returns numpt array 1x2 of slider ticks positions
        note: max position = 1, min = 0
        '''
        interval = []
        for i in self.slider.ticks:
            interval.append(self.slider.tickValue(i))
        interval_parameter = self.modparams.param('Interval').value()
        scale = self.data[interval_parameter].max()
        return np.array(sorted(interval))*scale
    def activeEntries(self):
        '''
        returns a list of active entries in the data bar
        '''
        plotlist = []
        for i in self.data.keys():
            if self.params.param(i).value() == True:
                plotlist.append(i)
        return plotlist
    def setParameters(self):
        self.paramlist = []
        self.modparamlist = ModifyingParameters
        # set parameters for plottings
        for i in self.data.keys():
            self.paramlist.append(dict(name=i, type='bool', value=False))

        # set modifying parameters
        self.modparamlist[1]['values'] = self.data.keys() # Parameter
        self.modparamlist[2]['values'] = self.data.keys() # Interval
        self.modparamlist[5]['limits'] = [1,self.datalength] # Reduce
        self.modparamlist[6]['children'][1]['values'] = self.data.keys() # Trend parameter
        # create parameter class instances()
        self.params = Parameter.create(name='params', type='group',children=self.paramlist)
        self.modparams = Parameter.create(name='modparams', type='group',children=self.modparamlist)
        self.tree.setParameters(self.params, showTop=False)
        self.modtree.setParameters(self.modparams, showTop=False)
        self.assignAttributes() # to get shorter names
    def assignAttributes(self):
        '''
        assign parameters from modparams tree to class DataViewer
        attributes to shorten code
        '''
        # assign chilren of 'Linear Trend' group to class attributes
        self.computeTrendFlag = self.modparams.param('Linear Trend').children()[0]
        self.trendParameter = self.modparams.param('Linear Trend').children()[1]
        self.trendSlope = self.modparams.param('Linear Trend').children()[2]
        self.trendIntersection = self.modparams.param('Linear Trend').children()[3]
    def setupGUI(self):
        # Global widget where we place our layout
        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        # splitter is a widget, which handles the layout
        # it splits the main window into parameter window
        # and the plotting area
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.layout.addWidget(self.splitter)

        # tree is a list of parameters to plot
        self.tree = ParameterTree(showHeader=False)
        # modtree is a list of governing parameters to modify plot
        self.modtree = ParameterTree(showHeader=False)
        # loadsave is a list of load and save buttons
        # self.loadsavetree = ParameterTree(showHeader=False)
        self.loadsavetree = pg.TreeWidget()
        # sublayout is were we place our plot and slider
        sublayout = pg.GraphicsLayoutWidget()
        # treesplitter splits parameter window into 2 halfs
        self.treesplitter = QtGui.QSplitter()
        self.buttonsplitter = QtGui.QSplitter()
        self.treesplitter.setOrientation(QtCore.Qt.Vertical)
        self.treesplitter.addWidget(self.tree)
        self.treesplitter.addWidget(self.modtree)
        self.treesplitter.addWidget(self.loadsavetree)
        self.treesplitter.setSizes([int(self.height()*0.501),
                                    int(self.height()*0.45),
                                    20])
        self.treesplitter.setStretchFactor(0, 1)
        self.treesplitter.setStretchFactor(1, 0)
        self.treesplitter.setStretchFactor(2, 0)

        self.splitter.addWidget(self.treesplitter)
        self.splitter.addWidget(sublayout)
        self.splitter.setSizes([int(self.width()*0.25), int(self.width()*0.75)])
        self.plt = sublayout.addPlot()
        self.slider = self.createSlider()
        self.timeaxis = pg.AxisItem('bottom')
        sublayout.nextRow()
        sublayout.addItem(self.slider)
        sublayout.nextRow()
        sublayout.addItem(self.timeaxis)

    def computeTrend(self):
        '''
        computer linear trend a and b and 
        from reduced data. it's important due to a speedup
        '''
        data = self.truncatedData
        if self.mainAxis == 'x': # if multiple plots vs x
            xpar = self.modparams.param('Parameter').value()
            ypar = self.trendParameter.value()
        if self.mainAxis == 'y': # if multiple plots vs y
            ypar = self.modparams.param('Parameter').value()
            xpar = self.trendParameter.value()
        # it's important to work with Reduced data
        x = data[xpar]
        y = data[ypar]
        A = np.array([x, np.ones(len(y))]).T
        ## Solves the equation a x = b by computing a vector x that 
        ## minimizes the Euclidean 2-norm || b - a x ||^2. 
        self.slope,self.intersection = np.linalg.lstsq(A,y)[0]
        self.trendSlope.setValue(self.slope)
        self.trendIntersection.setValue(self.intersection)

    def createSlider(self):
        slider = pg.GradientEditorItem(orientation='top', allowAdd=False)
        slider.rectSize = 0
        for i in slider.ticks:
            slider.setTickColor(i, QtGui.QColor(150,150,150))
        return slider

class ObjectGroupParam(pTypes.GroupParameter):
    def __init__(self):
	    pTypes.GroupParameter.__init__(self, name="Objects", addText="Add New..", addList=['Clock', 'Grid'])

if __name__ == '__main__':
    pg.mkQApp()
    win = DataViewer()
    win.setWindowTitle("Espinoza Team DataViewer")
    win.show()
    win.setGeometry(80, 30, 1000, 700)
    
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
    
    

