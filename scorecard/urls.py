"""
URL configuration for the scorecard app.

All routes are mounted under /api/v1/scorecard/ via bocra_backend/urls.py.
"""
from django.urls import path

from .views import (
    ComputeScoresView,
    CurrentScoresView,
    ManualMetricCreateView,
    ManualMetricListView,
    OperatorScoreDetailView,
    RankingsView,
    ScoreHistoryView,
    ScorecardWeightsView,
    ScorecardWeightUpdateView,
)

app_name = "scorecard"

urlpatterns = [
    # -- Weights ---------------------------------------------------------------
    path("weights/", ScorecardWeightsView.as_view(), name="weights"),
    path("weights/<str:dimension>/", ScorecardWeightUpdateView.as_view(), name="weight-update"),

    # -- Scores ----------------------------------------------------------------
    path("scores/", CurrentScoresView.as_view(), name="scores-current"),
    path("scores/history/", ScoreHistoryView.as_view(), name="scores-history"),
    path("scores/compute/", ComputeScoresView.as_view(), name="scores-compute"),
    path("scores/<str:operator_code>/", OperatorScoreDetailView.as_view(), name="scores-detail"),

    # -- Rankings --------------------------------------------------------------
    path("rankings/", RankingsView.as_view(), name="rankings"),

    # -- Manual metrics --------------------------------------------------------
    path("manual-metrics/", ManualMetricListView.as_view(), name="manual-metrics-list"),
    path("manual-metrics/create/", ManualMetricCreateView.as_view(), name="manual-metrics-create"),
]
