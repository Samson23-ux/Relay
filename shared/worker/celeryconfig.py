from kombu import Queue

task_acks_late = True
worker_concurrency = 100
timezone = "Africa/Lagos"
reject_on_worker_lost = True
worker_prefetch_multiplier = 1


queue_args = {
    "x-max-priority": 10,
    "x-dead-letter-routing-key": "dlq",
    "x-dead-letter-exchange": "relay.dlx",
}


task_queues = (
    Queue(name="relay.dlq", exchange="relay.dlx", routing_key="dlq"),
    Queue(
        name="relay.log",
        exchange="relay.direct",
        routing_key="log",
        queue_arguments=queue_args,
    ),
    Queue(
        name="relay.email",
        exchange="relay.direct",
        routing_key="email",
        queue_arguments=queue_args,
    ),
    Queue(
        name="relay.product",
        exchange="relay.direct",
        routing_key="product",
        queue_arguments=queue_args,
    ),
)

task_routes = {
    "shared.worker.tasks.log.save_log": {"queue": "relay.log"},
    "shared.worker.tasks.log.update_log": {"queue": "relay.log"},
    "apps.product_service.app.worker.tasks.product.get_product": {"queue": "relay.product"},
    "apps.user_service.app.worker.tasks.email.send_verification_email": {"queue": "relay.email"},
    "apps.product_service.app.worker.tasks.product.process_reservation": {"queue": "relay.product"},
    "apps.product_service.app.worker.tasks.product.restore_product_quantity": {"queue": "relay.product"},
}
