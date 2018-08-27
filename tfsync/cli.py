#!/bin/env python
"""

Name: cli.py
Purpose: Sync Terraform state file with current config
Date: 08/03/2018
Author: Jason DeCorte

Version History
08/06/2018 - Jason DeCorte
    - Added method_kwargs for method calls
    - Added --backend-config optional parameter
08/08/2018 - Jason DeCorte
    - Added ability to paginate over all results
    - Added DMS sync
08/09/2018 - Jason DeCorte
    - Fixed bug in lambda pagination
08/24/2018 - Jason DeCorte
    - Added optional no color flag (used for -no-color switch on terraform)
"""
import os
import boto3
import argparse
import logging
import pprint
import subprocess


def execute_tf(cmd, working_dir):
    """
    Execute a Terraform command
    :param cmd: Command to execute (list)
    :param working_dir: Directory containing the Terraform config files
    :return:
    """
    logger.debug("execute_tf entered")
    logger.debug("Command= {}".format(' '.join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=working_dir)
    logger.info("Terraform command started: pid [{}]".format(p.pid))
    for line in iter(p.stdout.readline, ''):
        line = line.decode('utf-8').strip()
        logger.info(line)
    exit_code = p.wait()
    logger.debug("execute_tf exited")
    return exit_code


def execute_tf_init(working_dir, backend_config, no_color=False):
    """
    Execute the Terraform Init command
    :param working_dir: Directory containing the Terraform config files
    :param backend_config: Optional file containing backend config
    :param no_color: Disable color output
    :return: None
    """
    logger.debug("execute_tf_init entered")
    command = ['/usr/local/bin/terraform', 'init']
    if no_color:
        command.append('-no-color')
    if backend_config:
        command.append('-backend-config={}'.format(backend_config))
    exit_code = execute_tf(command, working_dir)
    logger.info("Terraform Init completed with return code [{}]".format(exit_code))
    logger.debug("execute_tf_init exited")
    return True if not exit_code else False


def execute_tf_import(working_dir, address, provider_id, no_color=False):
    """
    Execute the Terraform Import command using the Address and ID
    :param working_dir: Directory containing the Terraform config files
    :param address: Terraform resource address
    :param provider_id: Provider dependent object identification
    :param no_color: Disable color output
    :return: None
    """
    logger.debug("execute_tf_import entered")
    logger.debug("Address: {}".format(address))
    logger.debug("Provider ID: {}".format(provider_id))
    command = ['/usr/local/bin/terraform', 'import']
    if no_color:
        command.append('-no-color')
    command.extend([address, provider_id])
    exit_code = execute_tf(command, working_dir)
    logger.info("Terraform Import completed with return code [{}]".format(exit_code))
    logger.debug("execute_tf_import exited")
    return True if not exit_code else False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sync Terraform State File with Environment')
    parser.add_argument('path', help='Path to Terraform config files')
    parser.add_argument('--backend-config', help='Optional backend config file')
    parser.add_argument("-D", "--debug", action="store_true",
                        help="Debug level logging [default: %(default)s]")
    parser.add_argument("--no-color", action="store_true", help="Turn off color in log messages")
    args = parser.parse_args()

    logger = logging.getLogger('tfsync')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    if args.debug:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    fh = logging.FileHandler(os.path.join(os.getcwd(), 'tfsync.log'), mode='w')
    if args.debug:
        fh.setLevel(logging.DEBUG)
    else:
        fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info("Start TFSync")

    logger.info("Call execute TF Init")
    if execute_tf_init(args.path, args.backend_config, args.no_color):
        logger.info("Terraform now initialized")

        config_list = [
            {
                'object_type': "sfn",
                'client_name': "stepfunctions",
                'method_name': "list_state_machines",
                'method_kwargs': {'maxResults': 100},
                'response_token': 'nextToken',
                'token_kwarg': 'nextToken',
                'object_key': "stateMachines",
                'attribute_list': [
                    'name',
                    'stateMachineArn'
                ],
                'aws_address_fmt': "{resource_type}.{obj[0]}",
                'aws_prov_id_fmt': "{obj[1]}",
                'aws_resource': "aws_sfn_state_machine",
            },
            {
                'object_type': "crawler",
                'client_name': "glue",
                'method_name': "get_crawlers",
                'method_kwargs': {'MaxResults': 100},
                'response_token': 'NextToken',
                'token_kwarg': 'NextToken',
                'object_key': "Crawlers",
                'attribute_list': [
                    "Name"
                ],
                'aws_address_fmt': "{resource_type}.{obj[0]}",
                'aws_prov_id_fmt': "{obj[0]}",
                'aws_resource': "aws_glue_crawler",
            },
            {
                'object_type': "lambda",
                'client_name': "lambda",
                'method_name': "list_functions",
                'method_kwargs': {},
                'response_token': 'NextMarker',
                'token_kwarg': 'Marker',
                'object_key': "Functions",
                'attribute_list': [
                    "FunctionName"
                ],
                'aws_address_fmt': "{resource_type}.{obj[0]}",
                'aws_prov_id_fmt': "{obj[0]}",
                'aws_resource': "aws_lambda_function",
            },
            {
                'object_type': "dms",
                'client_name': "dms",
                'method_name': "describe_replication_tasks",
                'method_kwargs': {},
                'response_token': 'Marker',
                'token_kwarg': 'Marker',
                'object_key': "ReplicationTasks",
                'attribute_list': [
                    "ReplicationTaskIdentifier"
                ],
                'aws_address_fmt': "{resource_type}.{obj[0]}",
                'aws_prov_id_fmt': "{obj[0]}",
                'aws_resource': "aws_dms_replication_task",
            },
        ]
        for config in config_list:
            logger.debug("Config= {}".format(pprint.pformat(config)))
            if [f for f in os.listdir(args.path) if f.startswith(config['object_type'])]:
                logger.info("SYNC {}s".format(config['object_type'].upper()))
                client = boto3.client(config['client_name'])
                response = getattr(client, config['method_name'])(**config['method_kwargs'])
                logger.debug('Response: {}'.format(pprint.pformat(response)))
                collect_objects = response.get(config['object_key'])
                response_token = config['response_token']
                while response.get(response_token):
                    config['method_kwargs'][config['token_kwarg']] = response.get(response_token)
                    response = getattr(client,
                                       config['method_name'])(**config['method_kwargs'])
                    logger.debug('Response: {}'.format(pprint.pformat(response)))
                    collect_objects.extend(response.get(config['object_key']))
                objects = map(lambda s: [s.get(attr) for attr in config['attribute_list']],
                              collect_objects)
                # todo: Compare list to state file
                for obj in objects:
                    aws_resource_address = (
                        config['aws_address_fmt'].format(resource_type=config['aws_resource'],
                                                         obj=obj))
                    aws_provider_id = config['aws_prov_id_fmt'].format(obj=obj)
                    ec = execute_tf_import(args.path, aws_resource_address,
                                           aws_provider_id, args.no_color)
                    if not ec:
                        err_msg = "Failed to import the resource {} id {}"
                        logger.error(err_msg.format(aws_resource_address, aws_provider_id))

    logger.info("TFSync Finished")
