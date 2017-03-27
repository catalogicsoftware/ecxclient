import imp
import httplib
import json
import logging
from optparse import OptionParser
import time
import csv
client = imp.load_source('client', '../ecxclient/sdk/client.py')

logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)

parser = OptionParser()
parser.add_option("--user", dest="username", help="ECX Username")
parser.add_option("--pass", dest="password", help="ECX Password")
parser.add_option("--host", dest="host", help="ECX Host, (ex. https://172.20.58.10:8443)")
parser.add_option("--job", dest="jobname", help="ECX Job Name")
parser.add_option("--swf", dest="workflow", help="Storage Workflow name for Job")
parser.add_option("--run", dest="runornot", help="Run job or print log from last run (true|false)")
parser.add_option("--dest", dest="destination", help="Destination for logfile (ex. /logs/log1.csv")
(options, args) = parser.parse_args()

session = client.EcxSession(options.host, options.username, options.password)

def validate_input():
    if(options.username is None or options.password is None or options.host is None or
       options.job is None or options.dest is None):
        print "Invalid input, use -h switch for help"
        sys.exit(2)

def get_jobs_list():
    jobs = client.EcxAPI(session, 'job').list()
    return jobs

def find_job_in_list(jobslist):
    for job in jobslist:
        if(job['name'] == options.jobname):
            return job
    logger.info("No job found with name %d" % options.jobname)
    sys.exit(2)

def get_swf_for_job(job):
    swfs = client.EcxAPI(session, 'policy').get(resid=job['policyId'])
    for swf in swfs:
        if (swf['name'] == options.workflow):
            return swf
    logger.info("No workflow found with name %d" % options.workflow)
    sys.exit(2)

def run_job_and_wait_for_completion(job, swf=None):
    if (swf is not None):
        run = client.JobAPI(session).run(job['id'], swf['id'])
    else:
        run = client.JobAPI(session).run(job['id'])
    logger.info("Running job... please wait.")
    time.sleep(5)
    job = update_job(job['id'])
    while (job['lastSessionStatus'] == "RUNNING"):
        time.sleep(5)
        job = update_job(job['id'])
    logger.info("Job finished.")
    
def update_job(jobid):
    return client.EcxAPI(session, 'job').get(resid=jobid)

def output_logs(job):
    return client.JobAPI(session).get_log_entries(job['lastrun']['sessionId'])

def parse_logs(logs):
    logger.info("Writing logs to: %s" % options.destination)
    logfile = csv.writer(open(options.destination, "wb+"))
    logfile.writerow(["TimeStamp", "Message"])
    for line in logs:
        logfile.writerow([time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(line['logTime']/1000)),
            line['message']])

session.login()

jobslist = get_jobs_list()
job = find_job_in_list(jobslist)
if (options.runornot == 'true'):
    if (options.workflow is not None):
        swf = get_swf_for_job(job)
        run_job_and_wait_for_completion(job, swf)
    else:
        run_job_and_wait_for_completion(job)

    
job = update_job(job['id'])
logs = output_logs(job)
parse_logs(logs)

session.delete('endeavour/session/')
