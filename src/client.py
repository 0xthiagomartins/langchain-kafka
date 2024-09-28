import json
import uuid
import threading
import logging
from kafka import KafkaConsumer, KafkaProducer


KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]
REQUEST_TOPIC = "runnable_requests"
RESPONSE_TOPIC = "runnable_responses"
GROUP_ID = "runnable_microservice_group"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RemoteRunnable:
    def __init__(self, timeout=30):
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda m: json.dumps(m).encode("utf-8"),
        )
        self.consumer = KafkaConsumer(
            RESPONSE_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=GROUP_ID,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        self.timeout = timeout
        self.responses = {}
        self.lock = threading.Lock()
        self.listener_thread = threading.Thread(
            target=self.listen_responses, daemon=True
        )
        self.listener_thread.start()

    def listen_responses(self):
        logger.info("Client is listening for responses...")
        for message in self.consumer:
            response = message.value
            request_id = response.get("id")
            if request_id:
                with self.lock:
                    self.responses[request_id] = response
                logger.info(f"Received response for id {request_id}")

    def send_request(self, method, params):
        request_id = str(uuid.uuid4())
        request = {
            "id": request_id,
            "method": method,
            "params": params,
        }
        with self.lock:
            self.responses[request_id] = None  # Initialize with None

        self.producer.send(REQUEST_TOPIC, request)
        self.producer.flush()
        logger.info(f"Sent request: {request}")

        # Wait for the response
        import time

        start_time = time.time()
        while True:
            with self.lock:
                response = self.responses.get(request_id)
                if response is not None:
                    del self.responses[request_id]  # Clean up
                    if "error" in response:
                        raise Exception(response["error"])
                    return response["result"]
            if time.time() - start_time > self.timeout:
                with self.lock:
                    del self.responses[request_id]
                raise TimeoutError(f"Request {request_id} timed out.")
            time.sleep(0.1)  # Sleep briefly to avoid busy waiting

    def invoke(self, data):
        return self.send_request("invoke", data)

    def batch(self, data_list):
        return self.send_request("batch", data_list)

    def stream(self, data):
        # For simplicity, assume stream returns a list
        return self.send_request("stream", data)

    def close(self):
        self.consumer.close()
        self.producer.close()
