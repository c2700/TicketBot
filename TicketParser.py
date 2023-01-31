import re
from collections import defaultdict

class ManualInterVentionError(Exception):
    def __init__(self, msg="Requires Manual Intervention"):
        self.msg = msg
        super(ManualInterVentionError, self).__init__(self.msg)


class TicketParser:
    def __init__(self, post_data):
        '''
        pull necessary data from ticket object and generate necessary data structs
        :param post_data: ticket object
        '''
        self.store_number = ""

        self.ticket_link = "https://connxaidev.service-now.com/incident.do?sys_id=" + post_data["sys_id"]
        self.post_data = post_data
        self.short_desc_list = self.post_data["short_description"].split(" || ")  ## splits short description into a list
        
        ## store number
        if self.post_data["u_store_number"] != ""
            self.store_number = self.post_data["u_store_number"]
        elif self.post_data["u_store_number"] == ""
            self.store_number = self.post_data["short_description"].split(" || ")[0].split()[-1]

        self.pod_num = re.sub("\s+", "", self.short_desc_list[1].replace("POD - ", ""))

        '''
        extracting pod number
        '''
        try:
            if isinstance(eval(self.pod_num), list):
                for i in eval(self.pod_num):
                    if re.search("^[0-9]P", i) is not None or re.search("^P[0-9]", i) is not None:
                        self.pod_num = i.replace("P", "")
                        break
        except:
            pass


        self.iface_list = []  # ["iface0", "iface1"]
        self.iface_state_dict = {}  # {"iface0": "state0", "iface1": "state1"}
        self.node_iface_state_dict = defaultdict(dict)  # {"node": {"iface_0": "state"}, {"iface_1": "state"}, "node_0": {"iface": "state", "iface_0": "state1"}}
        self.node_iface_dict = defaultdict(list)  # {"node0": ["iface0"], "node1": ["iface1"]}

        self.offline_node_list = []
        self.iface_ignore_list = ["t128-ipsec-1", "t128-ipsec-2"]  ### list of interfaces to ignore
        self.router_name = ""


        '''
        extract list of specified nodes from short description
        '''
        self.node_list = self.short_desc_list[2]  # ["node0", "node1"]
        try:
            if isinstance(eval(self.node_list), list):
                self.node_list = eval(self.node_list)
                for i in range(len(self.node_list)):
                    self.node_list[i] = self.node_list[i].strip()
        except:
            if isinstance(self.node_list, str):
                self.node_list = [self.node_list.strip()]
        '''
        end of extracting node to list
        '''

        '''
        extracting router name
        '''
        self.router_name = re.sub("[AB]\s+$", "", self.node_list[0])
        self.router_name = re.sub("[AB]$", "", self.router_name)

        '''
        extracting interface list & it's descriptions to a dictionary
        '''
        self.iface_desc_list = self.short_desc_list[3]
        try:
            if isinstance(eval(self.iface_desc_list), list):
                self.iface_desc_list = eval(self.iface_desc_list)
        except:
            if isinstance(self.iface_desc_list, str) and [self.iface_desc_list].__len__() == 1:
                self.iface_desc_list = [self.iface_desc_list]
        #### end of extracting interface list & it's descriptions

        #### extracting ifaces to a list and extracting ifaces & it's states to a dictionory
        if not isinstance(self.iface_desc_list, list):
            pass
        elif isinstance(self.iface_desc_list, list):
            for i in self.iface_desc_list:
                _iface_state = str.join(" ", i.strip().split()[-2:])

                if _iface_state == "went offline":
                    self.offline_node_list += [i.split(" ")[1]]
                    _node_iface_state = "node offline"
                    self.iface_list += [_node_iface_state]
                else:
                    _iface_name = i.strip().split(" ")[1]
                    self.iface_list += [_iface_name]
                    self.iface_state_dict[_iface_name] = _iface_state
        '''
        end of extracting ifaces to a list and extracting ifaces & it's states to a dictionory
        '''

        '''
        raise error if ticket requires manual intervention
        '''
        _ignore_iface_list = ["3", "128t-ipsec-1", "128t-ipsec-2"]
        if any(x in _ignore_iface_list for x in self.iface_list):
            _ = str.join(", ", [x for x in self.iface_list if x in _ignore_iface_list])
            raise ManualInterVentionError()
        '''
        end of "raise error if ticket requires manual intervention"
        '''


        ''' 
            extracting respective 
                1) "node name", "iface name" & "iface state" to "node_iface_state_dict" dictionary
                2) "node name" & "iface name" to "node_iface_dict" dictionary
        '''
        if self.iface_list.__len__() == 1 and self.node_list.__len__() == 1:
            _node_name = self.node_list[0]
            _iface_name = self.iface_list[0]
            _iface_state = self.iface_state_dict[_iface_name]
            self.node_iface_dict[_node_name] += [_iface_name]
            self.node_iface_state_dict[_node_name].update({_iface_name: _iface_state})

        if self.iface_list.__len__() == 1 and self.node_list.__len__() > 1:
            for j in self.node_list:
                _iface_name = self.iface_list[0]
                _iface_state = self.iface_state_dict[_iface_name]
                _node_name = j
                self.node_iface_dict[_node_name] += [_iface_name]
                self.node_iface_state_dict[_node_name].update({_iface_name: _iface_state})

        if self.iface_list.__len__() > 1 and self.node_list.__len__() == 1:
            _node_name = self.node_list[0]
            for i in self.iface_list:
                _iface_name = i
                _iface_state = self.iface_state_dict[_iface_name]
                self.node_iface_dict[_node_name] += [_iface_name]
                self.node_iface_state_dict[_node_name].update({_iface_name: _iface_state})

        if self.iface_list.__len__() > 1 and self.node_list.__len__() > 1:
            _node_A_iface = ["DIA", "digi-lte", "lte", "pa-1", "4", "3"]
            _node_B_iface = ["mpls-t1", "pa-2"]
            for i in self.node_list:
                for j in self.iface_list:
                    _iface_name = j
                    _node_name = i

                    '''
                    while looping through "node_list" & "iface_list" check the following
                        1) if ("iface_name" is a NodeA iface and "node" is NodeA)
                        2) if ("iface_name" is a NodeB iface and "node" is NodeB)
                    to make a dictionary of node_name & it's respective iface_name & iface_state which will be used by
                    an "SSHConn" instance
                    '''
                    if ((_iface_name in _node_A_iface) and (re.search("P[1-6|9]A", _node_name))) or ((_iface_name in _node_B_iface) and (re.search("P[1-6|9]B", _node_name))):
                        _iface_state = self.iface_state_dict[_iface_name]
                        self.node_iface_dict[_node_name] += [_iface_name]
                        self.node_iface_state_dict[_node_name].update({_iface_name: _iface_state})
        '''
        .--------.
        | END OF |
        '--------'
            extracting respective "node name", "iface name" & "iface state" to "node_iface_state_dict" dictionary
            extracting respective "node name" & "iface name" to "node_iface_dict" dictionary
        '''



    '''
    getters section
    '''

    '''
    returns { router_name: {node_name: { iface_name: iface_state}}}
    '''
    @property
    def get_router_node_iface_state_list(self):
        return {self.router_name: self.node_iface_state_dict}

    '''
    returns {"node0": {"iface0": "state", "iface1": "state"}, "node1": {"iface1": "state1"}}
    '''
    @property
    def get_node_iface_state_list(self):
        return self.node_iface_state_dict

    '''
    returns {"node0": "iface0", "node1": "iface1"}
    '''
    @property
    def get_node_iface_list(self):
        return self.node_iface_dict

    '''
    returns {"iface0": "state0", "iface1": "state1"}
    '''
    @property
    def get_iface_list_state(self):
        return self.iface_state_dict

    '''
    returns ["node_name_0", "node_name_1"]
    '''
    @property
    def get_nodes(self):
        return self.node_list

    '''
    returns ["iface_name_0", "iface_name_1"]
    '''
    @property
    def get_ifaces(self):
        if set(self.iface_list).intersection(set(self.iface_ignore_list)):
            return self.iface_list
        return self.iface_list


    '''
    returns pod_num
    '''
    @property
    def get_pod_num(self):
        return self.pod_num

    '''
    return offline nodes
    '''
    @property
    def get_offline_nodes(self):
        return self.offline_node_list

    '''
    returns {"iface_name_0": "iface_state", "iface_name_1": "iface_state"}
    '''
    @property
    def get_iface_desc_list(self):
        return self.iface_desc_list

    '''
    returns "router_name"
    '''
    @property
    def get_router_name(self):
        return self.router_name

    '''
    returns "store number"
    '''
    @property
    def get_store_number(self):
        return self.store_number

    '''
    returns short_description "pod_num - [node_name] || {'iface_name': 'iface_state'}" format
    '''
    @property
    def get_short_desc(self):
        self.short_desc = f"POD {self.pod_num} - [{str.join('|', self.node_list)}] || {str(self.iface_state_dict)}"
        return self.short_desc
