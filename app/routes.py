from app import app
from flask import render_template


#HOMEPAGE ROUTE
@app.route('/')
def index():
    return render_template('index.html')


#ERROR ROUTES
@app.errorhandler(404)
def page_not_found(error):
    error_status = 404
    error_message = "Page not found"
    return render_template('error.html', error_status=error_status, error_message=error_message), 404

@app.errorhandler(500)
def internal_server_error(error):
    error_status = 500
    error_message = "Internal server error"
    return render_template('error.html', error_status=error_status, error_message=error_message), 500

@app.errorhandler(403)
def forbidden(error):
    error_status = 403
    error_message = "Forbidden"
    return render_template('error.html', error_status=error_status, error_message=error_message), 403
