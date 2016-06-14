import json
import traceback
from json2html import *
import web
from docker import Client

BASE_URL = 'unix://var/run/docker.sock'

urls = (
    '/', 'Containers',
    '/containers', 'Containers',
    '/run', 'run',
    '/drone-harbour-run', 'DroneHarbourRun',
    '/action', 'Action',
    '/networks', 'Networks'
)

html_template = ""
render = web.template.render('templates/', base='layout')


class Containers:
    def GET(self):
        # Create a UDS socket
        text = ""
        try:
            cli = Client(base_url='unix://var/run/docker.sock')
            # Access /path/to/page from /tmp/Labelsprofilesvc.sock
            containers = cli.containers()
            col_heads = ["Names", "Image", "Tag", "Status", "Created", "Ports", "Labels", "Manage"]
            return render.containers(title="Containers", col_heads=col_heads, containers=containers)
        except Exception as e:
            traceback.print_exc()
            return "Unknown Error: " + str(e)


class Networks:
    def GET(self):
        # Create a UDS socket
        text = ""
        try:
            cli = Client(base_url='unix://var/run/docker.sock')
            # Access /path/to/page from /tmp/Labelsprofilesvc.sock
            networks = cli.networks()
            col_heads = ["Id", "Name", "IPAM", "Labels", "Manage"]
            return render.networks(title="Containers", col_heads=col_heads, networks=networks, json2html=json2html)
        except Exception as e:
            traceback.print_exc()
            return "Unknown Error: " + str(e)

class HarbourInternalError(web.HTTPError):
    """500 Internal Server Error`."""
    message = "internal server error"

    def __init__(self, message=None):
        status = '500 Internal Server Error ' + message
        headers = {'Content-Type': 'text/html'}
        web.HTTPError.__init__(self, status, headers, message or self.message)


def error_out(msg, e):
    traceback.print_exc()
    return HarbourInternalError(message = msg + ". Docker API says: " + str(e))


class DroneHarbourRun:
    def POST(self):
        # Create a UDS socket
        text = ""
        data = json.loads(web.data(), strict=False)
        print web.data()
        print data
        registry = data['registry']
        image = data['image']
        tag = ('tag' in data and data['tag']) or None
        envs = data['env'] or []
        ports = data['ports'] or []
        port_bindings = data['port_bindings'] or {}
        #links = data['links'] or {}
        links = {}
        publish_all_ports = data['publish_all_ports'] or False

        cli = Client(base_url='unix://var/run/docker.sock')

        cli.pull("{registry}:5000/{image}:latest".format(registry=registry, image=image))

        name = image

        # try:
        #     cli.create_network(name="network1", driver="bridge")
        # except:
        #     text += "Network not created"

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
                                                                                    publish_all_ports=publish_all_ports,
                                                                                    network_mode="network2"))
            text = new_container['Id']
            try:
                cli.start(name)
                text += " started"
            except Exception as e:
                return error_out("Image not started", e)
        except Exception as e:
            return error_out("Container not created", e)
        return text


class Action:
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

        if action in ["start", "stop", "restart"]:
            try:
                if data.action == "start":
                    cli.start(id)
                elif data.action == "stop":
                    cli.stop(id)
                else:
                    cli.restart(id)
                return render.notification(title="Harbour - {action} for {name}".format(action=action, name=name),
                                           message="Image {name} {action}ed successfully".format(action=action, name=name),
                                           status="success")
            except Exception as e:
                return error_out("Image not started", e)
        elif action == "logs":
            try:
                return "<pre>" + cli.logs(id) + "</pre>"
            except Exception as e:
                return error_out("Unable to get image logs", e)
        elif action == "inspect":
            try:
                return "<pre>" + json2html.convert(json=json.dumps(cli.inspect_container(id))) + "</pre>"
            except Exception as e:
                return error_out("Unable to inspect container", e)
        elif action == "top":
            try:
                top = cli.top(id)
                processes = []
                col_heads = top['Titles']
                for process in top['Processes']:
                    topdic = {}
                    header_idx=0
                    for header in top['Titles']:
                        topdic[header]=process[header_idx]
                        header_idx += 1
                    processes += [topdic]
                return render.top(title="{action} for {name}".format(action=action, name=name),
                                  col_heads=col_heads,
                                  processes=processes)
            except Exception as e:
                return error_out("Unable to run top con container", e)
        return html_template.format(page_title="{action} for {name}".format(action=action, name=name),
                                    page_content=text)


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
