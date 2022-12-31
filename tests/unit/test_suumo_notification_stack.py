import aws_cdk as core
import aws_cdk.assertions as assertions

from suumo_notification.suumo_notification_stack import SuumoNotificationStack

# example tests. To run these tests, uncomment this file along with the example
# resource in suumo_notification/suumo_notification_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SuumoNotificationStack(app, "suumo-notification")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
