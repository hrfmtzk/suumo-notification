import aws_cdk as core
import aws_cdk.assertions as assertions

from suumo_notification.suumo_notification_stack import SuumoNotificationStack


def test_sqs_queue_created():
    app = core.App()
    stack = SuumoNotificationStack(app, "suumo-notification")
    assertions.Template.from_stack(stack)
