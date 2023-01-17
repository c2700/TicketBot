import json

from pysnow import Client, QueryBuilder
from LogParser import *
from TicketParser import *
from ssh_connect import *
from TicketState import *
from ValidateTicket import *
from os import path
from json import loads, dumps

def Login():
    if not path.exists(".hash"):
        print("input snow creds")

        instance = input("instance: ")
        user = input("user: ")
        hashword = input("hashword: ")
        
        hash_dict = {
            "instance": instance,
            "user": user,
            "hashword": hashword
        }

        with open(".hash", 'a') as f_obj:
            json_dict = json.loads(json.dumps(hash_dict))
            json.dump(obj=json_dict, fp=f_obj, indent=4)

    elif path.exists(".hash"):
        with open(".hash", "r") as f_obj:
            json_obj = json.load(fp=f_obj)
            instance = json_obj["instance"]
            user = json_obj["user"]
            hashword = json_obj["hashword"]

    return instance, user, hashword




def ticket_validate_func(ticket_obj, snow_client_obj, auth):
    # ticket_link = f"https://connxai.service-now.com/incident.do?sys_id={ticket_obj['sys_id']}"
    ticket_link = f"https://connxaidev.service-now.com/incident.do?sys_id={ticket_obj['sys_id']}"

    ticket_api_link = f"https://connxaidev.service-now.com/api/now/table/incident/{ticket_obj['sys_id']}"
    # ticket_api_link = f"https://connxai.service-now.com/api/now/table/incident/{ticket_obj['sys_id']}"

    parsed_ticket = TicketParser(ticket_obj)

    print(f"\nvalidating ticket {ticket_obj['number']}")
    print(parsed_ticket.get_short_desc)

    iface_state_list = parsed_ticket.get_iface_list_state
    ifaces = parsed_ticket.get_ifaces

    #### parsed_ticket.get_router_node_iface_state_list['AAPNC4125P1']['AAPNC4125P1B'][0]["pa-2"]
    router_node_iface_state_list = parsed_ticket.get_router_node_iface_state_list
    node_iface_list = parsed_ticket.get_node_iface_list  # node_iface_list["AAPNC4125P1B"]
    router_name = parsed_ticket.get_router_name
    node_iface_state_list = parsed_ticket.get_node_iface_state_list
    pod_num = parsed_ticket.get_pod_num
    store_number = parsed_ticket.get_store_number
    print(f"store - {store_number}")

    notify_string = f"logging into POD {pod_num} & checking {str.join(', ', ifaces)} of router {router_name} of store {store_number}"
    print(notify_string)
    del notify_string
    dev_log_obj = SSHConn(pod_num=pod_num, router_name=router_name, node_iface_state_dict=node_iface_state_list)
    dev_log_obj.peer_state()
    parsed_device_log = dev_log_obj.get_parsed_device_log

    cmd_subcmd_used = dev_log_obj.show_cmd_subcmd_used

    LogParserObj = LogParser(parsed_device_log, cmd_subcmd_used)
    peers_count = LogParserObj.get_peers_count

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

    TicketStateObj = TicketState(node_list=node_iface_list.keys(),
                                 ticket_log_dict=parsed_ticket.node_iface_state_dict,
                                 dev_log=dev_log_obj.get_parsed_device_log,
                                 cmd_string=dev_log_obj.show_cmd_subcmd_used)
    ticket_action = TicketStateObj.get_ticket_action
    ticket_action_string = TicketStateObj.get_ticket_action_string[TicketStateObj.get_ticket_action]
    print(f"ticket_action => {ticket_action} - {ticket_action_string}\n")
    ValidateTicketObj = ValidateTicket(post_data=ticket_obj, dev_log=dev_log_obj.get_parsed_device_log, iface_state_list=iface_state_list, snow_client_obj=snow_client_obj, auth=auth)

    if ticket_action == 2:
        ValidateTicketObj.UpdateTicketWorkNotesField()
    if ticket_action == 1:
        ValidateTicketObj.E_BondTicketValues()
    updated_fields = ValidateTicketObj.get_updated_ticket_fields

    ValidateTicketObj.UpdateTicketRecord()
    ValidateTicketObj.CloseSnowSession()

def BotFunc():

    print("links & ID's of Non Proactive tickets & tickets that cannot be validated will be saved to 'no_proactive.txt', 'unvalidated.txt' respectively\n")

    instance, user, hashword = Login()
    print()

    # L2_UHD = 4, t1, digi-lte, lte
    # sdwan ai ops - pa-1 pa-2

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    snow_client = Client(instance=instance, user=user, password=hashword)

    snow_client.request_params["headers"] = headers
    incident_table = snow_client.resource(api_path="/table/incident")

    # query = QueryBuilder().field("sys_created_by").contains("moogint").AND().\
    query = QueryBuilder().field("sys_created_by").contains("Rohan.Philip").AND().\
            field("short_description").contains("operationally down").AND().\
            field("incident_state").equals([2])  # .AND().\
            # field("assigned_to{'value'}").contains("90d9ff531bfdd1908ac45243604bcbd7").AND().\


    print("pulling all unvalidated 'work in progress' tickets from snow assigned to Rohan Philip")
    ticket_obj_list = incident_table.get(query=query, stream=True).all()
    snow_client.close()
    print("\npulled all tickets from queue\n\n")
    for i in ticket_obj_list:
        try:
            snow_client_obj = snow_client.query(table='number', query={'number': i["number"]})
            ticket_validate_func(ticket_obj=i, snow_client_obj=snow_client_obj, auth=(user, hashword))
        except ManualInterVentionError:
            print("ticket requires manual intervention")
            with open("manual_intervention_tickets.txt", "a") as manual_ticket:
                manual_ticket.write(f"{i['number']} - https://connxaidev.service-now.com/incident.do?sys_id={i['sys_id']}\n")
                # manual_ticket.write(f"{i['number']} - https://connxai.service-now.com/incident.do?sys_id={i['sys_id']}\n")
        input("continue to next ticket")





# TODO: 1) lte ticket values
# TODO: 2) should iface 3 be dealt with through this bot?
# TODO: 3) tickets with multiple ifaces like ticket with store #4283 (new change to bot)
# TODO: 4) run this process as a daemon
