from pysnow import Client, QueryBuilder
from LogParser import *
from TicketParser import *
from ssh_connect import *
from TicketState import *
from ValidateTicket import *
from os import path
import re

def Login():
    if not path.exists(".hash"):
        print("no stored snow creds found. please input snow creds")
        instance = input("instance: ")
        user = input("user: ")
        password = input("password: ")
        cred_grp = input("enter cred group: ")

        hash_dict = {
            cred_grp: [
                {
                    "instance": instance,
                    "user": user,
                    "password": password
                }
            ]
        }

        with open(".hash", 'a') as f_obj:
            json_dict = json.loads(json.dumps(hash_dict))
            json.dump(obj=json_dict, fp=f_obj, indent=4)

    elif path.exists(".hash"):
        with open(".hash", "r") as f_obj:
            json_obj = json.load(fp=f_obj)
            json_obj = json_obj["cred1"][0]
            instance = json_obj["instance"]
            user = json_obj["user"]
            password = json_obj["password"]

    return instance, user, password




def ticket_validate_func(ticket_obj, snow_client_obj, auth):

    '''
    "TicketParser" object parsing a "ticket_obj" object
    :param ticket_obj: ticket object
    :param snow_client_obj:
    :param auth: snow auth
    '''
    parsed_ticket = TicketParser(ticket_obj)

    print(f"\nvalidating ticket {ticket_obj['number']}")
    print(parsed_ticket.get_short_desc)

    iface_state_list = parsed_ticket.get_iface_list_state
    ifaces = parsed_ticket.get_ifaces

    router_node_iface_state_list = parsed_ticket.get_router_node_iface_state_list
    node_iface_list = parsed_ticket.get_node_iface_list
    router_name = parsed_ticket.get_router_name
    node_iface_state_list = parsed_ticket.get_node_iface_state_list
    pod_num = parsed_ticket.get_pod_num
    store_number = parsed_ticket.get_store_number
    print(f"store - {store_number}")

    notify_string = f"logging into POD {pod_num} & checking {str.join(', ', ifaces)} of router {router_name} of store {store_number}"
    print(notify_string)
    del notify_string
    
    '''
    create an ssh connection object with the respective pod number
    '''
    dev_log_obj = SSHConn(pod_num=pod_num, router_name=router_name, node_iface_state_dict=node_iface_state_list)
    
    '''
    get peer path logs of iface specified in ticket (logs will be stored in "parsed_device_log" member var of "dev_log_obj")
    '''
    dev_log_obj.peer_state()
    
    '''
    get the peer path device log
    '''
    parsed_device_log = dev_log_obj.get_parsed_device_log
    
    '''
    return the "show command" used
    '''
    cmd_subcmd_used = dev_log_obj.show_cmd_subcmd_used
    


    '''
    "LogParser" object uses "parsed_device_log" member var from "dev_log_obj" to generate respective data structs being
    1) dict -> {'node': {'peer_iface_name': 'peer_iface_state'}}
    2) list & count of unavailable, up, down & init peer_names in it's own list
    3) count of all specified peers
    
    the "command_used" arg is passed to specifiy the method to check the interface states.
    ("show device-interface" value will execute "show device-interface" and "show peer path" commands.
    "show peers" value will execute only "show peers" command)
    '''
    LogParserObj = LogParser(parsed_device_log, cmd_subcmd_used)
    peers_count = LogParserObj.get_peers_count

    '''
    function needs to be called (It's here just in case anyone wants to call it). 
    It's to show peer logs & peers in specified in the logs
    call: show_peers_state_count("down peers", len(LogParserObj.get_down_iface_list))
    '''
    def show_peers_state_count(text, peer_count):
        if peer_count > 0:
            print(text, "-", peer_count)

    down_iface_list = LogParserObj.get_down_iface_list
    pseudo_down_iface_list = LogParserObj.get_pseudo_down_iface_list
    up_iface_list = LogParserObj.get_down_iface_list
    unvaialable_iface_list = LogParserObj.get_unavailable_iface_list
    init_iface_list = LogParserObj.get_init_iface_list

    unavailable_peers_count = LogParserObj.get_unavailable_peers_count
    up_peers_count = LogParserObj.get_up_peers_count
    down_peers_count = LogParserObj.get_down_peers_count
    init_peers_count = LogParserObj.get_init_peers_count

    '''
    To Set Ticket Field values & it's state
    '''
    TicketStateObj = TicketState(node_list=node_iface_list.keys(),
                                 ticket_log_dict=parsed_ticket.node_iface_state_dict,
                                 dev_log=dev_log_obj.get_parsed_device_log,
                                 cmd_string=dev_log_obj.show_cmd_subcmd_used)
    ticket_action = TicketStateObj.get_ticket_action
    ticket_action_string = TicketStateObj.get_ticket_action_string[TicketStateObj.get_ticket_action]
    print(f"ticket_action => {ticket_action} - {ticket_action_string}\n")
    ValidateTicketObj = ValidateTicket(post_data=ticket_obj, dev_log=dev_log_obj.get_parsed_device_log, iface_state_list=iface_state_list, snow_client_obj=snow_client_obj, auth=auth)

    '''
    set/change ticket object keys to it's respective values
    '''
    if ticket_action == 2:
        ValidateTicketObj.UpdateTicketWorkNotesField()
    if ticket_action == 1:
        ValidateTicketObj.E_BondTicketValues()

    '''
    PATCH ticket object location using updated ticket object fields
    '''
    ValidateTicketObj.UpdateTicketRecord()

def BotFunc():

    print("links & ID's of Non Proactive tickets & tickets that cannot be validated and require manual intervention will be saved to 'no_proactive.txt' and 'manual_tickets.txt' respectively\n")

    if not path.exists(".ssh_info"):
        print("\".ssh_info\" file not found. cannot validate tickets without it as it contains pod numbers mapped to it's respective IP's")
        exit(1)
    instance, user, password = Login()

    ### interfaces to assign to groups - reference
    # L2_UHD = 4, t1, digi-lte, lte
    # sdwan ai ops - pa-1, pa-2

    '''
    Client_object that creates a session with snow instance
    '''
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    #
    snow_client = Client(instance=instance, user=user, password=password)

    snow_client.request_params["headers"] = headers
    incident_table = snow_client.resource(api_path="/table/incident")   ## API calls should be made to objects in the incidents table


    ### swapcase of first characters of the user name preceding & following the "." to be used as arg in the QueryBuilder object for filtering
    user_fname_first_char = re.search("\w+\.", user).group()[0].swapcase()
    user_lname_first_char = re.search("\.\w+", user).group()[1].swapcase()
    filter_user = re.sub("^" + user_fname_first_char.swapcase(), user_fname_first_char, user)
    filter_user = re.sub("\." + user_lname_first_char.swapcase(), "." + user_lname_first_char, filter_user)

    # query = QueryBuilder().field("sys_created_by").contains("moogint").AND().\
    query = QueryBuilder().field("sys_created_by").contains(filter_user).AND().\
            field("short_description").contains("operationally down").AND().\
            field("incident_state").equals([2])

    print("pulling all unvalidated 'work in progress' tickets from snow assigned to Rohan Philip")
    '''
    pulling all ticket objects from user's queue after passing the filters
    '''
    ticket_obj_list = incident_table.get(query=query, stream=True).all()
    snow_client.close()
    print("\npulled all tickets from queue\n")

    for i in ticket_obj_list:
        ticket_link = f"https://connxaidev.service-now.com/incident.do?sys_id={i['sys_id']}"
        ticket_api_link = f"https://connxaidev.service-now.com/api/now/table/incident/{i['sys_id']}"
        try:
            '''
            snow ticket object referenced by ticket incident numer
            '''
            snow_client_obj = snow_client.query(table='incident', query={'number': i["number"]})

            '''
            ticket object validation function
            '''
            ticket_validate_func(ticket_obj=i, snow_client_obj=snow_client_obj, auth=(user, password))
        except ManualInterVentionError:
            print("ticket requires manual intervention")
            with open("manual_tickets.txt", "a") as manual_ticket:
                manual_ticket.write(f"{i['number']} - {ticket_link}\n")







