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
    def __init__(self, post_data, dev_log, iface_state_list, snow_client_obj, auth):
        self.grp_link = None
        self.grp_sys_id_value = None
        self.assign_grp_name = None
        self.snow_client_obj = snow_client_obj

        self.snow_req_session = requests.Session()
        self.snow_req_session.auth = auth

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

        self.store_number = self.post_data["short_description"].split(" || ")[0].split()[-1]
        # self.store_number = self.post_data["u_store_number"]

        self.wired_iface_list = [self.iface_list for i in self.iface_list if i in ["4", "t1"]]
        self.wireless_iface_list = [self.iface_list for i in self.iface_list if i in ["lte", "digi", "digi-lte"]]
        self.tunnel_list = [self.iface_list for i in self.iface_list if i in ["pa-1", "pa-2"]]

        self.assign_grp_name = ""
        self.updated_field_list = []
        self.updated_values = {}

        self.updated_values["contact_type"] = "monitoring_tool"
        self.updated_values["u_service_type"] = "sdwan_customer"
        self.updated_values["category"] = "transport"
        self.updated_values["u_issue_start_date_time"] = datetime.now(timezone("US/Eastern")).strftime("%F %T")

        _ticket_number = self.post_data["number"]
        self.ticket_link = f"https://connxaidev.service-now.com/incident.do?sys_id={self.post_data['sys_id']}"

        self.issue_type_dict = defaultdict(list)
        self.category_dict = defaultdict(list)
        self.subcategory_dict = defaultdict(list)

        _dev_data = str.join("\n", self.dev_data)
        self.work_notes = f"Hi Team,\n\nstore #{self.store_number}\n\nPlease find the logs attached below:\n\n{_dev_data}\n\n"


        self.avail_iface_list = ["4", "t1", "digi-lte", "lte", "pa-1", "pa-2"]
        self.node_iface_dict = {}

        def return_k_v_pair(key_list, value):
            return {**dict.fromkeys([str.join(", ", i) for i in permutations(key_list)], value)}

        self.subcategory_dict = {
                            "4": "broadband",
                            "digi-lte": "digi",
                            "lte": "lte",
                            "t1": "mpls t1",
                            # "3": "",
                            **dict.fromkeys(["pa-1", "pa-2"], "palo_alto"),
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


        _temp_iface_list = []
        _temp_iface_list.extend([str.join(", ", i) for i in combinations(["4", "t1", "digi-lte"], 2)])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Both Down")})

        _temp_iface_list.extend([str.join(", ", i) for i in combinations(["pa-1", "t1", "lte"], 2)])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Both Down")})

        _temp_iface_list.extend([str.join(", ", i) for i in combinations(["pa-1", "t1", "digi-lte"], 2)])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Both Down")})

        _temp_iface_list.extend([str.join(", ", i) for i in combinations(["t1", "pa-1", "pa-2"], 2)])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Both Down")})

        _temp_iface_list.extend([str.join(", ", i) for i in combinations(["4", "t1", "lte"], 2)])
        self.issue_type_dict.update({**dict.fromkeys(_temp_iface_list, "Both Down")})

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

        #### block to show "tunnel down" if iface is up
        _ = self.iface_list
        for i in _:
            for j in _:
                if i == j:
                    continue
                if (i in self.tunnel_iface_dict) and (j in list(self.iface_dict.values())) and (j in self.tunnel_iface_dict[i]):
                    if (self.iface_state_list[i] == "operationally down") and (self.iface_state_list[j] == "operationally down"):
                        tunnel_index = self.iface_list.index(i)
                        del self.iface_list[tunnel_index]
                    if (self.iface_state_list[i] == "operationally down") and (self.iface_state_list[j] == "operationally up"):
                        iface_index = self.iface_list.index(i)
                        del self.iface_list[iface_index]
        _ = str.join(", ", self.iface_list)

        self.updated_values["subcategory"] = self.subcategory_dict[_]
        self.updated_values["u_issue_type"] = self.issue_type_dict[_]

    def UpdateTicketWorkNotesField(self):
        _ = str.join(', ', self.iface_list)
        print(f"Updated ticket work notes with \"{_} peer path\" logs")

        self.updated_values["work_notes"] = self.work_notes

        self.updated_field_list += ["work_notes"]


    def ResolveTicketValues(self):
        _ = str.join(', ', self.iface_list)
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


    def E_BondTicketValues(self):
        # test env L2_UHD values
        l2_uhd_assignment_ifaces = ["4", "t1", "lte", "digi-lte"]
        sdwan_ai_ops_assignment_ifaces = ["pa-1", "pa-2"]

        if (any(x in l2_uhd_assignment_ifaces for x in self.iface_list)) or \
                (any(x in l2_uhd_assignment_ifaces for x in self.iface_list) and any(x in sdwan_ai_ops_assignment_ifaces for x in self.iface_list)):
            #### L2_UHD
            # self.grp_link = "https://connxaidev.service-now.com/api/now/table/incident//sys_user_group/3eb16e621b5568905780baebcc4bcbe8"
            self.updated_values["assignment_group"] = "L2_UHD"
        if any(x in sdwan_ai_ops_assignment_ifaces for x in self.iface_list):
            ## sdwan ai ops
            self.updated_values["assignment_group"] = "SDWAN AI OPS"

        self.UpdateTicketWorkNotesField()

        self.updated_field_list += ["assign_grp"]

        _ = []
        self.work_notes += f"Assigning this ticket to {self.assign_grp_name} as "
        for i in self.iface_list:
            _ += [f"\"{i} is {self.iface_state_list[i]}\""]
        self.work_notes += str.join(", ", _)
        del _


    def UpdateTicketRecord(self):

        ticket_link1 = f"https://connxaidev.service-now.com/api/now/table/incident/{self.post_data['sys_id']}"
        _updated_ticket_obj = self.snow_req_session.patch(url=ticket_link1, data=json.dumps(self.updated_values))  ## 200

        if _updated_ticket_obj.status_code == 200:
            with open("validated_tickets.txt", 'a') as validated_tickets_file:
                validated_tickets_file.write(f"{self.post_data['number']} - {self.ticket_link}\n")

    def CloseSnowSession(self):
        self.snow_req_session.close()


    def VendorIDWaiting(self):
        pass


    @property
    def get_updated_field_values(self):
        _ = {}
        for i in self.updated_field_list:
            _[i] = self.post_data[i] if i != "assign_grp" else self.assign_grp_name
        return _


    @property
    def get_assignment_group(self):
        return self.assign_grp_name, self.grp_link, self.grp_sys_id_value

    @property
    def get_state(self):
        return self.post_data["state"]

    @property
    def get_updated_ticket_fields(self):
        return self.updated_values

    @property
    def get_close_code(self):
        return self.updated_values["close_code"]
