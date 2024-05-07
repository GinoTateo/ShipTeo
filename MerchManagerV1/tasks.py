from celery import shared_task
from operations.Order_Backend import main


@shared_task
def my_task():
    print("Running email_parse_util")
    main()
