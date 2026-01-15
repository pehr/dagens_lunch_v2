# Dagens Lunch
This project is for using AI to scrape the webpages of lunch restaurants in Sweden. The backend is to be run on AWS, and the setup is to be done in CDK / Cloudfront. 

The infrastructure will consist of an API-Gateway, a DynomoDB table, two S3 buckets and a couple of Lambdas. 
It will also use SQS and eventbridge to kick of the parsing once a week.

## Lambdas
The two main lambdas will be for parsing the lunch information. One for parsing HTML content and one for getting information from menus in PDF or image format (JPG/PNG)

### Lambda Lunch Web Parser 
This lambda will listen to an SQS queue. The event message should have the following structure. 

```
{
  "restaurant_url": "https://www.bjorkmansskafferi.se/",
  "restaurant_id": "bjorkmansskafferi",
  "city": "Göteborg",
  "area": "Avenyn"
}
```
restaurant_url and restaurant_id are mandatory, the rest are optional.

When there's a message the lambda will use the URL to get the HTML content. Send the content to ChatGPT API and ask for the lunch menu in CSV format.

### Lambda Image Parser

