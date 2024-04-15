from celery import shared_task
from operations.email_parse_util import main


@shared_task
def my_task():
    print("Running email_parse_util")
    main()
