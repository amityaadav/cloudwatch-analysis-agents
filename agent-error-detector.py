import json
import re
from collections import defaultdict
from datetime import datetime

def lambda_handler(event, context):
    """
    Detects and categorizes errors from log events.
    
    Expected input (from Bedrock Agent or previous Action Group):
    {
        "events": [
            {
                "timestamp": "2025-12-03T17:19:34.396000",
                "message": "[ERROR] Runtime.ImportModuleError: ..."
            }
        ]
    }
    
    Returns:
    {
        "total_errors": 5,
        "error_types": {
            "ImportModuleError": {
                "count": 5,
                "severity": "critical",
                "messages": [...],
                "first_seen": "...",
                "last_seen": "..."
            }
        },
        "warnings": [...],
        "summary": "..."
    }
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    # Extract events from input
    if 'parameters' in event:
        # Coming from Bedrock Agent
        params = {p['name']: p['value'] for p in event['parameters']}
        events_json = params.get('events', '[]')
        if isinstance(events_json, str):
            events = json.loads(events_json)
        else:
            events = events_json
    elif 'body' in event:
        # Coming from previous Lambda via body
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        events = body.get('events', [])
    else:
        # Direct invocation
        events = event.get('events', [])
    
    print(f"Processing {len(events)} log events")
    
    # Error patterns
    error_patterns = {
        'ERROR': re.compile(r'\[ERROR\](.*)'),
        'Exception': re.compile(r'([\w\.]+Exception):(.*)'),
        'Traceback': re.compile(r'Traceback \(most recent call last\)'),
        'FAILED': re.compile(r'FAILED|Failed|failed'),
        'Timeout': re.compile(r'Task timed out|timeout', re.IGNORECASE)
    }
    
    warning_pattern = re.compile(r'\[WARNING\](.*)|\[WARN\](.*)')
    
    # Storage
    errors = defaultdict(lambda: {
        'count': 0,
        'messages': [],
        'timestamps': [],
        'severity': 'medium'
    })
    warnings = []
    
    # Process each event
    for event_data in events:
        message = event_data.get('message', '')
        timestamp = event_data.get('timestamp', '')
        
        # Check for errors
        if '[ERROR]' in message or 'ERROR' in message.upper():
            # Extract error type
            error_type = extract_error_type(message)
            
            errors[error_type]['count'] += 1
            errors[error_type]['messages'].append(message[:500])  # Truncate long messages
            errors[error_type]['timestamps'].append(timestamp)
            
            # Determine severity
            errors[error_type]['severity'] = determine_severity(error_type, message)
        
        # Check for warnings
        warning_match = warning_pattern.search(message)
        if warning_match:
            warnings.append({
                'timestamp': timestamp,
                'message': message[:300]
            })
    
    # Post-process errors
    error_summary = {}
    for error_type, data in errors.items():
        error_summary[error_type] = {
            'count': data['count'],
            'severity': data['severity'],
            'first_seen': min(data['timestamps']) if data['timestamps'] else None,
            'last_seen': max(data['timestamps']) if data['timestamps'] else None,
            'sample_messages': data['messages'][:3]  # Just first 3 examples
        }
    
    # Generate summary
    total_errors = sum(data['count'] for data in errors.values())
    critical_errors = [k for k, v in error_summary.items() if v['severity'] == 'critical']
    
    summary = f"Found {total_errors} errors across {len(error_summary)} error types. "
    if critical_errors:
        summary += f"CRITICAL: {', '.join(critical_errors[:3])}. "
    summary += f"{len(warnings)} warnings detected."
    
    result = {
        'total_errors': total_errors,
        'total_warnings': len(warnings),
        'error_types': error_summary,
        'warnings': warnings[:5],  # First 5 warnings
        'summary': summary
    }
    
    print(f"Analysis complete: {total_errors} errors, {len(error_summary)} types")
    
    # Extract parameters from Bedrock event
    action_group = event.get('actionGroup', 'error_detector')
    api_path = event.get('apiPath', '/detect_errors')
    http_method = event.get('httpMethod', 'POST')
    
    return {
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


def extract_error_type(message):
    """Extract the specific error type from message"""
    
    # Common patterns
    patterns = [
        r'Runtime\.(\w+Error)',           # Runtime.ImportModuleError
        r'(\w+Exception):',               # ValueError:
        r'(\w+Error):',                   # ImportError:
        r'\[ERROR\]\s+(\w+)',             # [ERROR] Timeout
        r'Error:\s+(\w+)',                # Error: Connection
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)
    
    # Generic error
    if 'timeout' in message.lower():
        return 'TimeoutError'
    elif 'permission' in message.lower() or 'access denied' in message.lower():
        return 'PermissionError'
    elif 'not found' in message.lower():
        return 'NotFoundError'
    else:
        return 'UnknownError'


def determine_severity(error_type, message):
    """Determine severity based on error type and context"""
    
    # Critical errors (service completely broken)
    critical_keywords = [
        'importmoduleerror',
        'runtimeerror', 
        'syntaxerror',
        'out of memory',
        'access denied',
        'authentication',
        'authorization'
    ]
    
    # High errors (functionality broken)
    high_keywords = [
        'timeout',
        'connection',
        'network',
        'api',
        'httperror'
    ]
    
    error_lower = f"{error_type} {message}".lower()
    
    if any(keyword in error_lower for keyword in critical_keywords):
        return 'critical'
    elif any(keyword in error_lower for keyword in high_keywords):
        return 'high'
    else:
        return 'medium'