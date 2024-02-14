from locust import task

from httpx_user import HttpxUser
from request_user import RequestUser


class TestUser(HttpxUser):
    @task
    def fetch_ably_time(self):
        self.client.get("/time")
