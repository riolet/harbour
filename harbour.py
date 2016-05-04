import json

import web
import requests
import requests_unixsocket
from subprocess import check_output

urls = (
    '/', 'index',
    '/run', 'run'
)

class index:
    def GET(self):
        # Create a UDS socket
        text = ""
        with requests_unixsocket.monkeypatch():
            # Access /path/to/page from /tmp/profilesvc.sock
            r = requests.get('http+unix://%2Fvar%2Frun%2Fdocker.sock/containers/json')
            containers = r.json()
            col_heads = containers[0].keys()
            text = "<table>"
            text += "<tr>"
            for col_head in col_heads:
                text += "<td>" + col_head +"</td>"
            text += "</tr>"
            for container in containers:
                text += "<tr>"
                for col_head in col_heads:
                    text += "<td>" + str(container[col_head]) + "</td>"
                text += "</tr>"
            text += "</table>"
            return text
            #return json2html.convert(r.json())
        return "Unknown Error"


class run:
    def POST(self):
        # Create a UDS socket
        text = ""
        data = web.input()
        print data
        registry = data.registry
        image = data.image
        envs = data.env
        ports = data.port

        text += check_output(["docker", "pull",
                              "{registry}:5000/{image}:latest".format(registry=registry, image=image)])

        name = "{image}_{port}".format(image=image, port=ports.split(":")[0])

        try:
            text += check_output(["docker", "stop", name])
        except:
            text += "Image not stopped"

        try:
            text += check_output(["docker", "rm", name])
        except:
            text += "Image not removed"

        jenvs = json.loads(envs)
        env_list = []
        for key, val in jenvs.iteritems():
            env_list += ["-e", str(key + "=" + val)]

        # print env_list

        print ["docker", "run", "--publish={ports}".format(ports=ports), "--detach=true",
               "--name={name}".format(name=name)] + env_list + [
                  "{registry}:5000/{image}".format(registry=registry, image=image)]

        text += check_output(["docker", "run", "--publish={ports}".format(ports=ports), "--detach=true",
                              "--name={name}".format(name=name)] + env_list + [
                                 "{registry}:5000/{image}".format(registry=registry, image=image)])


        return text

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()



