from PyQt5.uic import loadUi
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, \
    QApplication,\
    QWidget
from PyQt5 import QtCore
import sys
from util import *
from ui.login_ui import *
from ui.main_ui import *
"""
pyuic5 login.ui > login_ui.py"""

class LogIn(QDialog):

    switch_window = QtCore.pyqtSignal()

    def __init__(self,*args, **kwargs):
        super(LogIn, self).__init__(*args, **kwargs)
        #loadUi("ui/login.ui",self)
        self.ui = Ui_UNOS_login()
        self.ui.setupUi(self)
        self.ui.QpushButton_login.clicked.connect(self.unos_auth)
        self.token = ""
        self.expire = 0
        self.refreshtoken = ""
        self.baseurl = "api.unos.org"
        """
        TODO: need API ID and secret
        """
        self.client_id = ""
        self.client_secret = ""

    def unos_auth(self):

        """
        call the UNOS AUth class and use user credential to get the key time and refresh key
        :return:
        """


        username = self.ui.lineEdit_username.text()
        password = self.ui.lineEdit_password.text()
        if len(username) > 0 and len(password) > 0:
            self.token, self.expire, self.refreshtoken = UNOS_Auth(self.baseurl, self.client_id,self.client_secret).auth_init(username, password)
            if self.token == False:
                self.raise_error()
            else:
                self.login()
        else:
            self.raise_error()

    def login(self):
        self.switch_window.emit()

    def raise_error(self):
        qm = QtWidgets.QMessageBox
        qm.question(self, '', "Please enter the correct User info Authorization failure", qm.Yes)

if __name__ == "__main__":
    """
    APP Entry
    """
    app = QApplication(sys.argv)

    login = LogIn()
    widget = QtWidgets.QStackedWidget()
    widget.addWidget(login)
    widget.setFixedHeight(600)
    widget.setFixedWidth(800)

    widget.show()
    sys.exit(app.exec_())

