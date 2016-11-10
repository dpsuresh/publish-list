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

def gmtimestamp_ms(date_str):
    utc_time = time.strptime(date_str, '%Y-%m-%d')
    epoch_time_ms = calendar.timegm(utc_time) * 1000
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

header = True
i = 1
if len(sys.argv) > i and sys.argv[i] == '--noheader':
    header = False
    i += 1

# look for from-date-YYYY-mm-dd

if len(sys.argv) > i:
    date_from = sys.argv[i]
    i += 1

# look for to-date-YYYY-mm-dd

if len(sys.argv) > i:
    date_to = sys.argv[i]
    i += 1

if date_from == 0:

    # Error. We need atleast this. Display usage message

    print 'Usage: python list.py [--noheader] from-date-YYYY-mm-dd [to-date-YYYY-mm-dd]'
    exit(-1)

# Convert date_from and date_to to gmtimestamp in milliseconds

date_from = gmtimestamp_ms(date_from)
if date_to != 0:
    date_to = gmtimestamp_ms(date_to)

# Contruct the url for timeframe date_from - date_to
# url = 'http://contentindexing.partner-publishing.global.vespa.yahooapis.com:4080/search/?start=0&count=400&format=json&yql=select%20*%20from%20sources%20contentindexing%20where%20(tags%20contains%20%22ymedia%3Atype%3Dcollection%22)%20'

url = \
    'http://contentindexing.partner-publishing.global.vespa.yahooapis.com:4080/search/?start=0&count=400&format=json&yql=select%20*%20from%20sources%20contentindexing%20where%20((tags%20contains%20%22ymedia%3Atype%3Dcollection%22)OR(tags%20contains%20%22ymedia%3Atype%3Dlist%22))%20'

# AND modified > date_from

url += 'AND%20(modified%3E%22' + str(date_from) + '%22)%20'

# AND modified < date_to

if date_to != 0:
    url += 'AND%20(modified%3C%22' + str(date_to) + '%22)%20'
url += 'ORDER%20BY%20published%20desc%3B'

url_data = urllib.urlopen(url).read()
d = json.loads(url_data)

# Print pretty version of url

if header:
    print urllib.unquote(url).decode('utf8')
    print d['root']['fields']['totalCount'], ' Lists Modified'
    print

# Collect all list id

lists = {}
children = d['root']['children']

for i in range(len(children) - 1):
    id = children[i]['fields']['uuid']
    lists[id] = 1

# For each list figure out its attributes

ccm_url_base = 'http://tools.mct.corp.yahoo.com:8080/v1/object/'
header = \
    '"List UUID",Language,Type,"Collection/List Type","Rules Type",Modified,Created,Context,"List CCM"'
if header :
    print header
for l in lists:
    ccm_url = ccm_url_base + l
    ccm = json.loads(urllib.urlopen(ccm_url).read())

    # print l

    data = {'uuid': l, 'ccm_url': ccm_url}

    # Dont operate on ccms that are bad

    if 'self' not in ccm:
        data['lang'] = 'badccm'
        data['type'] = 'badccm'
        data['collection_type'] = 'badccm'
        data['rule_type'] = 'badccm'
        data['modified'] = 'badccm'
        data['created'] = 'badccm'
        data['context'] = ''
    else:
        data['lang'] = get_lang(ccm)
        data['type'] = get_type(ccm)
        data['collection_type'] = get_collection_list_type(ccm,
                data['type'])
        data['rule_type'] = ''
        data['test'] = ''
        if data['collection_type'] == 'playlist' \
            or data['collection_type'] == 'static':
            data['rule_type'] = get_rule_type(ccm)
        data['modified'] = get_modified(ccm)
        data['created'] = get_created(ccm)
        data['context'] = get_context(ccm)

    print '{uuid},{lang},{type},{collection_type},{rule_type},{modified},{created},{context},{ccm_url}'.format(**data)

