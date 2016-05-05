import json

import web
import requests
import requests_unixsocket
from subprocess import check_output

urls = (
    '/', 'index',
    '/run', 'run',
    '/drone-harbour-run', 'DroneHarbourRun'
)

html_template="""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="">
    <meta name="author" content="">

    <title>Harbour - {page_title}</title>

	<!-- Latest compiled and minified CSS -->
	<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">

	<!-- Optional theme -->
	<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">

	<!-- Latest compiled and minified JavaScript -->
	<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>

</head>
<body>
<div class="page-header">
        <h1>{page_title}</h1>
</div>
<div class="row">
	{page_content}
</div>
</body>
</html>
"""

class index:
    def GET(self):
        # Create a UDS socket
        text = ""
        with requests_unixsocket.monkeypatch():
            # Access /path/to/page from /tmp/Labelsprofilesvc.sock
            r = requests.get('http+unix://%2Fvar%2Frun%2Fdocker.sock/containers/json?all=1')
            containers = r.json()
            col_heads = ["Names", "Image", "Status", "Created", "Labels", "Ports"]
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
            return html_template.format(page_title="Containers", page_content=text)
        return "Unknown Error"


class DroneHarbourRun:
    def POST(self):
        # Create a UDS socket
        text = ""
        data = json.loads(web.data(), strict=False)
        print data
        #return data
        registry = data['registry']
        image = data['image']
        envs = data['env']
        ports = "{public_port}:{private_port}".format(public_port=data['public_port'],
                                                      private_port=data['private_port'])

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

        env_list = []
        for env in envs:
            env_list += ["-e", str(env)]

        labels = {'branch': data['build']['branch'],
                  'labels': data['build']['commit'],
                  'commit_message': data['build']['message']}

        label_list = []
        for key, val in labels.iteritems():
            label_list += ["--label", str(key + "=" + val)]

        # print env_list

        print ["docker", "run", "--publish={ports}".format(ports=ports), "--detach=true",
               "--name={name}".format(name=name)] + env_list + [
                  "{registry}:5000/{image}".format(registry=registry, image=image)]

        text += check_output(["docker", "run", "--publish={ports}".format(ports=ports), "--detach=true",
                              "--name={name}".format(name=name)] + env_list + label_list +
                             ["{registry}:5000/{image}".format(registry=registry, image=image)])
        return text

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()



