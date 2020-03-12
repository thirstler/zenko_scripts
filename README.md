Bucket clean-up and Zenko Search
================================

bucket_destruction.py:
----------------------
Fast and flexible bucket clean-up script that's useful for a number of situations.

search_bucket.py:
-----------------
Tool for searching Zenko bucket metadata using the search API.

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