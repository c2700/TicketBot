class TicketState:
    def __init__(self, node_list, ticket_log_dict, dev_log, cmd_string):

        self.node_list = list(node_list)
        self.ticket_log_dict = ticket_log_dict
        self.cmd_string = cmd_string
        self.dev_log = dev_log

        self.iface_name = ""
        self.node_peer_stat = ""
        self.ticket_peer_stat = ""

        self.e_bond_logs = []
        self.close_logs = []

        self.ticket_iface_state_dict = {}
        self.device_iface_state_dict = {}

        self.palo_alto_oper_stat = ""

        self.iface_name_dict = {
            "4": "DIA",
            "lte": "lte",
            "digi-lte": "digi-lte",
            "t1": "mpls-t1",
            "pa-1": "pa-1-intf",
            "pa-2": "pa-2-intf"
        }

        # self.peer_iface_dict = {
        #     "4": "DIA",
        #     "lte": "lte",
        #     "digi-lte": "digi-lte",
        #     "t1": "mpls-t1",
        # }
        #
        # self.tunnel_iface_dict = {
        #     "pa-1": "DIA",
        #     "pa-2": ["lte", "digi", "digi-lte"]
        # }

        self.ticket_action = 0
        self.ticket_action_dict = {0: "close", 1: "e-bond", 2: "update ticket content"}

        self.iface_list = []
        for i in self.node_list:
            self.iface_list += list(self.ticket_log_dict[i].keys())


        for i in self.dev_log:
            node_name = i.split()[3]
            dev_iface = i.split()[4]
            peer_state = i.split()[6]
            self.device_iface_state_dict.update({node_name: {dev_iface: peer_state}})

            if peer_state == "up":
                self.close_logs += [i]
            elif (peer_state == "down") or (peer_state == "unavailable") or (peer_state == "init"):
                self.e_bond_logs += [i]

        if self.e_bond_logs.__len__() >= (self.dev_log.__len__() - 1):
            self.ticket_action = 1
        else:
            self.ticket_action = 2


    @property
    def get_ebond_logs(self):
        return self.e_bond_logs

    @property
    def get_close_logs(self):
        return self.close_logs

    @property
    def get_ticket_action_string(self):
        return self.ticket_action_dict

    @property
    def get_ticket_action(self):
        return self.ticket_action



