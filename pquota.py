#!/usr/bin/python3
import sys
import urllib3
import os
import pwd
import argparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from purity_fb import PurityFb, FileSystem, FileSystemSnapshot, SnapshotSuffix, rest

#
#  User defined variables:
#	API_TOKEN is the api token needed to authenticate with the FlashBlade
#	management interface
#		i.e.   API_TOKEN="T-5b45345c-e51a-48bd-85cf-4564fe1bc0a1"
#
#	FB_IP is the IP address or hostname of the FlashBlade management interface
#		i.e.	FB_IP=10.21.222.232
#		i.e.	FB_IP=flashblade
#
#
API_TOKEN="T-5b32645c-e51a-48bd-85cf-3004fe1bc0a1"
FB_IP="10.21.225.35"
#
#
#

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
	print("=======================================================================\n")

def print_usage_header():
	print("")
	print("Filesystem         UID    Username  Usr-Quota  Def-quota   Used     %")
	print("========================================================================")

def print_user_usage_by_fs_uid(filesystem,uid):
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
		#username=str(res.items[I].user.name)
		username=str(get_username(UID))
		quota=res.items[I].quota
		usage=int(res.items[I].usage)
		if quota:
			percent=int((usage/quota)*100)
			quota=str(format_bytes(quota))
			print ('{:<19}{:<7}{:<10}{:<11}{:>9}{:>8}{:>5}'.format(filesystem,UID,username,str(quota),"-",str(format_bytes(usage)),str(percent)))
		else:
			if fs_def_user_quota != 0:
				percent=int((usage/fs_def_user_quota)*100)
			else:
				percent="-"
			quota="-"
			print ('{:<19}{:<7}{:<11}{:<10}{:>9}{:>8}{:>5}'.format(filesystem,UID,username,str(quota),str(format_bytes(fs_def_user_quota)),str(format_bytes(usage)),str(percent)))
	print_usage_footer

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

fb = PurityFb(FB_IP)

try:
	# Set API token
	fb.login(API_TOKEN)

	parser = argparse.ArgumentParser()
	parser.add_argument("-u", "--username", help="username to report on quota usage")
	parser.add_argument("-f", "--filesystem", help="filesystem to report quota usage on")
	parser.add_argument("-a", "--allusers", help="report quota usage for all users",action="store_true")
	args = parser.parse_args()

	if args.username and args.filesystem:
		filesystem=get_filesystem(args.filesystem)
		print_usage_header()
		uid=get_uid(args.username)
		print_user_usage_by_fs_uid(filesystem,uid)
	elif args.filesystem and args.allusers:
		uid="all"
		filesystem=get_filesystem(args.filesystem)
		print_usage_header()
		print_user_usage_by_fs_uid(filesystem,uid)
		print_usage_footer
	elif args.username:
		uid=get_uid(args.username)
		nfs_mounts=os.popen("mount|grep \"type nfs\" |awk '{print $1}' | awk -F\/ '{print $2}'")
		nfs_filesystems=nfs_mounts.read()
		nfs_filesystems=nfs_filesystems.strip()
		filesystems=nfs_filesystems.split('\n')
		print_usage_header()
		for f in filesystems:
			print_user_usage_by_fs_uid(f,uid)
	elif args.filesystem:
		uid=os.getuid()
		filesystem=get_filesystem(args.filesystem)
		print_usage_header()
		print_user_usage_by_fs_uid(filesystem,uid)
		print_usage_footer
	elif args.allusers:
		uid="all"
		nfs_mounts=os.popen("mount|grep \"type nfs\"|awk '{print $1}' | awk -F\/ '{print $2}'")
		nfs_filesystems=nfs_mounts.read()
		filesystems=nfs_filesystems.split('\n')
		print_usage_header()
		for f in filesystems:
			if len(f) > 1:
				#print_fs_usage(f)
				print_user_usage_by_fs_uid(f,uid)
		print_usage_footer
	else:
		nfs_mounts=os.popen("mount|grep \"type nfs\"|awk '{print $1}' | awk -F\/ '{print $2}'")
		nfs_filesystems=nfs_mounts.read()
		filesystems=nfs_filesystems.split('\n')
		filesystems=list(filter(None, filesystems))
		uid=os.getuid()
		print_usage_header()
		for f in filesystems:
			print_user_usage_by_fs_uid(f,uid)
		print_usage_footer

	print("\n")
	
	fb.logout()

except rest.ApiException as e:
	print("Exception: %s\n" % e)

