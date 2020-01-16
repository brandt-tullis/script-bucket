#! /usr/bin/env python3
#TODO: convert gcloud calls to API calls
#dependencies: pyyaml

import subprocess
import json

all_folders = []
org_id=1045899897599
# raw_output = subprocess.check_output(['gcloud','projects', 'list', '--format=value(name, project_id)'])
# output = raw_output.decode("utf-8").split('\n')
# projects = {}
# for line in output:
#     if line:
#         try:
#             projects[line.split()[0]] = line.split()[1]
#         except IndexError:
#             projects[line.split()[0]] = "NONE"

def recurse_folders(name):
    folder_id = name.rsplit('/', 1)[-1]
    raw_output = subprocess.check_output(['gcloud', 'resource-manager', 'folders', 'list', '--folder={}'.format(folder_id), '--format=json'])
    folders = json.loads(raw_output.decode("utf-8"))
    if folders:
        for sub_folder in folders:
            all_folders.append(sub_folder)
            print('Appended ' + sub_folder['displayName'])
            recurse_folders(sub_folder['name'])
    return

raw_output = subprocess.check_output(['gcloud', 'resource-manager', 'folders', 'list', '--organization={}'.format(org_id), '--format=json'])
folders = json.loads(raw_output.decode("utf-8"))
for folder in folders:
    all_folders.append(folder)
    print('Appended ' + folder['displayName'])
    recurse_folders(folder['name'])