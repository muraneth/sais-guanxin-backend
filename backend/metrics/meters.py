from prometheus_client.metrics import MetricWrapperBase, Histogram, Counter, Gauge
from service.config.config import config
from metrics.meter_key import MeterKey
from metrics.metrics import Metrics

meters: dict[Metrics, MetricWrapperBase] = {}
NAMESPACE = config.service.tenant_id.replace('-', '_')
SUBSYSTEM = config.app_id.replace('-', '_')

def record_count(meter_key: MeterKey, metric: Metrics, count: int) -> None:
    meter = meters.get(metric)
    if meter is None:
        meter = Counter(
            metric.name,
            metric.name,
            meter_key.__dict__.keys(),
            namespace=NAMESPACE,
            subsystem=SUBSYSTEM,
        )
        meters[metric] = meter
    meter.labels(*meter_key.__dict__.values()).inc(count)


def record_gauge(meter_key: MeterKey, metric: Metrics, value) -> None:
    meter = meters.get(metric)
    if meter is None:
        meter = Gauge(
            metric.name,
            metric.name,
            labelnames=meter_key.__dict__.keys(),
            namespace=NAMESPACE,
            subsystem=SUBSYSTEM,
        )
        meters[metric] = meter
    meter.labels(*meter_key.__dict__.values()).set(value)


def record_latency(meter_key: MeterKey, metric: Metrics, latency: float) -> None:
    meter = meters.get(metric)
    if meter is None:
        meter = Histogram(
            metric.name,
            metric.name,
            labelnames=meter_key.__dict__.keys(),
            namespace=NAMESPACE,
            subsystem=SUBSYSTEM,
        )
        meters[metric] = meter
    meter.labels(*meter_key.__dict__.values()).observe(latency)
