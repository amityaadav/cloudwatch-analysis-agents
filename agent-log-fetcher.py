import boto3
import json
from datetime import datetime, timedelta

logs_client = boto3.client('logs')

def lambda_handler(event, context):
    """
    Fetches logs from CloudWatch Logs for a specified log group and time range.
    
    Expected input (from Bedrock Agent):
    {
        "log_group_name": "/aws/lambda/celestial-newsletter",
        "hours_back": 24
    }
    
    Returns:
    {
        "log_group": "...",
        "time_range": "...",
        "total_events": 123,
        "events": [
            {
                "timestamp": "2024-12-09T10:30:00",
                "message": "Log message here"
            }
        ]
    }
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    # Extract parameters from Bedrock Agent
    params = {}
    if 'requestBody' in event and 'content' in event['requestBody']:
        # Bedrock Agent format
        content = event['requestBody']['content']
        if 'application/json' in content:
            properties = content['application/json'].get('properties', [])
            params = {p['name']: p['value'] for p in properties}
    elif 'parameters' in event:
        params = {p['name']: p['value'] for p in event['parameters']}
    else:
        # Direct invocation format
        params = event
    
    log_group_name = params.get('log_group_name', '/aws/lambda/celestial-newsletter')
    hours_back = int(params.get('hours_back', 24))
    
    print(f"Fetching logs from: {log_group_name}, hours_back: {hours_back}")
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)
    
    # Convert to milliseconds since epoch (CloudWatch format)
    start_time_ms = int(start_time.timestamp() * 1000)
    end_time_ms = int(end_time.timestamp() * 1000)
    
    try:
        # Fetch log events
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time_ms,
            endTime=end_time_ms,
            limit=100  # Start with 100, can paginate later
        )
        
        # Format events
        events = []
        for event_item in response.get('events', []):
            events.append({
                'timestamp': datetime.fromtimestamp(event_item['timestamp'] / 1000).isoformat(),
                'message': event_item['message']
            })
        
        result = {
            'log_group': log_group_name,
            'time_range': f"{start_time.isoformat()} to {end_time.isoformat()}",
            'total_events': len(events),
            'events': events
        }
        
        print(f"Successfully fetched {len(events)} log events")
        
        # Extract parameters from Bedrock event
        action_group = event.get('actionGroup', 'log_fetcher')
        api_path = event.get('apiPath', '/fetch_logs')
        http_method = event.get('httpMethod', 'POST')
        
        # Prepare Bedrock response
        bedrock_response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(result)
                    }
                }
            }
        }
        
        print(f"Returning to Bedrock: {json.dumps(bedrock_response)}")
        
        return bedrock_response
        
    except Exception as e:
        error_msg = f"Error fetching logs: {str(e)}"
        print(error_msg)
        
        action_group = event.get('actionGroup', 'log_fetcher')
        api_path = event.get('apiPath', '/fetch_logs')
        http_method = event.get('httpMethod', 'POST')
        
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({'error': error_msg})
                    }
                }
            }
        }