Set of scripts for dealing with Zenko and S3

bucket_destruction.py:  Fast and flexible bucket clean-up script that's handy
                        for a number of situations. 

crr_failure_trigger.py: This will send a mail to a configured address when 
                        there are multiple permanenet CRR failures to a 
                        location.

get_group_lag.py:       Just displays the lag in partitions for location
                        topics.

list_crr_backlog.py:    Displays objects in back-log for a given location. It
                        is better to use MD search to do this but this uses
                        kafka directly

reset_redis.py:         Resets pending and failed counters to clean-up Orbit 
                        UI in case it gets out of sync during testing.

search_bucket.py:       Tool for searching Zenko buckets. Again, there's a 
                        nodejs tool (that's also installed in the cloudservers)
                        for this but a python implementation seemed like a good
                        idea