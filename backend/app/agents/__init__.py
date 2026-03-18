"""
Auxilia AI Agents
Autonomous agents for parametric insurance automation
"""
from app.agents.trigger_agent import trigger_agent, TriggerAgent
from app.agents.risk_agent import risk_agent, RiskAgent
from app.agents.fraud_agent import fraud_agent, FraudAgent
from app.agents.payout_agent import payout_agent, PayoutAgent

__all__ = [
    "trigger_agent",
    "TriggerAgent",
    "risk_agent",
    "RiskAgent",
    "fraud_agent",
    "FraudAgent",
    "payout_agent",
    "PayoutAgent",
]
