#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2019 Nicholas Torres Okita <nicholas.okita@ggaunicamp.com>
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

# This file contains similar operations to the instance_operations however they
# are fake ones, so there is no actual instance creation or termination

from datetime import datetime
from datetime import timedelta
import csv

class pseudo_instance_operations:

    # function __init__
    # Initiliaze the class object by opening the input file which stores the
    # price at each (simulated) time. And set a initial time for the simulation
    # program to be running (in this example 15th of February of 2019).
    def __init__(self):
        self.input_f = open("log_prices.csv", "r")
        self.rd = []
        csv_dr = csv.DictReader(self.input_f, delimiter="\t")
        for row in csv_dr:
            self.rd.append(row)

        self.time_now = datetime.strptime("2019-02-15T00:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ")

    # function get_current_spot_price_allaz
    # \param instance_type: string with the name of the instance type
    # This function gets the current spot price (from a file) for an instance
    # type for all availability zones.
    def get_current_spot_price_allaz(self, instance_type):
        valid_time = datetime.strptime("2019-01-01T00:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ")
        dict = {}
        for row in self.rd:
            if (row['instance_type'] == instance_type):
                time_stamp = datetime.strptime(row['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
                if (time_stamp <= self.time_now and time_stamp >= valid_time):
                    valid_time = time_stamp
                    dict[row['az']] = float(row['price'])

        return dict

    # function get_current_spot_price
    # \param instance_type: string with the name of the instance type
    # \param az: string containing the availability zone
    # This function gets the current spot price (from a file) for an instance
    # type in an availability zone az
    def get_current_spot_price(self, instance_type, az):
        valid_time = datetime.strptime("2019-01-01T00:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ")
        price = -1
        for row in self.rd:
            if (row['instance_type'] == instance_type and row['az'] == az):
                time_stamp = datetime.strptime(row['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
                if (time_stamp <= self.time_now and time_stamp >= valid_time):
                    valid_time = time_stamp
                    price = float(row['price'])

        return price

    # function add_minutes
    # \param increase_time: time to be increased in minutes
    # Increment the current timer in increase_time minutes
    def add_minutes(self, increase_time):
        self.time_now = self.time_now + timedelta(minutes=increase_time)