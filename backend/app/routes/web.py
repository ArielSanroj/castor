"""
Web routes for serving HTML pages.
Handles landing page and other web interfaces.
"""
from flask import Blueprint, render_template, redirect, url_for
import os

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    """Serve index page."""
    try:
        return render_template('unified_dashboard.html')
    except Exception:
        # Fallback if template not found
        return {'message': 'Welcome to CASTOR ELECCIONES API', 'docs': '/api/health'}, 200


@web_bp.route('/webpage')
def webpage():
    """Serve landing page."""
    try:
        return render_template('webpage.html')
    except Exception as e:
        # Fallback if template not found
        return {
            'error': 'Template not found',
            'message': 'Landing page template not available',
            'details': str(e)
        }, 404


@web_bp.route('/media')
def media():
    """Serve CASTOR Medios page."""
    try:
        return render_template('media.html')
    except Exception as e:
        return {
            'error': 'Template not found',
            'message': 'Media template not available',
            'details': str(e)
        }, 404


@web_bp.route('/campaign')
def campaign():
    """Serve CASTOR Campañas page."""
    try:
        return render_template('campaign.html')
    except Exception as e:
        return {
            'error': 'Template not found',
            'message': 'Campaign template not available',
            'details': str(e)
        }, 404


@web_bp.route('/forecast')
def forecast():
    """Serve CASTOR Forecast page."""
    try:
        return render_template('forecast.html')
    except Exception as e:
        return {
            'error': 'Template not found',
            'message': 'Forecast template not available',
            'details': str(e)
        }, 404


@web_bp.route('/dashboard')
def unified_dashboard():
    """Redirect legacy dashboard route to root."""
    return redirect(url_for('web.index'))


@web_bp.route('/unified_dashboard')
def unified_dashboard_alias():
    """Redirect unified dashboard alias to root."""
    return redirect(url_for('web.index'))


@web_bp.route('/analytics')
def analytics_dashboard():
    """Serve CASTOR Analytics dashboard."""
    try:
        return render_template('analytics_dashboard.html')
    except Exception as e:
        return {
            'error': 'Template not found',
            'message': 'Analytics dashboard template not available',
            'details': str(e)
        }, 404


@web_bp.route('/dashboard-old')
def old_dashboard():
    """Serve old unified dashboard (legacy)."""
    return redirect(url_for('web.index'))
