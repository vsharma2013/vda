import json

def get_meta(event, context):
  return {
    'statusCode': 200,
    'headers': {
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    },
    'body': json.dumps('Hello from Lambda!  changed')
  }

def get_meta2(event, context):
  return get_meta(event, context)