#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_iam
)
from constructs import Construct

class BastionHostStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    sg_bastion_host = aws_ec2.SecurityGroup(self, "BastionHostSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for an bastion host',
      security_group_name='bastion-host-sg'
    )
    cdk.Tags.of(sg_bastion_host).add('Name', 'bastion-host-sg')

    #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ec2/InstanceClass.html
    #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ec2/InstanceSize.html#aws_cdk.aws_ec2.InstanceSize
    ec2_instance_type = aws_ec2.InstanceType.of(aws_ec2.InstanceClass.BURSTABLE3, aws_ec2.InstanceSize.MEDIUM)

    #XXX: As there are no SSH public keys deployed on this machine,
    # you need to use EC2 Instance Connect with the command
    #  'aws ec2-instance-connect send-ssh-public-key' to provide your SSH public key.
    # https://aws.amazon.com/de/blogs/compute/new-using-amazon-ec2-instance-connect-for-ssh-access-to-your-ec2-instances/
    bastion_host = aws_ec2.BastionHostLinux(self, "BastionHost",
      vpc=vpc,
      instance_type=ec2_instance_type,
      subnet_selection=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PUBLIC),
      security_group=sg_bastion_host
    )

    #TODO: SHOULD restrict IP range allowed to ssh acces
    bastion_host.allow_ssh_access_from(aws_ec2.Peer.ipv4("0.0.0.0/0"))

    #XXX: In order to test data pipeline, add {Kinesis, KinesisFirehose}FullAccess Policy to the bastion host.
    bastion_host.role.add_to_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["kinesis:*"]))
    bastion_host.role.add_to_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["firehose:*"]))

    self.sg_bastion_host = sg_bastion_host

    cdk.CfnOutput(self, 'BastionHostId', value=bastion_host.instance_id, export_name='BastionHostId')
    cdk.CfnOutput(self, 'BastionHostPublicDNSName', value=bastion_host.instance_public_dns_name, export_name='BastionHostPublicDNSName')

