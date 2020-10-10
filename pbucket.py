#!/usr/bin/python3
import sys
import urllib3
#import os
#import pwd
#import argparse
#import socket
#import configparser

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from purity_fb import PurityFb, FileSystem, FileSystemSnapshot, SnapshotSuffix, rest, NetworkInterface

CFG_FILE="/da-datastore/src/kparker/pquota.cfg"


######################################################################################################
#              Begin function declarations
######################################################################################################

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


flashblade_ip = "10.21.225.35"
APItoken = "T-5b32645c-e51a-48bd-85cf-3004fe1bc0a1"

try:
	if len(sys.argv) < 2:
		print("\n Usage: ",sys.argv[0], " bucket-name\n")
		exit()
	else:
		args=sys.argv[1]

	if args == "-a":
		fb = PurityFb(flashblade_ip)
		fb.login(APItoken)
		res = fb.buckets.list_buckets()
		num_buckets=int(res.pagination_info.total_item_count)
		print()
		for I in range(num_buckets):
			account_name=str(res.items[I].account.name)
			bucket_name=str(res.items[I].name)
			bucket_object_count=res.items[I].object_count
			bucket_space=format_bytes(res.items[I].space.total_physical)
			print(f'Account={account_name} - Bucket Name={bucket_name} - Obj count={bucket_object_count} using {bucket_space}.')
		fb.logout()
		print()

	else:
		bucket_name=args
		fb = PurityFb(flashblade_ip)
		fb.login(APItoken)
		res = fb.buckets.list_buckets(names=[bucket_name])
		account_name=str(res.items[0].account.name)
		bucket_object_count=res.items[0].object_count
		bucket_space=format_bytes(res.items[0].space.total_physical)
		print(f'\nAccount={account_name} - Bucket Name={bucket_name} - Obj count={bucket_object_count} using {bucket_space}.\n')

except rest.ApiException as e:
	print("Exception: %s\n" % e)
