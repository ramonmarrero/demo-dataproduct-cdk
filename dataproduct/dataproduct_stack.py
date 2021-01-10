from aws_cdk import (
    core,
    aws_ecr_assets as assets,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_logs as logs
)

class DataproductStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:

        self.ecsCluster = "DataProductCluster"

        self.ecsTaskDefinition = "DataProductTaskDefinition"

        self.vpc = "vpc-ec112387"

        self.ecsSubnet = "subnet-c70f5fba"

        self.ownerTag = "Ramon_Marrero"

        self.projectTag = "DataProduct"


        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # Find existing VPC
        vpc = ec2.Vpc.from_lookup(self,"VPC",
                                  vpc_id=self.vpc)

        # Create ECS Cluster
        cluster = ecs.Cluster(self, f"{self.ecsCluster}", vpc=vpc)


        # Adding Tags to Cluster
        core.Tags.of(cluster).add("Owner", f'{self.ownerTag}')
        core.Tags.of(cluster).add("Project", f'{self.projectTag}')
        core.Tags.of(cluster).add("Component", "ECS Cluster")

        # Create ECS Task Execution Role
        ecsExecutionRole = iam.Role(self, "FargateContainerExecutionRole",
                                    assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"))

        # Create ECS Task Role
        ecsTaskRole = iam.Role(self, "FargateContainerTaskRole",
                               assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"))

        # Create ECS Task Definition
        ecsTaskDefinition = ecs.TaskDefinition(self, f"{self.ecsTaskDefinition}",
                                               compatibility=ecs.Compatibility.FARGATE,
                                               cpu="2048",
                                               memory_mib="8192",
                                               execution_role=ecsExecutionRole,
                                               task_role=ecsTaskRole)

        # Create CloudWatch logs for Fargate
        logDetail = logs.LogGroup(self, f"{self.projectTag}LogGroup",
                                  log_group_name=f"/{self.projectTag}/{cluster.cluster_name}/"
                                  f"{ecsTaskDefinition.node.unique_id}",
                                  retention=logs.RetentionDays.SIX_MONTHS,
                                  removal_policy=core.RemovalPolicy.DESTROY)

        # Create ECR Repo / Build Docker Image / Push to Repo
        dataProductImage = assets.DockerImageAsset(self, "ecrImage",directory="./product",
                                                   build_args={ 'tag': 'mydataproduct'}, repository_name='dataproduct')

        # Add image to Task Definition
        ecsTaskDefinition.add_container(
            f"{self.projectTag}-container",
            image=ecs.ContainerImage.from_registry(dataProductImage.image_uri),
            logging=ecs.LogDriver.aws_logs(stream_prefix = f'{self.projectTag}', log_group=logDetail)
        )

        # Fix the addPrincipalPolicy permission issue.
        dataProductImage.repository.grant_pull(ecsTaskDefinition.obtain_execution_role())

        # Adding Tags to Repository
        core.Tags.of(dataProductImage).add("Owner", f'{self.ownerTag}')
        core.Tags.of(dataProductImage).add("Project", f'{self.projectTag}')
        core.Tags.of(dataProductImage).add("Component", "Repository")

        # Adding Tags to Task Definition
        core.Tags.of(ecsTaskDefinition).add("Owner", f'{self.ownerTag}')
        core.Tags.of(ecsTaskDefinition).add("Project", f'{self.projectTag}')
        core.Tags.of(ecsTaskDefinition).add("Component", "Task Definition")
        core.Tags.of(ecsTaskDefinition).add("Name", f"{self.ecsTaskDefinition}")


        # Create Lambda Function and dependencies

        #Create role for the lambda function
        awsLambdaFargateRole = iam.Role(
            self, 'aws_lambda_fargate_role',
            role_name='lambda-fargate-role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ])


        # Add PassRole policy to Lambda role
        awsLambdaFargateRole.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=[f"{ecsExecutionRole.role_arn}",
                       f"{ecsTaskRole.role_arn}",
                       ],
            actions=["iam:PassRole"]))

        # Add RunTask policy to Lambda role
        awsLambdaFargateRole.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=["ecs:RunTask"]))


        # Create lambda function
        lambda_fargate = _lambda.Function(self, f"{self.projectTag}-lambda-fargate",
                                          runtime=_lambda.Runtime.PYTHON_3_8,
                                          function_name=f"{self.projectTag}-lambda-fargate",
                                          role=awsLambdaFargateRole,
                                          handler="dataproduct-lambda.lambda_handler",
                                          code=_lambda.Code.asset("./function"),
                                          description="Lambda function to trigger Fargate",
                                          environment={
                                              'NAME': f"{self.projectTag}-lambda-fargate",
                                              'CLUSTER': f"{cluster.cluster_name}",
                                              'TASK_DEFINITION': f"{ecsTaskDefinition.node.unique_id}",
                                              'SUBNETS': f"{self.ecsSubnet}"
                                          }
                                          )

        # Adding Tags to Lambda
        core.Tags.of(lambda_fargate).add("Owner", f"{self.ownerTag}")
        core.Tags.of(lambda_fargate).add("Project", f"{self.projectTag}")
        core.Tags.of(lambda_fargate).add("Component", "Lambda")

        # Create Rest API
        api = apigateway.LambdaRestApi(
            self,
            'dataproduct-rest-api-gateway',
            handler=lambda_fargate
        )

        # Add Lambda dependency for ECS Cluster
        lambda_fargate.node.add_dependency(cluster)


        # Adding Tags to API
        core.Tags.of(api).add("Owner", f"{self.ownerTag}")
        core.Tags.of(api).add("Project", f"{self.projectTag}")
        core.Tags.of(api).add("Component", "API")


        # Output of resources

        # Lambda
        core.CfnOutput(
            self, "LambdaResource",
            description="Data Product Lambda Function",
            value=lambda_fargate.function_name
        )

        # Repository
        core.CfnOutput(
            self, "ECRResourceARN",
            description="Data Product Image URI",
            value=dataProductImage.image_uri
        )









