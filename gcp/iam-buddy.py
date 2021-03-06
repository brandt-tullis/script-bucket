#! /usr/bin/env python3
#TODO:
#return list of all members

import argparse, json, os, subprocess, sys, yaml

resources = []
iam_file = 'iam.yaml'
org_id=1045899897599
org_name='kw.com'

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
    full_member = ''
    for resource in resources:
        try:
            for binding in resource['iam']['bindings']:
                for member in binding['members']:
                    if member.rsplit(':', 1)[-1] == target_member:
                        if not full_member:
                            full_member = member
                        if resource['name'] not in matched_resources:
                            matched_resources.append(resource)
        except KeyError:
            pass
    return matched_resources, full_member

### argparse argument handling ###
parser = argparse.ArgumentParser()
script_name = parser.prog
# mutually exclusive groups prevent certain arguments from being used together
group0 = parser.add_mutually_exclusive_group()
group1 = parser.add_mutually_exclusive_group()
group2 = parser.add_mutually_exclusive_group()
group0.add_argument('-g','--get-iam',
    help='Retrieve iam policies on organization and all nested projects/folders.'
        ' Store policies as yaml in a file.', action='store_true')
group1.add_argument('-f','--find-member',
    help='Search file for member, returning found folders',
        nargs=1, action='store',metavar='<member>')
group2.add_argument('-d','--delete-member',
    help='Search file for member, then delete from org/folders/projects in GCP',
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

if args.delete_member:
    target_member = args.delete_member[0]

if args.find_member or args.delete_member:
    resources = load_file(iam_file, script_name)
    
    # prototype for finding a user
    matched_resources, full_member = find_member(target_member, resources)

    # return list of resources where target_member was found
    if matched_resources:
        print('\n{} found in the following resources:\n'.format(full_member))
        for resource in matched_resources:
            print(resource['name'])
        print('')
    else:
        print('\n{} not found.\n'.format(target_member))

if matched_resources and args.delete_member:
    # prompt for input to continue
    print('Are you sure you would like to remove {0} from the {1} kw.com organization iam policy, '
    'as well as iam policies for all nested folders and projects?'.format(target_member, org_name))
    input("Press Enter to continue...")
    for resource in matched_resources:
        if resource['type'] == 'organization':
            for binding in resource['iam']['bindings']:
                if full_member in binding['members']:
                    subprocess.check_output(['gcloud', 'organizations', 'remove-iam-policy-binding',
                        str(resource['id']), '--member={}'.format(full_member), '--role={}'.format(binding['role'])])
        elif resource['type'] == 'folder':
            for binding in resource['iam']['bindings']:
                if full_member in binding['members']:
                    subprocess.check_output(['gcloud', 'resource-manager', 'folders', 'remove-iam-policy-binding',
                        str(resource['id']), '--member={}'.format(full_member), '--role={}'.format(binding['role'])])
        elif resource['type'] == 'project':
            for binding in resource['iam']['bindings']:
                if full_member in binding['members']:
                    subprocess.check_output(['gcloud', 'projects', 'remove-iam-policy-binding',
                        str(resource['id']), '--member={}'.format(full_member), '--role={}'.format(binding['role'])])
    print('\n Deletions complete. Note that {} was not updated'.format(iam_file))
