import requests
import json

with open("../.hash") as _hash_var:
    _ = json.load(fp=_hash_var)
    auth = (_["user"], _["hashword"])

with open('test_json.json', 'r') as _test_json_f:
    _ = json.load(fp=_test_json_f)
    for i in _["result"]:
        req = requests.post("https://connxaidev.service-now.com/api/now/table/incident", auth=auth, data=json.dumps(i))
        if req.status_code == 201:
            print(f"created ticket {req.json()['number']} - https://connxaidev.service-now.com/incident.do?sys_id={req.json()['sys_id']}")
