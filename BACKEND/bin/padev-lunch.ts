#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { PadevLunchStack } from "../lib/padev-lunch-stack";

const app = new cdk.App();

const appName = app.node.tryGetContext("appName") || "padev-lunch";
const envName = app.node.tryGetContext("env") || process.env.ENV || "dev";

new PadevLunchStack(app, `${appName}-${envName}-stack`, {
  appName,
  envName,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  }
});
