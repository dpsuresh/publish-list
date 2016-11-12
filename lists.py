#!/usr/bin/python
# -*- coding: utf-8 -*-

# Report on the lists modified / created between two dates

import sys
import json
import urllib
import uuid
import time
import datetime
import calendar


# date time helper functions
# ----------------------------------------------------------------------

def gmtimestamp_ms(dt):
    #d = datetime.strptime(date_str, '%Y-%m-%d')
    epoch_time_ms = calendar.timegm(dt.timetuple()) * 1000
    return epoch_time_ms


# ccm access functions
# ----------------------------------------------------------------------

# get_lang : get lang from self->_lang

def get_lang(ccm):
    return ccm['self'].get('_lang', 'default')


# get_type : get type of ccm from self->tags[ymedia:type]
# This can return usually ["list", "collection"]
# but sometimes the CCM has only one of them or none

def get_type(ccm):
    type = []
    tags = ccm['self']['_tags']
    for i in range(len(tags)):
        if tags[i].startswith('ymedia:type='):
            index = tags[i].find('=') + 1
            type.append((tags[i])[index:])

    if 'list' in type and 'collection' in type:
        typestr = 'list+collection'
    elif len(type) == 0:
        typestr = 'empty'
    else:
        typestr = 'only:' + type[0]
    return typestr


def get_collection_list_type(ccm, list_type):
    result = 'default'
    if list_type == 'only:list':

        # For lists look for list_types

        tags = ccm['self']['_tags']
        lookfor = 'ymedia:list_type='
    else:

        # For collections look for collection_type

        if 'yahoo-media:collection' not in ccm:
            return 'badccm'
        tags = ccm['yahoo-media:collection']['_tags']
        lookfor = 'ymedia:collection_type='

    # Parse tags and find type

    for i in range(len(tags)):
        if tags[i].startswith(lookfor):
            index = tags[i].find('=') + 1
            result = (tags[i])[index:]
    return result


def get_rule_type(ccm):
    if 'yahoo-media:asset-list-rules' not in ccm:
        return 'empty'
    if 'rules' not in ccm['yahoo-media:asset-list-rules']:
        return 'empty'
    type = 'fixed'
    rules = ccm['yahoo-media:asset-list-rules']['rules']
    query_count = 0
    for r in rules:
        if 'query' in r:
            query_count += 1
    if query_count > 0:
        type = 'query ' + str(query_count)
    return type


def get_modified(ccm):
    if '_rev' not in ccm['self']:
        return ''
    m_uuid = uuid.UUID(ccm['self']['_rev'])
    ts = datetime.datetime.fromtimestamp((m_uuid.time
            - 0x01b21dd213814000L) * 100 / 1e9)
    return ts.date()


def get_created(ccm):
    if 'yahoo-media:keys' not in ccm:
        return ''
    m_uuid = uuid.UUID(ccm['yahoo-media:keys']['_rev'])
    ts = datetime.datetime.fromtimestamp((m_uuid.time
            - 0x01b21dd213814000L) * 100 / 1e9)
    return ts.date()


def get_context(ccm):

    # check context cache

    context_uuid = ccm['self']['_context']
    if context_uuid in context_cache:
        return context_cache[context_uuid]

    # get the context ccm

    ccm_url = 'http://tools.mct.corp.yahoo.com:8080/v1/object/' \
        + context_uuid
    context_ccm = json.loads(urllib.urlopen(ccm_url).read())

    # figure out the name

    contextname = context_uuid
    if 'ca_admin:context' in context_ccm:
        if 'name' in context_ccm['ca_admin:context']:
            contextname = context_ccm['ca_admin:context']['name']
        elif 'description' in context_ccm['ca_admin:context']:
            contextname = context_ccm['ca_admin:context']['description']

    # update context cache

    context_cache[context_uuid] = contextname
    return contextname


# MAIN
# --------------------------------------------------------------------

# context cache

context_cache = {}

# URL

date_from = 0
date_to = 0

# Argument Parsing

# look for --noheader

show_header = True
i = 1
if len(sys.argv) > i and sys.argv[i] == '--noheader':
    show_header = False
    i += 1

# look for from-date-YYYY-mm-dd

if len(sys.argv) > i:
    date_from = sys.argv[i]
    i += 1

# look for to-date-YYYY-mm-dd

if len(sys.argv) > i:
    date_to = sys.argv[i]
    i += 1

if date_from == 0 or date_to == 0:
    # Error. We need atleast this. Display usage message
    print 'Usage: python lists.py from-date-YYYY-mm-dd to-date-YYYY-mm-dd'
    exit(-1)

lists = {}
daysdelta = datetime.timedelta(days=4)
dt_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
dt_to = datetime.datetime.strptime(date_to, "%Y-%m-%d")

di = dt_from
while di < dt_to :
    # get list from di to di+days5
    di_from = di
    di_to = di_from + daysdelta
    if di_to > dt_to :
        di_to = dt_to
    
    # XXX DEBUG
    print di_from, di_to
    
    # Convert date_from and date_to to gmtimestamp in milliseconds
    di_from_ms = gmtimestamp_ms(di_from)
    di_to_ms = gmtimestamp_ms(di_to)

    # Contruct the url for timeframe di_from_ms - di_ti_ms
    url = \
        'http://contentindexing.partner-publishing.global.vespa.yahooapis.com:4080/search/?start=0&count=400&format=json&yql=select%20*%20from%20sources%20contentindexing%20where%20((tags%20contains%20%22ymedia%3Atype%3Dcollection%22)OR(tags%20contains%20%22ymedia%3Atype%3Dlist%22))%20'
    url += 'AND%20(modified%3E%22' + str(di_from_ms) + '%22)%20'
    url += 'AND%20(modified%3C%22' + str(di_to_ms) + '%22)%20'
    # XXX Remove order by as it is gives inaccurate results
    url += 'ORDER%20BY%20published%20desc%3B'

    url_data = urllib.urlopen(url).read()
    d = json.loads(url_data)
    
    totalCount = d['root']['fields']['totalCount']
    children = d['root']['children']

    if totalCount == 0:
        print 'No results found!'
        exit(-1)

    if totalCount > len(children):
        print 'WARNING: Max count exceeded. ', totalCount, \
            ' lists Modified. But only ', len(children), ' listids returned.'
        print "WARNING: Reduce timerange to get full list."
        print 

    # Print pretty version of url
    if show_header:
        print "Date range: ", di_from, " to ", di_to
        print urllib.unquote(url).decode('utf8')
        print totalCount, ' Lists Modified'
        print

    # Collect all list id
    for i in range(len(children) - 1):
        id = children[i]['fields']['uuid']
        lists[id] = 1
        
    di = di_to

# For each list figure out its attributes

if show_header:
    print '"List UUID",Language,Type,"Collection/List Type","Rules Type",Modified,Created,Context,"List CCM"'

for l in lists:
    ccm_url = 'http://tools.mct.corp.yahoo.com:8080/v1/object/' + l
    ccm = json.loads(urllib.urlopen(ccm_url).read())

    # print l

    data = {'uuid': l, 'ccm_url': ccm_url, 'lang': 'badccm', 'type' : 'badccm',
            'collection_type': '', 'rule_type':'', 'modified': '', 'created': '', 'context': ''}

    # Dont operate on ccms that are bad

    if 'self' in ccm:
        data['lang'] = get_lang(ccm)
        data['type'] = get_type(ccm)
        data['collection_type'] = get_collection_list_type(ccm, data['type'])
        if data['collection_type'] in {'playlist', 'static'}:
            data['rule_type'] = get_rule_type(ccm)
        data['modified'] = get_modified(ccm)
        data['created'] = get_created(ccm)
        data['context'] = get_context(ccm)

    print '{uuid},{lang},{type},{collection_type},{rule_type},{modified},{created},{context},{ccm_url}'.format(**data)

