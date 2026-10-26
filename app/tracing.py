from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


provider = TracerProvider(
    resource=Resource.create({SERVICE_NAME: "docapi"})
)
provider.add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("docapi")