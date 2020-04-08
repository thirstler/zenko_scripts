Utilities related to S3 and Scality Zenko
=========================================

search_bucket.py:
-----------------
Command-line tool for using the Zenko search API on Zenko buckets.

tagtool.py
----------
Command-line tool for mass-tagging of objects. Includes the ability to append
tags, remove specific tags or simply apply tags. Takes input from a keylist
file (or stdin).

bucket_destruction.py:
----------------------
Bucket clean-up tool. Useful because you can target versions, markers or 
everything independently. Works well for life-cycling versioned buckets. Also
good for simply blowing everything away (objects and unfinished MPUs) for easy
bucket removal.

Odds and Ends
=============

The following scripts are for dealing with maintenance or debugging
of a Zenko deployment.

get_group_lag.py:
-----------------
Just displays the lag in kafka partitions for specified location
topic. You can list available locations as well. You might use this
to confirm you're not behind on any backbeat related tasks. Or you 
might used it to make sure the queues are clear before you try and
do something stupid.

reset_redis.py:
---------------
Resets pending and failed counters to clean-up Orbit UI in case it
gets out of sync during testing. Make sure there's no lag in the 
queues (see get_group_lay.py) before you use this.

list_crr_backlog.py:
--------------------

Displays objects in back-log for a given location. It is better to
use MD search to do this but this uses kafka directly just in case.
This isn't terribly useful unless you don't have access to Orbit or
a search utility.