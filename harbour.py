import json
import traceback
from json2html import *
import web
from docker import Client

BASE_URL = 'unix://var/run/docker.sock'

urls = (
    '/', 'containers',
    '/containers', 'containers',
    '/run', 'run',
    '/drone-harbour-run', 'DroneHarbourRun',
    '/action', 'action',
)

html_template = """
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
            text = """
            <div class="col-md-12">
                <table class="table">
                    <thead>
                        <tr>"""
            for col_head in col_heads:
                text += "<th>" + col_head + "</th>"
            text += "</tr></thead><tbody>"
            name = None
            for container in containers:
                text += "<tr>"
                for col_head in col_heads:
                    val = ""
                    if col_head == 'Branch':
                        if container is not None and 'Labels' in container and container[
                            'Labels'] is not None and 'branch' in container['Labels']:
                            val = container['Labels']['branch']
                    elif col_head == "Ports":
                        ports = container['Ports']
                        count = 0
                        for port in ports:
                            if count > 0:
                                val += "<br/>"
                            if 'PublicPort' in port:
                                val += str(port['PublicPort']) + " -> "
                            val += str(port['PrivatePort'])
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
                        val += """
                                <form action="/action"><select id="sel_id" name="action"  onchange="this.form.submit();">
                                <option value="-1">Select</option>
                                <option value="start">Start</option>
                                <option value="stop">Stop</option>
                                <option value="restart">Restart</option>
                                <option value="logs">Logs</option>
                                <option value="top">Top</option>
                                <option value="inspect">Inspect</option>
                                </select>
                                <input type="hidden" name="name" value="{name}">
                                <input type="hidden" name="id" value="{id}">
                                </form>
                            """.format(name=name, id=container['Id'])
                    else:
                        val = str(container[col_head])
                    text += "<td>" + val + "</td>"

                text += "</tr>"
            text += "</tbody></table></div>"
            return html_template.format(page_title="Containers", page_content=text)
        except Exception as e:
            return "Unknown Error: " + str(e)


def error_out(msg, e):
    traceback.print_exc()
    return web.internalerror(msg + str(e))


class DroneHarbourRun:
    def POST(self):
        # Create a UDS socket
        text = ""
        data = json.loads(web.data(), strict=False)
        print web.data()
        print data
        registry = data['registry']
        image = data['image']
        tag = data['tag']
        envs = data['env'] or []
        ports = data['ports'] or []
        port_bindings = data['port_bindings'] or {}
        links = data['links'] or {}
        publish_all_ports = data['publish_all_ports'] or False

        cli = Client(base_url='unix://var/run/docker.sock')

        cli.pull("{registry}:5000/{image}:latest".format(registry=registry, image=image))

        name = image

        try:
            cli.stop(name)
            text += "Image stopped"
        except:
            text += "Image not stopped"

        try:
            cli.remove_container(name)
            text += "Image removed"
        except:
            text += "Image not removed"


        env_list = []
        if envs is not None:
            for env in envs:
                env_list += ["-e", str(env)]

        labels = {'branch': data['build']['branch'],
                  'commit': data['build']['commit'],
                  'commit_message': data['build']['message']}

        full_image_name = "{registry}:5000/{image}".format(registry=registry, image=image)

        if tag is not None and not tag == "$$TAG":
            try:
                cli.pull(repository=full_image_name, tag=tag)
            except Exception as e:
                return error_out("Unable to pull image",e)
            full_image_name += ":{tag}".format(tag=tag)
        else:
            try:
                cli.pull(repository=full_image_name)
            except Exception as e:
                return error_out("Unable to pull image", e)
        try:
            new_container = cli.create_container(name=image, image=full_image_name,
                                                 hostname=name, ports=ports, environment=envs,
                                                 labels=labels,
                                                 host_config=cli.create_host_config(port_bindings=port_bindings,
                                                                                    links=links,
                                                                                    publish_all_ports=publish_all_ports))
            text = new_container['Id']
            try:
                cli.start(name)
                text += " started"
            except Exception as e:
                return error_out("Image not started", e)
        except Exception as e:
            return error_out("Container not created", e)
        return text


class action:
    def GET(self):
        # Create a UDS socket
        text = """
        <div class="col-md-12">
        """
        data = web.input()
        action = data.action
        if data.name is not None:
            name = data.name
        else:
            name = "Anonymous"

        id = data.id
        cli = Client(base_url='unix://var/run/docker.sock')
        if data.action == "start":
            try:
                cli.start(id)
                text += "Image started"
            except Exception as e:
                return error_out("Image not started", e)
        elif data.action == "stop":
            try:
                cli.stop(id)
                text += "Image stopped"
            except Exception as e:
                return error_out("Image not stopped", e)
        elif data.action == "restart":
            try:
                cli.restart(id)
                text += "Image restarted"
            except Exception as e:
                return error_out("Image not restarted", e)
        elif data.action == "logs":
            try:
                text += "<pre>" + cli.logs(id) + "</pre>"
            except Exception as e:
                return error_out("Unable to get image logs", e)

        return html_template.format(page_title="{action} for {name}".format(action=action, name=name),
                                    page_content=text)


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
