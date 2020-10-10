#!/usr/bin/python3
import sys
import urllib3
import os
import pwd
import argparse
import socket
import configparser

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from purity_fb import PurityFb, FileSystem, FileSystemSnapshot, SnapshotSuffix, rest, NetworkInterface

CFG_FILE="/da-datastore/src/kparker/pquota.cfg"

def print_usage(filesystem,uid):
	fbips=get_fb_by_fs(filesystem)
	for fbip in fbips:
		token=get_token_by_ip(fbip)
		print_user_usage_by_fs_uid(fbip,token,filesystem,uid)

def get_filesystem(filesystem):
	first_char=filesystem[0]
	if first_char == ".":
		filesystem=os.getcwd()
		filesystem=os.path.abspath(filesystem)
		while not os.path.ismount(filesystem):
			filesystem=os.path.dirname(filesystem)
		filesystem=filesystem.rstrip("/")
	first_char=filesystem[0]
	if first_char == "/":
		command = "df  " + filesystem + "|grep -v Filesystem|awk '{print $1}'|awk -F/ '{print $2}'"
		command_out=os.popen(command)
		filesystem=command_out.read()
		filesystem=filesystem.strip()
	return(filesystem)

def get_fb_by_fs(filesystem):
	fb_ip=[]
	API_token=[]
	for I in range(len(dict)):
		if dict[I][4] == filesystem :
			fb_ip.append(dict[I][0])
			#break
	return(fb_ip)

def get_token_by_ip(ip):
	for I in range(len(dict)):
		if dict[I][0] == ip :
			api_token=dict[I][1]
			break
	return(api_token)

def get_username(uid):
	try:
		username=pwd.getpwuid(int(uid)).pw_name
	except:
		username=uid
	return username

def get_uid(username):
	if args.username.isnumeric():
		uid=args.username
	else:
		from pwd import getpwnam
		uid=getpwnam(args.username)[2]
	return(uid)

def print_usage_footer():
	print("============================================================================\n")

def print_usage_header():
	print("")
	print("Flashblade:Filesystem         UID    Username  Usr-Quota  Def-quota   Used    %")
	print("==================================================================================")

def print_user_usage_by_fs_uid(fbip,token,filesystem,uid):
	fb = PurityFb(fbip)
	fb.login(token)
	res = fb.usage_users.list_user_usage(file_system_names=[filesystem])
	fs_def_user_quota=res.items[0].file_system_default_quota
	if uid == "all" :
		# get usage for all users
		res = fb.usage_users.list_user_usage(file_system_names=[filesystem])
	else:
		# get usage for single user identified by uid
		res = fb.usage_users.list_user_usage(file_system_names=[filesystem],uids=[uid])

	# Get a count of number of entries we will need to display
	num_users=int(res.pagination_info.total_item_count)
	for I in range(num_users):
		UID=str(res.items[I].user.id)
		username=str(get_username(UID))
		quota=res.items[I].quota
		usage=int(res.items[I].usage)
		fb_fs=fbip + ":" + filesystem
		if quota:
			percent=int((usage/quota)*100)
			quota=str(format_bytes(quota))
			print ('{:<30}{:<7}{:<10}{:<11}{:>8}{:>8}{:>5}'.format(fb_fs,UID,username,str(quota),"-",str(format_bytes(usage)),str(percent)))
		else:
			if fs_def_user_quota != 0:
				percent=int((usage/fs_def_user_quota)*100)
			else:
				percent="-"
			quota="-"
			print ('{:<30}{:<7}{:<10}{:<10}{:>9}{:>8}{:>5}'.format(fb_fs,UID,username,str(quota),str(format_bytes(fs_def_user_quota)),str(format_bytes(usage)),str(percent)))
	#print_usage_footer
	fb.logout()


def format_bytes(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: ' KB', 2: ' MB', 3: ' GB', 4: ' TB'}
    while size > power:
        size /= power
        n += 1
    size=int(size)
    size_str=str(size) + power_labels[n]
    return size_str

######################################################################################################
#              End of function declarations
######################################################################################################

if os.path.isfile(CFG_FILE):
	config = configparser.ConfigParser()
	config.read(CFG_FILE)
else:
	exit_message="ERROR:  Config file " + CFG_FILE + " not found.\n\n"
	print("\n")
	sys.exit(exit_message)

try:
	dict=[]

	arrays = config.sections()

	for flashblade in arrays:
		flashblade_ip=config[flashblade]['ManagementIP']
		APItoken=config[flashblade]['APItoken']

		#print(f'DEBUG    IP={flashblade_ip} and token={APItoken}')

		fb = PurityFb(flashblade_ip)
		fb.login(APItoken)
		
		vips = fb.network_interfaces.list_network_interfaces(filter='services=\'data\'')
		filesystems = fb.file_systems.list_file_systems(filter='nfs.v3_enabled or nfs.v4_1_enabled')
		num_vips=int(vips.pagination_info.total_item_count)
		num_filesystems=int(filesystems.pagination_info.total_item_count)

		for cnt in range(num_vips):
			vip_ip=vips.items[cnt].address
			vip_name = socket.gethostbyaddr(vip_ip)
			vip_name=vip_name[0]
			for cnt2 in range(num_filesystems):
				fs_name=filesystems.items[cnt2].name
				dict.append([flashblade_ip,APItoken,vip_ip,vip_name,fs_name])
		fb.logout()

	parser = argparse.ArgumentParser()
	parser.add_argument("-u", "--username", help="username to report on quota usage")
	parser.add_argument("-f", "--filesystem", help="filesystem to report quota usage on")
	parser.add_argument("-a", "--allusers", help="report quota usage for all users",action="store_true")
	args = parser.parse_args()

	if args.username and args.filesystem:
		filesystem=get_filesystem(args.filesystem)
		uid=get_uid(args.username)
		print_usage_header()
		print_usage(filesystem,uid)
		print_usage_footer
	elif args.filesystem and args.allusers:
		uid="all"
		filesystem=get_filesystem(args.filesystem)
		print_usage_header()
		print_usage(filesystem,uid)
		print_usage_footer
	elif args.username:
		uid=get_uid(args.username)
		nfs_mounts=os.popen("mount|grep \"type nfs\" |awk '{print $1}' | awk -F\/ '{print $2}'")
		nfs_filesystems=nfs_mounts.read()
		nfs_filesystems=nfs_filesystems.strip()
		filesystems=nfs_filesystems.split('\n')
		print_usage_header()
		for filesystem in filesystems:
			print_usage(filesystem,uid)
		print_usage_footer
	elif args.filesystem:
		uid=os.getuid()
		filesystem=get_filesystem(args.filesystem)
		print_usage_header()
		print_usage(filesystem,uid)
		print_usage_footer
	elif args.allusers:
		uid="all"
		nfs_mounts=os.popen("mount|grep \"type nfs\"|awk '{print $1}' | awk -F\/ '{print $2}'")
		nfs_filesystems=nfs_mounts.read()
		filesystems=nfs_filesystems.split('\n')
		print_usage_header()
		for filesystem in filesystems:
			if len(filesystem) > 1:
				print_usage(filesystem,uid)
		print_usage_footer
	else:
		nfs_mounts=os.popen("mount|grep \"type nfs\"|awk '{print $1}' | awk -F\/ '{print $2}'")
		nfs_filesystems=nfs_mounts.read()
		filesystems=nfs_filesystems.split('\n')
		filesystems=list(filter(None, filesystems))
		uid=os.getuid()
		print_usage_header()
		for filesystem in filesystems:
			if len(filesystem) > 1:
				print_usage(filesystem,uid)
		print_usage_footer
#XXX
	
	print("\n")
	

except rest.ApiException as e:
	print("Exception: %s\n" % e)

