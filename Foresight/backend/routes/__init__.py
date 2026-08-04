"""HTTP layer.

Each module here is a Flask blueprint covering one area of the API. The
app factory in app.py registers them all under /api.

Routes are kept thin on purpose: read the request, check permission, call
a service, return JSON. Anything that involves a decision about the data
belongs in `services/`, where it can be tested without HTTP.
"""
