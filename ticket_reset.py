import requests
import re
from os import path
import json

def Login():
    if not path.exists(".hash"):
        print("no stored snow creds found. please input snow creds")
        _instance = input("snow instance: ")  ## snow domain (test or prod env domain name)
        _user = input("user: ")
        _password = input("password: ")

        _hash_dict = {
            "instance": _instance,
            "user": _user,
            "password": _password
        }

        with open(".hash", 'w') as _f_obj:
            json_dict = json.loads(json.dumps(_hash_dict))
            json.dump(obj=json_dict, fp=_f_obj, indent=4)

    elif path.exists(".hash"):
        with open(".hash", "r") as _f_obj:
            _json_obj = json.load(fp=_f_obj)
            _instance = _json_obj["instance"]
            _user = _json_obj["user"]
            _password = _json_obj["password"]

    return _instance, _user, _password


def reset_tickets():

    if not path.exists("test_ticket_ids"):
        print("please create a file named 'test_ticket_ids'. separate the ticket id's with new lines, commas or spaces")
        return
    
    if path.exists("test_ticket_ids") and not path.isfile("test_ticket_ids"):
        print("'test_ticket_ids' does not seem to be file. please re-create it as a file and separate with ticket id's with new lines, commas or spaces")
        return
    
    _instance, _user, _password = Login()
    
    if not re.search("dev", _instance):
        print("this is snow instance not a dev environment")
        return

    SnowSess = requests.Session()
    SnowSess.auth(_user, _password)

    empty_post_data = {
                "contact_type": "",
                "u_service_type": "",
                "category": "",
                "subcategory": "",
                "u_issue_type": "",
                "u_issue_start_date_time": "",
                "assignment_group": "",
            }

    with open('test_ticket_ids') as test_tickets:
        for i in test_tickets.readlines():
            inc_num = SnowSess.get(f"{_instance}.service-now.com/api/now/table/incident/{'sys_id'}")
            print(f"resetting ticket {inc_num} - {i}")
            try:
                SnowSess.patch(f"{_instance}.service-now.com/api/now/table/incident/{'sys_id'}", data=empty_post_data)
            except Exception as e:
                print(e)
                with open(f"could not reset ticket {inc_num} - {i}") as err_reset:
                    err_reset.write(i)

    SnowSess.close()


