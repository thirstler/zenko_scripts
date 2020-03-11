Set of scripts for dealing with Zenko and S3

bucket_destruction.py:  Fast and flexible bucket clean-up script that's handy
                        for a number of situations. 

get_group_lag.py:       Just displays the lag in partitions for location
                        topics.

list_crr_backlog.py:    Displays objects in back-log for a given location. It
                        is better to use MD search to do this but this uses
                        kafka directly

reset_redis.py:         Resets pending and failed counters to clean-up Orbit 
                        UI in case it gets out of sync during testing.

search_bucket.py:       Tool for searching Zenko bucket metadata using the
                        search API. You're welcome.