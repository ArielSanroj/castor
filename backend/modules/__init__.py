"""
CASTOR Modules.

Domain-driven modular architecture following Fowler's modularization pattern.
Each module represents a bounded context that can eventually become a microservice.

Modules:
    - analysis: Social media analysis and sentiment processing
    - campaign: Campaign strategy and content generation
    - auth: Authentication and user management
    - leads: Lead management and CRM

Usage:
    from modules.analysis import AnalysisModule
    from modules.campaign import CampaignModule
    from modules.auth import AuthModule
    from modules.leads import LeadsModule
"""
