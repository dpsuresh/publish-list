# publish-list
Publish list count


How to run a month of data - September
--------------------------------------
```
C02NW2TYG5RP-lm:publish-list kduddi$ python lists.py 2016-09-01 2016-10-01 > sep.csv
```
The code will run 4 days at a time to make sure each run is under 400 modified lists as content index won't return more than 400 lists.