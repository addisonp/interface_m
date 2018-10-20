import datetime

import arrow
import pytz
import tzlocal


def string_to_date(adict):
    """ Recursively search through a dict with nested lists and dicts
    for certain elements and converts them from string to datetime

    :param adict: dictionary
    :return: updated dictionary (though not really needed since we are passing by reference)
    """
    for key in adict.keys():
        if key in ["AuditoriumInstallDate", "InstallDate", "VPFStartDate", "IssueDate"]:
            if adict[key] is not None:
                adict[key] = arrow.get(adict[key]).datetime
        elif type(adict[key]) is dict:
            string_to_date(adict[key])
        elif type(adict[key]) is list:
            for item in adict[key]:
                if type(item) is dict:
                    string_to_date(item)
    return adict


def date_to_string(adict):
    """ Recursively searches through a dict with nested lists and dicts
    for certain elements and converts them from datetime to string

    :param adict: dictionary
    :return:  updated dictionary (though not really needed since we are passing by reference)
    """
    for key in adict.keys():
        if key in ["AuditoriumInstallDate", "InstallDate", "VPFStartDate"]:
            if adict[key] is not None:
                adict[key] = adict[key].date().isoformat()
        elif key in ["IssueDate"]:
            adict[key] = adict[key].strftime("%Y-%m-%dT%H:%M:%S")
        elif type(adict[key]) is dict:
            date_to_string(adict[key])
        elif type(adict[key]) is list:
            for item in adict[key]:
                if type(item) is dict:
                    date_to_string(item)
    return adict


def find_all_in_flm(keywords=[], adict={}, return_list=[]):
    """Recursively searches through a dict with nested lists and dicts
    for certain elements and searches for specific keywords and saves that data

    :param keywords: a list of strings
    :param adict: dictionary that contains nested dicts/lists
    :param return_list: return list of matches to the keywords
    :return: a list of matches to the keywords
    """

    for key in adict.keys():
        if key in keywords:
            if adict[key] is not None:
                return return_list.append(adict[key])
        elif type(adict[key]) is dict:
            find_all_in_flm(keywords, adict[key])
        elif type(adict[key]) is list:
            for item in adict[key]:
                if type(item) is dict:
                    find_all_in_flm(keywords, item)
    return return_list

def localtz_now():
    utc_now = datetime.datetime.utcnow()
    local_tz = tzlocal.get_localzone()
    return utc_now.replace(tzinfo=pytz.utc).astimezone(local_tz)


