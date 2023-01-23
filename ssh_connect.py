import re
from paramiko import *
from requests import ConnectTimeout
import json

class SSHConn:
    def __init__(self, pod_num, router_name, node_iface_state_dict):
        '''
        SSH into respective pods, execute necesary commands in that pod & pull necessary data
        :param pod_num: Pod number to SSH into
        :param router_name: router name
        :param node_iface_state_dict: dict of node, "iface in ticket" & "iface state in ticket".
                                                eg -> {'node': {'ticket iface name': 'ticket iface_state'}}
        '''

        self.subcmd = ""
        self.pod_num = pod_num
        if isinstance(pod_num, int):
            self.pod_num = str(self.pod_num)
        self.router_name = router_name

        self.node_list = []
        self.iface_list = []
        self.node_iface_dict = {}

        for i in node_iface_state_dict:
            self.node_iface_dict[i] = node_iface_state_dict[i]

        '''
        interfaces mapped to it's alias
        '''
        self.dev_iface_name_dict = {
            "4": "DIA",
            "lte": "lte",
            "digi-lte": "digi-lte",
            "t1": "mpls-t1",
            "pa-1": "pa-1-intf",
            "pa-2": "pa-2-intf"
        }

        '''
        peer path interfaces mapped to it's alias/peer interface
        '''
        self.peer_iface_dict = {
            "4": "DIA",
            "lte": "lte",
            "digi-lte": "digi-lte",
            "t1": "mpls-t1",
        }

        '''
        mapping of interfaces used by tunnels
        '''
        self.tunnel_iface_name_dict = {
            "pa-1": ["DIA", "4"],
            "pa-2": ["lte", "digi-lte"]
        }

        '''
        list used as reference to check which interface belongs to which node
        '''
        self.NodeA_iface_check_list = ["DIA", "4", "digi-lte", "lte"]
        self.NodeA_tunnel_check_list = ["pa-1"]
        self.NodeB_iface_check_list = ["t1", "mpls-t1"]
        self.NodeB_tunnel_check_list = ["pa-2"]

        self.device_log = []
        self.parsed_device_log = []
        self.command = ""

        ### looping through list of node_names
        for i in list(node_iface_state_dict.keys()):

            ### looping through list of ifaces
            for j in [list(node_iface_state_dict[i].keys()) for i in node_iface_state_dict][0]:
                if (i in self.node_list) and (j in self.iface_list):
                    continue
                if ((re.search("P[1-6|9]A$", i) and ((j in self.NodeA_iface_check_list) or
                                                     (j in self.NodeA_tunnel_check_list)))
                    or
                    (re.search("P[1-6|9]B$", i) and ((j in self.NodeB_iface_check_list) or
                                                     (j in self.NodeB_tunnel_check_list)))):
                    self.node_list += [i]
                    self.iface_list += [j]


        self.pod_ip_dict = {}
        with open(".ssh_info", 'r') as f_obj:
            self.pod_ip_dict = json.load(fp=f_obj)

        self.passwd = self.pod_ip_dict["placeholder"]
        if self.pod_num == "9":
            self.passwd = self.pod_ip_dict["it_is_free"]


        self.sshclient = SSHClient()
        self.sshclient.set_missing_host_key_policy(AutoAddPolicy)

        self.stdin = None
        self.stdout = None
        self.stderr = None


    '''
    send cmd to specified host
    '''
    def send_command(self, command):
        _host = self.pod_ip_dict[self.pod_num]
        self.sshclient.connect(hostname=_host, username="admin", password=self.passwd)
        try:
            self.stdin, self.stdout, self.stderr = self.sshclient.exec_command(command=command)
        except ConnectTimeout:
            print(f"connection to host {_host} in {self.pod_num} timed out")
            raise ConnectTimeout
        self.stdin.flush()  ## apparently the stdin requires that it be flushed before doing anything remotely or locally
        self.stderr.readlines()
        return self.stdout.readlines()[7:-2]


    '''
    this method is so that it's easier to close all ssh session's I/O stream that belongs to instance of this class
    '''
    def close_conn(self):
        self.stdin.close()
        self.stdout.close()
        self.stderr.close()
        self.sshclient.close()

    '''
    to get peer path. check tunnel & then check h/w iface peer path
    '''
    def peer_state(self, **kwargs):
        router_name = kwargs["router_name"] if "router_name" in kwargs else self.router_name
        # iface_name = kwargs["iface_name"] if "iface_name" in kwargs else self.iface_name
        self.command = "show peers router " + router_name + " summary"
        self.device_log = self.send_command(self.command)
        self.close_conn()

        '''
        loop through iface_list extracted from ticket object
        '''
        for a in self.iface_list:

            _ticket_iface_name = a  ## store iterated ticket object as reference variable (ref_ticket_var)

            '''
            loop through extracted node list
            '''
            for _node in self.node_list:

                '''
                loop through the huge device_log extracted from send_command method
                '''
                for b in self.device_log:
                    data_str = b.strip()

                    '''
                    ignore peer ifaces that are in standby state or peers that connected to ASHBURN Data Center
                    '''
                    if (re.search("[A-Z]+ASH[A-Z]+POD[1-6|9]", data_str.split()[2])) or (data_str.split()[6] == "standby"):
                        continue

                    _peer_iface_name = data_str.split()[4]  ## extract peer iface name device log
                    _node_name = data_str.split()[3]  ## extract node name from device log

                    ### ignore if the iface log is already extracted
                    if data_str in self.parsed_device_log:
                        continue

                    '''
                        1) check if ticket iface (_ticket_iface_name) is a direct iface (self.peer_iface_dict.keys()). eg: "broadband"
                           and if peer_path iface in the extracted device log is also a direct iface name. eg: DIA 
                    '''
                    if (_ticket_iface_name in self.peer_iface_dict.keys()) and (_peer_iface_name == self.dev_iface_name_dict[_ticket_iface_name]):
                        '''
                        add device log if specified direct iface in the device log is a NodeA iface
                        '''
                        if (_ticket_iface_name in self.NodeA_iface_check_list) and (_peer_iface_name in self.NodeA_iface_check_list):
                            if re.search("P[1-6|9]A$", _node_name):
                                self.parsed_device_log += [data_str]

                        '''
                        add device log if specified direct iface is a NodeB iface
                        '''
                        if (_ticket_iface_name in self.NodeB_iface_check_list) and (_peer_iface_name in self.NodeB_iface_check_list):
                            if re.search("P[1-6|9]B$", _node_name):
                                self.parsed_device_log += [data_str]
                        ## (The above two conditons PROBABLY could've been written better)

                    ### check if ticket iface is a tunnel
                    elif _ticket_iface_name in self.tunnel_iface_name_dict:

                        '''
                        check if peer iface in the iterated device log is used by the tunnel
                        '''
                        if _peer_iface_name in self.tunnel_iface_name_dict[_ticket_iface_name]:

                            '''
                            check if node in device log is NodeA
                            '''
                            if re.search("P[1-6|9]A$", _node_name):

                                '''
                                ignore if ticket iface is not a Node_A tunnel and peer iface used by tunnel is not a Node_A iface
                                '''
                                if (_ticket_iface_name not in self.NodeA_tunnel_check_list) and (_peer_iface_name not in self.NodeA_iface_check_list):
                                    continue

                                '''
                               ignore if ticket iface is not a Node_B tunnel and peer iface used by tunnel is not a Node_A iface
                               '''
                                if (_ticket_iface_name not in self.NodeB_tunnel_check_list) and (_peer_iface_name not in self.NodeA_iface_check_list):
                                    continue

                                '''
                               Add device log if node in device log is NodeA 
                                '''
                                self.parsed_device_log += [data_str]

                '''
                check if ticket iface is a tunnel iface
                '''
                if _ticket_iface_name in self.tunnel_iface_name_dict:

                    '''
                    use "device-interface" command to get state of tunnel iface
                    '''
                    _tunnel_iface_state = self.device_iface_state(_node, _ticket_iface_name)
                    _tunnel_state_str = f"{_ticket_iface_name} -"

                    '''
                    to check if something went wrong when executing the command
                    '''
                    if _tunnel_iface_state == "None":
                        print({"dis ain't ryt"})
                    else:
                        ### adding "tunnel iface" log
                        for i in _tunnel_iface_state:
                            _tunnel_state_str += f" {i} {_tunnel_iface_state[i]}"
                        if _tunnel_state_str not in self.parsed_device_log:
                            self.parsed_device_log += [_tunnel_state_str]


    '''
    "show device-interface" command method. discards "standby" state ifaces and returns a simplified dictionary
    of the iface state as a dictionary
    '''
    def device_iface_state(self, node_name, iface_name):
        self.command = f"show device-interface router {self.router_name} node {node_name} name {iface_name} summary"
        iface_stat = self.send_command(self.command)
        if iface_stat.__len__() > 1:
            for i in iface_stat:
                if i.split()[5] == "standby":
                    del iface_stat[iface_stat.index(i)]
                    break
        self.close_conn()
        if iface_stat == []:
            return "None"
        iface_stat = iface_stat[0].strip().split()
        _tunnel_iface_state = {
                "admin": iface_stat[2],
                "oper": iface_stat[3],
                "prov": iface_stat[4]
        }
        return _tunnel_iface_state

    '''
    returns which command was used on the pod
    '''
    @property
    def show_cmd_subcmd_used(self):
        if re.search("show device-interface", self.command) is not None:
            self.subcmd = "device-interface"
        elif re.search("router-interface", self.command) is not None:
            self.subcmd = "router-interface"
        elif re.search("show peers", self.command) is not None:
            self.subcmd = "peers"
        return self.subcmd

    '''
    returns the extracted device log. type: lis
    '''
    @property
    def get_parsed_device_log(self):
        return self.parsed_device_log




