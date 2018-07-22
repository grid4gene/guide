#!/usr/bin/env python

# Copyright (c) 2017-2018 Breakthrough Genomics Ltd. (Martin Triska)
#
# Following code is proprietary and any use without explicit permission
# from Breakthrough Genomics Ltd. is forbidden

import pipeline2

import sys

p = pipeline2.pipeline(sys.argv[1], sys.argv[2], sys.argv[3])
p.run_pipeline()
