#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
VPC and networking stack for OSCAR Slack Bot.

This module defines the VPC configuration, security groups, and VPC endpoints
used by the OSCAR Slack Bot infrastructure. It imports existing VPC resources
and configures networking for Lambda functions with OpenSearch access.
"""

import logging
import os
from typing import List, Optional
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    CfnOutput,
    Tags
)
from constructs import Construct

logger = logging.getLogger(__name__)


class OscarVpcStack(Stack):
    """
    VPC and networking resources for OSCAR Slack Bot.
    
    This construct imports existing VPC resources and configures security groups,
    VPC endpoints, and network ACLs for proper isolation and secure access to
    AWS services and OpenSearch clusters.
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize VPC and networking resources.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            **kwargs: Additional arguments for Stack
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Import existing VPC configuration
        self.vpc = self._import_existing_vpc()
        
        # Import or create security groups
        self.lambda_security_group = self._create_lambda_security_group()
        
        # Create VPC endpoints for improved security and performance
        self.vpc_endpoints = self._create_vpc_endpoints()
        
        # Configure network ACLs for additional security
        self._configure_network_acls()
        
        # Add outputs for other stacks to reference
        self._add_outputs()
        
        # Add tags to all resources
        self._add_tags()
    
    def _import_existing_vpc(self) -> ec2.IVpc:
        """
        Import the existing VPC configuration.
        
        Returns:
            The imported VPC
        """
        # Use the VPC ID from .env file
        vpc_id = os.environ.get("VPC_ID")
        
        if not vpc_id:
            raise ValueError("VPC_ID environment variable must be set for VPC deployment")
            
        logger.info(f"Importing existing VPC: {vpc_id}")
        
        try:
            vpc = ec2.Vpc.from_lookup(
                self, "ExistingVpc",
                vpc_id=vpc_id
            )
            
            logger.info(f"Successfully imported VPC: {vpc_id}")
            return vpc
            
        except Exception as e:
            logger.error(f"Failed to import VPC {vpc_id}: {e}")
            raise ValueError(f"Could not import VPC {vpc_id}. Please verify the VPC_ID in your .env file.")
    
    def _create_lambda_security_group(self) -> ec2.SecurityGroup:
        """
        Create or import security group for Lambda functions with OpenSearch access.
        
        Returns:
            The Lambda security group
        """
        # Try to import existing security group first
        existing_sg_id = os.environ.get("LAMBDA_SECURITY_GROUP_ID")
        
        if existing_sg_id:
            try:
                logger.info(f"Importing existing security group: {existing_sg_id}")
                return ec2.SecurityGroup.from_security_group_id(
                    self, "ExistingLambdaSecurityGroup",
                    security_group_id=existing_sg_id
                )
            except Exception as e:
                logger.warning(f"Failed to import security group {existing_sg_id}: {e}")
                logger.info("Creating new security group")
        
        # Create new security group
        security_group = ec2.SecurityGroup(
            self, "OscarLambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for OSCAR Lambda functions with OpenSearch access",
            security_group_name="oscar-lambda-sg",
            allow_all_outbound=False  # We'll configure specific outbound rules
        )
        
        # Add outbound rules for HTTPS access to AWS services
        security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="HTTPS access for AWS services and OpenSearch"
        )
        
        # Add outbound rule for HTTP (if needed for some services)
        security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="HTTP access for external APIs"
        )
        
        # Add outbound rule for DNS resolution
        security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.udp(53),
            description="DNS resolution"
        )
        
        security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(53),
            description="DNS resolution over TCP"
        )
        
        # Add specific rule for OpenSearch access (port 9200 and 9300 if needed)
        security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(9200),
            description="OpenSearch HTTP access"
        )
        
        # Add rule for VPC endpoint access within VPC
        security_group.add_egress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="VPC endpoint access within VPC"
        )
        
        logger.info("Created Lambda security group with OpenSearch access rules")
        return security_group
    
    def _create_vpc_endpoints(self) -> dict:
        """
        Create VPC endpoints for improved security and performance.
        
        Returns:
            Dictionary of created VPC endpoints
        """
        endpoints = {}
        
        # S3 Gateway Endpoint (no additional charges)
        try:
            # Try private subnets first, fallback to public if needed
            subnet_selection = None
            try:
                # Check if private subnets exist
                private_subnets = self.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ).subnets
                if private_subnets:
                    subnet_selection = [ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)]
            except:
                pass
            
            if not subnet_selection:
                # Use public subnets if no private subnets available
                subnet_selection = [ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)]
            
            s3_endpoint = ec2.GatewayVpcEndpoint(
                self, "S3VpcEndpoint",
                vpc=self.vpc,
                service=ec2.GatewayVpcEndpointAwsService.S3,
                subnets=subnet_selection
            )
            endpoints["s3"] = s3_endpoint
            logger.info("Created S3 VPC Gateway Endpoint")
        except Exception as e:
            logger.warning(f"Failed to create S3 VPC endpoint: {e}")
        
        # DynamoDB Gateway Endpoint (no additional charges)
        try:
            # Use same subnet selection logic
            subnet_selection = None
            try:
                private_subnets = self.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ).subnets
                if private_subnets:
                    subnet_selection = [ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)]
            except:
                pass
            
            if not subnet_selection:
                subnet_selection = [ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)]
            
            dynamodb_endpoint = ec2.GatewayVpcEndpoint(
                self, "DynamoDBVpcEndpoint",
                vpc=self.vpc,
                service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
                subnets=subnet_selection
            )
            endpoints["dynamodb"] = dynamodb_endpoint
            logger.info("Created DynamoDB VPC Gateway Endpoint")
        except Exception as e:
            logger.warning(f"Failed to create DynamoDB VPC endpoint: {e}")
        
        # Create security group for interface endpoints
        endpoint_security_group = ec2.SecurityGroup(
            self, "VpcEndpointSecurityGroup",
            vpc=self.vpc,
            description="Security group for VPC interface endpoints",
            security_group_name="oscar-vpc-endpoints-sg"
        )
        
        # Allow HTTPS access from Lambda security group
        endpoint_security_group.add_ingress_rule(
            peer=ec2.Peer.security_group_id(self.lambda_security_group.security_group_id),
            connection=ec2.Port.tcp(443),
            description="HTTPS access from Lambda functions"
        )
        
        # Determine subnet selection for interface endpoints
        interface_subnet_selection = None
        try:
            private_subnets = self.vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ).subnets
            if private_subnets:
                interface_subnet_selection = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        except:
            pass
        
        if not interface_subnet_selection:
            # Use public subnets if no private subnets available
            interface_subnet_selection = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        
        # Secrets Manager Interface Endpoint
        try:
            secrets_endpoint = ec2.InterfaceVpcEndpoint(
                self, "SecretsManagerVpcEndpoint",
                vpc=self.vpc,
                service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
                subnets=interface_subnet_selection,
                security_groups=[endpoint_security_group],
                private_dns_enabled=False  # Disabled due to existing DNS conflicts
            )
            endpoints["secrets_manager"] = secrets_endpoint
            logger.info("Created Secrets Manager VPC Interface Endpoint (private DNS disabled)")
        except Exception as e:
            logger.warning(f"Failed to create Secrets Manager VPC endpoint: {e}")
        
        # STS Interface Endpoint (for assume role operations)
        try:
            sts_endpoint = ec2.InterfaceVpcEndpoint(
                self, "STSVpcEndpoint",
                vpc=self.vpc,
                service=ec2.InterfaceVpcEndpointAwsService.STS,
                subnets=interface_subnet_selection,
                security_groups=[endpoint_security_group],
                private_dns_enabled=False  # Disabled due to existing DNS conflicts
            )
            endpoints["sts"] = sts_endpoint
            logger.info("Created STS VPC Interface Endpoint (private DNS disabled)")
        except Exception as e:
            logger.warning(f"Failed to create STS VPC endpoint: {e}")
        
        # Note: Lambda VPC endpoint is not available as a standard service
        # Lambda functions can communicate through other means
        
        return endpoints
    
    def _configure_network_acls(self) -> None:
        """
        Configure Network ACLs for additional security layers.
        
        This method creates custom Network ACLs with restrictive rules
        for enhanced security beyond security groups.
        """
        # Try to get private subnets for Lambda deployment
        private_subnets = []
        
        try:
            private_subnets = self.vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ).subnets
        except Exception as e:
            logger.warning(f"No private subnets with egress found: {e}")
        
        if not private_subnets:
            try:
                # Fallback to isolated private subnets
                private_subnets = self.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ).subnets
            except Exception as e:
                logger.warning(f"No isolated private subnets found: {e}")
        
        if not private_subnets:
            logger.warning("No private subnets found in VPC - skipping Network ACL configuration")
            return
        
        if private_subnets:
            # Create custom Network ACL for Lambda subnets
            lambda_nacl = ec2.NetworkAcl(
                self, "OscarLambdaNetworkAcl",
                vpc=self.vpc,
                network_acl_name="oscar-lambda-nacl"
            )
            
            # Allow outbound HTTPS traffic
            lambda_nacl.add_entry(
                "AllowOutboundHTTPS",
                cidr=ec2.AclCidr.any_ipv4(),
                rule_number=100,
                traffic=ec2.AclTraffic.tcp_port(443),
                direction=ec2.TrafficDirection.EGRESS,
                rule_action=ec2.Action.ALLOW
            )
            
            # Allow outbound HTTP traffic
            lambda_nacl.add_entry(
                "AllowOutboundHTTP",
                cidr=ec2.AclCidr.any_ipv4(),
                rule_number=110,
                traffic=ec2.AclTraffic.tcp_port(80),
                direction=ec2.TrafficDirection.EGRESS,
                rule_action=ec2.Action.ALLOW
            )
            
            # Allow outbound DNS
            lambda_nacl.add_entry(
                "AllowOutboundDNS",
                cidr=ec2.AclCidr.any_ipv4(),
                rule_number=120,
                traffic=ec2.AclTraffic.udp_port(53),
                direction=ec2.TrafficDirection.EGRESS,
                rule_action=ec2.Action.ALLOW
            )
            
            # Allow outbound OpenSearch
            lambda_nacl.add_entry(
                "AllowOutboundOpenSearch",
                cidr=ec2.AclCidr.any_ipv4(),
                rule_number=130,
                traffic=ec2.AclTraffic.tcp_port(9200),
                direction=ec2.TrafficDirection.EGRESS,
                rule_action=ec2.Action.ALLOW
            )
            
            # Allow inbound ephemeral ports for responses
            lambda_nacl.add_entry(
                "AllowInboundEphemeral",
                cidr=ec2.AclCidr.any_ipv4(),
                rule_number=100,
                traffic=ec2.AclTraffic.tcp_port_range(1024, 65535),
                direction=ec2.TrafficDirection.INGRESS,
                rule_action=ec2.Action.ALLOW
            )
            
            # Associate Network ACL with private subnets (first few subnets)
            for i, subnet in enumerate(private_subnets[:3]):  # Limit to first 3 subnets
                ec2.SubnetNetworkAclAssociation(
                    self, f"LambdaSubnetAssociation{i}",
                    network_acl=lambda_nacl,
                    subnet=subnet
                )
            
            logger.info("Configured Network ACLs for Lambda subnets")
    
    def _add_outputs(self) -> None:
        """
        Add CloudFormation outputs for other stacks to reference.
        """
        CfnOutput(
            self, "VpcId",
            value=self.vpc.vpc_id,
            description="ID of the imported VPC",
            export_name="OscarVpcId"
        )
        
        CfnOutput(
            self, "LambdaSecurityGroupId",
            value=self.lambda_security_group.security_group_id,
            description="Security group ID for Lambda functions",
            export_name="OscarLambdaSecurityGroupId"
        )
        
        # Output subnet IDs for Lambda deployment (try private first, fallback to public)
        subnet_ids = []
        subnet_type_used = "public"
        
        try:
            private_subnets = self.vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ).subnet_ids
            if private_subnets:
                subnet_ids = private_subnets
                subnet_type_used = "private-with-egress"
        except:
            pass
        
        if not subnet_ids:
            try:
                isolated_subnets = self.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ).subnet_ids
                if isolated_subnets:
                    subnet_ids = isolated_subnets
                    subnet_type_used = "private-isolated"
            except:
                pass
        
        if not subnet_ids:
            # Fallback to public subnets
            try:
                public_subnets = self.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PUBLIC
                ).subnet_ids
                if public_subnets:
                    subnet_ids = public_subnets
                    subnet_type_used = "public"
            except:
                pass
        
        if subnet_ids:
            CfnOutput(
                self, "LambdaSubnetIds",
                value=",".join(subnet_ids),
                description=f"Comma-separated list of {subnet_type_used} subnet IDs for Lambda deployment",
                export_name="OscarLambdaSubnetIds"
            )
        
        # Output VPC CIDR for reference
        CfnOutput(
            self, "VpcCidr",
            value=self.vpc.vpc_cidr_block,
            description="CIDR block of the VPC",
            export_name="OscarVpcCidr"
        )
        
        # Output availability zones
        CfnOutput(
            self, "AvailabilityZones",
            value=",".join(self.vpc.availability_zones),
            description="Availability zones of the VPC",
            export_name="OscarAvailabilityZones"
        )
    
    def _add_tags(self) -> None:
        """
        Add tags to all VPC resources.
        """
        Tags.of(self).add("Project", "OSCAR")
        Tags.of(self).add("Component", "VPC")
        Tags.of(self).add("Environment", os.environ.get("ENVIRONMENT", "dev"))
        Tags.of(self).add("ManagedBy", "CDK")
    
    @property
    def vpc_config_for_lambda(self) -> dict:
        """
        Get VPC configuration dictionary for Lambda functions.
        
        Returns:
            Dictionary with VPC configuration for Lambda deployment
        """
        private_subnets = self.vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        ).subnets
        
        if not private_subnets:
            private_subnets = self.vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ).subnets
        
        return {
            "vpc": self.vpc,
            "subnets": private_subnets,
            "security_groups": [self.lambda_security_group]
        }
    
    def get_subnet_ids(self, subnet_type: str = "private") -> List[str]:
        """
        Get subnet IDs for the specified subnet type.
        
        Args:
            subnet_type: Type of subnets to retrieve ("private", "public", "isolated")
            
        Returns:
            List of subnet IDs
        """
        if subnet_type == "private":
            subnets = self.vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ).subnet_ids
            
            if not subnets:
                subnets = self.vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ).subnet_ids
                
        elif subnet_type == "public":
            subnets = self.vpc.select_subnets(
                subnet_type=ec2.SubnetType.PUBLIC
            ).subnet_ids
            
        elif subnet_type == "isolated":
            subnets = self.vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ).subnet_ids
            
        else:
            raise ValueError(f"Invalid subnet type: {subnet_type}")
        
        return subnets