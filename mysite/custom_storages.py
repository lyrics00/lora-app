from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = "static"  # upload files under "static/"
    default_acl = None   # don't send an ACL since the bucket disallows them
    file_overwrite = True