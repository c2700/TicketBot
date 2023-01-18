# TicketBot
### Bot to validate proactive tickets

##### (The script can still be run but only for said conditions)

## working:
1. pull all proactive tickets that have "operationally down interface" from snow user's queue
2. parse each pulled ticket and create a mapped data struct of "router name", "node name", respective "interface name" & "interface states"
3. use created data struct as input to login to respective ticket's pod
4. login to pod & pull device interface logs
5. parse pulled device logs & create a data structre of "router name", "node name", respective "interface name" & "interface states"
6. prepare & set field values in the ticket object with respect to the device logs
7. patch ticket location with updated field values
7. set ticket state (if condition to do so is met) and field values based on device logs.
	* 	if interface is down - set assignment_group values
	* 	if interface is up - don't set assignment_group values
8. patch snow ticket location

### <ins>types of tickets that it works on:</ins>

- in user's queue and "work in progress" state
- one node with mulitiple interfaces
- two nodes with one interface each

## TODO:
 - [ ] handling tickets with 2 nodes showing multiple ifaces (eg: ticket from store 4283)
 - [ ] run this as a daemon
 
