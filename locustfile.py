from locust import task

from httpx_user import HttpxUser


class HelloWorldUser(HttpxUser):
    @task
    def hello_world(self):
        self.client.get("/time")
