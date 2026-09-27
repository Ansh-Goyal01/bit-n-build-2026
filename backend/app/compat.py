"""Environment workarounds. Imported first from ``app/__init__.py``.

Windows Smart App Control can block grpc's unsigned native DLL (cygrpc). The
only path that reaches grpc in this codebase is chromadb's module-level import
of OpenTelemetry's OTLP-grpc span exporter — telemetry Adhikaar never enables
(no ``chroma_otel_collection_endpoint`` is ever configured). When grpc cannot
load, register a stub exporter module so chromadb still imports; on machines
where grpc loads fine this does nothing.
"""

import sys
import types

_OTLP_TRACE_MODULE = "opentelemetry.exporter.otlp.proto.grpc.trace_exporter"


def _stub_blocked_grpc_exporter() -> None:
    try:
        import grpc  # noqa: F401 — probe only
        return
    except ImportError:
        pass

    class OTLPSpanExporter:  # pragma: no cover — never instantiated
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError(
                "OTLP grpc exporter unavailable: grpc is blocked on this machine "
                "and Adhikaar does not use Chroma OpenTelemetry export."
            )

    stub = types.ModuleType(_OTLP_TRACE_MODULE)
    stub.OTLPSpanExporter = OTLPSpanExporter
    sys.modules[_OTLP_TRACE_MODULE] = stub


_stub_blocked_grpc_exporter()
