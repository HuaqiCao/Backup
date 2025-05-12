from  matplotlib.backends.backend_qt5agg  import  ( NavigationToolbar2QT  as  NavigationToolbar ) 
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import math
import random
import sys
import layout1 as lay1
import layout2 as lay2
import layout3 as lay3
import layout4 as lay4
import layout5 as lay5
import win_lay1_binary as win_lay1
import win_lay2_binary as win_lay2
import win_lay3_binary as win_lay3
import win_lay4_binary as win_lay4
import win_lay5_binary as win_lay5

class _window_control():
    def __init__(self):
        super(_window_control, self).__init__()
        #init
        self._w1_yes = 0
        self._w2_yes = 0
        self._w3_yes = 0
        self._w4_yes = 0
        self._w5_yes = 0
        self.initState()

    def initState(self):
        if self._w2_yes:
            self.template_pick.closewin()
            self._w2_yes = 0
        if self._w3_yes:
            self.template_pick.closewin()
            self._w3_yes = 0
        self.pulse_inspect = win_lay1._pulse_inspect()
        self._w1_yes = 1
        self.pulse_inspect.show()
        self.pulse_inspect.commandLinkButton.clicked.connect(self._open_w2)

    def _open_w2(self):
        self.template_pick = win_lay2._benchmark_select()#self.pulse_inspect.FilePath,self.pulse_inspect.FileName,self.pulse_inspect.Paralist)
        self._w2_yes = 1
        if self._w3_yes:
            self.template_draw.closewin()
            self._w3_yes = 0
        if self._w1_yes:
            self.pulse_inspect.closewin()
            self._w1_yes = 0
        self.template_pick.show()
        self.template_pick.commandLinkButton_former.clicked.connect(self.initState)
        self.template_pick.commandLinkButton_next.clicked.connect(self._open_w3)

    def _open_w3(self):
        self.template_draw = win_lay3._benchmark_corr()
        self._w3_yes = 1
        if self._w2_yes:
            self.template_pick.closewin()
            self._w2_yes = 0
        if self._w4_yes:
            self.noisepowersepct_win.closewin()
            self._w4_yes = 0
        self.template_draw.show()
        self.template_draw.commandLinkButton_former.clicked.connect(self._open_w2)
        self.template_draw.commandLinkButton_next.clicked.connect(self._open_w4)
    def _open_w4(self):
        self._w4_yes = 1
        if self._w3_yes:
            self.template_draw.closewin()
            self._w3_yes = 0
        if self._w5_yes:
            self.matchedfilter_win.closewin()
            self._w5_yes = 0
        self.noisepowersepct_win = win_lay4._noisepowerspectrum()
        self.noisepowersepct_win.show()
        self.noisepowersepct_win.commandLinkButton_former.clicked.connect(self._open_w3)
        self.noisepowersepct_win.commandLinkButton_next.clicked.connect(self._open_w5)
    def _open_w5(self):
        self.matchedfilter_win = win_lay5._matchedfilter()
        self._w5_yes = 1
        if self._w4_yes:
            self.noisepowersepct_win.closewin()
            self._w4_yes = 0
        self.matchedfilter_win.show()
        self.matchedfilter_win.commandLinkButton_former.clicked.connect(self._open_w4)
        #self.matchedfilter_win.commandLinkButton_next.clicked.connect(QCoreApplication.instance().quit())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    '''
    pulse_inspect = win_lay1._pulse_inspect()
    pulse_inspect.show()
    template_pick = win_lay2._benchmark_select(pulse_inspect.FilePath,pulse_inspect.FileName,pulse_inspect.Paralist)
    template_draw = win_lay3._benchmark_corr()
    pulse_inspect.commandLinkButton.clicked.connect(pulse_inspect.closewin)
    pulse_inspect.commandLinkButton.clicked.connect(template_pick.show)
    template_pick.commandLinkButton_former.clicked.connect(template_pick.closewin)
    #QCoreApplication.instance().quit)#
    template_pick.commandLinkButton_former.clicked.connect(pulse_inspect.show)
    template_pick.commandLinkButton_next.clicked.connect(template_pick.closewin)
    template_pick.commandLinkButton_next.clicked.connect(template_draw.show)
    template_draw.commandLinkButton_former.clicked.connect(template_draw.closewin)
    template_draw.commandLinkButton_former.clicked.connect(template_pick.show)
    sys.exit(app.exec_())
    '''
    window = _window_control()
    sys.exit(app.exec_())
