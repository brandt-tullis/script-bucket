#! /usr/bin/env python3
#TODO:
#requirements file: pyyaml

import argparse, json, os, subprocess, sys, yaml

resources = []
iam_file = 'iam.yaml'
org_id=1045899897599
org_name='kw.com'

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
            recurse_folders(sub_folder['name'])
    return

def load_file(iam_file, script_name):
    # load contents of iam file
    print('Loading iam polices from {}...'.format(iam_file))
    with open(iam_file, 'r') as stream:
        try:
            resources = yaml.load(stream, Loader=yaml.FullLoader)
        except FileNotFoundError:
            print('{0} not found.'
            '\ncreate it by running:' 
            '\n{1} -g '.format(iam_file, script_name))
    return resources

def find_member(target_member, resources):
    matched_resources = []
    for resource in resources:
        try:
            for binding in resource['iam']['bindings']:
                for member in binding['members']:
                    if member.rsplit(':', 1)[-1] == target_member:
                        if resource['name'] not in matched_resources:
                            matched_resources.append(resource['name'])
        except KeyError:
            pass
    return matched_resources

### argparse argument handling ###
parser = argparse.ArgumentParser()
script_name = parser.prog
# mutually exclusive groups prevent certain arguments from being used together
group0 = parser.add_mutually_exclusive_group()
group1 = parser.add_mutually_exclusive_group()
group0.add_argument('-g','--get-iam',
    help='Retrieve iam policies on organization and all nested projects/folders.'
        ' Store policies as yaml in a file.', action='store_true')
group1.add_argument('-f','--find-member',
    help='Search file for member, returning found folders',
        nargs=1, action='store',metavar='<member>')
args = parser.parse_args()

if args.get_iam:
    # open yaml file, create if not present
    if os.path.exists(iam_file):
        print('Deleting {}'.format(iam_file))
        os.remove(iam_file)

    # get organization iam policy
    print('Loading organization IAM policy...')
    iam = projects = get_json(['gcloud', 'organizations', 'get-iam-policy', '{}'.format(org_id), '--format=json'])
    normalized = {}
    normalized['iam'] = iam
    normalized['name'] = org_name
    normalized['id'] = org_id
    normalized['parent'] = 'NONE'
    normalized['type'] = 'organization'
    resources.append(normalized)

    # get all project info and iam polices
    print('Loading project IAM polices...')
    projects = get_json(['gcloud', 'projects', 'list', '--format=json'])
    for project in projects:
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
        recurse_folders(folder['name'])

    # write data to file
    print('Writing data to {}...'.format(iam_file))
    with open(iam_file, 'w+') as stream:
        yaml.dump(resources, stream)
    sys.exit(0)

if args.find_member:
    target_member = args.find_member[0]
    resources = load_file(iam_file, script_name)
    
    # prototype for finding a user
    matched_resources = find_member(target_member, resources)

    # return list of resources where target_member was found
    print('\n{} found in the following resources:\n'.format(target_member))
    for resource in matched_resources:
        print(resource)
    print('')