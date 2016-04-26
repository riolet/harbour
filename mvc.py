import web
import requests
import requests_unixsocket



urls = (
    '/', 'index'
)

class index:
    def GET(self):
        # Create a UDS socket
        with requests_unixsocket.monkeypatch():
            # Access /path/to/page from /tmp/profilesvc.sock
            r = requests.get('http+unix://%2Fvar%2Frun%2Fdocker.sock')
            assert r.status_code == 200
        return "Welcome to guimon"

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()



