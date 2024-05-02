from flask import Blueprint, render_template

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(404)
def page_not_found(error):
    return render_template('error.html', error_status=404, error_message=error.description or "Page not found"), 404

@errors.app_errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_status=500, error_message="Internal server error"), 500

@errors.app_errorhandler(403)
def forbidden(error):
    return render_template('error.html', error_status=403, error_message="Forbidden"), 403