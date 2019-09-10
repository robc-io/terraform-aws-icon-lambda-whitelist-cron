import os
import subprocess
from jinja2 import Environment, FileSystemLoader
import botocore.vendored.requests as requests
import logging
import zipfile

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info('## ENVIRONMENT VARIABLES')
    logger.info(os.environ)
    logger.info('## EVENT')
    logger.info(event)
    logger.info('## CONTEXT')
    logger.info(context)

    try:
        logger.info('Downloading terraform')
        r = requests.get('https://releases.hashicorp.com/terraform/0.12.6/terraform_0.12.6_linux_amd64.zip')
        with open('/tmp/terraform_0.12.6_linux_amd64.zip', 'wb') as terrazip:
            terrazip.write(r.content)
        print('downloaded')
        with zipfile.ZipFile('/tmp/terraform_0.12.6_linux_amd64.zip', 'r') as zip_ref:
            zip_ref.extractall('/tmp/')

        logger.info('Downloading whitelist')
        whitelist_url = r'https://download.solidwallet.io/conf/prep_iplist.json'
        logger.info('## URL')
        logger.info(whitelist_url)
        json_whitelist = requests.get(whitelist_url)
        logger.info('## JSON')
        logger.info(json_whitelist.json())
        templates_dir = os.path.join(os.path.curdir, 'templates')
        env = Environment(loader=FileSystemLoader(templates_dir))

        render_dict = {'ip_list': json_whitelist.json()}

        rendered_tpl = env.get_template('main.tf').render(render_dict)
        logger.info('## RENDERED TF TEMPLATE')
        logger.info(rendered_tpl)

        with open('/tmp/rendered_security_groups.tf', 'w') as f:
            f.write(rendered_tpl)
        os.chmod('/tmp/terraform', 755)
        subprocess.call(['./terraform',
                         'init',
                         '-backend-config "bucket=$TF_VAR_terraform_state_bucket"',
                         '-backend-config "lock_table=$TF_VAR_lock_table"',
                         '-backend-config "region=$TF_VAR_aws_region"',
                         '-backend-config "key=$TF_VAR_key'
                         ], cwd='/tmp/')
        # subprocess.call(['./terraform', 'init'], cwd='/tmp/') # This could have been artifact of perms but whatever can't , wait, it can hurt
        subprocess.call(['./terraform', 'apply', '-auto-approve'], cwd='/tmp/')

        logger.info(subprocess.call(['./terraform', 'output', '-auto-approve'], cwd='/tmp/'))

    except Exception as e:
        logger.info(e)
        raise e
