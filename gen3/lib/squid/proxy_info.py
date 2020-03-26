#!/usr/bin/env python3

import json
import boto3
import os
import random
import socket




outcome = {}

"""
  function to get autoscaling groups

  @var String name [Optional]: the name of the autoscaling group you want.

  @return Dictionary containing the ASG looked up, them all if the variable is omited
"""
def get_asg(name=None):
    client = boto3.client('autoscaling')
    if name != None and os.environ.get('vpc_name') != None:
        ASG = client.describe_auto_scaling_groups(AutoScalingGroupNames=[name])['AutoScalingGroups']
        del client
    else:
        ASG = client.describe_auto_scaling_groups()['AutoScalingGroups']
        del client
    return ASG


"""
  function to get a list of instances with a "Healthy" status according to an autoscaling group

  @var list autoscaling_group  autoscaling groups from the function get_asg

  @return list containing the ids of the healthy instances
"""
def get_healthy_instances_id(autoscaling_group):
    ids_list = []
    for instances in autoscaling_group:
        for instance in instances['Instances']:
            if instance['HealthStatus'] == "Healthy":
                ids_list.append(instance['InstanceId'])
    return ids_list


"""
  function to find the instance attribute sourceDestinationCheck for a single instance
           this must be set to false if we want our instance to serve as proxy and be 
           the default gateway for a specific route table

  @var string instance_id  the id of the instance we want to know the value of the attibue 

  @return boolean True or False based on the attribute value
"""
def get_sourceDestinationCheck_attr(instance_id):
    client = boto3.client('ec2')
    response = client.describe_instance_attribute(InstanceId=instance_id, Attribute='sourceDestCheck')
    del client
    return response['SourceDestCheck']['Value']



"""
  function to ge the private ip of instances

  @var list instances_id list with the instances id you want to know the eni ids

  @return list with the private ips of the instances in the variable
"""
def get_instances_priv_ip(instances_id):
    reservations = get_instances_info(instances_id)
    priv_ip = []
    for reservation in reservations['Reservations']:
        for instance in reservation['Instances']:
            priv_ip.append(instance['PrivateIpAddress'])
    return priv_ip


"""
  function to ge the public ip of instances

  @var list instances_id list with the instances id you want to know the eni ids

  @return list with the private ips of the instances in the variable
"""
def get_instances_pub_ip(instances_id):
    reservations = get_instances_info(instances_id)
    pub_ip = []
    for reservation in reservations['Reservations']:
        for instance in reservation['Instances']:
            pub_ip.append(instance['PublicIpAddress'])
    return pub_ip


"""
  function to get the information of instances 

  @var list id_list list with the instances id you want to get the description

  @return list instances info
"""
def get_instances_info(id_list):
    client = boto3.client('ec2')
    instances = client.describe_instances(InstanceIds=id_list)
    del client
    return instances


"""
  function to check if a port is open for an address

  @var String addr address you want to check for the port
       Int port port to check

  @return int 0 if open, something else if otherwise
"""
def check_port(addr,port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    result = sock.connect_ex((addr, port))
    sock.close
    return result


"""
  function to get the eni ids of an instance

  @var list instances_id list with the instances id you want to know the eni ids

  @return list with the eni ids of the instances
"""
def get_instances_eni(instances_id): 
    reservations = get_instances_info(instances_id)
    ni_id = []
    for reservation in reservations['Reservations']:
        for instance in reservation['Instances']:
            for network_interfaces in instance['NetworkInterfaces']:
                ni_id.append(network_interfaces['NetworkInterfaceId'])
    return ni_id


"""
  function to get a vpc base upon its name 
  
  @var string name name of the vpc you want
  
  @return dictionary with the vpc description
"""
def get_vpc(name):
    client = boto3.client('ec2')
    vpcs   = client.describe_vpcs(Filters=[{'Name':'tag:Name','Values':[name]}])
    del client
    for vpc in vpcs['Vpcs']:
        return vpc

"""
  function to get route tables information

  @var String vpc_id id of the VPC where the route belongs to
       String name name of the route in question

  @return Dict containing the information of the table
"""
def get_route_table(vpc_id,name):
    client = boto3.client('ec2')
    route_table = client.describe_route_tables(Filters=[{'Name':'tag:Name','Values': [name]},{'Name':'vpc-id','Values':[vpc_id]}])
    del client
    return route_table



"""
  function to get the routing table id of a routing table

  @var Dict route_table expexted the value of the function get_route_table

  @return String the routing table id
"""
def get_route_table_id(route_table):
    for table in route_table['RouteTables']:
        for association in table['Associations']:
            return association['RouteTableId']


"""
  function that searches for a default gateway in a defined routing table

  @var string rtid the id of the routing table to be queried

  @return Dictionary with a boto response of the request
"""
def exist_default_gw(rtid):
    client = boto3.client('ec2')
    response = client.describe_route_tables(Filters=[{'Name': 'route.destination-cidr-block','Values':['0.0.0.0/0']}],RouteTableIds=[rtid])
    del client
    return response


def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()

"""
  function to get a hosted zone in route53 based on the comments

  @var String comment what you are looking for

  @return Dict with the hosted zone information
"""
def get_hosted_zone(comment):
     client = boto3.client('route53')
     zones = client.list_hosted_zones()
     del client
     for zone in zones['HostedZones']:
         if 'Comment' in zone['Config'] and comment in zone['Config']['Comment']:
             return zone


"""
  function to get the recordsets of a hosted zone

  @var String zone_id id of the zone you want the recordsets

  @return Dict with the recordsets
"""
def get_record_sets(zone_id):
     client = boto3.client('route53')
     record_sets = client.list_resource_record_sets(HostedZoneId=zone_id)
     del client
     return record_sets


"""
  function to determine if a recordset exist in a hosted zone

  @var list record_sets expected the value of the function get_record_sets
       String name name of the record set you are looking for

  @return Boool if it exist or not
"""
def exist_record_set(record_sets, name):
    for record_set in record_sets['ResourceRecordSets']:
        if name in record_set['Name']:
            return True
    return False



"""
  function to get a record set

  @var list record_sets expected the value of the function get_record_sets
       String name name of the record set you are looking for

  @return dictionary with the recordset details
"""
def get_record_set(record_sets, name):
    for record_set in record_sets['ResourceRecordSets']:
        if name in record_set['Name']:
            return record_set



def main():


    statusCode = 200
    if os.environ.get('domain_test') is not None:
        domain = os.environ['domain_test']
    else:
        domain = 'gen3.org'

    if os.environ.get('proxy_port') is not None:
        proxy_port = os.environ['proxy_port']
    else:
        proxy_port = 3128

    instances_info = {}

    vpc_id = get_vpc(os.environ.get('vpc_name'))['VpcId']
    eks_private_route_table_id = get_route_table_id(get_route_table(vpc_id,'eks_private'))
    private_kube_route_table_id = get_route_table_id(get_route_table(vpc_id,'private_kube'))
    current_gw = exist_default_gw(eks_private_route_table_id)

    current_gw_instance_id = ''

    for routing_table in current_gw['RouteTables']: 
        for route in routing_table['Routes']: 
            if 'DestinationCidrBlock' in route:
                if route['DestinationCidrBlock'] == '0.0.0.0/0':
                    current_gw_instance_id = route['InstanceId']
                    break

    available_proxies = get_healthy_instances_id(get_asg("squid-auto-%s" % os.environ.get('vpc_name')))

    
    for instance_id in available_proxies:
        instance = {}
        instance["priv_ip"] = get_instances_priv_ip([instance_id])[0]
        instance["pub_ip"] = get_instances_pub_ip([instance_id])[0]

        #print(instance["priv_ip"])
        if check_port(instance["priv_ip"],proxy_port) == 0:
            instance["port_3128"] = "Open"
        else:
            instance["port_3128"] = "Closed"

        instance["eni_id"] = get_instances_eni([instance_id])[0]

        if instance_id == current_gw_instance_id:
            instance["active"] = True
        else:
            instance["active"] = False

        instances_info[instance_id] = instance


    zone = get_hosted_zone(os.environ['vpc_name'])
    zone_id = zone['Id']
    record_sets = get_record_sets(zone_id)
    dns_info = get_record_set(record_sets,'cloud-proxy')

    if exist_record_set(record_sets,'cloud-proxy'):
        instances_info['cloud-proxy.internal.io'] = get_record_set(record_sets,'cloud-proxy')
    else:
        instances_info['cloud-proxy.internal.io'] = 'NONE'

         
    print(json.dumps(instances_info))
    return json.dumps(instances_info)

           

if __name__ == '__main__':
    main()
