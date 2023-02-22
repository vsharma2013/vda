import json
import boto3

bucket = 'zvissh-us-east-1'
region = 'us-east-1'

s3 = boto3.client('s3', region_name=region)
sm = boto3.client('sagemaker', region_name=region)
ddb = boto3.client('dynamodb', region_name=region)
cw = boto3.client('logs', region_name=region)

headers = {
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT'
}

def get_meta(event, context):
  key = event['queryStringParameters']['key']
  params = event['queryStringParameters']['params']
  result = 'none'
  if key == 'cstate':
      result = get_current_state()
  if key == 'logs':
      result = get_logs(params)

  # TODO implement
  return {
      'statusCode': 200,
      'headers': headers,
      'body': json.dumps(result)
  }

def get_current_state():
  eps = get_end_point()
  jobs = get_training_jobs()
  jobs = list(filter(lambda x: x['TrainingJobStatus'] == 'Completed', jobs))
  res = list()
  for job in jobs:
      js = sm.describe_training_job(TrainingJobName=job['TrainingJobName'])
      mtx = js['FinalMetricDataList']
      metrics = ['validation:binary_classification_accuracy', 'validation:roc_auc_score', 'validation:recall',
                  'train:accuracy', 'validation:accuracy']
      amtx = list(filter(lambda x: x['MetricName'] in metrics, mtx))
      for m in amtx:
          job[m['MetricName']] = m['Value']
      res.append(job)
  for r in res:
      for k, v in r.items():
          if 'Time' in k:
              r[k] = f'{v}'
  for k, v in eps.items():
          if 'Time' in k:
              eps[k] = f'{v}'
  models = ddb.scan(TableName = 'Models')['Items']
  models.sort(key = lambda x: x['timestamp']['S'])
  v = list(models[-1].values())
  cstatus = {
      'status': v[0]['S'],
      'job_name': v[1]['S'],
      'timestamp': v[3]['S']
  }
  return {
      'end_point': eps,
      'jobs': res,
      'cstatus': cstatus
  }

def get_logs(job_name):
    streams = cw.describe_log_streams(logGroupName = '/aws/sagemaker/TrainingJobs')
    streams2 = list(filter(lambda x: x['logStreamName'].startswith(job_name), streams['logStreams']))
    res = list()
    for s in streams2:
        start_query_response = cw.get_log_events(
            logGroupName='/aws/sagemaker/TrainingJobs',
            logStreamName=s['logStreamName'],
            startTime=s['creationTime'],
            endTime=s['lastIngestionTime'])
        res.append(start_query_response)
    return json.dumps(res)

def get_training_jobs():
    jobs = list()
    res = sm.list_training_jobs(SortBy='CreationTime', SortOrder='Descending')
    jobs.extend(res['TrainingJobSummaries'])
    while 'NextToken' in res and res['NextToken']:
        res = sm.list_training_jobs(SortBy='CreationTime', SortOrder='Descending', NextToken=res['NextToken'])
        jobs.extend(res['TrainingJobSummaries'])
    return jobs
    
def get_end_point():    
    eps = sm.list_endpoints(SortBy='CreationTime', SortOrder='Descending')['Endpoints']
    eps2 = list(filter(lambda x: 'FMD-1' in x['EndpointName'], eps))
    return eps2[0]
  

def get_s3_upload_ps_url(event, context):
  print(json.dumps(event))
  user = event['queryStringParameters']['user']
  
  presigned_upload_url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': bucket,
            'Key': user,
            'ContentType': 'image/png',
            'Expires': 3600
        }
    )
  
  res = {
      'statusCode': 200,
      'headers': headers,
      'body': json.dumps(presigned_upload_url)
  }
  
  return res