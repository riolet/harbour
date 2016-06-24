import datetime
import traceback
from json2html import *
import web
from docker import Client
import json

BASE_URL = 'unix://var/run/docker.sock'

urls = (
    '/', 'Containers',
    '/containers', 'Containers',
    '/run', 'run',
    '/create-container', 'CreateContainer',
    '/drone-harbour-run', 'DroneHarbourRun',
    '/action', 'Action',
    '/networks', 'Networks'
)

html_template = ""
render = web.template.render('templates/', base='layout')
render_plain = web.template.render('templates/')

class Containers:
    def GET(self):
        # Create a UDS socket
        options = {}
        data = web.input()
        if 'showall' in data:
            options['all'] = data.showall
            showall=True
        else:
            showall=False

        try:
            cli = Client(base_url='unix://var/run/docker.sock')
            containers = cli.containers(**options)
            col_heads = ["Names", "Image", "Command", "Status", "Created", "Ports", "Labels", "Manage"]
            return render.containers(title="Containers", col_heads=col_heads, containers=containers,
                                     render=render_plain, datetime=datetime,showall=showall)
        except Exception as e:
            traceback.print_exc()
            return "Unknown Error: " + str(e)


class CreateContainer:
    def GET(self):
        try:
            return render.createcontainerform(title="Create Container")
        except Exception as e:
            traceback.print_exc()
            return "Error: " + str(e)

    def POST(self):
        try:
            options = {}
            host_options = {}
            data = web.input(port_bindings_cont=[''],
                             port_bindings_host=[''],
                             environment_key=[''],
                             environment_value=[''])
            fields = ['image', 'name', 'command', 'environment', 'ports', 'port_bindings', 'publish_all_ports', 'network']
            data['environment'] = 'process'
            data['port_bindings'] = 'process'
            for field in fields:
                if field in data and data[field] is not None and len(data[field])>0 :
                    if field == 'ports':
                        options[field] = json.loads('['+data[field]+']')
                    elif field == 'environment':
                        environment_dic = {}
                        for i in range(len(data['environment_key'])):
                            environment_dic[str(data['environment_key'][i])] = str(data['environment_value'][i])
                        options[field] = environment_dic
                    elif field == 'port_bindings':
                        port_bindings_dic = {}
                        for i in range(len(data['port_bindings_cont'])):
                            port_bindings_dic[str(data['port_bindings_cont'][i])] = str(data['port_bindings_host'][i])
                        host_options[field] = port_bindings_dic
                    else:
                        options[field] = data[field]
            cli = Client(base_url='unix://var/run/docker.sock')

            options['host_config'] = cli.create_host_config(**host_options)
            print options

            result = cli.pull(repository=options['image'],stream=True)
            web.header('Content-type', 'text/html')
            web.header('Transfer-Encoding', 'chunked')
            yield render_plain.layout_top(title="Harbour - Creating container")
            for json_line in result:
                line = json.loads(json_line)
                if 'id' in line and 'status' in line:
                    yield line['id']+" "+line['status']+"\n"
            new_container = cli.create_container(**options)
            yield render_plain.notification_plain(message="Container {id} successfully created".format(id=new_container['Id']),
                                        status="success")
            yield render_plain.layout_bottom()
        except Exception as e:
            traceback.print_exc()
            yield "Error creating container: " + str(e)


class Networks:
    def GET(self):
        # Create a UDS socket
        text = ""
        try:
            cli = Client(base_url='unix://var/run/docker.sock')
            # Access /path/to/page from /tmp/Labelsprofilesvc.sock
            networks = cli.networks()
            col_heads = ["Id", "Name", "Driver", "Config", "Options", "Labels", "Manage"]
            return render.networks(title="Networks", col_heads=col_heads, networks=networks, render=render_plain)
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
        volumes = data['volumes'] or []
        volume_bindings = data['volume_bindings'] or []
        publish_all_ports = data['publish_all_ports'] or False

        cli = Client(base_url='unix://var/run/docker.sock')

        cli.pull("{registry}:5000/{image}:latest".format(registry=registry, image=image))

        if 'name' in data and data['name'] is not None:
            name = data['name']
        else:
            name = None

        # try:
        #     cli.create_network(name="network1", driver="bridge")
        # except:
        #     text += "Network not created"
        if name is not None:
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
            #-ToDo- Fix this
            options = {}
            if name in data and data['name'] is not None:
                options['name'] = data['name']
            new_container = cli.create_container(image=full_image_name,
                                                 hostname=name, ports=ports, environment=envs,
                                                 labels=labels, volumes=volumes,
                                                 host_config=cli.create_host_config(port_bindings=port_bindings,
                                                                                    links=links,
                                                                                    publish_all_ports=publish_all_ports,
                                                                                    binds=volume_bindings,
                                                                                    network_mode="network2"),**options)
            container_id = new_container['Id']
            text = container_id
            try:
                cli.start(container_id)
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

        if action in ["start", "stop", "restart", "remove"]:
            try:
                if data.action == "start":
                    cli.start(id)
                elif data.action == "stop":
                    cli.stop(id)
                elif data.action == "remove":
                    cli.remove_container(id)
                elif data.action == "restart":
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
