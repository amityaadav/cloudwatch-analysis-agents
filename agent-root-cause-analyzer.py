import json
from datetime import datetime

def lambda_handler(event, context):
    """
    Analyzes error patterns and determines root causes with recommendations.
    
    Expected input (from previous Action Group):
    {
        "error_types": {
            "ImportModuleError": {
                "count": 3,
                "severity": "critical",
                "sample_messages": [...]
            }
        }
    }
    
    Returns:
    {
        "analyses": [
            {
                "error_type": "ImportModuleError",
                "root_cause": "Missing Python dependencies in Lambda deployment package",
                "evidence": [...],
                "likely_causes": [...],
                "immediate_actions": [...],
                "prevention": [...]
            }
        ]
    }
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    # Extract error_types from input
    if 'parameters' in event:
        params = {p['name']: p['value'] for p in event['parameters']}
        error_types_json = params.get('error_types', '{}')
        if isinstance(error_types_json, str):
            error_types = json.loads(error_types_json)
        else:
            error_types = error_types_json
    elif 'body' in event:
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        error_types = body.get('error_types', {})
    else:
        error_types = event.get('error_types', {})
    
    print(f"Analyzing {len(error_types)} error types")
    
    # Analyze each error type
    analyses = []
    for error_type, error_data in error_types.items():
        analysis = analyze_error(error_type, error_data)
        analyses.append(analysis)
    
    result = {
        'total_analyses': len(analyses),
        'analyses': analyses
    }
    
    print(f"Root cause analysis complete for {len(analyses)} error types")
    
    # Extract parameters from Bedrock event
    action_group = event.get('actionGroup', 'root_cause_analyzer')
    api_path = event.get('apiPath', '/analyze_root_cause')
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


def analyze_error(error_type, error_data):
    """Perform root cause analysis for specific error type"""
    
    sample_messages = error_data.get('sample_messages', [])
    count = error_data.get('count', 0)
    severity = error_data.get('severity', 'medium')
    
    # Combine messages for analysis
    combined_message = ' '.join(sample_messages)
    
    # Route to specific analyzer
    if 'importmoduleerror' in error_type.lower() or 'import' in combined_message.lower():
        return analyze_import_error(error_type, error_data, combined_message)
    
    elif 'timeout' in error_type.lower() or 'timed out' in combined_message.lower():
        return analyze_timeout_error(error_type, error_data, combined_message)
    
    elif 'permission' in error_type.lower() or 'access denied' in combined_message.lower():
        return analyze_permission_error(error_type, error_data, combined_message)
    
    elif 'keyerror' in error_type.lower() or 'key error' in combined_message.lower():
        return analyze_key_error(error_type, error_data, combined_message)
    
    elif 'memory' in combined_message.lower() or 'out of memory' in combined_message.lower():
        return analyze_memory_error(error_type, error_data, combined_message)
    
    elif 'api' in combined_message.lower() or 'authentication' in combined_message.lower():
        return analyze_api_error(error_type, error_data, combined_message)
    
    else:
        return analyze_generic_error(error_type, error_data, combined_message)


def analyze_import_error(error_type, error_data, message):
    """Analyze import/module errors"""
    
    count = error_data.get('count', 0)
    
    # Determine specific cause
    if 'pydantic_core' in message or 'langchain' in message:
        root_cause = "Python package dependencies incompatible with Lambda runtime"
        evidence = [
            "Error mentions pydantic_core or langchain packages",
            "Lambda runtime cannot find required binary dependencies",
            f"Error occurred {count} times consistently"
        ]
        likely_causes = [
            "Package built on Mac/Windows but deployed to Linux Lambda runtime",
            "Binary dependencies (.so, .dylib files) platform-specific",
            "Missing or incorrectly packaged dependencies in deployment zip"
        ]
    elif 'no module named' in message.lower():
        root_cause = "Python module not included in Lambda deployment package"
        evidence = [
            f"Lambda cannot find the specified module",
            f"Consistent failure across {count} invocations"
        ]
        likely_causes = [
            "Module not installed in deployment package",
            "Incorrect package structure (wrong directory level)",
            "Module name typo or import path incorrect"
        ]
    else:
        root_cause = "Import or module loading failure"
        evidence = [f"Import failed {count} times"]
        likely_causes = ["Deployment package issue", "Dependency conflict"]
    
    return {
        'error_type': error_type,
        'severity': error_data.get('severity'),
        'root_cause': root_cause,
        'evidence': evidence,
        'likely_causes': likely_causes,
        'immediate_actions': [
            "Verify Lambda deployment package contains all required dependencies",
            "Check if dependencies were built for correct platform (Linux)",
            "Review recent code or deployment changes",
            "Test Lambda function manually with simple invocation"
        ],
        'short_term_fixes': [
            "Rebuild deployment package using Linux environment (Docker or GitHub Actions)",
            "Use --platform manylinux2014_x86_64 flag when installing Python packages",
            "Verify all dependencies in requirements.txt are included",
            "Test package locally with Amazon Linux Docker image"
        ],
        'long_term_prevention': [
            "Implement CI/CD pipeline that builds packages in Linux environment",
            "Add automated tests that verify imports before deployment",
            "Use Lambda Layers for large/complex dependencies",
            "Document deployment process and dependency requirements",
            "Set up pre-deployment validation checks"
        ],
        'monitoring_recommendations': [
            "Add CloudWatch alarm for Lambda errors",
            "Track error rate and set threshold alerts",
            "Monitor cold start failures specifically",
            "Implement canary deployments for package updates"
        ]
    }


def analyze_timeout_error(error_type, error_data, message):
    """Analyze timeout errors"""
    
    return {
        'error_type': error_type,
        'severity': error_data.get('severity'),
        'root_cause': "Function execution exceeded configured timeout limit",
        'evidence': [
            "Lambda terminated due to timeout",
            f"Occurred {error_data.get('count')} times"
        ],
        'likely_causes': [
            "Inefficient code or algorithms",
            "External API calls taking too long",
            "Network latency issues",
            "Processing large datasets",
            "Insufficient resources (CPU/memory)"
        ],
        'immediate_actions': [
            "Check Lambda timeout configuration (increase if needed)",
            "Review CloudWatch logs for slow operations",
            "Identify which operation is timing out",
            "Check if external APIs are responding slowly"
        ],
        'short_term_fixes': [
            "Increase Lambda timeout setting (max 15 minutes)",
            "Increase Lambda memory (gives more CPU)",
            "Add retry logic with exponential backoff",
            "Optimize slow code paths"
        ],
        'long_term_prevention': [
            "Profile code to identify bottlenecks",
            "Implement caching for repeated operations",
            "Use asynchronous processing for long tasks",
            "Consider Step Functions for workflows >15 min",
            "Optimize database queries and API calls"
        ],
        'monitoring_recommendations': [
            "Track P95/P99 execution duration",
            "Set alarms for approaching timeout threshold",
            "Monitor cold start vs warm start times"
        ]
    }


def analyze_permission_error(error_type, error_data, message):
    """Analyze IAM permission errors"""
    
    return {
        'error_type': error_type,
        'severity': error_data.get('severity'),
        'root_cause': "Lambda execution role lacks required IAM permissions",
        'evidence': [
            "Access denied or permission error in logs",
            f"Failed {error_data.get('count')} times consistently"
        ],
        'likely_causes': [
            "IAM role missing required policy",
            "Resource-based policy blocking access",
            "Service Control Policy (SCP) restriction",
            "Recent IAM policy changes"
        ],
        'immediate_actions': [
            "Identify which AWS service/resource is being accessed",
            "Review Lambda execution role IAM policies",
            "Check CloudTrail for AccessDenied events",
            "Verify resource exists and is in correct region"
        ],
        'short_term_fixes': [
            "Add required IAM permissions to execution role",
            "Follow principle of least privilege (grant only needed permissions)",
            "Test permissions with IAM Policy Simulator",
            "Check for typos in resource ARNs"
        ],
        'long_term_prevention': [
            "Document required permissions in code repository",
            "Use Infrastructure as Code (CloudFormation/Terraform) for IAM",
            "Implement IAM policy testing in CI/CD",
            "Regular IAM permission audits",
            "Use AWS managed policies when appropriate"
        ],
        'monitoring_recommendations': [
            "Set CloudWatch alarm for AccessDenied errors",
            "Monitor IAM policy changes via CloudTrail",
            "Track unauthorized access attempts"
        ]
    }


def analyze_key_error(error_type, error_data, message):
    """Analyze KeyError / missing data errors"""
    
    return {
        'error_type': error_type,
        'severity': error_data.get('severity'),
        'root_cause': "Code attempting to access non-existent dictionary key or data field",
        'evidence': [
            "KeyError exception raised",
            f"Occurred {error_data.get('count')} times"
        ],
        'likely_causes': [
            "Input data structure changed",
            "Missing error handling for optional fields",
            "Upstream service returning different format",
            "API version mismatch"
        ],
        'immediate_actions': [
            "Identify which key is missing from logs",
            "Check recent changes to input data sources",
            "Verify API contracts haven't changed",
            "Review recent code deployments"
        ],
        'short_term_fixes': [
            "Add defensive coding: use .get() instead of direct access",
            "Implement input validation",
            "Add fallback values for optional fields",
            "Log unexpected data structures for debugging"
        ],
        'long_term_prevention': [
            "Implement schema validation for inputs",
            "Use Pydantic or similar for data validation",
            "Add unit tests for edge cases",
            "Document expected data structures",
            "Version your APIs and data contracts"
        ],
        'monitoring_recommendations': [
            "Alert on KeyError exceptions",
            "Track data validation failures",
            "Monitor input data format changes"
        ]
    }


def analyze_memory_error(error_type, error_data, message):
    """Analyze out of memory errors"""
    
    return {
        'error_type': error_type,
        'severity': error_data.get('severity'),
        'root_cause': "Lambda function exceeded available memory allocation",
        'evidence': [
            "Out of memory error in logs",
            f"Occurred {error_data.get('count')} times"
        ],
        'likely_causes': [
            "Processing large datasets in memory",
            "Memory leaks in code",
            "Insufficient memory allocation",
            "Loading large files/dependencies"
        ],
        'immediate_actions': [
            "Check CloudWatch for Max Memory Used metric",
            "Compare to configured memory limit",
            "Identify which operation consumes most memory",
            "Review recent code changes"
        ],
        'short_term_fixes': [
            "Increase Lambda memory allocation",
            "Process data in smaller chunks/batches",
            "Use streaming for large files",
            "Clean up unused objects/variables"
        ],
        'long_term_prevention': [
            "Implement memory-efficient algorithms",
            "Use generators instead of loading all data",
            "Profile memory usage in development",
            "Consider S3 for large data processing",
            "Use pagination for database queries"
        ],
        'monitoring_recommendations': [
            "Track memory utilization percentage",
            "Alert when approaching memory limit",
            "Monitor memory trends over time"
        ]
    }


def analyze_api_error(error_type, error_data, message):
    """Analyze API/Authentication errors"""
    
    return {
        'error_type': error_type,
        'severity': error_data.get('severity'),
        'root_cause': "External API authentication or connection failure",
        'evidence': [
            "API error or authentication failure",
            f"Failed {error_data.get('count')} times"
        ],
        'likely_causes': [
            "Invalid or expired API key",
            "API rate limit exceeded",
            "API service outage",
            "Network connectivity issues",
            "Environment variable misconfigured"
        ],
        'immediate_actions': [
            "Verify API key is valid and not expired",
            "Check API service status page",
            "Review Lambda environment variables",
            "Test API endpoint manually (curl/Postman)",
            "Check for rate limiting headers in logs"
        ],
        'short_term_fixes': [
            "Update API key if expired",
            "Implement retry logic with exponential backoff",
            "Add rate limit handling",
            "Use AWS Secrets Manager for API keys",
            "Add API health checks before calling"
        ],
        'long_term_prevention': [
            "Set up API key rotation process",
            "Monitor API key expiration dates",
            "Implement circuit breaker pattern",
            "Add fallback mechanisms",
            "Cache API responses when appropriate",
            "Set up multi-region failover"
        ],
        'monitoring_recommendations': [
            "Alert on API authentication failures",
            "Track API response times and error rates",
            "Monitor rate limit approaching threshold",
            "Set up external API availability monitoring"
        ]
    }


def analyze_generic_error(error_type, error_data, message):
    """Generic analysis for unclassified errors"""
    
    return {
        'error_type': error_type,
        'severity': error_data.get('severity'),
        'root_cause': f"Unclassified error: {error_type}",
        'evidence': [
            f"Error occurred {error_data.get('count')} times",
            "Error pattern not recognized by analyzer"
        ],
        'likely_causes': [
            "Review error messages for specific cause",
            "May require manual investigation"
        ],
        'immediate_actions': [
            "Review full error stack traces in CloudWatch",
            "Search for error type in documentation",
            "Check recent code or configuration changes"
        ],
        'short_term_fixes': [
            "Add logging around error location",
            "Implement error handling",
            "Review and test recent changes"
        ],
        'long_term_prevention': [
            "Add more comprehensive error handling",
            "Improve logging for debugging",
            "Add error pattern to analyzer"
        ],
        'monitoring_recommendations': [
            "Set up alerts for this error type",
            "Track frequency and patterns"
        ]
    }