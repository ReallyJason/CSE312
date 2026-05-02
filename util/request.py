class Request:

    def __init__(self, request: bytes):
        # TODO: parse the bytes of the request and populate the following instance variables

        self.body = b""
        self.method = ""
        self.path = ""
        self.http_version = ""
        self.headers = {}
        self.cookies = {}

        head_end=request.find(b"\r\n\r\n")
        head_bytes=request[:head_end]
        self.body=request[head_end+4:]

        lines=head_bytes.decode().split("\r\n")

        texts=lines[0].split()
        self.method,self.path,self.http_version=texts[0],texts[1],texts[2]

        self.parsing_head(lines[1:])

    def parsing_head(self,l):
        for line in l:
            key,value=line.split(":",1)
            self.headers[key.strip()]=value.strip()

            if key.strip()=="Cookie":
                self.parsing_cook(value)

    def parsing_cook(self,cook):
        for cookie in cook.split(";"):
            cookie=cookie.strip()
            if "=" in cookie:
                key,value=cookie.split("=",1)
                self.cookies[key.strip()]=value.strip()


def test1():
    request = Request(b'GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: keep-alive\r\n\r\n')
    assert request.method == "GET"
    assert "Host" in request.headers
    assert request.headers["Host"] == "localhost:8080"  # note: The leading space in the header value must be removed
    assert request.body == b""  # There is no body for this request.
    # When parsing POST requests, the body must be in bytes, not str

    # This is the start of a simple way (ie. no external libraries) to test your code.
    # It's recommended that you complete this test and add others, including at least one
    # test using a POST request. Also, ensure that the types of all values are correct


if __name__ == '__main__':
    test1()
