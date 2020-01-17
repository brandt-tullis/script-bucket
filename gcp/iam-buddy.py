#! /usr/bin/env python3
#TODO:
#normalize folder, project, and organization

import subprocess
import json

all_folders = []
org_id=1045899897599
target_member='anthony.tartaglia@kw.com'

# raw_output = subprocess.check_output(['gcloud','projects', 'list', '--format=value(name, project_id)'])
# output = raw_output.decode("utf-8").split('\n')
# projects = {}
# for line in output:
#     if line:
#         try:
#             projects[line.split()[0]] = line.split()[1]
#         except IndexError:
#             projects[line.split()[0]] = "NONE"

def get_json(command):
    raw_output = subprocess.check_output(command)
    return json.loads(raw_output.decode("utf-8"))

def recurse_folders(name):
    folder_id = name.rsplit('/', 1)[-1]
    folders = get_json(['gcloud', 'resource-manager', 'folders', 'list', '--folder={}'.format(folder_id), '--format=json'])
    if folders:
        for sub_folder in folders:
            iam = get_json(['gcloud', 'resource-manager', 'folders', 'get-iam-policy', '{}'.format(folder['name'].rsplit('/', 1)[-1]), '--format=json'])
            folder['iam'] = iam
            all_folders.append(sub_folder)
            print('Appended ' + sub_folder['displayName'])
            recurse_folders(sub_folder['name'])
    return

# get top-level folder info
folders = get_json(['gcloud', 'resource-manager', 'folders', 'list', '--organization={}'.format(org_id), '--format=json'])
# recurse through each top-level folder, getting folder info and iam policies
for folder in folders:
    iam = get_json(['gcloud', 'resource-manager', 'folders', 'get-iam-policy', '{}'.format(folder['name'].rsplit('/', 1)[-1]), '--format=json'])
    folder['iam'] = iam
    all_folders.append(folder)
    recurse_folders(folder['name'])

for folder in folders:
    for binding in folder['iam']['bindings']:
        for member in binding['members']:
            print(member)
    print 