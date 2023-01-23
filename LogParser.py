import re

class LogParser:
    def __init__(self, dev_log_data, cmd_string):
        '''
        logs will be used to extract node_name, iface, iface_state and generate the necessarry data & data structs
        :param dev_log_data: logs pulled from ssh connections
        :param cmd_string: command used to pull the data
        '''

        self.dev_log_data = dev_log_data
        self.cmd_string = cmd_string

        self.iface_name = ""
        self.node_name = ""
        self.peer_stat = ""

        self.down_peers_dict = {}
        self.unavailable_peers_dict = {}
        self.up_peers_dict = {}
        self.init_peers_dict = {}

        self.down_peers_count = 0
        self.unavailable_peers_count = 0
        self.up_peers_count = 0
        self.init_peers_count = 0
        self.peers_count = 0
        self.tunnel_count = 0
        self.tunnel_state_dict = {}  # {"tun": {"oper": "", "admin": "", "prov": ""}}

        self.up_iface_list = []
        self.down_iface_list = []
        self.pseudo_down_iface_list = []
        self.init_iface_list = []
        self.unavailable_iface_list = []

        self.up_iface_dict = {}
        self.down_iface_dict = {}
        self.pseudo_down_iface_dict = {}
        self.init_iface_dict = {}
        self.unavailable_iface_dict = {}

        self.node_iface_peer_stat = {}

        self.avail_iface_list = ["4", "digi-lte", "lte", "t1", "3"]
        self.avail_tunnel_list = ["pa-1", "pa-2"]
        self.dev_iface_name_dict = {
            "4": "DIA",
            "lte": "lte",
            "digi-lte": "digi-lte",
            "t1": "mpls-t1",
            "pa-1": "pa-1-intf",
            "pa-2": "pa-2-intf",
            "3": "HA"
        }
        self.peer_iface_dict = {
            "4": "DIA",
            "lte": "lte",
            "digi-lte": "digi-lte",
            "t1": "mpls-t1",
        }

        self.tunnel_iface_name_dict = {
            "pa-1": ["DIA", "4"],
            "pa-2": ["lte", "digi-lte"]
        }
        self.iface_name_dict = {
            "DIA": "4",
            "mpls-t1": "t1",
            "digi-lte": "digi-lte",
            "lte": "lte",
        }


        '''
        function that generates data struct from peer path log containing node_name & it's respective peer_iface_name, 
        peer_iface_name state and a list and count of unavailable, up, down, unavailable & init state peers
        '''
        def get_peer():
            for i in self.dev_log_data:
                if re.search(".*- admin up oper up prov up", i):
                    continue

                temp_data_list = i.strip().split()
                self.node_name = temp_data_list[3]
                self.iface_name = temp_data_list[4]
                self.peer_stat = temp_data_list[6]
                self.node_iface_peer_stat[self.node_name] = {self.iface_name: self.peer_stat}  # {'node': {'iface': 'state'}, 'node_0': {'iface_0': 'state_0'}}
                self.peers_count += 1

                if self.peer_stat == "unavailable":
                    self.unavailable_peers_dict.update({self.node_name: self.node_iface_peer_stat[self.node_name]})
                    self.unavailable_peers_count += 1
                    self.unavailable_iface_list += [self.iface_name_dict[self.iface_name]]
                    self.unavailable_iface_dict[self.iface_name_dict[self.iface_name]] = "unavailable"

                if self.peer_stat == "down":
                    self.down_peers_dict.update({self.node_name: self.node_iface_peer_stat[self.node_name]})
                    self.down_peers_count += 1
                    self.down_iface_list += [self.iface_name_dict[self.iface_name]]
                    self.down_iface_dict[self.iface_name_dict[self.iface_name]] = "down"

                if self.peer_stat == "up":
                    self.up_peers_dict.update({self.node_name: self.node_iface_peer_stat[self.node_name]})
                    self.up_peers_count += 1
                    self.up_iface_list += [self.iface_name_dict[self.iface_name]]
                    self.up_iface_dict[self.iface_name_dict[self.iface_name]] = "up"

                if self.peer_stat == "init":
                    self.init_peers_dict.update({self.node_name: self.node_iface_peer_stat[self.node_name]})
                    self.init_peers_count += 1
                    self.init_iface_list += [self.iface_name_dict[self.iface_name]]
                    self.init_iface_dict[self.iface_name_dict[self.iface_name]] = "init"

            self.pseudo_down_iface_list += (self.init_iface_list + self.unavailable_iface_list + self.down_iface_list)
            # self.down_peers_count += self.unavailable_peers_count + self.init_peers_count

            self.init_iface_list = list(set(self.init_iface_list))
            self.up_iface_list = list(set(self.up_iface_list))
            self.down_iface_list = list(set(self.down_iface_list))
            self.unavailable_iface_list = list(set(self.unavailable_iface_list))
            self.pseudo_down_iface_list = list(set(self.pseudo_down_iface_list))

            # _ = self.down_iface_list
            _ = self.pseudo_down_iface_list
            for i in _:
                if i in self.avail_tunnel_list:
                    if any(x in self.avail_iface_list for x in self.tunnel_iface_name_dict[i]):
                        ## block to delete iface from list
                        del_elem_index = self.pseudo_down_iface_list.index(i)
                        del self.pseudo_down_iface_list[del_elem_index]
            del _
        '''
        end of data struct generation func
        '''

        '''
        if command is "show peers" then call "get_peer()"
        if command is "device-interface" then call "get_peer()" 1st and then shorten the "show device-interface" logs
        '''
        if self.cmd_string == "peers":
            get_peer()
        elif self.cmd_string == "device-interface":
            get_peer()
            for i in self.dev_log_data:
                if re.search("admin (up|down)", i):
                    _ = re.sub(".*- admin", "admin", i).split()
                    for j in range(len(_)):
                        state_type = _[j]
                        state = _[j-1]
                        self.tunnel_state_dict[_[0]] = {state_type: state}
                    del _
        '''
        end of data struct generation
        '''

    @property
    def get_show_peers_data(self):
        return self.node_iface_peer_stat

    @property
    def get_down_peers_data(self):
        return self.down_peers_dict

    @property
    def get_up_peers_data(self):
        return self.up_peers_dict

    @property
    def get_up_iface_list(self):
        return self.up_iface_dict

    @property
    def get_down_iface_list(self):
        return list(self.down_iface_dict.keys())

    @property
    def get_pseudo_down_iface_list(self):
        return list(self.pseudo_down_iface_dict.keys())

    @property
    def get_unavailable_iface_list(self):
        return list(self.unavailable_iface_dict.keys())

    @property
    def get_init_iface_list(self):
        return list(self.init_iface_dict.keys())

    @property
    def get_unavailable_peers_data(self):
        return self.unavailable_peers_dict

    @property
    def get_init_peers_data(self):
        return self.init_peers_dict

    @property
    def get_up_peers_count(self):
        return self.up_peers_count

    @property
    def get_peers_count(self):
        return self.peers_count

    @property
    def get_down_peers_count(self):
        return self.down_peers_count

    @property
    def get_unavailable_peers_count(self):
        return self.unavailable_peers_count

    @property
    def get_init_peers_count(self):
        return self.init_peers_count

