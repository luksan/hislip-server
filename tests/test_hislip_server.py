
from hislip_server.hislip_server import HislipServer


def test_main():
    main([])

class MyHiSlipServer(HislipServer):
    def new_connection():
        pass

    def trigger_received(self):
        pass

    def data_reveiced():
        pass

    def send_response(self):
        pass

    def status_query(self):
        pass

    def send_srq(self):
        pass
