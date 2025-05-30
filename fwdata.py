# Variables required
fwData = {
    "mgmtUrl":"lmickey-pan-lab-ngfw-mgmt.eastus.cloudapp.azure.com",
    "mgmtUser":"lmickey",
    "mgmtPass":"VZshgDaWJSd7fe8",
    "untrustAddr":"10.9.1.4/24",
    "untrustSubnet":"10.9.1.0/24",
    "untrustInt":"ethernet1/1",
    "untrustDFGW":"10.9.1.1",
    "trustAddr":"10.9.2.4/24",
    "trustSubnet":"10.9.2.0/24",
    "trustInt":"ethernet1/2",
    "tunnelInt":"tunnel.1",
    "tunnelAddr":"192.168.1.1/32",
    "panoramaAddr":"10.9.2.5",
    "publicInetAddr":"172.174.104.127",
    "mgmtAddr":"10.9.0.5",
    "untrustURL":"panfw-untrust-useast-azuredns.com"
}
paData = {
    "paTSGID":"1570970024",
    "paApiUser":"lmickey",
    "paApiToken":"token",
    "paInfraSubnet":"192.168.255.0/24",
    "paInfraBGPAS":65534,
    "paMobUserSubnet":"100.64.0.0/16",
    "paPortalHostname":"lab018462743.gpcloudservice.com",
    "paZtnaContSubnet":"172.16.0.0/20",
    "paZtnaAppSubnet":"172.20.0.0/16",
    "paSCEndpoint":"10.110.110.110"
} 