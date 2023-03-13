from datetime import datetime
from pytz import timezone
import json
from collections import defaultdict
from itertools import permutations, combinations
import requests

class UnvalidatedTicketError(Exception):
    def __init__(self, msg="Ticket Error Requires Manual Intervention"):
        self.msg = msg
        super(UnvalidatedTicketError, self).__init__(self.msg)


class ValidateTicket:
    # def __init__(self, snow_instance, post_data, dev_log, iface_state_list, snow_client_obj, auth):
    def __init__(self, snow_instance, post_data, dev_log, iface_state_list, snow_session_obj):
        '''
        Set Ticket Values based on parsed Device logs
        :param post_data: extracted ticket_object
        :param dev_log: parsed device log
        :param iface_state_list: dict of ticket_iface-ticket_state -> eg:  {"ticket_iface_name": "ticket_state"}
        :param snow_session_obj: requests.Session object that created session with snow
        # :param snow_client_obj: the snow client session object created by the PySnow.Client instance
        # :param auth: snow user auth
        '''

        self.grp_link = None
        self.grp_sys_id_value = None
        self.assign_grp_name = None
        self.snow_session_obj = snow_session_obj
        self.snow_instance = snow_instance
        # self.snow_client_obj = snow_client_obj
        # self.auth = auth

        self.iface_dict = {
            "mpls-t1": "t1",
            "DIA": "4",
            "digi": "digi",
            "digi-lte": "digi-lte",
            "lte": "lte",
        }

        self.tunnel_iface_dict = {
            "pa-1": ["4"],
            "pa-2": ["digi, digi-lte, lte"],
        }

        self.post_data = post_data
        self.dev_data = dev_log
        # self.down_iface_list = down_iface_list
        # self.up_iface_list = up_iface_list
        self.iface_state_list = iface_state_list
        self.iface_list = list(iface_state_list.keys())

        if self.post_data["u_store_number"] != "":
            self.store_number = self.post_data["u_store_number"]
        elif self.post_data["u_store_number"] == "":
            self.store_number = self.post_data["short_description"].split(" || ")[0].split()[-1]

        self.wired_iface_list = [self.iface_list for i in self.iface_list if i in ["4", "t1"]]
        self.wireless_iface_list = [self.iface_list for i in self.iface_list if i in ["lte", "digi", "digi-lte"]]
        self.tunnel_list = [self.iface_list for i in self.iface_list if i in ["pa-1", "pa-2"]]

        self.assign_grp_name = ""
        self.updated_field_list = []
        self.updated_values = {}

        '''
        default values set for below fields
        '''
        self.updated_values["contact_type"] = "monitoring_tool"
        self.updated_values["u_service_type"] = "sdwan_customer"
        self.updated_values["category"] = "transport"
        self.updated_values["u_issue_start_date_time"] = datetime.now(timezone("US/Eastern")).strftime("%F %T")
        '''
        end of default values
        '''

        _ticket_number = self.post_data["number"]
        self.ticket_link = f"https://{self.snow_instance}.service-now.com/incident.do?sys_id={self.post_data['sys_id']}"

        _dev_data = str.join("\n", self.dev_data)
        self.work_notes = f"Hi Team,\n\nstore #{self.store_number}\n\nPlease find the logs attached below:\n\n{_dev_data}\n\n"


        self.avail_iface_list = ["4", "t1", "digi-lte", "lte", "pa-1", "pa-2"]
        self.node_iface_dict = {}

        def return_k_v_pair(key_list, value):
            return {**dict.fromkeys([str.join(", ", i) for i in permutations(key_list)], value)}

        '''
        dictionary of list of permutations & combinations of device ifaces mapped to it's field values
        '''
        self.issue_type_dict = defaultdict(list)
        self.subcategory_dict = defaultdict(list)
        # self.category_dict = defaultdict(list)

        self.subcategory_dict = {
                            "4": "broadband",
                            "digi-lte": "digi",
                            "lte": "lte",
                            "t1": "mpls t1",
                            # "3": "",
                            **dict.fromkeys(["pa-1", "pa-2"], "palo alto"),
                            **dict.fromkeys([str.join(", ", i) for i in permutations(["pa-1", "pa-2"])], "palo alto"),
                            **dict.fromkeys([str.join(", ", i) for i in permutations(["lte", "t1"])], "t1 & lte"),
                            **dict.fromkeys([str.join(", ", i) for i in permutations(["digi-lte", "t1"])], "t1 & lte"),
                            **dict.fromkeys([str.join(", ", i) for i in permutations(["4", "t1"])], "broadband & t1"),
                            **dict.fromkeys([str.join(", ", i) for i in permutations(["4", "digi-lte"])], "broadband & lte"),
                            **dict.fromkeys([str.join(", ", i) for i in permutations(["4", "lte"])], "broadband & lte"),
                            **dict.fromkeys([str.join(", ", i) for i in permutations(["4", "t1", "digi-lte"])], "broadband & lte & t1"),
                            **dict.fromkeys([str.join(", ", i) for i in permutations(["4", "t1", "lte"])], "broadband & lte & t1"),
                            # **dict.fromkeys([str.join(", ", i) for i in permutations(["3", "4", "t1", "lte"])], ""),
                            # **dict.fromkeys([str.join(", ", i) for i in permutations(["3", "4", "t1", "digi-lte"])], ""),
                            # **dict.fromkeys([str.join(", ", i) for i in permutations(["3", "4", "t1"])], ""),
                            # **dict.fromkeys([str.join(", ", i) for i in permutations(["3", "4", "digi-lte"])], ""),
                            # **dict.fromkeys([str.join(", ", i) for i in permutations(["3", "4", "lte"])], ""),
                            # **dict.fromkeys([str.join(", ", i) for i in permutations(["3", "t1"])], ""),
                            # **dict.fromkeys([str.join(", ", i) for i in permutations(["3", "lte"])], ""),
                            # **dict.fromkeys([str.join(", ", i) for i in permutations(["3", "digi-lte"])], ""),
                        }


        _temp_iface_list = ["4", "pa-1", "pa-2", "t1", "lte"]
        self.issue_type_dict = {**dict.fromkeys(_temp_iface_list, "Down")}

        ## digi - others - sdwan_customer
        self.issue_type_dict.update({"digi-lte": "Others"})


        '''
        dict of field values created from permutations and combinations of ifaces and it's respective "to-be-assgined"
        values 
        '''
        _temp_iface_list = []
        _ = [["4", "t1", "digi-lte"],
             ["pa-1", "t1", "lte"],
             ["pa-1", "t1", "digi-lte"],
             ["t1", "pa-1", "pa-2"],
             ["4", "t1", "lte"]]

        for i in _:
            _temp_iface_list.extend([str.join(", ", i) for i in combinations(i, 2)])
            self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Both Down")})

        ## TODO: replace "Others" with necessary values wherever necessary
        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["4", "t1", "lte"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["4", "t1", "digi-lte"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["pa-1", "t1", "lte"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["pa-1", "t1", "digi-lte"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["t1", "pa-1", "pa-2"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["4", "pa-2"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["3", "4", "digi-lte", "t1"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["3", "4", "lte", "t1"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["3", "4", "digi-lte"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["3", "4", "lte"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["3", "4", "t1"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})

        _temp_iface_list.extend([str.join(", ", i) for i in permutations(["3", "t1"])])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Others")})
        ## END of Replace "Others" with necessary values

        _ = self.iface_list  # store iface_list as a throw away iterable
        '''
        Delete only down ifaces/tunnels from list if said ifaces/tunnels are up as only "down" ifaces needs to be dealt 
        with 
        
        1) delete "iface" from list if tunnel is down & "iface" used by tunnel is up
        2) delete "tunnel" from list if "tunnel" & "iface" are down
        '''
        for i in _:
            for j in _:
                if i == j:
                    continue

                ### check if "i" is a tunnel and "j" is the iface used by the tunnel "i"
                if (i in self.tunnel_iface_dict) and (j in list(self.iface_dict.values())) and (j in self.tunnel_iface_dict[i]):

                    ### if tunnel "i" and iface "j" are operationally down then delete the tunnel "i" from iface_list
                    if (self.iface_state_list[i] == "operationally down") and (self.iface_state_list[j] == "operationally down"):
                        tunnel_index = self.iface_list.index(i)
                        del self.iface_list[tunnel_index]

                    ### if tunnel "i" is operationally up and iface "j" is operationally down then delete the iface "j" from iface_list
                    if (self.iface_state_list[i] == "operationally down") and (self.iface_state_list[j] == "operationally up"):
                        iface_index = self.iface_list.index(i)
                        del self.iface_list[iface_index]

        ## store iface_list as a throw away string var that will be used as a "dict key" to access values from "category" & "subcategory" dict.s
        _ = str.join(", ", self.iface_list)

        ## use above throw away "dict key" to set the values for the below fields
        self.updated_values["subcategory"] = self.subcategory_dict[_]
        self.updated_values["u_issue_type"] = self.issue_type_dict[_]


    '''
    setting ticket work notes
    '''
    def UpdateTicketWorkNotesField(self):
        _ = str.join(', ', self.iface_list)  # this var is used in the print statement below
        print(f"Updated ticket work notes with \"{_} peer path\" logs")
        self.updated_values["work_notes"] = self.work_notes
        self.updated_field_list += ["work_notes"]


    '''
    setting values to ticket when resolving ticket
    '''
    def ResolveTicketValues(self):
        _ = str.join(', ', self.iface_list)  # this var is used in the print statement below
        self.work_notes += f"Closing this ticket as interface \"{_} is operationally up\""

        self.post_data["state"] = "6"
        self.post_data["work_notes"] = self.work_notes
        self.post_data["close_notes"] = self.work_notes
        self.post_data["close_code"] = "Alert"

        self.updated_field_list += ["state"]
        self.updated_field_list += ["work_notes"]
        self.updated_field_list += ["close_notes"]
        self.updated_field_list += ["close_code"]
        print(f"{self.post_data['number'] - self.post_data['work_notes']}")


    '''
    setting values to ticket when e-bonding ticket
    '''
    def E_BondTicketValues(self):
        # test env L2_UHD values
        l2_uhd_assignment_ifaces = ["4", "t1", "lte", "digi-lte"]
        sdwan_ai_ops_assignment_ifaces = ["pa-1", "pa-2"]

        ## check if iface_list is in l2_uhd or sdwan_ai_ops assignment list & set the "assignment_group" field value accordingly
        if (any(x in l2_uhd_assignment_ifaces for x in self.iface_list)) or \
                (any(x in l2_uhd_assignment_ifaces for x in self.iface_list) and any(x in sdwan_ai_ops_assignment_ifaces for x in self.iface_list)):
            #### L2_UHD
            self.updated_values["assignment_group"] = "L2_UHD"
        if any(x in sdwan_ai_ops_assignment_ifaces for x in self.iface_list):
            ## sdwan ai ops
            self.updated_values["assignment_group"] = "SDWAN AI OPS"

        ## block that appends iface state to work_notes using throw away var
        _ = []
        self.work_notes += f"Assigning this ticket to {self.assign_grp_name} as "
        for i in self.iface_list:
            _ += [f"\"{i} is {self.iface_state_list[i]}\""]
        self.work_notes += str.join(", ", _)
        del _

        ## update the work_notes with the logs
        self.UpdateTicketWorkNotesField()

        ## adding work_notes to list of updated fields
        self.updated_field_list += ["assign_grp"]

    '''
    PATCH'ing SNOW ticket object
    '''
    def UpdateTicketRecord(self):
        ## update ticket fields using patch call
        _ticket_uri = f"https://{self.snow_instance}.service-now.com/api/now/table/incident/{self.post_data['sys_id']}"
        _updated_ticket_obj = self.snow_session_obj.patch(url=_ticket_uri, data=json.dumps(self.updated_values))
        # _updated_ticket_obj = requests.patch(url=ticket_uri, data=json.dumps(self.updated_values), auth=self.auth)
        # _updated_ticket_obj.close()

        if _updated_ticket_obj.status_code == 200:
            with open(".validated_tickets.txt", 'a') as validated_tickets_file:
                validated_tickets_file.write(f"{self.post_data['number']} - {self.ticket_link}\n")


    '''
    closing the connection to SNOW instance
    '''
    # def CloseSnowSession(self):
    #     self.snow_req_session.close()


    ## TODO
    def VendorIDWaiting(self):
        pass


    '''
    getters section
    '''

    '''
    returns fields of updated values
    '''
    @property
    def get_updated_field_values(self):
        _ = {}
        for i in self.updated_field_list:
            _[i] = self.post_data[i] if i != "assign_grp" else self.assign_grp_name
        return _


    '''
    returns assignment_group values after updating ticket object
    '''
    @property
    def get_assignment_group(self):
        return self.assign_grp_name, self.grp_link, self.grp_sys_id_value

    '''
    return ticket state
    '''
    @property
    def get_state(self):
        return self.post_data["state"]

    '''
    return upadted ticket values
    '''
    @property
    def get_updated_ticket_fields(self):
        return self.updated_values

    '''
    return close code (if any)
    '''
    @property
    def get_close_code(self):
        return self.updated_values["close_code"]
