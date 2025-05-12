# ------------------------------------------------- ----- 
# -------------------- mplwidget.py -------------------- 
# -------------------------------------------------- ---- 
from  PyQt5.QtWidgets  import * 
from  matplotlib.backends.backend_qt5agg  import  FigureCanvas 
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from  matplotlib.figure  import  Figure 
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QSizePolicy
    
class  MplWidget(QWidget):  
    def  __init__ ( self ,  parent  =  None ): 
        QWidget.__init__ ( self, parent)
        self.fig = Figure(tight_layout=True, figsize=(200, 200), dpi=100)
        self.fig.tight_layout()
        self.canvas  =  FigureCanvas(self.fig)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        vertical_layout =  QVBoxLayout() 
        vertical_layout.addWidget(self.canvas) 
        self.canvas.axes =  self.canvas.figure.add_subplot((111),projection=None,position=[0.14, 0.15, 0.84, 0.83])
        self.setLayout(vertical_layout )
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setIconSize(QSize(20,20))
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)

    def defcanvas(self):
        #self.canvas.axes.set_xlim([-120,120])
        #self.canvas.axes.set_ylim([0,120])
        self.canvas.axes.set_xlabel('Time (sample point)')
        self.canvas.axes.set_ylabel('Amplitude (ADC)')
        self.canvas.axes.grid(True)

    def msgwarning1(self):
        QMessageBox.about(self, "Error!", "Wrong baseline calculation interval!")
    def msgwarning2(self):
        QMessageBox.about(self, "Error!", "Please set a correct threshold value!")
    def msgwarning3(self):
        QMessageBox.about(self, "Error!", "Finished!")

        
