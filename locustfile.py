from locust import task, HttpUser

from httpx_user import HttpxUser
from request_user import RequestsUser


class RequestsTestUser(RequestsUser):
    @task
    def fetch_ably_time(self):
        self.client.get("/time")


# class HttpxTestUser(HttpxUser):
#     @task
#     def fetch_ably_time(self):
#         self.client.get("/time")
#

