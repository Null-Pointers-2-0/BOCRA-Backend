from django.urls import path

from .views import (
    AlertCategoriesView,
    AlertLogsView,
    AlertStatsView,
    AlertSubscribeView,
    ConfirmSubscriptionView,
    DeleteSubscriptionView,
    MySubscriptionsView,
    UnsubscribeView,
    UpdateSubscriptionView,
)

app_name = "alerts"

urlpatterns = [
    # Public
    path("categories/", AlertCategoriesView.as_view(), name="categories"),
    path("subscribe/", AlertSubscribeView.as_view(), name="subscribe"),
    path("confirm/<str:token>/", ConfirmSubscriptionView.as_view(), name="confirm"),
    path("unsubscribe/<str:token>/", UnsubscribeView.as_view(), name="unsubscribe"),

    # Authenticated
    path("subscriptions/", MySubscriptionsView.as_view(), name="subscriptions"),
    path("subscriptions/update/", UpdateSubscriptionView.as_view(), name="subscriptions-update"),
    path("subscriptions/delete/", DeleteSubscriptionView.as_view(), name="subscriptions-delete"),

    # Staff
    path("logs/", AlertLogsView.as_view(), name="logs"),
    path("stats/", AlertStatsView.as_view(), name="stats"),
]
