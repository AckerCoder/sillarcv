import pulumi
import pulumi_aws as aws
from utils import tags

# VPC principal
vpc = aws.ec2.Vpc("main",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags=tags | {"Name": "sillarcv-vpc"}
)

# Internet Gateway
igw = aws.ec2.InternetGateway("main",
    vpc_id=vpc.id,
    tags=tags | {"Name": "sillarcv-igw"}
)

# Subnets privadas en diferentes AZs
private_subnet_1 = aws.ec2.Subnet("private-1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone=aws.get_availability_zones().names[0],
    tags=tags | {"Name": "sillarcv-private-1"}
)

private_subnet_2 = aws.ec2.Subnet("private-2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone=aws.get_availability_zones().names[1],
    tags=tags | {"Name": "sillarcv-private-2"}
)

# NAT Gateway (necesario para que las Lambdas en subnets privadas accedan a internet)
public_subnet = aws.ec2.Subnet("public",
    vpc_id=vpc.id,
    cidr_block="10.0.0.0/24",
    availability_zone=aws.get_availability_zones().names[0],
    map_public_ip_on_launch=True,
    tags=tags | {"Name": "sillarcv-public"}
)

eip = aws.ec2.Eip("nat",
    domain="vpc",
    tags=tags | {"Name": "sillarcv-nat-eip"}
)

nat_gateway = aws.ec2.NatGateway("main",
    allocation_id=eip.id,
    subnet_id=public_subnet.id,
    tags=tags | {"Name": "sillarcv-nat"}
)

# Tablas de ruteo
public_route_table = aws.ec2.RouteTable("public",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )
    ],
    tags=tags | {"Name": "sillarcv-public-rt"}
)

private_route_table = aws.ec2.RouteTable("private",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            nat_gateway_id=nat_gateway.id,
        )
    ],
    tags=tags | {"Name": "sillarcv-private-rt"}
)

# Asociaciones de tablas de ruteo
public_route_table_assoc = aws.ec2.RouteTableAssociation("public",
    subnet_id=public_subnet.id,
    route_table_id=public_route_table.id
)

private_route_table_assoc_1 = aws.ec2.RouteTableAssociation("private-1",
    subnet_id=private_subnet_1.id,
    route_table_id=private_route_table.id
)

private_route_table_assoc_2 = aws.ec2.RouteTableAssociation("private-2",
    subnet_id=private_subnet_2.id,
    route_table_id=private_route_table.id
)

# Security Group para las Lambdas
lambda_sg = aws.ec2.SecurityGroup("lambda",
    description="Security group for Lambda functions",
    vpc_id=vpc.id,
    egress=[aws.ec2.SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
    )],
    tags=tags | {"Name": "sillarcv-lambda-sg"}
)

# Export the subnet IDs and security group ID
private_subnet_ids = [private_subnet_1.id, private_subnet_2.id]
security_group_id = lambda_sg.id

# Export the VPC ID
pulumi.export("vpc_id", vpc.id)
pulumi.export("private_subnet_ids", private_subnet_ids)
pulumi.export("lambda_security_group_id", security_group_id)