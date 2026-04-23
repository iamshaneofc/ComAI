"""Store onboarding lifecycle values (persisted on ``Store.onboarding_status``)."""

ONBOARDING_CREATED = "created"
ONBOARDING_CONNECTED = "connected"
ONBOARDING_SYNCING = "syncing"
ONBOARDING_READY = "ready"
ONBOARDING_FAILED = "failed"

ALLOWED_ONBOARDING_STATUSES = frozenset(
    {
        ONBOARDING_CREATED,
        ONBOARDING_CONNECTED,
        ONBOARDING_SYNCING,
        ONBOARDING_READY,
        ONBOARDING_FAILED,
    }
)
