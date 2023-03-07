from rtspscanner import RTSPScanner

scanner = RTSPScanner()
scanner.address = "192.168.1.10"
scanner.creds = 'admin:admin'

res = scanner.run()
print(res)
