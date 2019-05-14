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

# This module simulates the execution of a SPITS program given Spot instance prices stored in a file

import logging
import sys
import time
from datetime import datetime
import operator
from instance_operations import instance_operations
from pseudo_instance_operations import pseudo_instance_operations
import rds_operations
import random

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
    string_name = "simulation{}.log"
    handler = logging.FileHandler(string_name.format(now.strftime("%Y%m%d%H%M%S")))
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
    fake_ops = pseudo_instance_operations()
    ops = instance_operations(logger)

    jm_perf = 0
    for result in all_performance:
        if result[0] == "c5.4xlarge":
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
            price = ops.get_current_spot_price(instance_type, az)

            if (price < best_price and price > 0):
                best_price = price + 0.09375
                best_az = az

        costperinterp = float(interpsec / (best_price / 3600))
        string = "{}\t{}\t{}"
        time_to_run = target_tasks / (jm_perf + interpsec * target_nodes * (1-((target_nodes-1)/1000.0)))
        price_to_pay = time_to_run * target_nodes * best_price / 3600 + time_to_run * 0.68 / 3600
        logger.info(string.format(instance_type,time_to_run,price_to_pay))

# function main
#
# \param (command line input) interval : time to wait for the next iteration in seconds
# \param (command line input) time_skip : time to skip in simulation in minutes
# \param (command line input) failure_create : failure rate (percentage) when creating an instance
# \param (command line input) failure_execute : failure rate (percentage) while instance is running
# \param (command line input) budget : budget in dollars to complete the execution
# \param (command line input) data_hash : dataset hash stored in the database
# \param (command line input) nodes : number of instances running
# \param (command line input) target_tasks : number of tasks to be executed (if empty, gets from database from
# data_hash)
# (id parameters is set as default to 41, can be changed in code)
#
# Before the iterations loop, this function sets the input parameters and
# initializes the database connection, getting the id number for the dataset
# and how many tasks need to be completed.
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
# The differences between the simulation and the real module (to_execute.py) is
# that the simulation considers that there is an user defined chance of an
# instance failing to be created (defined by failure_create), to simulate an
# instance unavailability from the Spot and an instance failing during execution
# (defined by failure_exec), to simulate an instance being terminated by the
# provider. Furthermore, it allows the user to define the prices via a file
# (log_prices.py) so that they can see how the algorithm behaves given price
# changes. At last, to allow the user to simulate the execution without waiting
# for the actual execution time, it is possible to set a time_skip, so that the
# module will simulate how much of the task was completed (with a random
# oscillation of 10% and performance penalty of 0.1% with an increased number of
# instances) and how much was spent.
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
    time_skip = float(get_from_input("time_skip", input_dict))
    failure_create = float(get_from_input("failure_create", input_dict))
    failure_exec = float(get_from_input("failure_exec", input_dict))

    list_running = []
    budget = float(get_from_input("budget", input_dict))
    data_hash = get_from_input("data_hash", input_dict)
    target_nodes = int(get_from_input("nodes", input_dict))

    all_zones = ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e', 'us-east-1f']

    idparameters = 41

    conn = rds_operations.rds_connect()
    target_tasks = float(get_from_input("target_tasks", input_dict))
    if (target_tasks == -1):
        target_tasks = rds_operations.get_interpols(conn, idparameters, rds_operations.get_iddata(conn, data_hash))
    iddata = rds_operations.get_iddata(conn, data_hash)

    spent_sofar = 0
    wk_spent_sofar = 0
    jm_spent_sofar = 0
    tasks_sofar = 0

    in_budget = budget
    _in_budget = in_budget
    in_tasks = target_tasks

    fake_ops = pseudo_instance_operations()
    ops = instance_operations(logger)

    pareto(target_nodes, data_hash, idparameters)
    jm_cost = 0.68
    jm_interpsec = rds_operations.get_interpsec(conn, iddata, idparameters, "c5.4xlarge")

    tasks_str = 'TASKS PROCESSED SO FAR = {}/{}'
    spent_str = 'HOW MONEY WAS SPENT (TOTAL = JM + WK) = {} = {} + {}'
    money_str = 'MONEY SPENT SO FAR = {}/{} (user requested = {})'
    instances_str = 'NUMBER OF INSTANCES RUNNING = {}/{}'
    simulated_time = 'SIMULATED TIMENOW = {}'

    log_to_csv = 'CSV\t{}\t{}'

    time_spent = 0

    while target_tasks > 0:
        negative_bias = (len(list_running)-1)/1000
        for inst in list_running:
            price = ops.get_current_spot_price(inst[1], inst[2]) + 0.09375
            wk_spent_sofar += price * time_skip / 60

            coin_toss = random.random()
            if (coin_toss < failure_exec):
                logger.debug('REMOVING INST ' + inst[1] + ' FOR RANDOM FAILURE (' + str(coin_toss) + '/' + str(
                    failure_exec) + ')')
                list_running.remove(inst)
            else:
                tasks_sofar += inst[8] * random.uniform(0.9 - negative_bias, 1.1 - negative_bias) * time_skip * 60

        tasks_sofar += random.uniform(jm_interpsec[1] - jm_interpsec[2], jm_interpsec[1] + jm_interpsec[2]) * time_skip * 60
        jm_spent_sofar += 0.68 * time_skip / 60

        spent_sofar = wk_spent_sofar + jm_spent_sofar

        target_tasks = in_tasks - tasks_sofar
        budget = in_budget - spent_sofar

        logger.info(simulated_time.format(fake_ops.time_now))
        logger.info(tasks_str.format(tasks_sofar, in_tasks))
        logger.info(spent_str.format(spent_sofar, jm_spent_sofar, wk_spent_sofar))
        logger.info(money_str.format(spent_sofar, in_budget, _in_budget))
        logger.info(instances_str.format(len(list_running), target_nodes))
        logger.info(log_to_csv.format(time_spent/60,spent_sofar))

        logger.debug("INSTANCES RUNNING")
        for inst in list_running:
            logger.debug("(" + inst[1] + "," + inst[2] + "," + str(inst[3]) + "," + str(inst[8]) + ")")

        if (target_tasks <= 0):
            break

        target_ratio = target_tasks / budget

        old_list = list_running
        list_running = []

        for inst in old_list:
            price = ops.get_current_spot_price(inst[1], inst[2]) + 0.09375
            if (inst[8]/(price/3600) >= target_ratio):
                list_running.append(inst)
            else:
                logger.debug('REMOVING INST ' + inst[1])

        if (len(list_running) < target_nodes):
            candidates = []

            while len(candidates) == 0:
                budget = in_budget - spent_sofar
                target_ratio = target_tasks / budget
                all_performance = rds_operations.get_interpsec_allinstances(conn, iddata, idparameters)
                for result in all_performance:
                    instance_type = result[0]
                    interpsec = result[1]
                    stddev_interpsec = result[2]

                    # prices = instance_operations.get_current_spot_price_allaz(ec2, instance_type)

                    for az in all_zones:
                        price = ops.get_current_spot_price(instance_type, az) + 0.09375
                        costperinterp = float(interpsec / (price / 3600))
                        costperinterp_stdev = float(stddev_interpsec / (price / 3600))
                        costperinterp_positive = costperinterp + costperinterp_stdev
                        costperinterp_negative = costperinterp - costperinterp_stdev
                        tuple = (
                        "inactive", instance_type, az, price, costperinterp, costperinterp_stdev, costperinterp_negative,
                        costperinterp_positive, interpsec)

                        if costperinterp_negative > target_ratio:
                            if (instance_type != "p3.2xlarge"):
                                candidates.append(tuple)

                candidates.sort(key=operator.itemgetter(8), reverse=True)
                logger.debug(candidates)

                if (len(candidates) == 0):
                    logger.error("IMPOSSIBLE TO RUN EXPERIMENT WITH THIS CONFIGURATION")
                    in_budget += in_budget / 10
                    logger.error("INCREASING BUDGET BY 10\% (TO " + str(in_budget) + " USD)")

            k = 0
            while len(list_running) < target_nodes:
                for i in range(0,(int(target_nodes/5))):
                    if (random.random() > failure_create):
                        list_running.append(candidates[k])
                    else:
                        logger.debug("FAILED TO CREATE INSTANCE OF TYPE " + candidates[k][1])
                        k = (k + 1) % len(candidates)

                    if len(list_running) >= target_nodes:
                        break
                k = (k + 1) % len(candidates)

        time.sleep(interval)
        fake_ops.add_minutes(time_skip)
        time_spent += time_skip

if __name__ == "__main__":
    logger = getLogger(__name__)
    main()

