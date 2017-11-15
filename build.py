#!/usr/bin/env python

"""
Build a docker image for the current project state.

Environment variables will be automatically loaded from a `.env` file.
In order to specify build args to docker, create environment variables
prefixed with `BUILD_ARG_` (e.g. `BUILD_ARG_SG_BASE_IMAGE=registry/sg/base:latest`).

In order to push to Amazon ECR, it is necessary to have AWS credentials and the boto3
package installed.
The boto3 client will look in the environment variables:

AWS_ACCESS_KEY_ID: The access key for your AWS account.
AWS_SECRET_ACCESS_KEY: The secret key for your AWS account.
AWS_SESSION_TOKEN:
    The session key for your AWS account.
    This is only needed when you are using temporary credentials.
    The AWS_SECURITY_TOKEN environment variable can also be used,
    but is only supported for backwards compatibility purposes.
    AWS_SESSION_TOKEN is supported by multiple AWS SDKs besides python.

Boto3 will also check the aws shared credentials file if necessary.
See http://boto3.readthedocs.io/en/latest/guide/configuration.html#shared-credentials-file
for more details.
"""

import os
import sys
import base64
import argparse

import docker
import logbook  # easier log handler setup to see boto and other logs
from logbook.compat import redirect_logging
from dotenv import load_dotenv, find_dotenv

# Logging (because we always want logging)
redirect_logging()
log = logbook.Logger(__file__)


def _build(docker_client, path, registry, repo, tags, will_push=False):
    for tag in tags:
        t = '{}/{}:{}'.format(registry, repo, tag)
        log.info('building docker image {}', t)
        docker_client.images.build(
            path=path,
            tag=t,
            rm=True,
            pull=True,
            buildargs=build_args,
        )
        log.info('completed building image')
        if will_push:
            log.info('attempting to push image to {}', registry)
            for line in docker_client.images.push(
                '{}/{}'.format(registry, repo),
                tag=tag,
                stream=True
            ):
                log.debug(line)
            log.info('successfully pushed image')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-e', '--env',
        dest='env',
        default='.env',
        help=(
            'environment variable file to load into the current context. ' +
            'Default: `.env`. The script will search from the current working ' +
            'directory up until finding a file with the correct name.'))

    group.add_argument(
        '--no-env',
        dest='env',
        action='store_false',
        help='disable loading environment variable files')

    group = parser.add_argument_group('BUILD')
    group.add_argument(
        '-d', '--dockerfile',
        dest='path',
        default='.',
        help='path to the dockerfile, defaults to the current directory.')
    group.add_argument(
        '-t', '--tag',
        dest='tags',
        nargs='*',
        help='tag to use for image, defaults to `latest`, overrides BUILD_TAG environment variable.')
    group.add_argument(
        '--latest',
        dest='will_add_latest',
        action='store_true',
        help='tag the image with `latest` regardless of the presence of other tags.')
    group.add_argument(
        '-r', '--repository',
        dest='repository',
        help='name of the image, overrides BUILD_REPOSITORY environment variable.')
    group.add_argument(
        '-g', '--registry',
        dest='registry',
        help='name of the container registry, overrides BUILD_REGISTRY environment variable. Will be ignored for amazon uploads.')
    group.add_argument(
        '--push',
        dest='will_push',
        action='store_true',
        help='push the built image to the registry, will attempt to login to the registry before pushing.')
    group.add_argument(
        '--no-login',
        dest='will_login',
        action='store_false',
        help='do not try to login to the registry, by default login is always attempted. Will be ignored for amazon uploads.')
    group.add_argument(
        '-u', '--login-user',
        dest='login_user',
        help='username to login to the docker registry, overrides BUILD_USER environment variable.')
    group.add_argument(
        '-p', '--login-password',
        dest='login_password',
        help='password to login to the docker registry, overrides BUILD_PASSWORD environment variable.')

    group = parser.add_argument_group('AMAZON')
    group.add_argument(
        '--aws',
        dest='is_amazon_mode',
        action='store_true',
        help='use amazon ECR rather than a vanilla docker registry')
    group.add_argument(
        '--amazon-region',
        dest='amazon_region',
        help=(
            'the amazon region, overrides BUILD_AMAZON_REGION environment variable. ' +
            'If neither this flag nor the variable exist, will use the default region boto3 config.'))
    group.add_argument(
        '--amazon-registry-ids',
        dest='amazon_registry_ids',
        nargs='*',
        help='amazon registry ids, if not provided, the default registy will be used')

    group = parser.add_argument_group('LOGGING')
    group.add_argument(
        '-l', '--loglevel',
        dest='level',
        default='INFO',
        metavar='LOG_LEVEL',
        help="logging output level: {CRITICAL|ERROR|WARNING|NOTICE|INFO|DEBUG}.")
    group.add_argument(
        '--debug',
        dest='level',
        action='store_const',
        const='DEBUG',
        help="use loglevel DEBUG, this is equivalent to `-l DEBUG`")
    group.add_argument(
        '--silent',
        dest='silent',
        action='store_true',
        help="disable logging to stdout.")

    args = parser.parse_args()
    if args.silent:
        log_handler = logbook.NullHandler()
    else:
        log_handler = logbook.StreamHandler(sys.stdout, level=logbook.lookup_level(args.level.upper()))

    with log_handler:

        if args.env:
            env = find_dotenv(args.env)
            log.info('loading environment from {}', env)
            load_dotenv(env)

        docker_client = docker.from_env(version='auto')

        repo = args.repository or os.environ.get('BUILD_REPOSITORY', '')
        tags = set(args.tags or {os.environ.get('BUILD_TAG', 'latest')})
        if args.will_add_latest:
            tags.add('latest')
        build_args = {k[10:]: v for k, v in os.environ.items() if k.startswith('BUILD_ARG_')}
        path = args.path

        if args.is_amazon_mode:
            log.info('running in AMAZON mode')
            log.info('attempting to get ECR registry token')
            import boto3
            amazon_client = boto3.client('ecr', region_name=args.amazon_region)
            if args.amazon_registry_ids:
                response = amazon_client .get_authorization_token(registryIds=args.amazon_registry_ids)
            else:
                response = amazon_client .get_authorization_token()
            log.debug('{}', response)
            for auth in response['authorizationData']:
                registry = auth['proxyEndpoint'].replace('https://', '')
                creds = base64.b64decode(auth['authorizationToken'])
                user, pswd = creds.split(':')
                docker_client.login(user, pswd, registry=registry)
                _build(docker_client, path, registry, repo, tags, will_push=args.will_push)
        else:
            registry = args.registry or os.environ.get('BUILD_REGISTRY', '')
            if args.will_login:
                user = args.login_user or os.environ.get('BUILD_USER')
                pswd = args.login_password or os.environ.get('BUILD_PASSWORD')
                log.info('attempting to login to {} as {}', registry, user)
                login_response = docker_client.login(user, pswd, registry=registry)
                log.info('successfully logged in')
                log.debug('{}', login_response)
            _build(docker_client, path, registry, repo, tags, will_push=args.will_push)

        log.info('finished')
