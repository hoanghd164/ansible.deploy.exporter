import argparse
import pika
import time
import json
import threading
import os

time_wait = 1

class RabbitMQClient:
    def __init__(self, config):
        self.config = config
        credentials = pika.PlainCredentials(config["username"], config["password"])
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(config["host"], config["port"], config["vhost"], credentials))
        self.channel = self.connection.channel()

    def send_message(self, queue_info, number_of_messages, immediate=False):
        credentials = pika.PlainCredentials(self.config["username"], self.config["password"])
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.config["host"], self.config["port"], self.config["vhost"], credentials))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue_info["name"])
        for i in range(number_of_messages):
            self.channel.basic_publish(exchange='', routing_key=queue_info["name"], body=queue_info["message"])
            print(" [x] Sent '{}' to queue '{}'".format(queue_info["message"], queue_info["name"]))
            if not immediate:
                time.sleep(time_wait)  # wait for time_wait seconds before sending the next message

    def receive_message(self, queue_name, time_wait):
        while True:
            method_frame, properties, body = self.channel.basic_get(queue=queue_name, auto_ack=False)
            if method_frame:
                print(" [x] Received %r" % body)
                self.channel.basic_ack(method_frame.delivery_tag)
                time.sleep(time_wait)  # wait for time_wait seconds after processing each message
            else:
                print('No message returned')
                break

    def close_connection(self):
        if self.connection is not None and self.connection.is_open:
            self.connection.close()

    def clear_queue(self, queue_name):
        print(f"Clearing queue {queue_name}")
        os.system(f"rabbitmqctl purge_queue {queue_name}")

def main():
    parser = argparse.ArgumentParser(description='This script sends and receives messages to/from RabbitMQ.')
    parser.add_argument('-r', action='store_true', help='Receive messages from RabbitMQ. Example: python3 rabbitmq.py -r, default time_wait is 5 second. To change the time_wait, use --time_wait option. Example: python3 rabbitmq.py -r --time_wait 5')
    parser.add_argument('-s', action='store_true', help='Send messages to RabbitMQ. Example: python3 rabbitmq.py -s, default number of messages is 1. To change the number of messages, use --set_queues option. Example: python3 rabbitmq.py -s --set_queues 10')
    parser.add_argument('--time_wait', type=int, default=5, help='Time to wait before consuming from the queue. example: python3 rabbitmq.py -r --time_wait 1')
    parser.add_argument('--set_queues', type=int, help='Set the number of messages in all queues, example: python3 rabbitmq.py -s --set_queues 1000')
    parser.add_argument('--set_nonqueue', action='store_true', help='Remove all messages from the queues')

    args = parser.parse_args()

    config = {
        "username": "hoanghd",
        "password": "Hoanghd164",
        "host": "localhost",
        "port": 5672,
        "vhost": "/",
        "queue": [
            {
                "name": "backup_infra_exporter_1990",
                "number_of_messages": 2000,
                "message": "Hello backup_infra_exporter_1990!"
            },
            {
                "name": "backup_infra_exporter_1994",
                "number_of_messages": 2000,
                "message": "Hello backup_infra_exporter_1994!"
            }
        ]
    }

    threads = []
    clients = []
    for queue_info in config["queue"]:
        client = RabbitMQClient(config)
        clients.append(client)
        if args.s:
            t = threading.Thread(target=client.send_message, args=(queue_info, args.set_queues if args.set_queues else queue_info["number_of_messages"], args.set_queues is not None))
            t.start()
            threads.append(t)
        if args.r:
            t = threading.Thread(target=client.receive_message, args=(queue_info["name"], args.time_wait))
            t.start()
            threads.append(t)
        if args.set_nonqueue:
            t = threading.Thread(target=client.clear_queue, args=(queue_info["name"],))
            t.start()
            threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()

    # Close connections
    for client in clients:
        client.close_connection()

if __name__ == "__main__":
    main()