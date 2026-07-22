from . import admin,common,github_auth,history,settings,upload
routers=[common.router,github_auth.router,history.router,settings.router,upload.router,admin.router]
