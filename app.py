#!/usr/bin/env python3

from aws_cdk import core

from dataproduct.dataproduct_stack import DataproductStack


app = core.App()

env_EU = core.Environment(account="447450868602", region="eu-central-1")

DataproductStack(app, "dataproduct",  env=env_EU)

app.synth()
