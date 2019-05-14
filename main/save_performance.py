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

# This file script stores performance information to a Relational Database Server (RDS) database.
# To store the information the experiment configuration should be passed as input by the command line:
# aph = argv[1]
# apm = argv[2]
# window = argv[3]
# np = argv[4]
# gens = argv[5]
# data_hash = argv[6]
# performance = argv[7]

import logging
import sys
import requests
import rds_operations

# function getInstanceType
# \return String containing instance type
# This function simply requests an AWS local URL to get its instance type
def getInstanceType():
    response = requests.get('http://169.254.169.254/latest/meta-data/instance-type')
    output = response.text
    return str(output)

# function main
# \param (command line argument) aph: aperture in half offsets
# \param (command line argument) apm: aperture in midpoints
# \param (command line argument) window: time window
# \param (command line argument) np: Number of members in population
# \param (command line argument) gens: Number of generations
# \param (command line argument) data_hash: Data md5sum
# \param (command line argument) performance: Performance measurement
#
# This function accesses the MySQL database using rds_operations and adds a
# performance measurement relating to an experiment. If the performance
# measurement is zero, then it will simply ignore the value.
#
# This is an example code and can be modified to better suit the user needs.
# However, keep in mind that others parts of the code will need to be modified
# as well, namely rds_operations.py, to_execute.py and simulation.py.
def main():
    # Remote access to MySQL database in RDS
    conn = rds_operations.rds_connect()

    # Get parameters from input
    aph = float(sys.argv[1])
    apm = float(sys.argv[2])
    window = float(sys.argv[3])
    np = int(sys.argv[4])
    gens = int(sys.argv[5])

    # Get parameters id
    idparameters = rds_operations.get_idparameters(conn, aph, apm, window, np, gens)

    # Get data id from hash
    data_hash = sys.argv[6]
    iddata = rds_operations.get_iddata(conn, data_hash)

    # Gets current instance type and performance
    instance_type = getInstanceType()
    interpsec = float(sys.argv[7])

    # Gets experiment id (with data, parameters and instance type)
    idexperiment = rds_operations.get_idexperiment(conn, iddata, idparameters, instance_type)

    # Insert performance measurement to the database
    # Does not insert if it was zero
    if (interpsec != 0):
        rds_operations.insert_interpsec(conn, idexperiment, interpsec)


if __name__ == "__main__":
    logger = logging.getLogger()
    main()
