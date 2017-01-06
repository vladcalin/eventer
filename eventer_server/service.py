import os
import time
import json

from tornado.web import RedirectHandler

from pymicroservice.core.microservice import PyMicroService
from pymicroservice.core.decorators import public_method

from eventer_server.handlers.page_handlers import DashboardHandler, ProjectsHandler, PlotsHandler, EventsHandler, \
    StatusHandler, CreateProjectHandler, ViewProjectHandler, EditProjectHandler, CreateEventCategoryHandler, \
    ViewEventCategory, AboutHandler, DocsHandler, EventsStatisticsHandler, ImportDataHandler
from eventer_server.lib.query import QueryParser
from eventer_server.models import Project, FieldSpecs, EventCategory, Event, QueryHistory


class EventerService(PyMicroService):
    name = "eventer_server"
    host = "127.0.0.1"
    port = 8000

    api_token_header = "X-Api-Token"
    max_parallel_blocking_tasks = os.cpu_count()

    extra_handlers = [
        ("/projects/view/([a-f0-9]+)", ViewProjectHandler),
        ("/projects/view/([a-f0-9]+)/edit", EditProjectHandler),
        ("/projects/view/([a-f0-9]+)/create_category", CreateEventCategoryHandler),
        ("/projects/view/([a-f0-9]+)/categories/([a-f0-9]+)", ViewEventCategory),
        ("/dashboard", DashboardHandler),
        ("/projects", ProjectsHandler),
        ("/plots", PlotsHandler),
        ("/events", EventsHandler),
        ("/events/statistics", EventsStatisticsHandler),
        ("/events/import", ImportDataHandler),
        ("/status", StatusHandler),
        ("/projects/create", CreateProjectHandler),
        ("/about", AboutHandler),
        ("/docs", DocsHandler),
        ("/", RedirectHandler, {"url": "/about"}),
    ]

    root_directory = os.path.dirname(os.path.abspath(__file__))
    # create your templates
    template_dir = os.path.join(root_directory, "html", "templates")

    # setup your static files
    static_dirs = [
        (r"/static", os.path.join(root_directory, "html", "static")),
    ]

    # service registries
    service_registry_urls = []
    service_registry_ping_interval = 30

    def __init__(self, host, port, registry):
        super(EventerService, self).__init__()
        self.host = host
        self.port = port
        if registry:
            self.service_registry_urls = [registry]

    @public_method
    def create_project(self, name, description, owner):
        if not name or not description or not owner:
            raise ValueError("Bad parameters submitted")
        project = Project(name=name, description=description, owner=owner)
        project.save()
        return str(project.id)

    @public_method
    def update_project(self, project_id, name=None, description=None, owner=None):
        project = Project.objects.get(id=project_id)
        if name:
            project.name = name
        if description:
            project.description = description
        if owner:
            project.owner = owner
        project.save()
        return True

    @public_method
    def delete_project(self, project_id):
        project = Project.objects.get(id=project_id)
        project.delete()
        return True

    @public_method
    def create_category(self, name, description, project_id, fields):
        field_specs = [FieldSpecs(**fieldspec) for fieldspec in fields]

        if len(set([f["name"] for f in field_specs])) != len(field_specs):
            raise ValueError("Duplicate value name")

        event_category = EventCategory(name=name, description=description, project=project_id, fields=field_specs)
        event_category.save()
        return str(event_category.id)

    @public_method
    def submit_event(self, source, category, values):
        event = Event()
        event.source = source
        event.category = category
        event.set_values(**values)

        event.save()
        return str(event.id)

    @public_method
    def query_events(self, query):
        _start = time.time()
        parse_result = QueryParser().parse_query(query)
        events = Event.filter_by_query(parse_result)
        to_return = [{
                         "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                         "values": event.values,
                         "source": event.source
                     } for event in events]
        _duration = time.time() - _start

        QueryHistory.create_new("unknown", query, events, _duration)

        return to_return

    @public_method
    def query_events_for_field(self, query, field):
        items = self.query_events(query)
        return [{"timestamp": item["timestamp"], "value": item["values"][field]} for item in items]

        # Implement your token validation logic

    def api_token_is_valid(self, api_token):
        return True
