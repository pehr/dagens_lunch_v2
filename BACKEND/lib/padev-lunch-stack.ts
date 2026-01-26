import * as path from "path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as iam from "aws-cdk-lib/aws-iam";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3n from "aws-cdk-lib/aws-s3-notifications";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";

interface PadevLunchStackProps extends cdk.StackProps {
  appName: string;
  envName: string;
}

export class PadevLunchStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: PadevLunchStackProps) {
    super(scope, id, props);

    const { appName, envName } = props;
    const name = (component: string) => `${appName}-${envName}-${component}`;

    const restaurantSourcesBucket = new s3.Bucket(this, "RestaurantSourcesBucket", {
      bucketName: name("restaurant-sources"),
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true
    });

    const weeklyLunchmenusBucket = new s3.Bucket(this, "WeeklyLunchmenusBucket", {
      bucketName: name("weekly-lunchmenus"),
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true
    });

    const deadLetterQueue = new sqs.Queue(this, "LunchmenuParseDLQ", {
      queueName: name("lunchmenu-parse-dlq"),
      retentionPeriod: cdk.Duration.days(14)
    });

    const parseQueue = new sqs.Queue(this, "LunchmenuParseQueue", {
      queueName: name("lunchmenu-parse-queue"),
      visibilityTimeout: cdk.Duration.minutes(5),
      deadLetterQueue: {
        queue: deadLetterQueue,
        maxReceiveCount: 3
      }
    });

    const tableName = name("lunchrestaurants");

    const lunchTable = new dynamodb.CfnTable(this, "LunchRestaurantsTable", {
      tableName,
      billingMode: "PAY_PER_REQUEST",
      attributeDefinitions: [
        { attributeName: "restaurant_id", attributeType: "S" },
        { attributeName: "sk", attributeType: "S" },
        { attributeName: "city", attributeType: "S" },
        { attributeName: "week", attributeType: "S" },
        { attributeName: "day", attributeType: "S" }
      ],
      keySchema: [
        { attributeName: "restaurant_id", keyType: "HASH" },
        { attributeName: "sk", keyType: "RANGE" }
      ],
      globalSecondaryIndexes: [
        {
          indexName: "by_location_and_day",
          keySchema: [
            { attributeName: "city", keyType: "HASH" },
            { attributeName: "week", keyType: "RANGE" },
            { attributeName: "day", keyType: "RANGE" },
            { attributeName: "restaurant_id", keyType: "RANGE" }
          ],
          projection: { projectionType: "ALL" }
        }
      ]
    });

    lunchTable.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);

    const table = dynamodb.Table.fromTableName(this, "LunchRestaurantsTableRef", tableName);

    const lambdaCode = lambda.Code.fromAsset(path.join(__dirname, "..", "lambdas"), {
      bundling: {
        image: lambda.Runtime.PYTHON_3_11.bundlingImage,
        command: [
          "bash",
          "-c",
          "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
        ]
      }
    });

    const openAiApiKeySecret = new secretsmanager.Secret(this, "OpenAiApiKeySecret", {
      secretName: name("openai-api-key"),
      description: "OpenAI API key for menu parsing Lambdas"
    });

    const parseHtmlLambda = new lambda.Function(this, "ParseHtmlLunchmenuLambda", {
      functionName: name("parse-html-lunchmenu"),
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "parse_html.index.handler",
      code: lambdaCode,
      timeout: cdk.Duration.minutes(2),
      environment: {
        WEEKLY_LUNCHMENUS_BUCKET: weeklyLunchmenusBucket.bucketName,
        RESTAURANT_SOURCES_BUCKET: restaurantSourcesBucket.bucketName,
        OPENAI_API_KEY_SECRET_ARN: openAiApiKeySecret.secretArn,
        OPENAI_MAX_TOKENS_OVERRIDES: JSON.stringify({ pagoden: 4000 })
      }
    });

    const parseImageLambda = new lambda.Function(this, "ParseImageLunchmenuLambda", {
      functionName: name("parse-image-lunchmenu"),
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "parse_image.index.handler",
      code: lambdaCode,
      timeout: cdk.Duration.minutes(3),
      environment: {
        WEEKLY_LUNCHMENUS_BUCKET: weeklyLunchmenusBucket.bucketName,
        RESTAURANT_SOURCES_BUCKET: restaurantSourcesBucket.bucketName,
        TABLE_NAME: tableName,
        OPENAI_API_KEY_SECRET_ARN: openAiApiKeySecret.secretArn,
        OPENAI_MAX_TOKENS_OVERRIDES: JSON.stringify({ pagoden: 4000 })
      }
    });

    const importToDdbLambda = new lambda.Function(this, "ImportLunchmenuToDdbLambda", {
      functionName: name("import-lunchmenu-to-dynamodb"),
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "import_to_ddb.index.handler",
      code: lambdaCode,
      timeout: cdk.Duration.minutes(2),
      environment: {
        TABLE_NAME: tableName
      }
    });

    const enqueueRestaurantsLambda = new lambda.Function(this, "EnqueueLunchrestaurantsLambda", {
      functionName: name("enqueue-lunchrestaurants"),
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "enqueue_restaurants.index.handler",
      code: lambdaCode,
      timeout: cdk.Duration.minutes(1),
      environment: {
        TABLE_NAME: tableName,
        QUEUE_URL: parseQueue.queueUrl
      }
    });

    const apiLambda = new lambda.Function(this, "LunchApiLambda", {
      functionName: name("api"),
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "api.index.handler",
      code: lambdaCode,
      timeout: cdk.Duration.minutes(1),
      environment: {
        TABLE_NAME: tableName,
        GSI_NAME: "by_location_and_day"
      }
    });

    parseHtmlLambda.addEventSource(new lambdaEventSources.SqsEventSource(parseQueue));

    restaurantSourcesBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(parseImageLambda),
      { prefix: "menus/" }
    );

    weeklyLunchmenusBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(importToDdbLambda),
      { prefix: "weekly/" }
    );

    if (envName === "prod") {
      const weeklyRule = new events.Rule(this, "WeeklyLunchmenuIngestRule", {
        ruleName: name("weekly-lunchmenu-ingest"),
        schedule: events.Schedule.cron({
          minute: "0",
          hour: "8",
          weekDay: "MON"
        })
      });

      weeklyRule.addTarget(new targets.LambdaFunction(enqueueRestaurantsLambda));
    }

    const api = new apigateway.RestApi(this, "LunchApi", {
      restApiName: name("api"),
      deployOptions: {
        throttlingRateLimit: 5,
        throttlingBurstLimit: 20
      }
    });

    const restaurants = api.root.addResource("restaurants");

    const apiDdbRole = new iam.Role(this, "ApiDdbRole", {
      assumedBy: new iam.ServicePrincipal("apigateway.amazonaws.com")
    });
    table.grantReadData(apiDdbRole);
    apiDdbRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["dynamodb:Query"],
        resources: [`${table.tableArn}/index/by_location_and_day`]
      })
    );

    const listRestaurantsIntegration = new apigateway.AwsIntegration({
      service: "dynamodb",
      action: "Scan",
      options: {
        credentialsRole: apiDdbRole,
        requestTemplates: {
          "application/json": JSON.stringify({
            TableName: tableName,
            FilterExpression: "#sk = :INFO",
            ExpressionAttributeNames: { "#sk": "sk" },
            ExpressionAttributeValues: { ":INFO": { S: "INFO" } }
          })
        },
        integrationResponses: [
          {
            statusCode: "200",
            responseParameters: {
              "method.response.header.Access-Control-Allow-Origin": "'*'"
            },
            responseTemplates: {
              "application/json": [
                "#set($inputRoot = $input.path('$'))",
                "{",
                "  \"items\": [",
                "#foreach($item in $inputRoot.Items)",
                "    {",
                "      \"restaurant_id\": \"$item.restaurant_id.S\",",
                "      \"sk\": \"$item.sk.S\",",
                "      \"restaurant_name\": \"$!item.restaurant_name.S\",",
                "      \"url\": \"$!item.url.S\",",
                "      \"city\": \"$!item.city.S\",",
                "      \"city_name\": \"$!item.city_name.S\",",
                "      \"area\": \"$!item.area.S\",",
                "      \"info\": \"$!item.info.S\",",
                "      \"lunch_hours\": \"$!item.lunch_hours.S\",",
                "      \"address\": \"$!item.address.S\",",
                "      \"coordinates\": \"$!item.coordinates.S\",",
                "      \"phone\": \"$!item.phone.S\"",
                "    }#if($foreach.hasNext),#end",
                "#end",
                "  ]",
                "}"
              ].join("\n")
            }
          }
        ]
      }
    });

    restaurants.addMethod("GET", listRestaurantsIntegration, {
      methodResponses: [
        {
          statusCode: "200",
          responseParameters: {
            "method.response.header.Access-Control-Allow-Origin": true
          }
        }
      ]
    });

    const restaurantById = restaurants.addResource("{restaurant_id}");

    const getRestaurantIntegration = new apigateway.AwsIntegration({
      service: "dynamodb",
      action: "GetItem",
      options: {
        credentialsRole: apiDdbRole,
        requestTemplates: {
          "application/json": JSON.stringify({
            TableName: tableName,
            Key: {
              restaurant_id: { S: "$input.params('restaurant_id')" },
              sk: { S: "INFO" }
            }
          })
        },
        integrationResponses: [
          {
            statusCode: "200",
            responseParameters: {
              "method.response.header.Access-Control-Allow-Origin": "'*'"
            },
            responseTemplates: {
              "application/json": [
                "#set($inputRoot = $input.path('$'))",
                "#set($item = $inputRoot.Item)",
                "{",
                "      \"restaurant_id\": \"$item.restaurant_id.S\",",
                //"      \"sk\": \"$item.sk.S\",",
                "      \"restaurant_name\": \"$!item.restaurant_name.S\",",
                "      \"url\": \"$!item.url.S\",",
                "      \"city\": \"$!item.city.S\",",
                "      \"city_name\": \"$!item.city_name.S\",",
                "      \"area\": \"$!item.area.S\",",
                "      \"info\": \"$!item.info.S\",",
                "      \"lunch_hours\": \"$!item.lunch_hours.S\",",
                "      \"address\": \"$!item.address.S\",",
                "      \"coordinates\": \"$!item.coordinates.S\",",
                "      \"phone\": \"$!item.phone.S\"",
                "}"
              ].join("\n")
            }
          }
        ]
      }
    });

    restaurantById.addMethod("GET", getRestaurantIntegration, {
      methodResponses: [
        {
          statusCode: "200",
          responseParameters: {
            "method.response.header.Access-Control-Allow-Origin": true
          }
        }
      ]
    });

    const restaurantByWeek = restaurantById.addResource("{week}");
    const restaurantWeekIntegration = new apigateway.AwsIntegration({
      service: "dynamodb",
      action: "Query",
      options: {
        credentialsRole: apiDdbRole,
        requestTemplates: {
          "application/json": JSON.stringify({
            TableName: tableName,
            KeyConditionExpression: "restaurant_id = :id AND begins_with(#sk, :prefix)",
            ExpressionAttributeNames: { "#sk": "sk" },
            ExpressionAttributeValues: {
              ":id": { S: "$input.params('restaurant_id')" },
              ":prefix": { S: "MENU#$input.params('week')" }
            }
          })
        },
        integrationResponses: [
          {
            statusCode: "200",
            responseParameters: {
              "method.response.header.Access-Control-Allow-Origin": "'*'"
            },
            responseTemplates: {
              "application/json": [
                "#set($inputRoot = $input.path('$'))",
                "{",
                "  \"items\": [",
                "#foreach($item in $inputRoot.Items)",
                "    {",
                "      \"restaurant_id\": \"$item.restaurant_id.S\",",
                "      \"city\": \"$!item.city.S\",",
                "      \"week\": \"$!item.week.S\",",
                "      \"day\": \"$!item.day.S\",",
                "      \"dishes\": [",
                "#foreach($dish in $item.dishes.L)",
                "        #set($dishMap = $dish.M)",
                "        #set($tags = $dishMap.tags.L)",
                "        {",
                "          \"name\": \"$dishMap.name.S\",",
                "          \"price\": #if($dishMap.price.N != \"\")$dishMap.price.N#else null#end,",
                "          \"tags\": [",
                "#if($tags != \"\")",
                "#foreach($tag in $tags)",
                "            \"$tag.S\"#if($foreach.hasNext),#end",
                "#end",
                "#end",
                "          ]",
                "        }#if($foreach.hasNext),#end",
                "#end",
                "      ]",
                "    }#if($foreach.hasNext),#end",
                "#end",
                "  ]",
                "}"
              ].join("\n")
            }
          }
        ]
      }
    });

    restaurantByWeek.addMethod("GET", restaurantWeekIntegration, {
      methodResponses: [
        {
          statusCode: "200",
          responseParameters: {
            "method.response.header.Access-Control-Allow-Origin": true
          }
        }
      ]
    });

    const lunch = api.root.addResource("lunch");
    const lunchCity = lunch.addResource("{city}");
    const lunchWeek = lunchCity.addResource("{week}");
    const lunchDay = lunchWeek.addResource("{day}");
    const lunchByLocationIntegration = new apigateway.AwsIntegration({
      service: "dynamodb",
      action: "Query",
      options: {
        credentialsRole: apiDdbRole,
        requestTemplates: {
          "application/json": [
            "#set($area = $input.params('area'))",
            "{",
            "  \"TableName\": \"" + tableName + "\",",
            "  \"IndexName\": \"by_location_and_day\",",
            "  \"KeyConditionExpression\": \"#city = :city AND #week = :week AND #day = :day\",",
            "  \"ExpressionAttributeNames\": {",
            "    \"#city\": \"city\",",
            "    \"#week\": \"week\",",
            "    \"#day\": \"day\"#if($area != \"\"),",
            "    \"#area\": \"area\"#end",
            "  },",
            "  \"ExpressionAttributeValues\": {",
            "    \":city\": {\"S\": \"$input.params('city')\"},",
            "    \":week\": {\"S\": \"$input.params('week')\"},",
            "    \":day\": {\"S\": \"$input.params('day')\"}#if($area != \"\"),",
            "    \":area\": {\"S\": \"$area\"}#end",
            "  }",
            "#if($area != \"\")",
            "  ,\"FilterExpression\": \"#area = :area\"",
            "#end",
            "}"
          ].join("\n")
        },
        integrationResponses: [
          {
            statusCode: "200",
            responseParameters: {
              "method.response.header.Access-Control-Allow-Origin": "'*'"
            },
            responseTemplates: {
              "application/json": [
                "#set($inputRoot = $input.path('$'))",
                "{",
                "  \"items\": [",
                "#foreach($item in $inputRoot.Items)",
                "    {",
                "      \"restaurant_id\": \"$item.restaurant_id.S\",",
                "      \"restaurant_name\": \"$item.restaurant_name.S\",",
                "      \"city\": \"$!item.city.S\",",
                "      \"area\": \"$!item.area.S\",",
                "      \"week\": \"$!item.week.S\",",
                "      \"day\": \"$!item.day.S\",",
                "      \"dishes\": [",
                "#foreach($dish in $item.dishes.L)",
                "        #set($dishMap = $dish.M)",
                "        #set($tags = $dishMap.tags.L)",
                "        {",
                "          \"name\": \"$dishMap.name.S\",",
                "          \"price\": #if($dishMap.price.N != \"\")$dishMap.price.N#else null#end,",
                "          \"tags\": [",
                "#if($tags != \"\")",
                "#foreach($tag in $tags)",
                "            \"$tag.S\"#if($foreach.hasNext),#end",
                "#end",
                "#end",
                "          ]",
                "        }#if($foreach.hasNext),#end",
                "#end",
                "      ]",
                "    }#if($foreach.hasNext),#end",
                "#end",
                "  ]",
                "}"
              ].join("\n")
            }
          }
        ]
      }
    });

    lunchDay.addMethod("GET", lunchByLocationIntegration, {
      methodResponses: [
        {
          statusCode: "200",
          responseParameters: {
            "method.response.header.Access-Control-Allow-Origin": true
          }
        }
      ]
    });

    weeklyLunchmenusBucket.grantPut(parseHtmlLambda);
    weeklyLunchmenusBucket.grantPut(parseImageLambda);
    restaurantSourcesBucket.grantRead(parseImageLambda);
    weeklyLunchmenusBucket.grantRead(importToDdbLambda);

    openAiApiKeySecret.grantRead(parseHtmlLambda);
    openAiApiKeySecret.grantRead(parseImageLambda);

    table.grantReadWriteData(importToDdbLambda);
    table.grantReadData(enqueueRestaurantsLambda);
    table.grantReadData(apiLambda);
    table.grantReadData(parseImageLambda);

    parseQueue.grantSendMessages(enqueueRestaurantsLambda);

    new cdk.CfnOutput(this, "ApiEndpoint", {
      value: api.url
    });

    new cdk.CfnOutput(this, "OpenAiApiKeySecretArn", {
      value: openAiApiKeySecret.secretArn
    });
  }
}
