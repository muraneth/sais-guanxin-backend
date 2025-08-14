import traceback
import logging
from starlette.middleware.cors import CORSMiddleware  #引入 CORS中间件模块
import nest_asyncio
import uvicorn
from fastapi import FastAPI
from prometheus_client import start_http_server, make_asgi_app, CollectorRegistry, multiprocess
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager
from worker.process_task import process_pending_tasks
from metrics.meter_key import MeterKey
from metrics.meters import record_latency, record_count
from metrics.metrics import REQUEST_LATENCY, REQUEST_ERROR_COUNT
from service import health
from service.api import dialog, user_file, stream_search, view, question_recommend, report, message
from service.api.ai_doctor import patient_chat, doctor_console
from service.exceptions.auth_exception import AuthFailedException
from service.config.config import config
from util.execution_context import ExecutionContext
from util.logger import service_logger, custom_logging_config, access_logger
from util.timer import Timer

nest_asyncio.apply()

# 设置 apscheduler 日志级别
logging.getLogger('apscheduler').setLevel(logging.WARNING)

# 添加定时任务，背景调度器
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动定时任务调度器
    # 使用 max_instances=1 来限制任务的并发数，TODO：等资源充足后，去掉 max_instances 限制
    scheduler.add_job(process_pending_tasks, IntervalTrigger(seconds=2), max_instances=1)
    scheduler.start()
    service_logger.info("Scheduler started.")

    yield  # 生命周期中的主事件循环

    scheduler.shutdown()
    service_logger.info("Scheduler stopped.")


app = FastAPI(lifespan=lifespan)

# 设置跨域传参
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],  #设置允许的origins来源
    allow_credentials=True,
    allow_methods=["*"],  # 设置允许跨域的http方法，比如 get、post、put等。
    allow_headers=["*"])  #允许跨域的headers，可以用来鉴别来源等作用。


# 中间件增加监控
# 如果成功，只记录时延
# 如果失败，只记录次数
@app.middleware("http")
async def monitor_process_time(request: Request, call_next):
    timer = Timer()
    with ExecutionContext() as ctx:
        response: Response = await call_next(request)
        if response.status_code >= 400:
            record_count(MeterKey(request.url.path, request.method), REQUEST_ERROR_COUNT, 1)
            access_logger.error(f"failed to execute {request.method}: {request.url.path}, "
                                f"status_code: {response.status_code}, ctx: {ctx}")
        else:
            access_logger.info(f"execute {request.method}: {request.url.path} ok")
            record_latency(MeterKey(request.url.path, request.method),
                           REQUEST_LATENCY,
                           timer.duration())
        return response


@app.exception_handler(Exception)
async def common_exception_handler(request: Request, exc: Exception):
    record_count(MeterKey(request.url.path, request.method), REQUEST_ERROR_COUNT, 1)
    access_logger.error(f"failed to execute {request.method}: {request.url.path}, "
                        f"ctx: {ExecutionContext.current()}, stack: {traceback.format_exc()}")
    if isinstance(exc, AuthFailedException):
        return JSONResponse({"detail": str(exc)}, status_code=401)
    else:
        return JSONResponse({"detail": str(exc)}, status_code=500)

app.include_router(view.router)
app.include_router(dialog.router)
app.include_router(user_file.router)
app.include_router(health.router)
app.include_router(stream_search.router)
app.include_router(question_recommend.router)
app.include_router(report.router)
app.include_router(message.router)
app.include_router(patient_chat.router)
app.include_router(doctor_console.router)

if __name__ == '__main__':
    nest_asyncio.apply()
    # 创建一个新的 CollectorRegistry 对象。这是 Prometheus 的注册表，用于收集和管理指标。此对象允许我们在后续步骤中将多进程数据收集到同一个注册表中。
    registry = CollectorRegistry()
    # 配置 MultiProcessCollector 来支持 Prometheus 的多进程模式，并将 registry 作为参数传入
    # 多进程模式需要通过 MultiProcessCollector 将多个进程的指标汇总到同一个注册表中。
    multiprocess.MultiProcessCollector(registry)
    # 启动一个 HTTP 服务器，使 Prometheus 可以通过 http://<host>:2112/metrics 收集到的监控数据
    # 此服务器会在 2112 端口监听，并使用前面定义的 registry 来暴露指标。
    start_http_server(port=config.prometheus_port, registry=registry)
    uvicorn.run(app='main:app', host='0.0.0.0', port=8088, loop="asyncio", log_config=custom_logging_config, access_log=False, workers=8)
