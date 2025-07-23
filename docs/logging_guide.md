# Logging Best Practices Guide

This document outlines the logging architecture and best practices implemented in the Weather Map Application.

## Overview

The application uses a sophisticated logging system that follows industry best practices for production applications. The logging configuration provides:

- **Multiple log files** for different purposes
- **Structured logging** with JSON format for analysis
- **Performance monitoring** with timing information
- **API request/response tracking**
- **Proper log rotation** to manage disk space
- **Environment-based configuration**

## Log Files Structure

The application creates separate log files in the `logs/` directory:

### 1. `app.log` - General Application Logs
- **Purpose**: All application events and general logging
- **Level**: DEBUG and above
- **Format**: Detailed with module, function, and line information
- **Rotation**: 10MB files, 5 backups
- **Use Case**: General debugging and application monitoring

### 2. `error.log` - Error-Only Logs
- **Purpose**: ERROR and CRITICAL level messages only
- **Level**: ERROR and above
- **Format**: Detailed with full stack traces
- **Rotation**: 10MB files, 10 backups (more backups for errors)
- **Use Case**: Quick error analysis and alerting

### 3. `api.log` - API Request/Response Logs
- **Purpose**: All API calls to external services
- **Level**: DEBUG and above
- **Format**: JSON for easy parsing and analysis
- **Rotation**: 10MB files, 5 backups
- **Use Case**: API performance monitoring, debugging API issues

### 4. `performance.log` - Performance Metrics
- **Purpose**: Timing information for operations
- **Level**: INFO and above
- **Format**: JSON with timing data
- **Rotation**: 5MB files, 3 backups
- **Use Case**: Performance analysis and optimization

## Logging Architecture

### Configuration-Based Setup

```python
from src.weather_map.logging_config import setup_logging, get_logger

# Setup logging (done once at application start)
setup_logging()

# Get logger for your module
logger = get_logger(__name__)
```

### Logger Hierarchy

- **Root Logger**: Catches all unhandled logs
- **Application Loggers**: Module-specific loggers
- **Third-party Loggers**: Reduced verbosity for external libraries

### Specialized Loggers

#### 1. Performance Logger
```python
from src.weather_map.logging_config import PerformanceLogger

with PerformanceLogger("operation_name", logger):
    # Your code here
    pass
# Automatically logs start time, end time, and duration
```

#### 2. API Logger
```python
from src.weather_map.logging_config import APILogger

api_logger = APILogger()
api_logger.log_request('GET', url, params)
api_logger.log_response(status_code, response_time)
api_logger.log_error(exception, context)
```

## Best Practices Implemented

### 1. **Separate Concerns**
- Different log files for different purposes
- Errors separated from general logs
- API calls tracked separately
- Performance metrics isolated

### 2. **Structured Logging**
- JSON format for machine-readable logs
- Consistent field names across log entries
- Extra context information included

### 3. **Security**
- API keys and sensitive data automatically masked
- No credentials logged in plain text
- Safe error message formatting

### 4. **Performance**
- Minimal overhead for disabled log levels
- Efficient log rotation
- Asynchronous logging where possible

### 5. **Operational Excellence**
- Log rotation prevents disk space issues
- Multiple backup files for critical logs
- Environment-based configuration
- Console and file output separation

## Log Levels Usage

### DEBUG
- Detailed diagnostic information
- Variable values and state information
- Only in development/troubleshooting

### INFO
- General application flow
- Successful operations
- User actions and results

### WARNING
- Recoverable errors
- Deprecated functionality usage
- Performance concerns

### ERROR
- Application errors that don't stop execution
- Failed API calls
- Data processing errors

### CRITICAL
- Application-stopping errors
- Security issues
- Configuration problems

## Environment Configuration

Set environment variables to control logging:

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export LOG_LEVEL=INFO

# Custom log directory
export LOG_DIR=custom_logs
```

## Log Analysis Examples

### 1. Find All Errors
```bash
grep "ERROR\|CRITICAL" logs/error.log
```

### 2. API Performance Analysis
```bash
jq '.response_time' logs/api.log | sort -n
```

### 3. Operation Timing
```bash
jq 'select(.message | contains("Completed operation"))' logs/performance.log
```

### 4. Failed API Calls
```bash
jq 'select(.status_code >= 400)' logs/api.log
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Error Rate**: Count of ERROR/CRITICAL messages
2. **API Response Times**: Average response times from api.log
3. **Failed Requests**: HTTP 4xx/5xx responses
4. **Performance Degradation**: Increasing operation times

### Recommended Alerts

- **High Error Rate**: More than 10 errors per minute
- **API Failures**: More than 5% failed API calls
- **Slow Performance**: Operations taking >5 seconds
- **Log File Size**: When approaching rotation limits

## Integration with Monitoring Tools

The JSON format logs are compatible with:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **Datadog**
- **New Relic**
- **Prometheus + Grafana**

## Development vs Production

### Development
- Console output enabled
- DEBUG level logging
- Detailed error messages

### Production
- File-only logging
- INFO level or higher
- Sanitized error messages
- Log aggregation enabled

## Troubleshooting Common Issues

### 1. No Logs Appearing
- Check log directory permissions
- Verify LOG_LEVEL environment variable
- Ensure logging setup is called

### 2. Log Files Too Large
- Reduce log level in production
- Adjust rotation settings
- Implement log cleanup scripts

### 3. Performance Impact
- Use appropriate log levels
- Avoid logging in tight loops
- Consider asynchronous logging for high-volume scenarios

## Future Enhancements

1. **Centralized Logging**: Ship logs to central aggregation service
2. **Real-time Monitoring**: Stream logs to monitoring dashboards
3. **Automated Alerting**: Set up alerts based on log patterns
4. **Log Analytics**: Implement automated log analysis and reporting
