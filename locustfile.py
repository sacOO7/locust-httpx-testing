import httpx
from locust import task, HttpUser

from httpx_user import HttpxUser
from request_user import RequestsUser


class RequestsTestUser(RequestsUser):
    pool_connections = 100
    pool_maxsize = 100

    @task
    def fetch_ably_time(self):
        self.client.get("/time")


# class HttpxTestUser(HttpxUser):
#     limits = httpx.Limits(max_keepalive_connections=150, max_connections=150, keepalive_expiry=120)
#
#     @task
#     def fetch_ably_time(self):
#         self.client.get("/time")
