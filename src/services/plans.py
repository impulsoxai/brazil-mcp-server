"""Plan definitions for SaaS API tiers."""

from dataclasses import dataclass


@dataclass
class Plan:
    name: str
    monthly_limit: int
    rate_limit_per_minute: int


PLANS: dict[str, Plan] = {
    "free": Plan(
        name="free",
        monthly_limit=1000,
        rate_limit_per_minute=20,
    ),
    "starter": Plan(
        name="starter",
        monthly_limit=10000,
        rate_limit_per_minute=60,
    ),
    "pro": Plan(
        name="pro",
        monthly_limit=50000,
        rate_limit_per_minute=120,
    ),
}

DEFAULT_PLAN = "free"


def get_plan(plan_name: str) -> Plan:
    """Get plan by name. Falls back to free if unknown."""
    return PLANS.get(plan_name, PLANS[DEFAULT_PLAN])
