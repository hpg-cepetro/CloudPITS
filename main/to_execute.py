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

# The main in this file is to be executed in the Job Manager to select the best
# instances for a given input price. If the user selects a very low price (for
# example 5 dollars), the script will try to increase the budget constraint to
# something feasible.

import logging
import sys
import time
import boto3
from datetime import datetime
from datetime import timedelta
import operator
import threading
from instance_operations import instance_operations
import rds_operations

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
    logger.setLevel(logging.DEBUG)
    #Log formatter
    formatter = logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s")
    #Log File handler
    handler = logging.FileHandler("jm_handler.log")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    #Screen handler
    screenHandler = logging.StreamHandler(stream=sys.stdout)
    screenHandler.setLevel(logging.DEBUG)
    screenHandler.setFormatter(formatter)
    logger.addHandler(screenHandler)
    return logger

# function get_from_input
#
# \param _string: String to be searched from input
# \param input_dict: Input dictionary of pairs key=value
# \return Value stored for _string or -1 if it does not exist
def get_from_input(_string, input_dict):
    if _string in input_dict:
        return input_dict[_string]
    else:
        return -1

# function pareto
# \param target_nodes: number of instances that will be used
# \param data_hash: data to be executed hash (needs to be stored in the database)
# \param idparameters: database id with the parameters used in experiment
#
# This function will print the estimated Pareto given the stored performance and
# current price for each instance. Note that the Job Manager instance selected
# is the c5.4xlarge and all disks are 20GB 1000IOPS, therefore the prices are
# defined as such.
#
# Furthermore, we consider a performance penalty of 0.1% for each new instance
# added.
def pareto(target_nodes, data_hash, idparameters):
    all_zones = ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e', 'us-east-1f']

    conn = rds_operations.rds_connect()
    target_tasks = rds_operations.get_interpols(conn, idparameters, rds_operations.get_iddata(conn, data_hash))
    iddata = rds_operations.get_iddata(conn, data_hash)

    all_performance = rds_operations.get_interpsec_allinstances(conn, iddata, idparameters)
    ops = instance_operations(logger)

    jm_perf = 0
    for result in all_performance:
        if result[0]== "c5.4xlarge":
            jm_perf = float(result[1])

    logger.info("INSTANCE_TYPE\tTIME_TO_RUN(seconds)\tCOST(dollars)")
    for result in all_performance:
        instance_type = result[0]
        interpsec = result[1]
        stddev_interpsec = result[2]

        # prices = instance_operations.get_current_spot_price_allaz(ec2, instance_type)

        best_price = 10000
        best_az = ""

        for az in all_zones:
            price = ops.get_current_spot_price(instance_type, az) + 0.09375

            if (price < best_price and price > 0):
                best_price = price
                best_az = az

        costperinterp = float(interpsec / (best_price / 3600))
        string = "{}\t{}\t{}"
        time_to_run = target_tasks / (jm_perf + interpsec * target_nodes * (1-((target_nodes-1)/1000.0)))
        price_to_pay = time_to_run * target_nodes * best_price / 3600 + time_to_run * 0.68 / 3600
        logger.info(string.format(instance_type,time_to_run,price_to_pay))

# function main
#
# \param (command line input) interval : time to wait for the next iteration in minutes
# \param (command line input) budget : budget in dollars to complete the execution
# \param (command line input) data_hash : dataset hash stored in the database
# \param (command line input) nodes : maximum number of instances running
# (id parameters is set as default to 41, can be changed in code)
#
# Before the iterations loop, this function sets the input parameters and
# initializes the database connection, getting the number dataset and how many
# tasks need to be completed.
#
# The most important part is after the initialization, in which the program
# computes how much was spent (considering a Job Manager of type c5.4xlarge
# and a 20GB 1000IOPS disk) and how many tasks were completed. With those
# values, it verifies if any instance is constantly going over budget,
# killing the ones that are and replacing them with instances that are not.
#
# If the experiment cannot continue due to budget constraints, then the budget
# is increased by 10%.
#
# This loop ends after the main SPITS program finishes the execution (or the
# number of tasks completed is greater or equal to the one stored in
# the database).
def main():
    input_dict = {}
    for cur in sys.argv:
        if '=' in cur:
            key, val = cur.split('=')
            input_dict.update({key: val})

    interval = float(get_from_input("interval", input_dict))

    budget = float(get_from_input("budget", input_dict))
    data_hash = get_from_input("data_hash", input_dict)
    target_nodes = int(get_from_input("nodes", input_dict))

    valid_count = int(get_from_input("valid_count", input_dict))
    if (valid_count == -1):
        valid_count = 1

    all_zones = ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e', 'us-east-1f']

    idparameters = 41

    conn = rds_operations.rds_connect()
    target_tasks = rds_operations.get_interpols(conn, idparameters, rds_operations.get_iddata(conn, data_hash))
    iddata = rds_operations.get_iddata(conn, data_hash)

    spent_sofar = 0
    tasks_sofar = 0

    in_budget = budget
    _in_budget = in_budget
    in_tasks = target_tasks

    pareto(target_nodes, data_hash, idparameters)

    tasks_str = 'TASKS PROCESSED SO FAR = {}/{}'
    money_str = 'MONEY SPENT SO FAR = {}/{} (user requested = {})'
    money_left_str = 'MONEY LEFT TO SPEND = {} (user requested = {}) | TARGET RATIO = {}'
    instances_str = 'NUMBER OF INSTANCES RUNNING = {}/{}'
    simulated_time = 'TIMENOW = {}'

    ops = instance_operations(logger)
    time_start = ops.get_jobmanager_init_time()

    ec2 = boto3.client('ec2', region_name='us-east-1')
    cloudwatch = boto3.client('cloudwatch')

    log_to_csv = 'CSV\t{}\t{}'

    time_spent = 0

    run_dict = {}
    wk_spent_sofar = 0
    jm_spent_sofar = 0
    ec2_res = boto3.resource('ec2', region_name='us-east-1')
    #time.sleep(180)
    while target_tasks > 0:
        # Update cost
        jm_diff = (datetime.utcnow() - time_start)
        jm_spent_sofar = jm_diff.total_seconds() * (0.68+0.09375) / 3600

        for key,inst in run_dict.items():
            diff = datetime.utcnow() - inst["cur_time"]
            inst["cur_time"] = datetime.utcnow()
            wk_spent_sofar += float(inst["price"]) * diff.total_seconds() / 3600
            inst["prev_valid"] = inst["valid"]
            inst["valid"] = 0

        # Verifies running instances
        instance_reservations = ops.get_instance_reservations()
        for instance in instance_reservations['Reservations']:
            instance_id = instance['Instances'][0]['InstanceId']
            instance_type = instance['Instances'][0]['InstanceType']
            instance_az = instance['Instances'][0]['Placement']['AvailabilityZone']

            ec2_instance = ec2_res.Instance(instance_id)
            init_time = datetime.strptime(ec2_instance.launch_time.strftime("%Y-%m-%dT%H:%M:%S"), "%Y-%m-%dT%H:%M:%S")

            result = cloudwatch.get_metric_statistics(Namespace='Performance',
                                                      MetricName='perf_sec',
                                                      StartTime=(datetime.today() - timedelta(minutes=2*interval)),
                                                      Dimensions=[{'Name': 'Instance Id', 'Value': instance_id},
                                                                  {'Name': 'Type', 'Value': instance_type}],
                                                      EndTime=datetime.today(),
                                                      Period=60,
                                                      Statistics=['Average'])

            tasks_completed = cloudwatch.get_metric_statistics(Namespace='Performance',
                                                      MetricName='tasks_completed',
                                                      StartTime=(datetime.today() - timedelta(minutes=2*interval)),
                                                      Dimensions=[{'Name': 'Instance Id', 'Value': instance_id},
                                                                  {'Name': 'Type', 'Value': instance_type}],
                                                      EndTime=datetime.today(),
                                                      Period=60,
                                                      Statistics=['Maximum'])

            result_stdev = cloudwatch.get_metric_statistics(Namespace='Performance',
                                                            MetricName='perf_sec_stdev',
                                                            StartTime=(datetime.today() - timedelta(minutes=2*interval)),
                                                            Dimensions=[{'Name': 'Instance Id', 'Value': instance_id},
                                                                        {'Name': 'Type', 'Value': instance_type}],
                                                            EndTime=datetime.today(),
                                                            Period=60,
                                                            Statistics=['Average'])

            if tasks_completed['Datapoints']:
                if (tasks_completed['Datapoints'][0]['Maximum']) > tasks_sofar:
                    tasks_sofar = tasks_completed['Datapoints'][0]['Maximum']

            if not instance_id in run_dict:
                if result['Datapoints'] and result_stdev['Datapoints']:
                    price = ops.get_current_spot_price(instance_type, instance_az) + 0.09375
                    performance_negative = float(result['Datapoints'][0]['Average']) - float(
                        result_stdev['Datapoints'][0]['Average'])

                    instance_dict = {"instance_id":instance_id,
                                     "instance_type":instance_type,
                                     "instance_az":instance_az,
                                     "price":price,
                                     "performance_negative":performance_negative,
                                     "init_time":init_time,
                                     "cur_time": init_time,
                                     "valid":valid_count,
                                     "prev_valid": valid_count}

                    run_dict[instance_id] = instance_dict
                else:
                    price = ops.get_current_spot_price(instance_type, instance_az) + 0.09375
                    instance_dict = {"instance_id": instance_id,
                                     "instance_type": instance_type,
                                     "instance_az": instance_az,
                                     "price": price,
                                     "performance_negative": -1,
                                     "init_time": init_time,
                                     "cur_time": init_time,
                                     "valid": valid_count,
                                     "prev_valid":valid_count}
                    run_dict[instance_id] = instance_dict
            else:
                instance_dict = run_dict[instance_id]
                instance_dict["valid"] = instance_dict["prev_valid"]

                if result['Datapoints'] and result_stdev['Datapoints']:
                    instance_dict["price"] = ops.get_current_spot_price(instance_type, instance_az) + 0.09375
                    instance_dict["performance_negative"] = float(result['Datapoints'][0]['Average']) - float(result_stdev['Datapoints'][0]['Average'])

        spent_sofar = wk_spent_sofar + jm_spent_sofar

        target_tasks = in_tasks - tasks_sofar
        budget = in_budget - spent_sofar

        target_ratio = target_tasks / budget

        logger.info(simulated_time.format(datetime.now()))
        logger.info(tasks_str.format(tasks_sofar, in_tasks))
        logger.info(money_str.format(spent_sofar, in_budget, _in_budget))
        logger.info(money_left_str.format(budget, _in_budget, target_ratio))
        logger.info(instances_str.format(len(run_dict.keys()), target_nodes))
        logger.info(log_to_csv.format(((datetime.utcnow() - time_start).total_seconds()),spent_sofar))

        logger.debug("INSTANCES RUNNING")
        for key,inst in run_dict.items():
            logger.debug(inst)

        if (target_tasks <= 0):
            break

        for key,inst in run_dict.items():
            if (inst["performance_negative"]/(inst["price"]/3600) < target_ratio or inst["performance_negative"] == -1):
                inst["valid"] -= 1
                logger.debug("DECREASING COUNTER FOR INST " + inst["instance_id"] + "(" + inst["instance_type"] + "), NOW: " + str(inst["valid"]))
            else:
                inst["valid"] = min(inst["valid"] + 1, valid_count)

            if (inst["valid"] <= 0):
                logger.debug('REMOVING INST ' + inst["instance_id"])
                ops.terminateInstance(inst["instance_id"])


        for key in list(run_dict.keys()):
            if run_dict[key]["valid"] <= 0:
                del run_dict[key]

        if (len(list(run_dict.keys())) < target_nodes):
            candidates = []

            while len(candidates) == 0:
                budget = in_budget - spent_sofar
                target_ratio = target_tasks / budget
                all_performance = rds_operations.get_interpsec_allinstances(conn, iddata, idparameters)

                for result in all_performance:
                    instance_type = result[0]
                    interpsec = result[1]
                    stddev_interpsec = result[2]

                    prices = ops.get_current_spot_price_allaz(instance_type)

                    for az in prices:
                        price = prices[az] + 0.09375
                        costperinterp = float(interpsec / (price / 3600))
                        costperinterp_stdev = float(stddev_interpsec / (price / 3600))
                        costperinterp_negative = costperinterp - costperinterp_stdev

                        instance_dict = {"instance_id": "inactive",
                                         "instance_type": instance_type,
                                         "instance_az": az,
                                         "price": price,
                                         "performance_negative": interpsec,
                                         }

                        if costperinterp_negative > target_ratio:
                            temp = [inst for inst in run_dict.values() if inst['instance_type'] == instance_type and inst['instance_az'] == az]
                            if (len(temp) == 0):
                                candidates.append(instance_dict)
                            else:
                                for inst in temp:
                                    if (inst not in candidates):
                                        candidates.append(inst)

                candidates.sort(key=operator.itemgetter('performance_negative'), reverse=True)

                if (len(candidates) == 0):
                    logger.error("IMPOSSIBLE TO RUN EXPERIMENT WITH THIS CONFIGURATION")
                    in_budget += in_budget / 10
                    logger.error("INCREASING BUDGET BY 10\% (TO " + str(in_budget) + " USD)")

            logger.debug("CANDIDATES")
            for inst in candidates:
                logger.debug(inst)

            k = 0
            counter = 0
            while len(run_dict.keys()) < target_nodes and counter < 5:
                threads = []
                num_threads = min(target_nodes - len(run_dict.keys()), int(target_nodes/5))
                # Replace instances
                for i in range(0, num_threads):
                    thr = threading.Thread(target=ops.createSpotInstanceThreads, args=(candidates[k]['instance_type'], candidates[k]['instance_az'], candidates[k]['price'],valid_count,run_dict))
                    thr.start()
                    threads.append(thr)

                for thr in threads:
                    thr.join()

                k = (k + 1) % len(candidates)
                if k == 0:
                    counter += 1

        time.sleep(interval*60)

if __name__ == "__main__":
    logger = getLogger(__name__)
    main()
