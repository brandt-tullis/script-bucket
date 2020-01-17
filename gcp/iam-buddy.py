#! /usr/bin/env python3
#TODO:
#load all iam into yaml
#command line arguments
#add organization

import subprocess
import json

resources = []
found_resources = []
org_id=1045899897599
target_member='brandt.tullis@kw.com'

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

def normalize_folder(folder, iam):
    normalized = {}
    normalized['iam'] = iam
    normalized['name'] = folder['displayName']
    normalized['id'] = folder['name'].rsplit('/', 1)[-1]
    normalized['parent'] = folder['parent'].rsplit('/', 1)[-1]
    normalized['type'] = 'folder'
    return normalized

def recurse_folders(name):
    folder_id = name.rsplit('/', 1)[-1]
    folders = get_json(['gcloud', 'resource-manager', 'folders', 'list', '--folder={}'.format(folder_id), '--format=json'])
    if folders:
        for sub_folder in folders:
            iam = get_json(['gcloud', 'resource-manager', 'folders', 'get-iam-policy', '{}'.format(folder['name'].rsplit('/', 1)[-1]), '--format=json'])
            normalized = normalize_folder(folder, iam)
            resources.append(normalized)
            print('Appended ' + sub_folder['displayName'])
            print(normalized)
            recurse_folders(sub_folder['name'])
    return

# get all project info and iam polices
print('Loading project IAM polices...')
projects = get_json(['gcloud', 'projects', 'list', '--format=json'])
for project in projects:
    print(project)
    iam = get_json(['gcloud', 'projects', 'get-iam-policy', '{}'.format(project['projectId']), '--format=json'])
    normalized = {}
    normalized['iam'] = iam
    normalized['name'] = project['name']
    normalized['id'] = project['projectId']
    try:
        normalized['parent'] = project['parent']['id']
    except KeyError:
        normalized['parent'] = 'NONE'
    normalized['type'] = 'project'
    resources.append(normalized)

# get top-level folder info
print('Loading folder IAM polices...')
folders = get_json(['gcloud', 'resource-manager', 'folders', 'list', '--organization={}'.format(org_id), '--format=json'])

# recurse  each top-level folder, getting folder info and iam policies
for folder in folders:
    iam = get_json(['gcloud', 'resource-manager', 'folders', 'get-iam-policy', '{}'.format(folder['name'].rsplit('/', 1)[-1]), '--format=json'])
    normalized = normalize_folder(folder, iam)
    resources.append(normalized)
    print(normalized)
    recurse_folders(folder['name'])

#prototype for finding a user
for resource in resources:
    try:
        for binding in resource['iam']['bindings']:
            for member in binding['members']:
                if member.strip('user:') == target_member:
                    if resource['displayName'] not in found_resources:
                        found_resources.append(folder['displayName'])
    except KeyError:
        pass

for resource in found_resources:
    print(folder + '\n')