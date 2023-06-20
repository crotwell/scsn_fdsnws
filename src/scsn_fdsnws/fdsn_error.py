
import cherrypy

class FDSNWSError(cherrypy.HTTPError):
    def __init__(self, status=500, message_html=None):
        super().__init__(status=status, message="")
        self._fdsn_error = message_html

    def set_response(self):
        super().set_response()
        response = cherrypy.serving.response
        response.body = self._fdsn_error.encode('utf-8')
