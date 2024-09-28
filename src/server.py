# run_microservice.py

import json
import logging
from langchain_core.runnables import Runnable
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]
REQUEST_TOPIC = "runnable_requests"
RESPONSE_TOPIC = "runnable_responses"
GROUP_ID = "runnable_microservice_group"


class RunnableMicroservice:
    def __init__(self):
        self.consumer = KafkaConsumer(
            REQUEST_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda m: json.dumps(m).encode("utf-8"),
        )
        self.runnables: dict[str, Runnable] = {}

    def runnable(self, runnable_id):
        runnable = self.runnables.get(runnable_id, None)
        if not runnable:
            raise Exception(f"Runnable {runnable_id} Not Found")
        return runnable

    def handle_message(self, runnable_id, message):
        runnable = self.runnable(runnable_id)
        try:
            request = message.value
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params")

            logger.info(f"Received request: {request}")

            if method == "invoke":
                result = self.runnable.invoke(params)
            elif method == "batch":
                result = self.runnable.batch(params)
            elif method == "stream":
                # For streaming, you might need to handle it differently
                # Here, we'll assume stream returns a list for simplicity
                result = list(self.runnable.stream(params))
            else:
                result = {"error": f"Unknown method {method}"}

            response = {
                "id": request_id,
                "result": result,
            }
        except Exception as e:
            logger.exception("Error processing message")
            response = {
                "id": request_id if "request_id" in locals() else None,
                "error": str(e),
            }

        self.producer.send(RESPONSE_TOPIC, response)
        self.producer.flush()
        logger.info(f"Sent response: {response}")

    def run(self):
        logger.info("Runnable Microservice is running...")
        for message in self.consumer:
            self.handle_message(message)


if __name__ == "__main__":
    service = RunnableMicroservice()
    service.run()
