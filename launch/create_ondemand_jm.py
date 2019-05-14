#!/usr/bin/python

# The MIT License (MIT)
#
# Copyright (c) 2018-2019 Nicholas Torres Okita <nicholas.okita@ggaunicamp.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

# This function creates a Job Manager instance

import boto3
import logging
import sys
from datetime import datetime

# function getLogger
#
# \param name: Name of the logger
# \return Logger object
#
# This function simply creates a new logger object to output information
def getLogger(name):
    now = datetime.now()
    #Logging configuration
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    #Log formatter
    formatter = logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s")
    #Log File handler
    handler = logging.FileHandler("create_spot.log")
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    #Screen handler
    screenHandler = logging.StreamHandler(stream=sys.stdout)
    screenHandler.setLevel(logging.INFO)
    screenHandler.setFormatter(formatter)
    logger.addHandler(screenHandler)
    return logger

# function main
# \param (command line input) instance type: name of instance type to be created
#
# This function is the one responsible for creating the instance. The user needs
# to complete information regarding the user_data (script to be run when the
# instance starts), and other parameters for the instance creation, such as
# ImageId and SecurityGroupId (the others are document through out the code).
def main():
    # Variable containing the user script to initialize and execute the program
    user_data = """#!/bin/bash"""

    if len(sys.argv) <= 1:
        logger.error('Please insert the instance type')
        return

    logger.info('Starting the instance deployment from the template "'+sys.argv[1]+'"')
    instance_type_in = sys.argv[1]

    ec2 = boto3.resource('ec2',region_name='us-east-1')
    instances = ec2.create_instances(
                InstanceType=instance_type_in,
                ImageId='', # Image AMI id
                InstanceInitiatedShutdownBehavior='terminate',
                SecurityGroupIds=[''], # Security group ID to create instances
                SubnetId='', # Subnet Id
                UserData=user_data,
                MaxCount=1,
                MinCount=1,
                KeyName='', # Instance key name
                Monitoring={
                    'Enabled': True
                },
                BlockDeviceMappings=[ # This is the root disk, can be
                                      # reconfigured to what is more
                                      # convenient
                {
                    'DeviceName': '/dev/sda1',
                    'VirtualName': 'eth0',
                    'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeSize': 20,
                        'VolumeType': 'io1',
                        'Iops': 1000
                    },
                    'NoDevice':''
                },
                ]
            )

    # Get the instance id from the created instance
    instance_id = instances[0].id
    logger.info('Instance deployed! Instance id: '+instance_id)

    # Set tags, user can edit to add more tags or rename them
    result = ec2.create_tags(Resources=[instance_id],
            Tags=[
                {
                    'Key': 'Type',
                    'Value': 'jobmanager-ondemand'
                },
                {
                    'Key': 'Name',
                    'Value': 'JobManager'
                }
                ]
            )

if __name__ == '__main__':
    logger = getLogger(__name__)
    main()
