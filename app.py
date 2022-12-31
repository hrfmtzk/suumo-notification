import aws_cdk as cdk

from suumo_notification.suumo_notification_stack import SuumoNotificationStack

app = cdk.App()
SuumoNotificationStack(
    app,
    "SuumoNotificationStack",
)

app.synth()
