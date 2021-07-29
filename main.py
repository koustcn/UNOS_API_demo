from login import *
from natsort import natsorted
import pyodbc
"""
LICENSE 

Please refer to 
https://creativecommons.org/licenses/by-nc/3.0/


You are free to:
Share — copy and redistribute the material in any medium or format
Adapt — remix, transform, and build upon the material
The licensor cannot revoke these freedoms as long as you follow the license terms.
Under the following terms:
Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use.
NonCommercial — You may not use the material for commercial purposes.


"""


"""
TODO: connect to LIS database or other methods 
"""
server = ''
database = ''
username = ''
password = ''
cnxn = pyodbc.connect(
    'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)


class Main_windows(QtWidgets.QMainWindow):
    switch_window = QtCore.pyqtSignal(str)

    def __init__(self, token, expire, refreshtoken, baseurl, client_id, client_secret, parent=None):
        """

        :param token:
        :param expire:
        :param refreshtoken:
        :param baseurl:
        :param client_id:
        :param client_secret:
        :param parent:
        """
        super(Main_windows, self).__init__(parent=parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.token = token
        self.expire = expire
        self.refreshtoken = refreshtoken
        self.baseurl = baseurl
        self.client_id = client_id
        self.client_secret = client_secret
        self.ui.actionLogin.triggered.connect(self.login_clicked)  # login in convert
        self.ui.button_timer.setDisabled(True)
        self.show_timer()  # timer start
        self.ui.button_patientid.clicked.connect(self.search_pt)  # search function selected
        self.ui.tbox_patientid.returnPressed.connect(self.search_pt)  # enter clicked to search pt
        self.ui.actionexit.triggered.connect(self.exit)
        self.m_data = {}  # this to use store all basic  patient info form LIS
        self.unos_data = {}  # this to store all basic patient info from unos
        self.data_color = {
            "First Name": "black",
            "Last Name": "black",
            "DOB": "black",
            "Blood Type": "black",
            "Category": "black",
            "SSN": "black",
            "Status": "black",
            "Unacceptables": "black"
        }  # list to keep color info for the row inorder to display the correct color
        self.m_ua = {}  # dict to store LIS unacceptable data
        self.unos_ua = {}  # dict to store all unos unacceptable data
        self.etag = ""  # etag to for unos version control
        self.ua_only_in_unos = []  # a list to keep all antibodies which is unique to unos
        self.ua_only_in_m = []  # a list to keep all antibodies which is unique to mtida
        self.ui.cbox_center_code.addItems(["GGGG"])
        self.ui.cbox_center_type.addItems(["TX1"])
        self.ui.cbox_program_tpye.addItems(["KI", "HR", "IN", "PA", "LU", "LI"])
        """
        UPDATE all parameter for the unos. 
        """
        self.ui.button_ab_update.clicked.connect(self.unos_update)  # event to update the unos antibodies table
        self.register_id = ""  # unos register id
        self.ui.button_timer.clicked.connect(self.renew_token)  # refresh token use refresh token.
        self.dict_cat = {
            "KI": ["KR", "KPR", "KSB", "KLR", "KUR", "KHR"],
            "HR": ["HR", "KHR", "HIR", "HLR"],
            "LU": ["LUR", "KUR", "LLR", "LBR"],
            "LI": ["LR", "LLR", "LVBM", "KLR", "HIR"],
            "IN": ["KSB", "SBR"],
            "PA": ["PR", "KPR"]
        }

    def exit(self):
        """

        :return:
        """
        if self.user_warnning(1):
            exit(0)

    def login_clicked(self):
        """

        :return:
        """
        """
        TODO login click swith to the login screen
        """
        print("YES")
        """self.login = LogIn()
        self.login.switch_window.connect(self.show_login)
        self.login.show()"""

    def user_warnning(self, message):

        qm = QtWidgets.QMessageBox

        if message == 0:
            qm.question(self, '', "Not able to update because the patient is not existed in Unet", qm.Yes)
        if message == 1:
            answer = qm.question(self, '', "Are you sure that you want to exit? ", qm.Yes | qm.No)
            if answer == qm.Yes:
                return True
            else:
                return False
        if message == 2:
            answer = qm.question(self, '', "One or more values does not match do you still want to continue?",
                                 qm.Yes | qm.No)
            if answer == qm.Yes:
                return True
            else:
                return False
        if message == 3:
            qm.question(self, '',
                        "Patient cPRA is greater than 98, A director approved is required for Kidney listing",
                        qm.Yes)
        if message == 4:
            qm.question(self, '', "Please enter the patient identifier", qm.Yes)

    def show_timer(self):
        """
        main timer loop to use QTimer

        :return:
        """
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.display_time)
        timer.start(1000)  # count every second

    def display_time(self):
        """
        display timer
        :return:
        """
        self.expire -= 1
        if self.expire > 0 and self.expire % 60 == 0:
            self.ui.button_timer.setText(str(int(self.expire / 60)) + " Min Left")
        elif self.expire < 60:
            self.ui.button_timer.setDisabled(False)
            self.ui.button_timer.setText("Session Expired Click To Reset")
        elif self.expire < 30:
            self.renew_token()


    def search_pt(self):
        """
        search patient by MRN or LIS id.

        :return:
        """
        self.m_data = {}
        self.unos_data = {}
        self.data_color = {
            "First Name": "black",
            "Last Name": "black",
            "DOB": "black",
            "Blood Type": "black",
            "Category": "black",
            "SSN": "black",
            "Status": "black",
            "Unacceptables": "black"
        }
        self.ui.text_unos_status.clear()
        txt_from_box = self.ui.tbox_patientid.text().strip()
        if txt_from_box.strip() == "":
            self.user_warnning(4)
            return
        m_search = M_DataBaseQuery(cnxn)
        m_id_result = m_search.query_by_mid(txt_from_box)
        mrn_result = m_search.query_by_mrn(txt_from_box)
        if len(mrn_result) > 0:
            self.m_data, self.m_ua = m_search.m_datebase_paser(mrn_result[0])
        if len(m_id_result) > 0:
            self.m_data, self.m_ua = m_search.m_datebase_paser(m_id_result[0])
        self.display_pt_info()

    def display_pt_info(self):
        """

        :return:
        """
        self.ui.txt_from_mtilda.clear()
        self.ui.txt_from_unos.clear()
        self.ui.label_cpra.clear()
        if len(self.m_data) == 0:
            self.ui.txt_from_mtilda.appendPlainText("Patient Not Found!")
        else:
            self.auto_cat_selector()
            self.download_pt_from_unos()
            self.info_checker()
            for k, v in self.m_data.items():
                self.ui.txt_from_mtilda.appendHtml(
                    '<p style = "color:{}">{}: {}</p>'.format(str(self.data_color[k]), str(k), str(v)))
            for k, v in self.unos_data.items():
                self.ui.txt_from_unos.appendHtml(
                    '<p style = "color:{}">{}: {}</p>'.format(str(self.data_color[k]), str(k), str(v)))
        self.ui.txt_ab_mtilda.clear()
        self.ui.txt_ab_unos.clear()
        self.add_split_ag()
        self.ua_compare()
        self.auto_ua_checker()

        str_ua_unos = ""
        str_ua_m = ""
        for i in self.unos_ua:
            if i in self.ua_only_in_unos:
                str_ua_unos = str_ua_unos + "<strong style='color: red'>{} </strong>".format(i)
            else:
                str_ua_unos = str_ua_unos + "<span style='color: black'>{} </span>".format(i)
        self.ui.txt_ab_unos.appendHtml(str_ua_unos)
        for i in self.m_ua:
            if i in self.ua_only_in_m:
                str_ua_m = str_ua_m + "<strong  style='color: green'>{} </strong>".format(i)
            else:
                str_ua_m = str_ua_m + "<span style='color: black'>{} </span>".format(i)
        self.ui.txt_ab_mtilda.appendHtml(str_ua_m)

    def ua_compare(self):
        """
        compare two list generate the difference
        """

        self.ua_only_in_unos = list(set(self.unos_ua) - set(self.m_ua))
        self.ua_only_in_m = list(set(self.m_ua) - set(self.unos_ua))

    def info_checker(self):
        """
        format the self m_data and unos data, formate the data and remove junk info
        :return:
        """
        try:
            self.m_data["DOB"] = self.m_data["DOB"].strftime("%Y-%m-%d")
        except:
            pass
        try:
            self.unos_data["DOB"] = self.unos_data["DOB"][0:10]
        except:
            pass
        if len(self.m_data) == len(self.unos_data):
            if self.unos_data["Status"]  in [4099, 7999, 2999]:
                self.unos_data["Status"] = "AI"
            if self.unos_data["Status"] in [4010, 7010, 2020, 2016, 2140] :
                self.unos_data["Status"] = "AA"
            # print(self.m_data)

            for k, v in self.unos_data.items():
                v = str(v)
                v = re.sub("[^0-9A-Za-z]", "", v)
                if v.upper().strip() != re.sub("[^0-9A-Za-z]", "", str(self.m_data[k]).upper().strip()):
                    self.data_color[k] = 'red'
                if k == "Category":
                    if self.m_data["Category"].strip() in self.dict_cat[v]:
                        self.data_color[k] = 'black'

    def download_pt_from_unos(self):
        """

        :return:
        """

        X_Center_Code = self.ui.cbox_center_code.currentText()
        X_Center_Type = self.ui.cbox_center_type.currentText()
        X_Program_Type = self.ui.cbox_program_tpye.currentText()
        self.unos_connect = waiting_list_manger(self.baseurl, self.token, X_Center_Code, X_Center_Type, X_Program_Type)

        if self.m_data["SSN"] is not None:
            self.register_id, allinfo = self.unos_connect.filter_by_ssn(self.m_data["SSN"])
            if self.register_id is False:
                self.ui.text_unos_status.clear()
                if len(allinfo) == 0:
                    self.ui.text_unos_status.appendPlainText(
                        "The patient is not in the UNet, please check the patient status and program type")
                else:
                    self.ui.text_unos_status.appendPlainText(str(allinfo))
            else:
                self.unos_data = self.unos_connect.unos_info_paser(allinfo)
                raw_unos_ua, self.etag = self.unos_connect.get_un_list(self.register_id)
                self.unos_ua = self.unos_connect.unos_ua_covert_list_ua(raw_unos_ua)
        else:
            self.ui.text_unos_status.appendPlainText(
                "Please check the SSN in LIS")


    def unos_error_paser(self, info):
        """
        paser for convert the unos error to readable information
        :param info:
        :return:
        """

        try:
            return_info = ''
            for i in info[0]["Messages"]:
                # print(i)
                return_info = return_info + "{}{}\r\n".format(i["Message"], i["Property"])
            return return_info
        except:
            try:
                return info["ValidationResults"][0]["Messages"][0]["Message"]
            except:
                pass
            return str(info)

    def add_split_ag(self):
        """
        add split antiboies
        :return:
        """
        split_ag_dict = {
            "A9": ["A23", "A24"],
            "A10": ["A25", "A26", "A34", "A66"],
            "A19": ["A29", "A30", "A31", "A32", "A33", "A74"],
            "A28": ["A68", "A69"],
            "B5": ["B51", "B52"],
            "B12": ["B44", "B45"],
            "B14": ["B64", "B65"],
            "B15": ["B62", "B63", "B75", "B76", "B77"],
            "B16": ["B38", "B39"],
            "B17": ["B57", "B58"],
            "B21": ["B49", "B50"],
            "B22": ["B54", "B55", "B56"],
            "B40": ["B60", "B61"],
            "B70": ["B71", "B72"],
            "Cw3": ["Cw9", "Cw10"],
            "DQ3":["DQ7","DQ8","DQ9"],
            "DR3":["DR17","DR18"],
            "DR2":["DR15","DR16"],
            "DR5":["DR11","DR12"]
        }

        for k, v in split_ag_dict.items():
            if len(list(set(v) - set(self.m_ua))) == 0:
                self.m_ua.append(k)
        self.m_ua = natsorted(self.m_ua)

    def auto_ua_checker(self):
        """
        control the check box for unos ab detected and unos ab tests

        :return:
        """
        self.ui.checker_ab_test.setChecked(True)
        # print(len(self.m_ua))
        if len(self.m_ua) > 0 and "NEGATIVE" not in self.m_ua:
            self.ui.checker_ab_detected.setChecked(True)
        else:
            self.ui.checker_ab_detected.setChecked(False)

    def auto_cat_selector(self):
        """
        match the unos cat with the mtilda cat, if the patient has two or more organs listed
        The user is able to select one of those and query from unos
        :return:
        """

        list_cat = []
        for k, v in self.dict_cat.items():
            if self.m_data["Category"].strip() in v:
                list_cat.append(k)
        if len(list_cat) > 0 and self.ui.cbox_program_tpye.currentText() not in list_cat:
            index = self.ui.cbox_program_tpye.findText(list_cat[0])
            self.ui.cbox_program_tpye.setCurrentIndex(index)

    def unos_update(self):
        """
        update unacceptable
        :return:
        """
        if len(self.unos_data) == 0:  # if no unos data return not able to update
            self.user_warnning(0)
            return
        for k, v in self.data_color.items():  # display warning if mismatch info found
            if v == "red":
                if self.user_warnning(2) is False:
                    return
                break

        ab_to_update = self.ui.txt_ab_mtilda.toPlainText()  # get the list from LIS input
        to_unos, to_error = self.unos_connect.list_ab_convert_to_unos_ua(ab_to_update)  # convert to the unos format
        """
        Control AntibodiesDetected and  AntibodiesDetected paramters. 
        """
        if self.ui.checker_ab_detected.checkState() > 0:
            to_unos["AntibodiesDetected"] = True
        else:
            to_unos["AntibodiesDetected"] = False

        if self.ui.checker_ab_test.checkState() > 0:
            to_unos["AntibodiesTested"] = True
        else:
            to_unos["AntibodiesTested"] = False

        unos_echo, txt_echo = self.unos_connect.update_unos_ua(self.register_id, to_unos, self.etag)  # update

        self.ui.text_unos_status.clear()  # clear the status

        if len(to_error) > 0:  # display the antibodies which is not able to update
            self.ui.text_unos_status.appendPlainText("".join(to_error))
        if unos_echo:
            if len(txt_echo["ValidationResults"]) == 0:
                self.ui.text_unos_status.appendPlainText("UNOS update status okay")
            else:
                self.ui.text_unos_status.appendPlainText(self.unos_error_paser(txt_echo))
            self.ui.label_cpra.setText(str(txt_echo["Value"]["CpraPercentScore"]))
            if txt_echo["Value"]["CpraPercentScore"] > 98:
                self.user_warnning(3)
        else:
            if len(txt_echo) > 0:
                self.ui.text_unos_status.appendPlainText(self.unos_error_paser(txt_echo))

    def renew_token(self):
        """
        token renew call
        :return:
        """
        self.token, self.expire, self.refreshtoken = UNOS_Auth(self.baseurl, self.client_id,
                                                               self.client_secret).auth_refresh(self.refreshtoken)
        self.expire = int(self.expire)
        self.show_timer()

    def show_login(self):
        controller = Controller()
        controller.show_login()


class Controller:
    """
    windows switch for the login.
    """

    def __init__(self):
        """

        """
        self.token = ""
        self.expire = 3600
        self.refreshtoken = ""

    def show_login(self):
        """
        login in windows
        :return:
        """

        self.login = LogIn()
        self.login.switch_window.connect(self.show_main)
        self.login.show()

    def show_main(self):
        """
        basic parameters for the unet
        :return:
        """
        self.token = self.login.token
        self.expire = self.login.expire
        self.refreshtoken = self.login.refreshtoken
        self.baseurl = self.login.baseurl
        self.client_id = self.login.client_id
        self.client_secret = self.login.client_secret
        self.window = Main_windows(self.token, self.expire, self.refreshtoken, self.baseurl, self.client_id,
                                   self.client_secret)
        self.login.close()
        self.window.show()


def main():
    app = QtWidgets.QApplication(sys.argv)
    controller = Controller()
    controller.show_login()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
