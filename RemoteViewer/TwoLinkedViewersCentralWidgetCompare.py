import sys
import os
import vtk

from ccpi.viewer import viewer2D, viewer3D
from ccpi.viewer.QCILViewerWidget import QCILViewerWidget

# Import linking class to join 2D and 3D viewers
import ccpi.viewer.viewerLinker as vlink

from PySide2 import QtCore, QtWidgets
from PySide2.QtGui import QRegExpValidator
from PySide2.QtCore import QRegExp
import glob, sys, os
from functools import partial
import posixpath, ntpath
import posixpath as dpath
from brem.ui import RemoteFileDialog
from brem.ui import RemoteServerSettingDialog
import brem as drx
from eqt.threading import Worker
from eqt.ui import FormDialog, UIFormFactory
import tempfile


class SingleViewerCenterWidget(QtWidgets.QMainWindow):

    def __init__(self, parent = None):
        QtWidgets.QMainWindow.__init__(self, parent)
        # self.resize(800,600)
        self._tmpdir = None
        self._menus = {}

        self.SetUpMenus()

        self.frame = QCILViewerWidget(viewer=viewer2D,
                                      shape=(600, 600),
                                      interactorStyle=vlink.Linked2DInteractorStyle)
        self.frame1 = QCILViewerWidget(viewer=viewer3D,
                                       shape=(600, 600),
                                       interactorStyle=vlink.Linked3DInteractorStyle)
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.frame)
        layout.addWidget(self.frame1)
        widget = QtWidgets.QWidget(self)
        widget.setLayout(layout)
        # self.setCentralWidget(self.frame)
        self.setCentralWidget(widget)

        self.show()

    @property
    def tempdir(self):
        if self._tmpdir is None: 
            self._tmpdir = tempfile.TemporaryDirectory()
            print ("created", self._tmpdir.name)
        return self._tmpdir

    def CleanUpAndClose(self):
        self.tempdir.cleanup()
        self.close()

    def SetUpMenus(self):
        self.SetUpFileMenu()
        self.SetUpViewMenu()

    def SetUpViewMenu(self):
        viewMenu = self.menuBar().addMenu("View")

        viewSelected = QtWidgets.QAction('Visualise Selected File', parent=self)
        viewSelected.triggered.connect(lambda: self.GetAndVisualiseFile())

        viewMenu.addAction(viewSelected)
        self._menus['view'] = {'visualise': viewSelected}

    def SetUpFileMenu(self):

        fileMenu = self.menuBar().addMenu("File")

        selectFile = QtWidgets.QAction('Select File', parent=self)
        
        selectRemoteFile = QtWidgets.QAction('Select Remote File', parent=self)
        selectRemoteFile.triggered.connect(lambda: self.browseRemote())
        
        configureRemote = QtWidgets.QAction('Configure Remote', parent=self)
        configureRemote.triggered.connect(self.openConfigRemote)
        
        quit = QtWidgets.QAction('Quit', parent=self)
        quit.triggered.connect(self.CleanUpAndClose)

        fileMenu.addAction(selectFile)
        fileMenu.addAction(selectRemoteFile)
        fileMenu.addSeparator()
        fileMenu.addAction(configureRemote)
        fileMenu.addSeparator()
        fileMenu.addAction(quit)

        actions = {'file' : selectFile, 
                   'remoteFile' : selectRemoteFile , 
                   'configureRemote': configureRemote, 
                   'quit': quit}

        self._menus['file'] = { 'menu' : fileMenu , 'actions' : actions }
    
    def openConfigRemote(self):

        dialog = RemoteServerSettingDialog(self,port=None,
                                    host=None,
                                    username=None,
                                    private_key=None)
        dialog.Ok.clicked.connect(lambda: self.getConnectionDetails(dialog))
        dialog.exec()

    def getConnectionDetails(self, dialog):
        for k,v in dialog.connection_details.items():
            print (k,v)
        self.connection_details = dialog.connection_details

    def browseRemote(self):
        # private_key = os.path.abspath("C:\Apps\cygwin64\home\ofn77899\.ssh\id_rsa")
        # port=22
        # host='ui3.scarf.rl.ac.uk'
        # username='scarf595'
        if hasattr(self, 'connection_details'):
            username = self.connection_details['username']
            port = self.connection_details['server_port']
            host = self.connection_details['server_name']
            private_key = self.connection_details['private_key']

            logfile = os.path.join(os.getcwd(), "RemoteFileDialog.log")
            dialog = RemoteFileDialog(self,
                                        logfile=logfile,
                                        port=port,
                                        host=host,
                                        username=username,
                                        private_key=private_key)
            dialog.Ok.clicked.connect(lambda: self.getSelected(dialog))
            if hasattr(self, 'files_to_get'):
                try:
                    dialog.widgets['lineEdit'].setText(self.files_to_get[0][0])
                except:
                    pass
            dialog.exec()

    def getSelected(self, dialog):
        if hasattr(dialog, 'selected'):
            print (type(dialog.selected))
            for el in dialog.selected:
                print ("Return from dialogue", el)
            self.files_to_get = list (dialog.selected)

    def GetAndVisualiseFile(self):
        # 1 download self.files_to_get
        if len(self.files_to_get) == 1:
            self.asyncCopy = AsyncCopyFromSSH()
            if not hasattr(self, 'connection_details'):
                self.statusBar().showMessage("define the connection")
                return
            username = self.connection_details['username']
            port = self.connection_details['server_port']
            host = self.connection_details['server_name']
            private_key = self.connection_details['private_key']

            self.asyncCopy.setRemoteConnectionSettings(username=username,
                                                       port=port, host=host, private_key=private_key)
            self.asyncCopy.SetRemoteFileName(dirname=self.files_to_get[0][0], filename=self.files_to_get[0][1])
            self.asyncCopy.SetDestinationDir(os.path.abspath(self.tempdir.name))
            self.asyncCopy.signals.finished.connect(lambda: self.visualise())
            self.asyncCopy.GetFile()

    def visualise(self):
        print("HERE WE ARE")
        f = os.path.join(os.path.abspath(self.tempdir.name), self.files_to_get[0][1])
        if os.path.exists(f):
            print("YEEEE")

            #reader = vtk.vtkNIFTIImageReader()
            reader = vtk.vtkMetaImageReader()
            reader.SetFileName(f)
            reader.Update()

            self.frame.viewer.setInputData(reader.GetOutput())
            self.frame1.viewer.setInputData(reader.GetOutput())
        else:
            print("WTF")
# class TwoLinkedViewersCenterWidget(QtWidgets.QMainWindow):

#     def __init__(self, parent = None):
#         QtWidgets.QMainWindow.__init__(self, parent)
#         #self.resize(800,600)
        
#         self.frame1 = QCILViewerWidget(viewer=viewer2D, shape=(600,600),
#               interactorStyle=vlink.Linked2DInteractorStyle)
#         self.frame2 = QCILViewerWidget(viewer=viewer2D, shape=(600,600),
#               interactorStyle=vlink.Linked2DInteractorStyle)
                
#         # reader = vtk.vtkMetaImageReader()
#         # reader.SetFileName('head.mha')
#         # reader.Update()
#         reader1 = vtk.vtkNIFTIImageReader()
#         reader2 = vtk.vtkNIFTIImageReader()
#         dirname = os.path.abspath('C:/Users/ofn77899/Documents/Projects/PETMR/data/MCIR_compare')
#         # reader1.SetFileName(os.path.join(dirname, 'parallelproj_cpu_100.nii'))
#         # reader2.SetFileName(os.path.join(dirname, 'scarf_class_100.nii'))
#         reader1.SetFileName(os.path.join(dirname, 'parallelproj_adjoint_gate0.nii'))
#         reader2.SetFileName(os.path.join(dirname, 'ray_adjoint_gate0.nii'))
#         reader1.Update()
#         reader2.Update()

#         math = vtk.vtkImageMathematics()
#         math.SetOperationToSubtract()
#         math.SetInput1Data(reader1.GetOutput())
#         math.SetInput2Data(reader2.GetOutput())
#         math.Update()
#         stats = vtk.vtkImageHistogramStatistics()
#         stats.SetInputConnection(math.GetOutputPort())
#         stats.Update()
#         print("Difference min:{} max:{} mean:{} std: {}".format(stats.GetMinimum(), stats.GetMaximum(),
#          stats.GetMean(), stats.GetStandardDeviation()))

#         self.frame1.viewer.setInputData(reader1.GetOutput())
#         self.frame2.viewer.setInputData(reader2.GetOutput())
        
#         self.frame1.viewer.updateCornerAnnotation('parallelproj', 3)
#         self.frame2.viewer.updateCornerAnnotation('ray-cast', 3)
#         # Initially link viewers
#         self.linkedViewersSetup()
#         self.link2D3D.enable()

#         layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
#         layout.addWidget(self.frame1)
#         layout.addWidget(self.frame2)
        
#         cw = QtWidgets.QWidget()
#         cw.setLayout(layout)
#         self.setCentralWidget(cw)
#         self.central_widget = cw
#         self.show()

#     def linkedViewersSetup(self):
#         v2d = self.frame1.viewer
#         v3d = self.frame2.viewer
#         self.link2D3D = vlink.ViewerLinker(v2d, v3d)
#         self.link2D3D.setLinkPan(True)
#         self.link2D3D.setLinkZoom(True)
#         self.link2D3D.setLinkWindowLevel(True)
#         self.link2D3D.setLinkSlice(True)
class RemoteAsyncCopyFromSSHSignals(QtCore.QObject):
    status = QtCore.Signal(tuple)
    job_id = QtCore.Signal(int)
class AsyncCopyFromSSH(object):
    def __init__(self, parent=None):

        self.internalsignals = RemoteAsyncCopyFromSSHSignals()
        self.threadpool = QtCore.QThreadPool()
        self.logfile = 'AsyncCopyFromSSH.log'
        self._worker = None
        
    def SetRemoteFileName(self, dirname, filename):
        self.remotefile = filename
        self.remotedir = dirname
    def SetDestinationDir(self, dirname):
        self.localdir = dirname

    @property
    def signals(self):
        return self.worker.signals

    @property
    def worker(self):
        if self._worker is None:
            username = self.connection_details['username']
            port = self.connection_details['port']
            host = self.connection_details['host']
            private_key = self.connection_details['private_key']
            localdir = self.localdir

            self._worker = Worker(self.copy_worker, 
                                  remotedir=self.remotedir, 
                                  remotefile = self.remotefile,
                                  host=host, 
                                  username=username, 
                                  port=port, 
                                  private_key=private_key, 
                                  logfile=self.logfile, 
                                  update_delay=10, 
                                  localdir=localdir)
        return self._worker

    def setRemoteConnectionSettings(self, username=None, 
                                    port= None, host=None, private_key=None, localdir=None):
        self.connection_details = {'username': username, 
                                   'port': port,
                                   'host': host, 
                                   'private_key': private_key,
                                   'localdir': localdir}

    def copy_worker(self, **kwargs):
        # retrieve the appropriate parameters from the kwargs
        host         = kwargs.get('host', None)
        username     = kwargs.get('username', None)
        port         = kwargs.get('port', None)
        private_key  = kwargs.get('private_key', None)
        logfile      = kwargs.get('logfile', None)
        update_delay = kwargs.get('update_delay', None)
        remotefile   = kwargs.get('remotefile', None)
        remotedir    = kwargs.get('remotedir', None)
        localdir     = kwargs.get('localdir', None)

        if remotefile is not None:

            # get the callbacks
            message_callback  = kwargs.get('message_callback', None)
            progress_callback = kwargs.get('progress_callback', None)
            status_callback   = kwargs.get('status_callback', None)
            
            
            from time import sleep

            a = drx.BasicRemoteExecutionManager(host=host, username=username,
                           port=22, private_key=private_key)

            a.login(passphrase=False)
            
            # if message_callback is not None:
            #     message_callback.emit("{}".format(tail.decode('utf-8')))
            # set the progress to 100
            if progress_callback is not None:
                progress_callback.emit(0)

            a.changedir(remotedir)
            cwd = os.getcwd()
            os.chdir(localdir)
            print("get file", remotefile)
            a.get_file("{}".format(remotefile))
            print("done")
            
            a.logout()
            os.chdir(cwd)
            
            if progress_callback is not None:
                progress_callback.emit(100)
            
    def GetFile(self):
        self.threadpool.start(self.worker)

if __name__ == "__main__":
 
    app = QtWidgets.QApplication(sys.argv)
 
    window = SingleViewerCenterWidget()
    # window = TwoLinkedViewersCenterWidget()
 
    sys.exit(app.exec_())
