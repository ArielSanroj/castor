"""
Web routes for serving HTML pages.
Handles landing page and other web interfaces.
"""
from flask import Blueprint, render_template, redirect, url_for

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


@web_bp.route('/testigo/registro')
def witness_register():
    """Serve witness registration page (PWA)."""
    try:
        return render_template('witness_register.html')
    except Exception as e:
        return {
            'error': 'Template not found',
            'message': 'Witness registration template not available',
            'details': str(e)
        }, 404


@web_bp.route('/testigo/asignaciones')
def witness_assignments():
    """Serve witness assignments page."""
    try:
        return render_template('witness_register.html')
    except Exception as e:
        return {
            'error': 'Template not found',
            'details': str(e)
        }, 404


@web_bp.route('/testigo/offline')
def witness_offline():
    """Serve offline page for PWA."""
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sin Conexion - Castor</title>
        <style>
            body { font-family: sans-serif; background: #1a1a2e; color: #f1f5f9; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; text-align: center; }
            .container { padding: 20px; }
            h1 { font-size: 1.5rem; margin-bottom: 16px; }
            p { color: #94a3b8; }
            button { background: #4361ee; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 1rem; cursor: pointer; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Sin Conexion</h1>
            <p>No hay conexion a internet. Verifica tu conexion e intenta de nuevo.</p>
            <button onclick="location.reload()">Reintentar</button>
        </div>
    </body>
    </html>
    '''


@web_bp.route('/campaign-team')
def campaign_team_dashboard():
    """Serve Campaign Team Dashboard."""
    try:
        return render_template('campaign_team_dashboard.html')
    except Exception as e:
        return {
            'error': 'Template not found',
            'message': 'Campaign team dashboard template not available',
            'details': str(e)
        }, 404
