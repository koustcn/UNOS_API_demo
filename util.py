import base64
import json
import requests
import re
"""
import packages above
"""


class UNOS_Auth():
    """

    """

    def __init__(self, baseurl, client_id, client_secret):
        """

        :param url:
        :param client_id:
        :param client_secret:
        """
        self.baseurl = baseurl
        self.client_id = client_id
        self.client_secret = client_secret
        self. encodedData = base64.b64encode(bytes(f"{self.client_id}:{self.client_secret}",
                                                   "ISO-8859-1")).decode("ascii") #generate header data
        self. headers = {'Authorization': 'Basic %s' % self.encodedData}

    def json_paser(self, message):
        """

        :param message: message paser
        :return:if 200 return all info else return false with error info
        """
        message_content = json.loads(message.content)

        if message.status_code == 200:
            access_token = message_content["access_token"]
            expires_in = message_content["expires_in"]
            refresh_token = message_content["refresh_token"]
            return access_token, expires_in, refresh_token
        else:
            error_message = None
            error_descr = None
            try:
                error_message=  message_content["error"]
                error_descr =  message_content["error_description"]
            except:
                pass
            return False, error_message, error_descr

    def auth_init(self, username, password):
        """

        :param username: unos username login
        :param password: unos password login
        :return: token for access, expires time and the token for refresh
        """
        message = requests.post("https://%s/oauth/accesstoken?grant_type=password"%self.baseurl,
                          data={"username": username, "password": password}, headers=self.headers)

        return self.json_paser(message)

    def auth_refresh(self,refresh_token):
        """

        :param refresh_token:
        :return: refresh token
        """
        message = requests.post("https://%s/oauth/refresh-accesstoken?grant_type="
                          "refresh_token&refresh_token=%s" % (self.baseurl, refresh_token), headers=self.headers)
        return self.json_paser(message)

class waiting_list_manger():
    """

    """
    def __init__(self, baseurl, token, X_Center_Code, X_Center_Type, X_Program_Type):
        """
        :param baseurl:
        :param token:
        :param X_Center_Code:
        :param X_Center_Type:
        :param X_Program_Type:
        """
        self.baseurl = baseurl
        self.token = token
        self.header = {'Authorization' : 'Bearer {}'.format(token),
                        "X-Center-Code": X_Center_Code,
                        "X-Center-Type": X_Center_Type,
                        "X-Program-Type":X_Program_Type}
        self.ua_table = {}
    def filter_by_ssn (self, ssn):
        """

        :param ssn:patient ssn
        :return:register id for management
        """
        ssn = re.sub("[^0-9A-Za-z]", "", ssn)
        message = requests.get("https://%s/waitlist-registration/v1/registrations?$filter="
                               "SocialSecurityNumber eq '%s'"%(self.baseurl, ssn),
            headers=self.header)
        #print(message.status_code)
        #print(message.content)
        if message.status_code == 200:
            return_dict = json.loads(message.content.decode('utf-8'))
            if len(return_dict["Value"]) == 0: # for the patient not in the unos
                return False, return_dict["Value"]
            for i in return_dict["Value"]:
                return i["RegistrationId"], i
        else:
            return False, message.content

    def prepare_ua_table(self):
        """
        convert the unos data to unos ua table format
        :return:None
        """
        ua_dict = {
            "UnacceptableAntigensA": ["A", "A*"],
            "UnacceptableAntigensB": ["B", "B*"],
            "UnacceptableAntigensBW": ["Bw", "Bw"],
            "UnacceptableAntigensC": ["Cw", "C*"],
            "UnacceptableAntigensDPB1": ["DP", "DPB1*"],
            "UnacceptableAntigensDQA1": ["DQA1*", "DQA1*"],
            "UnacceptableAntigensDQB1": ["DQ", "DQB1*"],
            "UnacceptableAntigensDR": ["DR", "DRB1*"],
            "UnacceptableAntigensDR51": ["DR", "DRB"],
            "UnacceptableAntigensDR52": ["DR", "DRB"],
            "UnacceptableAntigensDR53": ["DR", "DRB"]
        }
        for k, v in ua_dict.items():
            message = requests.get("https://%s/waitlist-registration/v1/lookups/%s" %(self.baseurl ,k),
                                   headers=self.header)
            if message.status_code == 200:
                message_content = json.loads(message.content)
                list_message_dict = message_content["Value"]
                for i in list_message_dict:
                    i["table"] = k
                    if i["Code"].find(":") > -1 or i["Code"].find("*") > -1:
                        self.ua_table[v[1] + i["Code"]] = i
                    else:
                        try:
                            hla_digtal = str(int(i["Code"]))
                        except:
                            hla_digtal =  i["Code"]
                        self.ua_table[v[0] + hla_digtal] = i

        #print(self.ua_table)

    def list_ab_convert_to_unos_ua (self, str_ab):
        """
        :param str_ab: antibodies in str format
        :return:
        """
        if len(self.ua_table) < 1 :
            self.prepare_ua_table()
        ua_unos_data = {"AntibodiesDetected": True,
                "AntibodiesTested": True,
                "UnacceptableAntigensB": [],
                "UnacceptableAntigensA": [],
                "UnacceptableAntigensBW": [],
                "UnacceptableAntigensC": [],
                "UnacceptableAntigensDQB1": [],
                "UnacceptableAntigensDR": [],
                "UnacceptableAntigensDR51": [],
                "UnacceptableAntigensDR52": [],
                "UnacceptableAntigensDR53": [],
                "UnacceptableAntigensDPB1": [],
                "UnacceptableAntigensDQA1": [],
                }

        list_ab = str_ab.split()
        list_unknow = []
        for i in list_ab:
            #i = i.upper()
            try:
                unacceptableantigens = self.ua_table [i]["table"]
                unacceptableantigens_code = self.ua_table [i]["Id"]
                if self.ua_table [i]["IsActive"] == True:
                    ua_unos_data[unacceptableantigens].append(unacceptableantigens_code)
                else:
                    list_unknow.append(i)
            except:
                list_unknow.append(i)
        return ua_unos_data, list_unknow

    def get_un_list(self, register_id):
        """

        :param register_id:
        :return:
        """
        m=requests.get("https://%s/waitlist-registration/v1/registrations/%s/unacceptable-antigens"
                       %(self.baseurl,str(register_id)), headers=self.header)
        if m.status_code == 200:
            return json.loads(m.content)['Value'], m.headers['ETag']
        else:
            return json.loads(m.content)['ValidationResults'], False

    def unos_ua_covert_list_ua(self,unos_ua):
        """

        :param unos_ua:
        :return: list of ua human readable
        """
        if len(self.ua_table) < 1:
            self.prepare_ua_table()
        list_ua = []
        for k,v in self.ua_table.items():# iter all ua table if the table id == dict return by unos then add the key to a list
            if v['Id'] in unos_ua[v['table']]:
                list_ua.append(k)
        return list_ua

    def update_unos_ua(self, register_id,  ua_unos, etag):
        """

        :param ua_unos:
        :return:
        """
        self.header ['If-Match'] = etag
        self.header['Content-Type'] = "application/json; charset=UTF-8"
        ua_unos = json.dumps(ua_unos)
        m = requests.post('https://%s/waitlist-registration/v1/registrations/%s/unacceptable-antigens'%(self.baseurl,register_id),
                          headers = self.header, data= ua_unos)
        print(m.content)
        if m.status_code == 200:
            print(json.loads(m.content))
            return True, json.loads(m.content)
        else:
            return False, self.error_message_decode(json.loads(m.content))

    def error_message_decode(self, dict_str):
        """

        :param dict_str:
        :return:
        """
        if len(dict_str['ValidationResults']) > 0:
            return dict_str['ValidationResults']
        else:
            return True

    def unos_info_paser(self, str_input):
        data_dict = {
            "First Name": "FirstName",
            "Last Name": "LastName",
            "DOB": "DateOfBirth",
            "Blood Type": "VerifiedBloodTypeCode",
            "Category": "RegistrationOrganCode",
            "SSN": "SocialSecurityNumber",
            "Status": "MedicalUrgencyStatusId",
        }
        for k, v in data_dict.items():
            try:
                data_dict[k] = str_input[v]
            except:
                data_dict[k] = None
        return data_dict

class M_DataBaseQuery():
    """
    
    """
    def __init__(self, cnxn):
        """

        :param cnxn:
        """
        self.cnxn = cnxn
        self.cursor = cnxn.cursor()
        pass
    def query_by_mrn(self, mrn):
        """

        :param mrn:
        :return:
        """
        str_query = "select first_name, last_name, dob, abo, category_code, ssn, wait_list_status, cum_antibodies_2 from " \
                    "Patients left join Patient_abs_antigens on Patients.patient_number = Patient_abs_antigens.patient_number " \
                    "where Patients.medical_record = ? "
        self.cursor.execute(str_query, mrn)
        row = self.cursor.fetchall()
        return row

    def query_by_mid(self, patient_mid):
        """

        :param patient_mid: in LIS database the patient id was stored as interger, this query will
        :return:
        """
        try:
            int(patient_mid)
            str_query = "select first_name, last_name, dob, abo, category_code, ssn, wait_list_status, cum_antibodies_2 from " \
                        "Patients left join Patient_abs_antigens on Patients.patient_number = Patient_abs_antigens.patient_number " \
                        "where Patients.patient_number = ? "
            self.cursor.execute(str_query, patient_mid)
            row = self.cursor.fetchall()
            return row
        except:
            return []


    def m_datebase_paser(self, str_input):
        """
        get the result from database change a dict/.
        :param str_input:
        :return:
        """
        data_dict = {
            "First Name": "",
            "Last Name": "",
            "DOB": "",
            "Blood Type": "",
            "Category": "",
            "SSN": "",
            "Status": "",
            "Unacceptables": ""
        }
        base_info = {}
        ua = []

        i = 0
        for k, v in data_dict.items():
            if k != "Unacceptables":
                base_info[k] = str_input[i]
            else:
                if str_input[i] is not None:
                    if len(str_input[i]) >0:
                         ua = str_input[i].split()
            i = i + 1

        dp_table = {"DP1": ["DPB1*01:01"],
                    "DP2": ["DPB1*02:01"],
                    "DP3": ["DPB1*03:01"],
                    "DP4": ["DPB1*04:01", "DPB1*04:02"],
                    "DP5": ["DPB1*05:01"],
                    "DP6": ["DPB1*06:01"],
                    "DP9": ["DPB1*09:01"],
                    "DP10": ["DPB1*10:01"],
                    "DP11": ["DPB1*11:01"],
                    "DP13": ["DPB1*13:01"],
                    "DP14": ["DPB1*14:01"],
                    "DP15": ["DPB1*15:01"],
                    "DP17": ["DPB1*17:01"],
                    "DP18": ["DPB1*18:01"],
                    "DP19": ["DPB1*19:01"],
                    "DP20": ["DPB1*20:01"],
                    "DP23": ["DPB1*23:01"],
                    "DP28": ["DPB1*28:01"]
                    }
        """dq_table = {"DQ2":["DQB1*02:01","DQB1*02:02"],
                    "DQ4":["DQB1*04:"]}"""

        neg_table = {"NEG":[],"Negative":[],"Neg":[],"NEGATIVE":[]}

        check_table = {**dp_table,**neg_table}
        #print(check_table)

        ua_clean = ua.copy()
        for k, v in enumerate(ua):

            if v in check_table:
                ua_clean.remove(v)
                ua_clean = ua_clean + check_table[v]


        return base_info, [x for x in ua_clean if not ("(" in x or ")" in x or "DPA1*" in x)]




if __name__ == "__main__":
    pass




