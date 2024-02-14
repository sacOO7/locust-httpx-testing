from locust import task

from httpx_user import HttpxUser
from niquest_user import NiquestsUser
from request_user import RequestsUser

#
# class RequestsTestUser(RequestsUser):
#     @task
#     def fetch_ably_time(self):
#         self.client.get("/time")


# class HttpxTestUser(HttpxUser):
#     @task
#     def fetch_ably_time(self):
#         self.client.get("/time")
#
#
class NiquestsTestUser(NiquestsUser):
    @task
    def fetch_ably_time(self):
        self.client.get("/time")
