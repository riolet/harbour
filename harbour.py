import json
from json2html import *
import web
from docker import Client

BASE_URL = 'unix://var/run/docker.sock'

urls = (
    '/', 'containers',
    '/containers', 'containers',
    '/run', 'run',
    '/drone-harbour-run', 'DroneHarbourRun',
    '/logs', 'logs',
    '/inspect', 'inspect',
    '/top', 'top'
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
<div class="content">
    <div class="navbar navbar-inverse">
          <div class="container-fluid">
            <div class="navbar-header">
              <a href="../" class="navbar-brand">Harbour</a>
              <button class="navbar-toggle" type="button" data-toggle="collapse" data-target="#navbar-main">
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
              </button>
            </div>
          </div>

            <div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1">
                <ul class="nav navbar-nav">
                    <li><a href="/containers">Containers</a></li>
                </ul>
            </div>
    </div>
    <div class="row-fluid">
        <div class="col-md-12">
            <div class="page-header">
                    <h1>{page_title}</h1>
            </div>
        </div>
    </div>
    <div class="row-fluid">
        {page_content}
    </div>
</div>
</body>
</html>
"""


# def list_files(startpath):
#     for root, dirs, files in os.walk(startpath):
#         level = root.replace(startpath, '').count(os.sep)
#         indent = ' ' * 4 * (level)
#         print('{}{}/'.format(indent, os.path.basename(root)))
#         subindent = ' ' * 4 * (level + 1)
#         for f in files:
#             print('{}{}'.format(subindent, f))

class containers:
    def GET(self):
        # Create a UDS socket
        text = ""
        try:
            cli = Client(base_url='unix://var/run/docker.sock')
            # Access /path/to/page from /tmp/Labelsprofilesvc.sock
            containers = cli.containers()
            col_heads = ["Names", "Image", "Status", "Created", "Ports", "Manage"]
            text="""
            <div class="col-md-12">
                <table class="table">
                    <thead>
                        <tr>"""
            for col_head in col_heads:
                text += "<th>" + col_head +"</th>"
            text += "</tr></thead><tbody>"
            name = None
            for container in containers:
                text += "<tr>"
                for col_head in col_heads:
                    val = ""
                    if col_head == "Ports":
                        ports = container['Ports']
                        count = 0
                        for port in ports:
                            if count > 0:
                                val += "<br/>"
                            val += str(port['PublicPort']) + " -> " + str(port['PrivatePort'])
                            count += 1
                    elif col_head == "Names":
                        if container and col_head in container and container[col_head]:
                            Names = container[col_head]
                            count = 0
                            for name in Names:
                                if count > 0:
                                    val += "<br/>"
                                val += str(name)
                                count += 1
                    elif col_head == "Manage":
                            val = '<a href="/logs?name={name}">logs</a> ' \
                                  '<a href="/inspect?id={id}">inspect</a> ' \
                                  '<a href="/top?id={id}">top</a>'.format(name=name, id=container['Id'])
                    else:
                        val = str(container[col_head])
                    text += "<td>" + val + "</td>"

                text += "</tr>"
            text += "</tbody></table></div>"
            return html_template.format(page_title="Containers", page_content=text)
        except Exception as e:
            return "Unknown Error: "+str(e)


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
        public_port=data['public_port']
        private_port=data['private_port']

        cli = Client(base_url='unix://var/run/docker.sock')

        text += cli.pull("{registry}:5000/{image}:latest".format(registry=registry, image=image))

        name = "{image}_{port}".format(image=image, port=public_port)

        try:
            text += cli.stop(name)
        except:
            text += "Image not stopped"

        try:
            text += cli.remove_container(name)
        except:
            text += "Image not removed"


        labels = {'branch': data['build']['branch'],
                  'commit': data['build']['commit'],
                  'commit_message': data['build']['message']}

        text = cli.create_container(image="{registry}:5000/{image}".format(registry=registry, image=image),
                                    hostname=name, ports=public_port, environment=envs,
                                    labels=labels)
        text = cli.start(image=image)
        return text

class logs:
    def GET(self):
        # Create a UDS socket
        text = """
        "<div class="col-md-12">
        """
        data = web.input()
        # text += "<pre>"+check_output(["docker", "logs", data.name], stderr=STDOUT)+"</pre></div>"
        # return html_template.format(page_title="Logs for {name}".format(name=data.name), page_content=text)

class inspect:
    def GET(self):
        # Create a UDS socket
        text = """
        "<div class="col-md-12">
        """
        data = web.input()
        # with requests_unixsocket.monkeypatch():
        #     r = requests.get('http+unix://%2Fvar%2Frun%2Fdocker.sock/containers/{id}/json'.format(id=data.id))
        #     text += json2html.convert(json = r.text) + "</div>"
        #     return html_template.format(page_title="Inspecting", page_content=text)

class top:
    def GET(self):
        # Create a UDS socket
        text = """
        "<div class="col-md-12">
        """
        data = web.input()
        # with requests_unixsocket.monkeypatch():
        #     r = requests.get('http+unix://%2Fvar%2Frun%2Fdocker.sock/containers/{id}/top'.format(id=data.id))
        #     text += json2html.convert(json = r.text) + "</div>"
        #     return html_template.format(page_title="Inspecting", page_content=text)

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()



