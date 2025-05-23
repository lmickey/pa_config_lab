Insructions:

1. Enter at minimum the mgmtUrl, mgmtUser, mgmtPass in the fwdata.py (use fwdata.py.example for reference)

2. Run configure_initial_config.py to set NTP/DNS configuration

3. Register the firewall with https://support.paloaltonetworks.com to your SE CSP, get the licenses and generate OTP and get device certificate

4. Run configure_interfaces.py to do basic interface configuration

5. Run configure_addr_objects.py to setup default address objects used in the rest of the configuration

6. Run configure_routing.py to setup default routing configuration

7. Run create_nat_rule.py to seutp nat policy

8. Run create_fw_rule.py to add default firewall rules

######### Panorama Steps ############## Skip if not using panorama
1. Run configure_panorama.py to instantiate panorama configuration

2. License and Register Panorama as you did with the firewall above

3. Run create_sc_in_Panorama.py to 

######### SCM Steps ################### Skip if not using SCM
1. 