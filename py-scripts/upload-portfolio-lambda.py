import boto3
import StringIO
import zipfile
import mimetypes
import json

def lambda_handler(event, context):
    s3 = boto3.resource('s3')
    sns = boto3.resource('sns')

    source_location = {
        "bucketName": "portfoliobuild.cludio.net",
        "objectKey": "portfoliobuild.zip"
    }

    try:
        topic = sns.Topic('arn:aws:sns:us-east-1:956031752817:deployPortfolioTopic')

        job = event.get('CodePipeline.job')

        if job:
            for artifact in job['data']['inputArtifacts']:
                if artifact['name'] == 'BuildArtifact':
                    source_location = artifact['location']['s3Location']

        portfolio_bucket = s3.Bucket('portfolio.cludio.net')
        build_bucket = s3.Bucket(source_location['bucketName'])

        print "Building protfolio from " + str(source_location)

        portfolio_zip = StringIO.StringIO()
        build_bucket.download_fileobj(source_location['objectKey'],portfolio_zip)

        with zipfile.ZipFile(portfolio_zip) as myzip:
            for nm in myzip.namelist():
                obj = myzip.open(nm)
                portfolio_bucket.upload_fileobj(obj, nm,
                ExtraArgs={'ContentType': mimetypes.guess_type(nm)[0]})
                portfolio_bucket.Object(nm).Acl().put(ACL='public-read')

        topic.publish(
            Subject = 'Portfolio Deployed',
            Message = 'Portfolio deployed successfully')

        if job:
            print str(job['id'])
            codepipeline = boto3.client('codepipeline')
            codepipeline.put_job_success_result(jobId=job['id'])

    except:
        topic.publish(
            Subject = 'Portfolio Deploy Failed',
            Message = 'Portfolio not deployed due to lambda error')
        raise
    return 'ready and return'
