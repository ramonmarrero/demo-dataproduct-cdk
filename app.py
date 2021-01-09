#!/usr/bin/env python3

from aws_cdk import core

from dataproduct.dataproduct_stack import DataproductStack


app = core.App()
DataproductStack(app, "dataproduct")

app.synth()
