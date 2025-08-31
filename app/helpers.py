# app/helpers.py
def api_response(success, message, data=None, status_code=200):
    return {
        "success": success,
        "message": message,
        "data": data
    }, status_code