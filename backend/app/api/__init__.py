from flask import Blueprint

from app.api import (
    auth,
    users,
    projects,
    repos,
    git_http,
    storage_api,
    posts,
    discussion,
    issues,
    wiki,
    admin,
    community,
)


def register_blueprints(app):
    app.register_blueprint(auth.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(repos.bp)
    app.register_blueprint(git_http.bp)
    app.register_blueprint(storage_api.bp)
    app.register_blueprint(posts.bp)
    app.register_blueprint(discussion.bp)
    app.register_blueprint(issues.bp)
    app.register_blueprint(wiki.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(community.bp)
