import * as path from "path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3n from "aws-cdk-lib/aws-s3-notifications";
import * as sqs from "aws-cdk-lib/aws-sqs";

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

    const lambdaCode = lambda.Code.fromAsset(path.join(__dirname, "..", "lambdas"));

    const parseHtmlLambda = new lambda.Function(this, "ParseHtmlLunchmenuLambda", {
      functionName: name("parse-html-lunchmenu"),
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "parse_html.index.handler",
      code: lambdaCode,
      timeout: cdk.Duration.minutes(2),
      environment: {
        WEEKLY_LUNCHMENUS_BUCKET: weeklyLunchmenusBucket.bucketName,
        RESTAURANT_SOURCES_BUCKET: restaurantSourcesBucket.bucketName
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
        RESTAURANT_SOURCES_BUCKET: restaurantSourcesBucket.bucketName
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
      timeout: cdk.Duration.minutes(2),
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

    const weeklyRule = new events.Rule(this, "WeeklyLunchmenuIngestRule", {
      ruleName: name("weekly-lunchmenu-ingest"),
      schedule: events.Schedule.cron({
        minute: "0",
        hour: "9",
        weekDay: "MON"
      })
    });

    weeklyRule.addTarget(new targets.LambdaFunction(enqueueRestaurantsLambda));

    const api = new apigateway.RestApi(this, "LunchApi", {
      restApiName: name("api"),
      deployOptions: {
        throttlingRateLimit: 5,
        throttlingBurstLimit: 20
      }
    });

    const restaurants = api.root.addResource("restaurants");
    restaurants.addMethod("GET", new apigateway.LambdaIntegration(apiLambda));

    const restaurantById = restaurants.addResource("{restaurant_id}");
    restaurantById.addMethod("GET", new apigateway.LambdaIntegration(apiLambda));

    const restaurantByWeek = restaurantById.addResource("{week}");
    restaurantByWeek.addMethod("GET", new apigateway.LambdaIntegration(apiLambda));

    const lunch = api.root.addResource("lunch");
    const lunchCity = lunch.addResource("{city}");
    const lunchWeek = lunchCity.addResource("{week}");
    const lunchDay = lunchWeek.addResource("{day}");
    lunchDay.addMethod("GET", new apigateway.LambdaIntegration(apiLambda));

    weeklyLunchmenusBucket.grantPut(parseHtmlLambda);
    weeklyLunchmenusBucket.grantPut(parseImageLambda);
    restaurantSourcesBucket.grantRead(parseImageLambda);
    weeklyLunchmenusBucket.grantRead(importToDdbLambda);

    table.grantReadWriteData(importToDdbLambda);
    table.grantReadData(enqueueRestaurantsLambda);
    table.grantReadData(apiLambda);

    parseQueue.grantSendMessages(enqueueRestaurantsLambda);

    new cdk.CfnOutput(this, "ApiEndpoint", {
      value: api.url
    });
  }
}
