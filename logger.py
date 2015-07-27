
from syslog import openlog, syslog, LOG_INFO, LOG_ERR, LOG_WARNING, LOG_DEBUG

def set_logname(s):
    openlog(s)

def warning(s):
    syslog(LOG_WARNING, s)

def error(s):
    syslog(LOG_ERR, s)

def info(s):
    syslog(LOG_INFO, s)

def debug(s):
    syslog(LOG_DEBUG, s)
