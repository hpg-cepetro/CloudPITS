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

# This file contains the RDS operations to access and get information from a Relational Database Server (RDS)
# At this moment it requires that the

import pymysql
import rds_config
import sys

# function rds_connect
#
# \return conn connection object
#
# This function uses the configuration stored in the rds_config.py file to
# create a connection to a database. The connection object is then returned
# to the function caller. If there was an error while trying to connect to the
# database, the program will call sys.exit() and close.
def rds_connect():
    # Remote access to MySQL database in RDS
    rds_host = rds_config.db_host
    name = rds_config.db_username
    password = rds_config.db_password
    db_name = rds_config.db_name

    # Try connection
    try:
        conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)
    except:
        print("ERROR: Unexpected error: Could not connect to MySql instance.")
        sys.exit()

    return conn

# function get_idparameters
# \param conn: Database connection object
# \param aph: Aperture in half offsets
# \param apm: Aperture in midpoints
# \param window: Window of time samples
# \param np: Number of population members
# \param gens: Number of generations
#
# \return idparameters: key to idparameters in the database
#
# This function will access the database through the conn object and then search
# for the parameters table that has it. These parameters are mainly used for
# seismic programs, which was the SPITS program used for this prototype.
#
# If the function cannot find the paramters table with the input paramters, then
# create a new entry. At last, return the idparameters key stored.
def get_idparameters(conn, aph, apm, window, np, gens):
    idparameters = -1
    with conn.cursor() as cur:
        query = "select * from experimentos.parameters where `aph`={} and `apm`={} and `window` like {} and `np`={} and `gens`={};"
        cur.execute(query.format(aph, apm, window, np, gens))
        results = cur.fetchall()
        if len(results) == 0:
            query = "insert into experimentos.parameters(`aph`,`apm`,`window`,`np`,`gens`) values({},{},{},{},{});"
            cur.execute(query.format(aph, apm, window, np, gens))
            cur.execute("select LAST_INSERT_ID();")
            results = cur.fetchall()
            idparameters = results[0][0]
        else:
            idparameters = results[0][0]
        conn.commit()
    conn.commit()

    return idparameters

# function get_iddata
# \param conn: Database connection object
# \param data_hash: md5sum of the data set being used
#
# \return iddata
#
# This function will return the iddata from the table that stores the data set,
# returning -1 if the table was not found.
def get_iddata(conn, data_hash):
    iddata = -1
    with conn.cursor() as cur:
        query = "select * from experimentos.data where hash='{}'"
        cur.execute(query.format(data_hash))
        results = cur.fetchall()
        if len(results) == 0:
            print("Data wasn't found")
        else:
            iddata = results[0][0]
        conn.commit()
    conn.commit()

    return iddata

# function get_idexperiment
# \param conn: Database connection object
# \param iddata: id for the data set being used
# \param idparameters: id for the set of parameters being used
# \param instance_type: string containing the instance type
#
# \return idexperiment
#
# Using the previously gotten iddata and idparameters, plus the instance_type
# this functino will return an experiment table (which is a table that contains
# experiment informations for a given instance in a set of parameters). If the
# table does not exist, create a new one. Then return the table id.
def get_idexperiment(conn, iddata, idparameters, instance_type):
    idexperiment = -1
    with conn.cursor() as cur:
        query = "select * from experimentos.experiment where data_iddata={} and parameters_idparameters={} and instance_name='{}'"
        cur.execute(query.format(iddata, idparameters, instance_type))
        results = cur.fetchall()
        if len(results) == 0:
            query = "insert into experimentos.experiment(`data_iddata`,`parameters_idparameters`,`instance_name`) values({},{},'{}');"
            print(query.format(iddata, idparameters, instance_type))
            cur.execute(query.format(iddata, idparameters, instance_type))
            cur.execute("select LAST_INSERT_ID();")
            results = cur.fetchall()
            idexperiment = results[0][0]
        else:
            idexperiment = results[0][0]
        conn.commit()
    conn.commit()

    return idexperiment

# function insert_interpsec
# \param conn: Database connection object
# \param idexperiment: id for the experiment
# \param interpsec: performance measurement
#
# This function accesses the database using the connection object conn, then
# it inserts a new performance entry for a given experiment.
def insert_interpsec(conn, idexperiment, interpsec):
    with conn.cursor() as cur:
        query = "insert into experimentos.interpsec(`interpsec`,`experiment_idperformance`) values({},{});"
        cur.execute(query.format(interpsec, idexperiment))
    conn.commit()

# function insert_interpols
# \param conn: Database connection object
# \param idparametrs: id for the parameters
# \param iddata: id for the data set
# \param interpols: number of tasks completed
#
# This function accesses the database using the connection object conn, then
# it inserts the total amount of tasks completed for the pair of parameters
# and data set.
def insert_interpols(conn, idparameters, iddata, interpols):
    with conn.cursor() as cur:
        query = "insert into experimentos.interpols(`parameters_idparameters`,`data_iddata`, `interpols`) values({},{},{});"
        cur.execute(query.format(idparameters, iddata, interpols))
    conn.commit()

# function get_interpols
# \param conn: Database connection object
# \param idparametrs: id for the parameters
# \param iddata: id for the data set
#
# \return Number of tasks to be completed for a pair of data set and parameters
#
# This function simply accesses the database via the conn object and gets the
# number of tasks for the pair iddata and idparameters.
def get_interpols(conn, idparameters, iddata):
    with conn.cursor() as cur:
        query = "select avg(interpols) from experimentos.interpols where `parameters_idparameters`={} and `data_iddata`={};"
        cur.execute(query.format(idparameters, iddata))
        results = cur.fetchall()
        conn.commit()
    conn.commit()

    return results[0][0]

# function get_interpsec_allinstances
# \param conn: Database connection object
# \param iddata: id for the data set
# \param idparametrs: id for the parameters
#
# \return Performance measurements for all instances
#
# This function accesses the database via the conn object and runs a query to
# return the performance information (stored as interpsec) for all instances
# types that executed the data with a set of parameters.
def get_interpsec_allinstances(conn, iddata, idparameters):
    with conn.cursor() as cur:
        query = """select instance_name, avg(interpsec) as interpsec, stddev(interpsec) as stddev, min(interpsec) as min_interpsec,
            max(interpsec) as max_interpsec, T.name, T.hash
            from experimentos.interpsec inner join experimentos.experiment on experiment_idperformance=idperformance
            inner join experimentos.data T on data_iddata=T.iddata
            where iddata={} and parameters_idparameters={}
            group by T.name, instance_name
            order by T.name, interpsec;
        """

        cur.execute(query.format(iddata, idparameters))
        results = cur.fetchall()
        conn.commit()
    conn.commit()

    return results

# function get_interpsec_allinstances
# \param conn: Database connection object
# \param iddata: id for the data set
# \param idparametrs: id for the parameters
# \param instance_type: string containing an instance type
#
# \return Performance measurements for an instance
#
# This function accesses the database via the conn object and runs a query to
# return the performance information (stored as interpsec) for an input instance
# type that executed the data with a set of parameters.
def get_interpsec(conn, iddata, idparameters, instance_type):
    with conn.cursor() as cur:
        query = """select instance_name, avg(interpsec) as interpsec, stddev(interpsec) as stddev, min(interpsec) as min_interpsec,
                max(interpsec) as max_interpsec, T.name, T.hash
                from experimentos.interpsec inner join experimentos.experiment on experiment_idperformance=idperformance
                inner join experimentos.data T on data_iddata=T.iddata
                where iddata={} and parameters_idparameters={} and instance_name="{}"
                group by T.name, instance_name
                order by T.name, interpsec;
        """

        cur.execute(query.format(iddata, idparameters, instance_type))
        results = cur.fetchall()
        conn.commit()
    conn.commit()

    return results