#!/usr/bin/env python

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

# This file contains functions that realize operations in the AWS instances

import logging
import sys
import time
import boto3
import base64
from datetime import datetime

# function getLogger
#
# \param name: Name of the logger
# \return Logger object
#
# This function simply creates a new logger object to output information
def getLogger(name):
    now = datetime.now()
    # Logging configuration
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # Log formatter
    formatter = logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s")
    # Log File handler
    handler = logging.FileHandler("jm_handler.log")
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # Screen handler
    screenHandler = logging.StreamHandler(stream=sys.stdout)
    screenHandler.setLevel(logging.INFO)
    screenHandler.setFormatter(formatter)
    logger.addHandler(screenHandler)
    return logger

class instance_operations:

    # function __init__
    # \param logger : logger to output information
    # Initialize the class ec2 client and resource
    def __init__(self, logger):
        self.logger = logger 
        self.ec2 = boto3.client('ec2', region_name='us-east-1')
        self.ec2res = boto3.resource('ec2', region_name='us-east-1')

    # function get_current_spot_price_allaz
    # \param instance_type : string containing the instance type
    # Gets current spot price for an input instance type in all availability zones
    def get_current_spot_price_allaz(self, instance_type):
        dict = {}
        history = self.ec2.describe_spot_price_history(
            StartTime=datetime.now().isoformat(),
            EndTime=datetime.now().isoformat(),
            ProductDescriptions=['Linux/UNIX'],
            InstanceTypes=[instance_type])

        for h in history['SpotPriceHistory']:
            dict[h['AvailabilityZone']] = float(h['SpotPrice'])

        return dict

    # function get_current_spot_price_allaz
    # \param instance_type : string containing the instance type
    # \param az : availability zone
    # Gets current spot price for an input instance type in an input availability zones
    def get_current_spot_price(self, instance_type, az):
        history = self.ec2.describe_spot_price_history(
            StartTime=datetime.now().isoformat(),
            EndTime=datetime.now().isoformat(),
            ProductDescriptions=['Linux/UNIX'],
            InstanceTypes=[instance_type],
            AvailabilityZone=az)

        price = -1
        if (len(history['SpotPriceHistory']) > 0):
            price = float(history['SpotPriceHistory'][0]['SpotPrice'])

        return price

    # function terminateInstance
    # \param instanceid: string containing the instance id to be terminated
    # Terminates instance described by instanceid
    def terminateInstance(self, instanceid):
        inst = self.ec2res.Instance(instanceid)
        inst.terminate()

    # function createSpotInstance
    # \param instance_type_in: string containing the instance type
    # \param az : availability zone
    # \param price : instance price
    # Creates an Spot instance of type instance_type_in, in availability zone az
    # and priced at max price.
    def createSpotInstance(self, instance_type_in, az, price):
        # To be completed by user defined subnets
        subnets = {
            'us-east-1a': '',
            'us-east-1b': '',
            'us-east-1c': '',
            'us-east-1d': '',
            'us-east-1e': '',
            'us-east-1f': ''
        }

        bestZone = ['', sys.float_info.max]

        zones = self.ec2.describe_availability_zones()
        zoneNames = []
        for zone in zones['AvailabilityZones']:
            if zone['State'] == 'available':
                zoneNames.append(zone['ZoneName'])

        PRICE = str(price * 1.2)
        INSTANCE = instance_type_in

        bestZone[0] = az
        bestZone[1] = price
        now_str = "[" + datetime.now().isoformat() + "]     "
        self.logger.info(INSTANCE + "    " + bestZone[0] + "    " + PRICE)

        # Variable containing the user script to initialize and execute the program
        user_data = """#!/bin/bash 
        """

        instance_type = INSTANCE
        response = self.ec2.request_spot_instances(
            SpotPrice=PRICE,
            InstanceCount=1,
            LaunchSpecification={
                'InstanceType': instance_type,
                'ImageId': '', # Image AMI id
                'SecurityGroupIds': [''], # Security group ID to create instances
                'SubnetId': subnets[bestZone[0]],
                'UserData': (base64.b64encode(user_data.encode())).decode(),
                'KeyName': '', # Instance key name
                'Monitoring': {
                    'Enabled': True
                },
                'Placement': {
                    'AvailabilityZone': bestZone[0]
                },
                'BlockDeviceMappings': [  # This is the root disk, can be
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
                        'NoDevice': ''
                    },
                ]
            }
        )

        spot_request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
        time.sleep(30)
        response = self.ec2.describe_spot_instance_requests(SpotInstanceRequestIds=[spot_request_id])
        cur_spot = response['SpotInstanceRequests'][0]
        if ('InstanceId' in cur_spot):
            now_str = "[" + datetime.now().isoformat() + "] "
            self.logger.info("SPOTID " + cur_spot['InstanceId'])
            result = self.ec2.create_tags(Resources=[cur_spot['InstanceId']],
                                     Tags=[ # Instance tags (default as Type and Name)
                                         {
                                             'Key': 'Type',
                                             'Value': 'worker-spot'
                                         },
                                         {
                                             'Key': 'Name',
                                             'Value': 'Auto-Generated Spot Worker ' + instance_type_in
                                         }
                                     ]
                                     )
            return cur_spot['InstanceId']
        else:
            now_str = "[" + datetime.now().isoformat() + "] "
            self.logger.error('Spot Request for ' + instance_type_in + ' failed in zone ' + bestZone[0])
            self.ec2.cancel_spot_instance_requests(SpotInstanceRequestIds=[spot_request_id])
            return ''

    # function createSpotInstanceThreads
    # \param instance_type_in: string containing the instance type
    # \param az : availability zone
    # \param price : instance price
    # \param valid_count : Number of times instance must perform over budget
    # \param ret_dict : Return the object created
    # Create a Spot instance using threads (call createSpotInstance function)
    def createSpotInstanceThreads(self, instance_type_in, az, price, valid_count, ret_dict):
        ret = self.createSpotInstance(instance_type_in, az, price)
        if ret != '':
            ec2_instance = self.ec2res.Instance(ret)
            init_time = datetime.strptime(ec2_instance.launch_time.strftime("%Y-%m-%dT%H:%M:%S"),
                                          "%Y-%m-%dT%H:%M:%S")

            instance_dict = {"instance_id": ret,
                             "instance_type": instance_type_in,
                             "instance_az": az,
                             "price": price,
                             "performance_negative": -1,
                             "init_time": init_time,
                             "cur_time": init_time,
                             "valid": valid_count,
                             "prev_valid": valid_count}

            ret_dict[ret] = instance_dict
        else:
            self.logger.error("FAILED TO CREATE INSTANCE OF TYPE " + instance_type_in)

    # function replaceInstance
    # \param list : list of instances
    # \param oldTuple : instance to be replaced
    # Replaces an instance with one with better cost per performance ratio
    def replaceInstance(self, list, oldTuple):
        counter = 0
        # (instance_id, instance_type, az, price, costperinterp, costperinterp_stdev)
        for inst in list:
            self.logger.debug("Counter for " + str(oldTuple[1]) + ": " + str(counter))
            self.logger.debug("Trying instance: " + str(inst[1]))
            counter = counter + 1
            if ((oldTuple[7] < inst[6]) and (oldTuple[1] != inst[1])):
                if (self.createSpotInstance(inst[1], inst[2], inst[3]) != ''):
                    self.terminateInstance(oldTuple[0])
                    now_str = "[" + datetime.now().isoformat() + "] "
                    self.logger.info('Replacing ' + oldTuple[1] + ' in zone ' + oldTuple[2] + ' with best case performance as ' + str(oldTuple[7]) + ' with ' + inst[1] + ' in zone ' + inst[2] + ' with worst case performance as ' + str(inst[6]))
                    return
            else:
                break
        now_str = "[" + datetime.now().isoformat() + "] "
        self.logger.info(oldTuple[1] + ' in zone ' + oldTuple[2] + ' with best case performance as ' + str(oldTuple[7]) + ' could not be replaced')

    # function newInstance
    # \param list : list sorted in decrescent cost/performance order (best first)
    # Creates a new instance with the best cost/performance in list
    def newInstance(self, list):
        counter = 0
        # (instance_id, instance_type, az, price, costperinterp, costperinterp_stdev)
        for inst in list:
            if (self.createSpotInstance(inst[1], inst[2], inst[3]) != ''):
                self.logger.info('Started new instance of type ' +  inst[1])
                return

        self.logger.info('Couldn\'t start new instance')

    # function get_instance_reservations
    # \return list of instance reservations
    # Get instances ids that have tag:Type worker-spot and is
    # turned on and running
    def get_instance_reservations(self):
        filters = []
        f1 = {}
        f1['Name'] = 'tag:Type'
        f1['Values'] = ['worker-spot']
        filters.append(f1)
        f2 = {}
        f2['Name'] = 'instance-state-name'
        f2['Values'] = ['running']
        filters.append(f2)

        instance_reservations = self.ec2.describe_instances(Filters=filters)
        return instance_reservations

    # function get_jobmanager_reservations
    # \return list of instance reservations
    # Get instances ids that have tag:type jobmanager-ondemand and is
    # turned on and running
    def get_jobmanager_reservations(self):
        filters = []
        f1 = {}
        f1['Name'] = 'tag:Type'
        f1['Values'] = ['jobmanager-ondemand']
        filters.append(f1)
        f2 = {}
        f2['Name'] = 'instance-state-name'
        f2['Values'] = ['running']
        filters.append(f2)

        instance_reservations = self.ec2.describe_instances(Filters=filters)
        return instance_reservations

    # function get_jobmanager_reservations
    # \return time object with the job manager initialization time
    # Gets the time that the job manager started running
    def get_jobmanager_init_time(self):
        jm_res = self.get_jobmanager_reservations()
        instance = jm_res['Reservations'][0]
        instance_id = instance['Instances'][0]['InstanceId']

        ec2_instance = self.ec2res.Instance(instance_id)
        init_time = datetime.strptime(ec2_instance.launch_time.strftime("%Y-%m-%dT%H:%M:%S"), "%Y-%m-%dT%H:%M:%S")

        return init_time
