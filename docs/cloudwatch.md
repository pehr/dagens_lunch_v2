# Cloudwatch


## Insight Queries
Basic query with filtering:

```
fields @timestamp, path, resourcePath, status
| filter status != "200"
| sort @timestamp desc
```
Query to analyze status codes:
```
fields @timestamp, path, resourcePath, status
| stats count() by status
| sort count desc
```
Query to analyze specific paths:
```
fields @timestamp, path, resourcePath, status
| filter path like /prod/restaurants/
| sort @timestamp desc
```
Query to get error rates by resource path:
```
fields @timestamp, path, resourcePath, status
| stats count() as total_requests, 
        sum(status >= 400) as error_count,
        (sum(status >= 400) * 100.0 / count()) as error_rate
  by resourcePath
| sort error_rate desc
```
The key points for your JSON logs:

CloudWatch Logs Insights automatically discovers JSON fields, so you can reference them directly (path, resourcePath, status, etc.)
No parsing is needed since your logs are already in valid JSON format
You can use all the standard CloudWatch Logs Insights commands (fields, filter, stats, sort, limit) with your JSON fields
Field names are case-sensitive and should match exactly what's in your JSON